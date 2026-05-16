from __future__ import annotations

import asyncio
import math
import time
from collections import deque
from enum import StrEnum
from typing import TYPE_CHECKING

from google.genai import types
from loguru import logger

from app.core.config import settings

if TYPE_CHECKING:
    from app.services.llm.gemini import GeminiClient

_MAX_CHARS = 8000  # ~2048 tokens at 4 chars/token heuristic
_EMBEDDING_DIM = 768
# gemini-embedding-001: free tier generous; approximate cost reference
_COST_PER_1K_CHARS = 0.000025


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm < 1e-12:
        return vec
    return [v / norm for v in vec]


class EmbedTaskType(StrEnum):
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"


class _RpmLimiter:
    """Simple sliding-window RPM limiter for embedding calls."""

    def __init__(self, max_calls: int, window_seconds: float = 60.0) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._timestamps and now - self._timestamps[0] >= self._window:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._max:
                wait = self._window - (now - self._timestamps[0])
                await asyncio.sleep(wait)
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._window:
                    self._timestamps.popleft()
            self._timestamps.append(time.monotonic())


class GeminiEmbedder:
    def __init__(
        self,
        gemini_client: GeminiClient,
        model: str | None = None,
    ) -> None:
        self._client = gemini_client
        self._model = model or settings.GEMINI_MODEL_EMBED
        self.truncation_count: int = 0

    def _truncate(self, text: str) -> str:
        if len(text) > _MAX_CHARS:
            self.truncation_count += 1
            logger.warning(
                f"Truncating embedding input from {len(text)} to {_MAX_CHARS} chars "
                f"(total truncations so far: {self.truncation_count})"
            )
            return text[:_MAX_CHARS]
        return text

    async def embed_one(self, text: str, *, task_type: EmbedTaskType) -> list[float]:
        text = self._truncate(text)
        resp = await self._client.raw_client.aio.models.embed_content(
            model=self._model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type.value,
                output_dimensionality=_EMBEDDING_DIM,
            ),
        )
        if resp.embeddings is None or len(resp.embeddings) == 0:
            raise ValueError("Empty embedding response from Gemini")
        values = resp.embeddings[0].values
        if values is None:
            raise ValueError("Embedding values are None")
        return _l2_normalize(list(values))

    async def embed_batch(
        self,
        texts: list[str],
        *,
        task_type: EmbedTaskType,
        batch_size: int = 100,
        rpm_limit: int = 1500,
    ) -> list[list[float]]:
        """Embed a list of texts with concurrency and RPM control.

        Returns a list of 768-dim L2-normalized vectors. Failed embeddings become zero vectors.
        gemini-embedding-001 Matryoshka truncation to 768 dims returns unnormalized vectors;
        we normalize here so cosine similarity = dot product on stored vectors.
        """
        if not texts:
            return []

        semaphore = asyncio.Semaphore(batch_size)
        rate_limiter = _RpmLimiter(max_calls=rpm_limit)

        async def _one(idx: int, text: str) -> tuple[int, list[float]]:
            async with semaphore:
                await rate_limiter.acquire()
                embedding = await self.embed_one(text, task_type=task_type)
                return idx, embedding

        tasks = [_one(i, t) for i, t in enumerate(texts)]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        output: list[list[float]] = [[0.0] * _EMBEDDING_DIM] * len(texts)
        for r in raw_results:
            if isinstance(r, Exception):
                logger.error(f"Batch embedding error: {r}")
            else:
                idx, vec = r  # type: ignore[misc]
                output[idx] = vec

        return output

    @staticmethod
    def estimate_cost(texts: list[str]) -> float:
        total_chars = sum(min(len(t), _MAX_CHARS) for t in texts)
        return total_chars / 1000 * _COST_PER_1K_CHARS
