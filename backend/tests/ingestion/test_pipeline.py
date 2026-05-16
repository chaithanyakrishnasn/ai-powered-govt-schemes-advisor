"""Unit tests for IngestionPipeline (mocked extractor, no DB or network)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.extraction.schemas import ExtractionResult
from app.services.ingestion.pipeline import IngestionPipeline


def _write_jsonl(path: Path, schemes: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(s) for s in schemes))


def _minimal_scheme(
    slug: str = "test-slug",
    eligibility: str | None = "Age between 18 and 60",
) -> dict:
    return {
        "slug": slug,
        "name": f"Test Scheme {slug}",
        "level": "central",
        "source_url": "https://example.com",
        "source": "myscheme",
        "raw_eligibility_text": eligibility,
    }


def _mock_extractor(results: list[ExtractionResult]) -> MagicMock:
    extractor = MagicMock()
    extractor.extract_batch = AsyncMock(return_value=results)
    extractor.usage = None
    return extractor


@pytest.mark.asyncio
async def test_pipeline_preflight_missing_api_key(tmp_path: Path) -> None:
    """Pipeline raises RuntimeError when GEMINI_API_KEY is absent and skip_extraction=False."""
    jsonl = tmp_path / "schemes.jsonl"
    _write_jsonl(jsonl, [_minimal_scheme()])

    pipeline = IngestionPipeline(
        extractor=_mock_extractor([]), cache_dir=tmp_path / "cache"
    )

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = ""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            await pipeline.run([jsonl], dry_run=True, skip_extraction=False)


@pytest.mark.asyncio
async def test_pipeline_does_not_cache_failures(tmp_path: Path) -> None:
    """Failed extractions are NOT written to cache and increment extraction_failed."""
    jsonl = tmp_path / "schemes.jsonl"
    _write_jsonl(jsonl, [_minimal_scheme()])
    cache_dir = tmp_path / "cache"

    failed_result = ExtractionResult(
        rules=[], overall_confidence=0.0, failed=True, failure_reason="API timeout"
    )
    pipeline = IngestionPipeline(
        extractor=_mock_extractor([failed_result]), cache_dir=cache_dir
    )

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "fake-key"
        report = await pipeline.run([jsonl], dry_run=True, skip_extraction=False)

    assert report.extraction_failed == 1
    assert report.extraction_success == 0
    assert list(cache_dir.glob("*.json")) == []


@pytest.mark.asyncio
async def test_pipeline_distinguishes_empty_vs_failed(tmp_path: Path) -> None:
    """Empty eligibility text is cached as success; failed extraction is not cached."""
    jsonl = tmp_path / "schemes.jsonl"
    _write_jsonl(jsonl, [
        _minimal_scheme(slug="empty-scheme", eligibility=None),
        _minimal_scheme(slug="fail-scheme", eligibility="Age between 18 and 60"),
    ])
    cache_dir = tmp_path / "cache"

    success_result = ExtractionResult(rules=[], overall_confidence=0.5)
    failed_result = ExtractionResult(
        rules=[], overall_confidence=0.0, failed=True, failure_reason="API error"
    )
    pipeline = IngestionPipeline(
        extractor=_mock_extractor([success_result, failed_result]),
        cache_dir=cache_dir,
    )

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "fake-key"
        report = await pipeline.run([jsonl], dry_run=True, skip_extraction=False)

    assert report.extraction_success == 1
    assert report.empty_eligibility_count == 1
    assert report.extraction_failed == 1
    # Only the empty-input scheme is cached; the failed one is not
    assert len(list(cache_dir.glob("*.json"))) == 1
