#!/usr/bin/env python3
"""Inspect any RawScheme JSONL file by slug."""

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))  # scripts/ on path

from scrapers.schema import RawScheme


def find_by_slug(file_path: Path, slug: str) -> dict | None:  # type: ignore[type-arg]
    with file_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            with contextlib.suppress(json.JSONDecodeError):
                data = json.loads(line)
                if data.get("slug") == slug:
                    return data  # type: ignore[no-any-return]
    return None


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect a RawScheme JSONL file by slug",
        epilog="Example: dump.py data/raw/myscheme_karnataka/schemes.jsonl us",
    )
    parser.add_argument("file", help="Path to the JSONL file")
    parser.add_argument("slug", help="Scheme slug to look up")
    parser.add_argument("--raw", action="store_true", help="Print raw JSON without RawScheme validation")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    data = find_by_slug(file_path, args.slug)
    if data is None:
        print(f"Slug '{args.slug}' not found in {file_path}", file=sys.stderr)
        sys.exit(1)

    if args.raw:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        scheme = RawScheme.model_validate(data)
        print(json.dumps(scheme.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
