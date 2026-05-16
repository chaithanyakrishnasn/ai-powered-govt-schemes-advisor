"""
Utility to inspect and optionally delete all extraction cache files.

The cache schema version bump in cache.py (1.0 → 1.1) already makes old entries
unreachable, so deletion is optional. Use this script to reclaim disk space.

Usage:
    uv run python scripts/clear_extraction_cache.py          # dry-run, list files
    uv run python scripts/clear_extraction_cache.py --yes    # delete all cache files
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect / clear extraction cache.")
    parser.add_argument("--yes", action="store_true", help="Actually delete (default is dry-run)")
    parser.add_argument(
        "--cache-dir",
        default="data/cache/extractions",
        help="Cache directory (default: data/cache/extractions)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    cache_dir = Path(args.cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = repo_root / cache_dir

    if not cache_dir.exists():
        print(f"Cache directory not found: {cache_dir}")
        sys.exit(0)

    files = sorted(cache_dir.glob("*.json"))
    if not files:
        print("Cache is empty.")
        sys.exit(0)

    # Summarise contents
    total_rules = 0
    failed_count = 0
    for f in files:
        try:
            d = json.loads(f.read_text())
            total_rules += len(d.get("rules", []))
            notes = (d.get("extraction_notes") or "").lower()
            if d.get("failed") or "extraction failed" in notes:
                failed_count += 1
        except Exception:
            failed_count += 1

    print(f"Cache directory : {cache_dir}")
    print(f"Total files     : {len(files)}")
    print(f"Total rules     : {total_rules}")
    print(f"Failed entries  : {failed_count} (poisoned — no rules due to errors)")
    print()

    if args.yes:
        for f in files:
            f.unlink()
        print(f"Deleted {len(files)} cache file(s).")
    else:
        print("Dry-run mode — pass --yes to actually delete.")
        print(f"Would delete {len(files)} file(s) ({sum(f.stat().st_size for f in files) // 1024} KB).")


if __name__ == "__main__":
    main()
