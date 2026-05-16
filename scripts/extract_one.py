"""
CLI: extract eligibility rules for one scheme from a JSONL file.

Usage:
    uv run python scripts/extract_one.py --slug pm-kisan
    uv run python scripts/extract_one.py --input data/raw/myscheme/schemes.jsonl --slug pm-kisan
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Allow importing from backend/app when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.extraction.extractor import EligibilityExtractor, print_cost_preflight
from app.services.extraction.schemas import SchemeContext
from app.services.extraction.validators import validate_rules
from app.services.llm.gemini import GeminiClient


def _find_scheme(jsonl_path: Path, slug: str) -> dict | None:
    with jsonl_path.open() as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("slug") == slug:
                return obj
    return None


def _resolve_input(input_arg: str | None, slug: str) -> Path:
    root = Path(__file__).parent.parent
    if input_arg:
        p = Path(input_arg)
        return p if p.is_absolute() else Path.cwd() / p
    # Auto-detect: check both JSONL files
    for candidate in [
        root / "data/raw/myscheme_karnataka/schemes.jsonl",
        root / "data/raw/myscheme/schemes.jsonl",
    ]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate schemes.jsonl. Pass --input explicitly."
    )


async def main(slug: str, input_path: str | None) -> None:
    jsonl = _resolve_input(input_path, slug)
    scheme = _find_scheme(jsonl, slug)
    if scheme is None:
        print(f"[ERROR] Slug '{slug}' not found in {jsonl}", file=sys.stderr)
        sys.exit(1)

    eligibility_text = scheme.get("raw_eligibility_text") or ""
    ctx = SchemeContext(
        scheme_name=scheme.get("name", slug),
        ministry=scheme.get("ministry") or "",
        level=scheme.get("level", "central"),
        state=scheme.get("state"),
    )

    print(f"\n{'═' * 60}")
    print(f"  Scheme : {ctx.scheme_name}")
    print(f"  Slug   : {slug}")
    print(f"  Level  : {ctx.level}" + (f" ({ctx.state})" if ctx.state else ""))
    print(f"  Source : {jsonl.name}")
    print(f"{'═' * 60}")
    print("\nRaw eligibility text:")
    print("─" * 40)
    print(eligibility_text or "(none)")
    print("─" * 40)

    print_cost_preflight(1)

    extractor = EligibilityExtractor(GeminiClient(), rpm_limit=10)
    result = await extractor.extract(eligibility_text, ctx)

    print(f"\n{'─' * 60}")
    print(f"  Extracted {len(result.rules)} rule(s)  |  overall_confidence={result.overall_confidence:.2f}")
    print(f"{'─' * 60}")

    if result.rules:
        for i, rule in enumerate(result.rules, 1):
            v = rule.value
            if v.min is not None and v.max is not None:
                val_str = f"between({v.min}, {v.max})"
            elif v.in_ is not None:
                val_str = f"in {v.in_}"
            else:
                val_str = str(v.value)
            print(
                f"  [{i}] {rule.rule_type:20s} {rule.operator:10s} {val_str:25s} "
                f"group={rule.logic_group}  conf={rule.confidence:.2f}"
            )
            print(f"       {rule.description}")

    if result.extraction_notes:
        print(f"\nNotes: {result.extraction_notes}")

    if result.has_unstructured_remainder:
        print("\nUnstructured remainder:")
        print(f"  {result.unstructured_remainder}")

    # Run validators against the pre-validated rules (informational)
    report = validate_rules(result.rules)
    if report.warnings:
        print("\nValidation warnings:")
        for w in report.warnings:
            print(f"  ⚠  {w.message}")

    print(f"\nToken usage: {extractor.usage}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract eligibility rules for one scheme.")
    parser.add_argument("--slug", required=True, help="Scheme slug (e.g. pm-kisan, us)")
    parser.add_argument(
        "--input",
        default=None,
        help="Path to JSONL file (auto-detected if omitted)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.slug, args.input))
