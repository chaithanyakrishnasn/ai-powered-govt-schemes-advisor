"""
Post-ingestion verification dashboard.

Usage:
    uv run python scripts/verify_ingestion.py
    uv run python scripts/verify_ingestion.py --input data/raw/myscheme_karnataka/schemes.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import func, select, text  # type: ignore[import-untyped]

from app.core.logging import setup_logging  # type: ignore[import-untyped]
from app.db.models import EligibilityRule, Scheme
from app.db.session import async_session_maker


async def run_verification(input_paths: list[Path]) -> None:
    async with async_session_maker() as session:
        # ── Total schemes ──────────────────────────────────────────────
        total_schemes: int = (
            await session.scalar(select(func.count()).select_from(Scheme))
        ) or 0

        # By source
        source_counts_rows = (
            await session.execute(
                select(Scheme.source, func.count().label("n"))
                .group_by(Scheme.source)
                .order_by(text("n DESC"))
            )
        ).all()

        # By level
        level_counts_rows = (
            await session.execute(
                select(Scheme.level, func.count().label("n"))
                .group_by(Scheme.level)
                .order_by(text("n DESC"))
            )
        ).all()

        # By state (top 10)
        state_counts_rows = (
            await session.execute(
                select(Scheme.state, func.count().label("n"))
                .group_by(Scheme.state)
                .order_by(text("n DESC"))
                .limit(10)
            )
        ).all()

        # ── Total rules ────────────────────────────────────────────────
        total_rules: int = (
            await session.scalar(select(func.count()).select_from(EligibilityRule))
        ) or 0

        # By rule_type
        rule_type_rows = (
            await session.execute(
                select(EligibilityRule.rule_type, func.count().label("n"))
                .group_by(EligibilityRule.rule_type)
                .order_by(text("n DESC"))
            )
        ).all()

        # ── Rules-per-scheme distribution ──────────────────────────────
        rules_per_scheme_rows = (
            await session.execute(
                select(Scheme.slug, func.count(EligibilityRule.id).label("n"))
                .outerjoin(EligibilityRule, EligibilityRule.scheme_id == Scheme.id)
                .group_by(Scheme.slug)
            )
        ).all()

        rules_per_scheme = {row[0]: row[1] for row in rules_per_scheme_rows}
        dist: Counter[str] = Counter()
        for count in rules_per_scheme.values():
            if count == 0:
                dist["0 rules"] += 1
            elif count <= 2:
                dist["1-2 rules"] += 1
            elif count <= 5:
                dist["3-5 rules"] += 1
            else:
                dist["6+ rules"] += 1

        zero_rule_slugs = [slug for slug, n in rules_per_scheme.items() if n == 0]

        # ── Confidence stats ───────────────────────────────────────────
        conf_rows = (
            await session.execute(
                select(
                    EligibilityRule.rule_type,
                    func.avg(EligibilityRule.confidence).label("avg_conf"),
                    func.min(EligibilityRule.confidence).label("min_conf"),
                    func.max(EligibilityRule.confidence).label("max_conf"),
                )
                .group_by(EligibilityRule.rule_type)
                .order_by(text("avg_conf DESC"))
            )
        ).all()

        # ── Sample schemes ─────────────────────────────────────────────
        sample_schemes_rows = (
            await session.execute(select(Scheme).limit(5))
        ).scalars().all()

        sample_details: list[tuple[object, list[object]]] = []
        for scheme in sample_schemes_rows:
            rule_rows = (
                await session.execute(
                    select(EligibilityRule).where(
                        EligibilityRule.scheme_id == scheme.id  # type: ignore[union-attr]
                    )
                )
            ).scalars().all()
            sample_details.append((scheme, list(rule_rows)))

        # ── Mismatch check against source JSONL ────────────────────────
        mismatches: list[str] = []
        if input_paths:
            import json

            source_slugs: set[str] = set()
            for p in input_paths:
                if p.exists():
                    with p.open() as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                with contextlib.suppress(Exception):
                                    source_slugs.add(json.loads(line)["slug"])
            db_slugs = set(rules_per_scheme.keys())
            mismatches = sorted(source_slugs - db_slugs)

    # ── Print report ───────────────────────────────────────────────────────
    w = 56
    print("\n" + "═" * w)
    print("  INGESTION VERIFICATION REPORT")
    print("═" * w)
    print(f"\n  Total schemes in DB : {total_schemes}")
    print(f"  Total rules in DB   : {total_rules}")
    if total_schemes > 0:
        print(f"  Avg rules/scheme    : {total_rules / total_schemes:.1f}")

    print("\n  By source:")
    for row in source_counts_rows:
        print(f"    {row[0]:30s}: {row[1]}")

    print("\n  By level:")
    for row in level_counts_rows:
        print(f"    {row[0]:30s}: {row[1]}")

    print("\n  By state (top 10):")
    for row in state_counts_rows:
        state_label = str(row[0]) if row[0] else "(none/central)"
        print(f"    {state_label:30s}: {row[1]}")

    print("\n  Rules-per-scheme distribution:")
    for bucket in ["0 rules", "1-2 rules", "3-5 rules", "6+ rules"]:
        print(f"    {bucket:20s}: {dist[bucket]}")

    # Data quality alert — fires when majority of schemes have no rules
    if total_schemes > 0 and dist["0 rules"] / total_schemes > 0.5:
        print()
        print(f"  ⚠⚠⚠ DATA QUALITY ALERT: {dist['0 rules']} of {total_schemes} schemes have 0 eligibility rules.")
        print("  This is unusually high. Check:")
        print("    1. backend/.env contains a valid GEMINI_API_KEY")
        print("    2. Re-run ingestion: uv run python scripts/ingest.py --force-extract \\")
        print("           --input data/raw/myscheme/schemes.jsonl [...]")
        print("    3. Inspect data/cache/extractions/ for 'Extraction failed' notes")

    print("\n  Top 10 rule types:")
    for row in rule_type_rows[:10]:
        print(f"    {row[0]:30s}: {row[1]}")

    print("\n  Confidence by rule type:")
    for row in conf_rows:
        avg = float(row[1]) if row[1] else 0.0
        print(f"    {row[0]:30s}: avg={avg:.2f}")

    print("\n  Sample schemes:")
    for scheme, rules in sample_details:
        print(f"\n    ── {scheme.slug!r} ({len(rules)} rules)")  # type: ignore[union-attr]
        print(f"       {scheme.name}")  # type: ignore[union-attr]
        for rule in rules[:3]:
            print(f"       • {rule.rule_type} {rule.operator} {rule.value}")  # type: ignore[union-attr]
        if len(rules) > 3:
            print(f"       … and {len(rules) - 3} more")

    if zero_rule_slugs:
        print(f"\n  ⚠  Schemes with 0 rules ({len(zero_rule_slugs)}):")
        for slug in zero_rule_slugs[:20]:
            print(f"    - {slug}")
    else:
        print("\n  ✓  All schemes have at least 1 rule")

    if mismatches:
        print(f"\n  ✗ Mismatches — in JSONL but not in DB ({len(mismatches)}):")
        for slug in mismatches[:20]:
            print(f"    - {slug}")
    elif input_paths:
        print("\n  ✓  No mismatches — all source schemes are in DB")

    print("\n" + "═" * w + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify ingestion results.")
    parser.add_argument(
        "--input",
        nargs="*",
        default=[],
        help="Source JSONL files (for mismatch check)",
    )
    args = parser.parse_args()

    setup_logging()

    input_paths = [Path(p).resolve() for p in args.input]

    asyncio.run(run_verification(input_paths))


if __name__ == "__main__":
    main()
