from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from app.schemas.raw_scheme import RawScheme
from app.services.extraction.extractor import EligibilityExtractor, UsageStats, print_cost_preflight
from app.services.extraction.schemas import ExtractionResult, SchemeContext
from app.services.ingestion.cache import ExtractionCache
from app.services.ingestion.dedup import Deduplicator
from app.services.ingestion.loader import load_jsonl_files
from app.services.ingestion.mapper import to_db_objects
from app.services.ingestion.upserter import SchemeUpserter

_PROGRESS_FILE = Path("data/cache/ingestion_progress.json")


@dataclass
class IngestionReport:
    total_schemes: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    # extraction_success: schemes that returned rules OR had empty eligibility text (both valid)
    extraction_success: int = 0
    # extraction_empty: subset of success where eligibility_text was blank/missing
    empty_eligibility_count: int = 0
    # extraction_failed: API/network/parse errors — NOT cached, need --force-extract to retry
    extraction_failed: int = 0
    extraction_skipped: int = 0
    db_inserted: int = 0
    db_updated: int = 0
    db_failed: int = 0
    total_rules: int = 0
    rules_by_type: dict[str, int] = field(default_factory=dict)
    schemes_zero_rules: list[str] = field(default_factory=list)
    # Extraction failure samples (slug, reason) — capped at 20
    failure_samples: list[tuple[str, str]] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    usage: UsageStats | None = None


def _load_progress(resume: bool) -> set[str]:
    if not resume or not _PROGRESS_FILE.exists():
        return set()
    try:
        data = json.loads(_PROGRESS_FILE.read_text())
        slugs: set[str] = set(data.get("completed_slugs", []))
        logger.info(f"Resume: found {len(slugs)} already-completed scheme(s)")
        return slugs
    except Exception as e:
        logger.warning(f"Could not read progress file: {e}")
        return set()


def _save_progress(completed: set[str]) -> None:
    _PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PROGRESS_FILE.write_text(json.dumps({"completed_slugs": sorted(completed)}, indent=2))


def _make_context(raw: RawScheme) -> SchemeContext:
    return SchemeContext(
        scheme_name=raw.name,
        ministry=raw.ministry or "",
        level=raw.level,
        state=raw.state,
    )


def _empty_extraction(raw: RawScheme, reason: str) -> ExtractionResult:
    return ExtractionResult(
        rules=[],
        extraction_notes=f"Skipped extraction: {reason}",
        has_unstructured_remainder=bool(raw.raw_eligibility_text),
        unstructured_remainder=raw.raw_eligibility_text,
        overall_confidence=0.0,
    )


def _is_failed(extraction: ExtractionResult) -> bool:
    """True if the extraction represents an API/network/parse error (not a valid LLM response)."""
    if extraction.failed:
        return True
    # Fallback: detect poisoned cache entries written before the failed=True field existed
    notes = (extraction.extraction_notes or "").lower()
    return "extraction failed" in notes


