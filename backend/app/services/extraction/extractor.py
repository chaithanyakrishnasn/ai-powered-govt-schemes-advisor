from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import TYPE_CHECKING, cast

from loguru import logger

from app.core.config import settings
from app.services.extraction.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.extraction.schemas import ExtractionResult, SchemeContext
from app.services.extraction.validators import validate_rules

if TYPE_CHECKING:
    from app.services.llm.gemini import GeminiClient

# Tokens per scheme estimate for cost preflight
_AVG_INPUT_TOKENS = 800
_AVG_OUTPUT_TOKENS = 400
# Gemini 2.5 Flash pricing (USD per 1M tokens, as of 2025)
_COST_PER_1M_INPUT = 0.15
_COST_PER_1M_OUTPUT = 0.60


class _SlidingWindowRateLimiter:
    """Allows at most `max_calls` per `window_seconds`."""

    def __init__(self, max_calls: int, window_seconds: float = 60.0) -> None:
        self._max_calls = max_calls
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            # Drop timestamps outside the window
            while self._timestamps and now - self._timestamps[0] >= self._window:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._max_calls:
                wait = self._window - (now - self._timestamps[0])
                logger.debug(f"Rate limiter: waiting {wait:.1f}s")
                await asyncio.sleep(wait)
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._window:
                    self._timestamps.popleft()
            self._timestamps.append(time.monotonic())


class UsageStats:
    def __init__(self) -> None:
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.call_count: int = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.call_count += 1

    @property
    def estimated_cost_usd(self) -> float:
        return (
            self.total_input_tokens / 1_000_000 * _COST_PER_1M_INPUT
            + self.total_output_tokens / 1_000_000 * _COST_PER_1M_OUTPUT
        )

    def __str__(self) -> str:
        return (
            f"Calls: {self.call_count} | "
            f"Input tokens: {self.total_input_tokens:,} | "
            f"Output tokens: {self.total_output_tokens:,} | "
            f"Estimated cost: ${self.estimated_cost_usd:.4f}"
        )


def print_cost_preflight(n_schemes: int) -> None:
    total_input = n_schemes * _AVG_INPUT_TOKENS
    total_output = n_schemes * _AVG_OUTPUT_TOKENS
    cost = (
        total_input / 1_000_000 * _COST_PER_1M_INPUT
        + total_output / 1_000_000 * _COST_PER_1M_OUTPUT
    )
    print(
        f"\n── Cost preflight ──────────────────────────────────\n"
        f"  Schemes      : {n_schemes}\n"
        f"  Est. input   : {total_input:,} tokens ({_AVG_INPUT_TOKENS}/scheme)\n"
        f"  Est. output  : {total_output:,} tokens ({_AVG_OUTPUT_TOKENS}/scheme)\n"
        f"  Est. cost    : ${cost:.4f} USD (Gemini 2.0 Flash)\n"
        f"────────────────────────────────────────────────────\n"
    )


class EligibilityExtractor:
    def __init__(
        self,
        gemini_client: GeminiClient,
        model: str | None = None,
        rpm_limit: int = 10,
    ) -> None:
        self._client = gemini_client
        self._model = model or settings.GEMINI_MODEL_FAST
        self._rate_limiter = _SlidingWindowRateLimiter(max_calls=rpm_limit)
        self.usage = UsageStats()

    async def extract(
        self,
        eligibility_text: str,
        context: SchemeContext | None = None,
    ) -> ExtractionResult:
        ctx = context or SchemeContext()
        user_prompt = build_user_prompt(eligibility_text, ctx)

        await self._rate_limiter.acquire()

        try:
            result, completion = await self._client.instructor_client.chat.completions.create_with_completion(
                model=self._model,
                response_model=ExtractionResult,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                generation_config={"temperature": 0.0},
                max_retries=3,
            )
        except Exception as exc:
            logger.error(f"Extraction error for {ctx.scheme_name!r}: {exc}")
            return ExtractionResult(
                rules=[],
                overall_confidence=0.0,
                failed=True,
                failure_reason=str(exc),
                has_unstructured_remainder=bool(eligibility_text),
                unstructured_remainder=eligibility_text or None,
            )

        # Extract token usage from completion metadata
        input_tokens = 0
        output_tokens = 0
        try:
            meta = completion.usage_metadata
            if meta:
                input_tokens = getattr(meta, "prompt_token_count", 0) or 0
                output_tokens = getattr(meta, "candidates_token_count", 0) or 0
        except AttributeError:
            pass

        self.usage.add(input_tokens, output_tokens)
        logger.debug(
            f"Extracted {len(result.rules)} rules for {ctx.scheme_name!r} "
            f"| in={input_tokens} out={output_tokens} tokens"
        )

        # Run deterministic validators and log any drops
        validation_report = validate_rules(result.rules)
        if validation_report.has_errors:
            dropped = len(result.rules) - len(validation_report.passing_rules)
            logger.warning(
                f"{ctx.scheme_name!r}: dropped {dropped} rule(s) after validation. "
                f"Errors: {[e.message for e in validation_report.errors]}"
            )
            result = ExtractionResult(
                rules=validation_report.passing_rules,
                extraction_notes=result.extraction_notes,
                has_unstructured_remainder=result.has_unstructured_remainder,
                unstructured_remainder=result.unstructured_remainder,
                overall_confidence=result.overall_confidence,
            )
        for w in validation_report.warnings:
            logger.warning(f"{ctx.scheme_name!r} validation warning: {w.message}")

        return result

    async def extract_batch(
        self,
        items: list[tuple[str, SchemeContext]],
        concurrency: int = 5,
    ) -> list[ExtractionResult]:
        semaphore = asyncio.Semaphore(concurrency)

        async def _bounded(text: str, ctx: SchemeContext) -> ExtractionResult:
            async with semaphore:
                return await self.extract(text, ctx)

        tasks = [_bounded(text, ctx) for text, ctx in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final: list[ExtractionResult] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                # Defense-in-depth: extract() should have caught this already.
                ctx = items[i][1]
                logger.error(f"Unexpected batch exception for {ctx.scheme_name!r}: {r}")
                final.append(
                    ExtractionResult(
                        rules=[],
                        overall_confidence=0.0,
                        failed=True,
                        failure_reason=str(r),
                        has_unstructured_remainder=True,
                        unstructured_remainder=items[i][0],
                    )
                )
            else:
                final.append(cast(ExtractionResult, r))
        return final
