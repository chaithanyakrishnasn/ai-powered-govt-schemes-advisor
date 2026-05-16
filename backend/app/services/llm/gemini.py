from __future__ import annotations

import asyncio
from functools import cached_property
from typing import cast

import google.genai as genai
import instructor

from app.core.config import settings


class GeminiClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.GEMINI_API_KEY

    @cached_property
    def _genai_client(self) -> genai.Client:
        return genai.Client(api_key=self._api_key)

    @cached_property
    def instructor_client(self) -> instructor.AsyncInstructor:
        return cast(
            instructor.AsyncInstructor,
            instructor.from_genai(
                self._genai_client,
                mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS,
                use_async=True,
            ),
        )

    @cached_property
    def raw_client(self) -> genai.Client:
        return self._genai_client

    async def embed_text(self, text: str) -> list[float]:
        resp = await self._genai_client.aio.models.embed_content(
            model=settings.GEMINI_MODEL_EMBED,
            contents=text,
        )
        if resp.embeddings is None or len(resp.embeddings) == 0:
            raise ValueError("Empty embedding response from Gemini")
        values = resp.embeddings[0].values
        if values is None:
            raise ValueError("Embedding values are None")
        return list(values)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        tasks = [self.embed_text(t) for t in texts]
        return await asyncio.gather(*tasks)

    async def generate_text(self, prompt: str, model: str | None = None) -> str:
        """Generate text using the raw Gemini client."""
        model_name = model or settings.GEMINI_MODEL_FAST
        response = await self._genai_client.aio.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        if not response.text:
            raise ValueError("Empty generation response from Gemini")
        return response.text