class IngestionPipeline:
    def __init__(
        self,
        extractor: EligibilityExtractor | None = None,
        cache_dir: Path = Path("data/cache/extractions"),
    ) -> None:
        self._extractor = extractor
        self._cache = ExtractionCache(cache_dir)

    async def run(
        self,
        input_paths: list[Path],
        *,
        limit: int | None = None,
        dry_run: bool = False,
        skip_extraction: bool = False,
        force_extract: bool = False,
        rpm_limit: int = 10,
        concurrency: int = 5,
        resume: bool = False,
    ) -> IngestionReport:
        start = time.monotonic()
        report = IngestionReport()

        # ── 0. Preflight: API key required unless skip_extraction is set ─────
        if not skip_extraction:
            from app.core.config import settings

            if not (settings.GEMINI_API_KEY or "").strip():
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. "
                    "Add it to backend/.env and re-run. "
                    "Use --skip-extraction to bypass if you only want to re-map cached results."
                )

        # ── 1. Load ──────────────────────────────────────────────────────────
        schemes, load_stats = load_jsonl_files(input_paths)
        if not schemes:
            logger.warning("No schemes loaded — nothing to do.")
            report.elapsed_seconds = time.monotonic() - start
            return report

        # ── 2. Dedup ─────────────────────────────────────────────────────────
        deduplicator = Deduplicator()
        schemes, dup_report = deduplicator.filter(schemes)
        Deduplicator.print_report(dup_report)

        # ── 3. Apply limit + resume ───────────────────────────────────────────
        if limit is not None:
            schemes = schemes[:limit]

        completed_slugs = _load_progress(resume)
        pending = [s for s in schemes if s.slug not in completed_slugs]
        skipped_resume = len(schemes) - len(pending)
        if skipped_resume:
            logger.info(f"Skipping {skipped_resume} already-completed scheme(s) (resume mode)")
        report.extraction_skipped = skipped_resume
        report.total_schemes = len(schemes)

        if not pending:
            logger.info("All schemes already completed.")
            report.elapsed_seconds = time.monotonic() - start
            return report

        # ── 4. Cost preflight ─────────────────────────────────────────────────
        if not skip_extraction:
            n_to_extract = len(pending) if force_extract else sum(
                1 for s in pending
                if self._cache.get(s.raw_eligibility_text or "", s.name, s.ministry or "") is None
            )
            if n_to_extract > 0:
                print_cost_preflight(n_to_extract)
            else:
                print("\n── All schemes in cache — no Gemini calls needed ──\n")

        # ── 5. Extraction phase ───────────────────────────────────────────────
        extractions: dict[str, ExtractionResult] = {}

        if skip_extraction:
            for s in pending:
                cached = self._cache.get(s.raw_eligibility_text or "", s.name, s.ministry or "")
                if cached is not None:
                    extractions[s.slug] = cached
                    report.cache_hits += 1
                else:
                    extractions[s.slug] = _empty_extraction(s, "skip_extraction=True, not in cache")
                    report.extraction_skipped += 1
        else:
            extractions = await self._run_extraction(
                pending, force_extract, concurrency, report
            )

        # ── 6. DB phase ───────────────────────────────────────────────────────
        if dry_run:
            print("\n── Dry run — no DB writes ───────────────────────────────────")
            for s in pending:
                ex = extractions.get(s.slug, _empty_extraction(s, "extraction missing"))
                _scheme, rules = to_db_objects(s, ex)
                status = "FAILED" if _is_failed(ex) else f"{len(rules)} rules"
                print(f"  Would upsert: {s.slug!r} ({status})")
            print("────────────────────────────────────────────────────────────\n")
        else:
            await self._run_upserts(pending, extractions, completed_slugs, report)

        # ── 7. Collate report ─────────────────────────────────────────────────
        report.cache_hits = self._cache.stats.hits
        report.cache_misses = self._cache.stats.misses
        if self._extractor:
            report.usage = self._extractor.usage
        report.elapsed_seconds = time.monotonic() - start
        return report

    async def _run_extraction(
        self,
        pending: list[RawScheme],
        force_extract: bool,
        concurrency: int,
        report: IngestionReport,
    ) -> dict[str, ExtractionResult]:
        """Extract eligibility rules for all pending schemes.

        Three outcome categories per scheme:
          failure     — API/network/parse error; result has failed=True.
                        Do NOT cache. Increment extraction_failed.
          empty-input — eligibility_text was blank/missing; nothing to extract.
                        Cache normally. Increment extraction_success + empty_eligibility_count.
          success     — LLM returned a valid response (rules may still be empty if
                        the text contained no structured criteria).
                        Cache normally. Increment extraction_success.
        """
        results: dict[str, ExtractionResult] = {}

        # Separate cache hits from items that need Gemini calls
        to_extract: list[tuple[str, SchemeContext, str]] = []  # (text, ctx, slug)
        for s in pending:
            elig = s.raw_eligibility_text or ""
            if not force_extract:
                cached = self._cache.get(elig, s.name, s.ministry or "")
                if cached is not None:
                    results[s.slug] = cached
                    continue
            to_extract.append((elig, _make_context(s), s.slug))

        if not self._extractor:
            logger.error("No extractor configured — cannot call Gemini.")
            for _, _, slug in to_extract:
                raw_s = next(s for s in pending if s.slug == slug)
                report.extraction_failed += 1
                if len(report.failure_samples) < 20:
                    report.failure_samples.append((slug, "no extractor configured"))
                results[slug] = _empty_extraction(raw_s, "no extractor configured")
            return results

        if to_extract:
            logger.info(f"Extracting {len(to_extract)} scheme(s) via Gemini…")
            items = [(text, ctx) for text, ctx, _ in to_extract]
            batch_results = await self._extractor.extract_batch(items, concurrency=concurrency)

            for (text, ctx, slug), extraction in zip(to_extract, batch_results, strict=True):
                raw_s = next(s for s in pending if s.slug == slug)

                if _is_failed(extraction):
                    # ── Failure: API/network/parse error ─────────────────────
                    reason = extraction.failure_reason or extraction.extraction_notes or "unknown"
                    logger.warning(f"Extraction failed for {slug!r}: {reason[:120]}")
                    report.extraction_failed += 1
                    if len(report.failure_samples) < 20:
                        report.failure_samples.append((slug, reason[:120]))
                    # Do NOT cache — a retry with a working API key should re-extract
                elif not text:
                    # ── Empty input: nothing to extract ───────────────────────
                    self._cache.set(text, ctx.scheme_name, ctx.ministry, extraction)
                    report.extraction_success += 1
                    report.empty_eligibility_count += 1
                else:
                    # ── Success: valid LLM response (rules may be empty) ──────
                    self._cache.set(text, ctx.scheme_name, ctx.ministry, extraction)
                    report.extraction_success += 1

                results[slug] = extraction

            logger.info(
                f"Extraction complete: {len(results)}/{len(pending)} | "
                f"success={report.extraction_success} failed={report.extraction_failed}"
            )

        return results

    async def _run_upserts(
        self,
        pending: list[RawScheme],
        extractions: dict[str, ExtractionResult],
        completed_slugs: set[str],
        report: IngestionReport,
    ) -> None:
        from app.db.session import async_session_maker

        total = len(pending)
        for i, raw in enumerate(pending):
            extraction = extractions.get(slug := raw.slug)
            if extraction is None:
                extraction = _empty_extraction(raw, "extraction result missing")

            scheme_obj, rules = to_db_objects(raw, extraction)

            # Accumulate rule stats
            report.total_rules += len(rules)
            for rule in rules:
                rt = str(rule.rule_type)
                report.rules_by_type[rt] = report.rules_by_type.get(rt, 0) + 1
            if not rules and raw.raw_eligibility_text:
                report.schemes_zero_rules.append(slug)

            async with async_session_maker() as session:
                upserter = SchemeUpserter(session)
                result = await upserter.upsert(scheme_obj, rules)

            if result.action == "inserted":
                report.db_inserted += 1
            elif result.action == "updated":
                report.db_updated += 1
            else:
                report.db_failed += 1

            completed_slugs.add(slug)
            _save_progress(completed_slugs)

            if (i + 1) % 10 == 0 or (i + 1) == total:
                logger.info(
                    f"DB progress: {i + 1}/{total} | "
                    f"inserted={report.db_inserted} updated={report.db_updated} "
                    f"failed={report.db_failed}"
                )
