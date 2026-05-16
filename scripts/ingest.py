"""
Full ingestion pipeline: JSONL → Postgres.

Usage:
    # Dry run — no DB writes, see what would happen
    uv run python scripts/ingest.py \\
        --input data/raw/myscheme_karnataka/schemes.jsonl \\
        --limit 10 --dry-run

    # Real ingestion
    uv run python scripts/ingest.py \\
        --input data/raw/myscheme_karnataka/schemes.jsonl \\
        --rpm-limit 10 --concurrency 5

    # Multiple sources
    uv run python scripts/ingest.py \\
        --input data/raw/myscheme/schemes.jsonl data/raw/myscheme_karnataka/schemes.jsonl

    # Skip Gemini, re-map from cache only
    uv run python scripts/ingest.py \\
        --input data/raw/myscheme_karnataka/schemes.jsonl --skip-extraction
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow importing from backend/app when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.logging import setup_logging  # type: ignore[import-untyped]
from app.services.extraction.extractor import EligibilityExtractor
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.llm.gemini import GeminiClient


def _build_extractor(rpm_limit: int) -> EligibilityExtractor:
    return EligibilityExtractor(GeminiClient(), rpm_limit=rpm_limit)


def _print_report(report: object) -> None:
    from app.services.ingestion.pipeline import IngestionReport

    r: IngestionReport = report  # type: ignore[assignment]

    print("\n" + "═" * 56)
    print("  INGESTION REPORT")
    print("═" * 56)
    print(f"  Total schemes      : {r.total_schemes}")
    print(f"  Time elapsed       : {r.elapsed_seconds:.1f}s")
    print()
    print(f"  Cache hits         : {r.cache_hits}")
    print(f"  Cache misses       : {r.cache_misses}")
    hit_rate = r.cache_hits / max(1, r.cache_hits + r.cache_misses)
    print(f"  Cache hit rate     : {hit_rate:.0%}")
    print()
    print(f"  Extraction success : {r.extraction_success} (with rules or empty-input)")
    print(f"  Extraction empty   : {r.empty_eligibility_count} (no eligibility text in source)")
    print(f"  Extraction failed  : {r.extraction_failed} (API/parse errors — NOT cached)")
    print(f"  Extraction skipped : {r.extraction_skipped}")
    print()
    print(f"  DB inserted        : {r.db_inserted}")
    print(f"  DB updated         : {r.db_updated}")
    print(f"  DB failed          : {r.db_failed}")
    print()
    print(f"  Total rules        : {r.total_rules}")
    schemes_with_rules = max(1, r.total_schemes - len(r.schemes_zero_rules))
    print(f"  Avg rules/scheme   : {r.total_rules / schemes_with_rules:.1f}")
    print(f"  Schemes (0 rules)  : {len(r.schemes_zero_rules)}")

    if r.rules_by_type:
        print()
        print("  Top rule types:")
        for rt, count in sorted(r.rules_by_type.items(), key=lambda x: -x[1])[:10]:
            print(f"    {rt:30s}: {count}")

    if r.schemes_zero_rules:
        print()
        print("  ⚠  Schemes with 0 rules (need investigation):")
        for slug in r.schemes_zero_rules[:20]:
            print(f"    - {slug}")

    if r.failure_samples:
        print()
        print("  ✗ Extraction failures (sample):")
        for slug, reason in r.failure_samples[:10]:
            print(f"    {slug}: {reason[:100]}")

    if r.usage:
        print()
        print(f"  Token usage        : {r.usage}")

    if r.extraction_failed > 0:
        print()
        print(f"  ⚠⚠  {r.extraction_failed} extraction(s) FAILED (API/parse errors).")
        print("      Failed schemes were NOT cached. Fix the root cause, then re-run")
        print("      with --force-extract to retry them.")

    print("═" * 56 + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest schemes into Postgres.")
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="One or more JSONL file paths",
    )
    parser.add_argument("--limit", type=int, default=None, help="Process at most N schemes")
    parser.add_argument("--dry-run", action="store_true", help="No DB writes")
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip Gemini — only use cached extractions",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Ignore cache, re-extract everything",
    )
    parser.add_argument("--rpm-limit", type=int, default=10, help="Gemini RPM limit")
    parser.add_argument("--concurrency", type=int, default=5, help="Extraction concurrency")
    parser.add_argument("--resume", action="store_true", help="Skip already-completed schemes")
    args = parser.parse_args()

    setup_logging()

    repo_root = Path(__file__).parent.parent
    input_paths = [Path(p).resolve() for p in args.input]
    for p in input_paths:
        if not p.exists():
            print(f"[ERROR] Input file not found: {p}", file=sys.stderr)
            sys.exit(1)

    extractor = None if args.skip_extraction else _build_extractor(args.rpm_limit)

    pipeline = IngestionPipeline(
        extractor=extractor,
        cache_dir=repo_root / "data/cache/extractions",
    )

    report = await pipeline.run(
        [Path(p) for p in input_paths],
        limit=args.limit,
        dry_run=args.dry_run,
        skip_extraction=args.skip_extraction,
        force_extract=args.force_extract,
        rpm_limit=args.rpm_limit,
        concurrency=args.concurrency,
        resume=args.resume,
    )

    _print_report(report)

    if report.db_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
