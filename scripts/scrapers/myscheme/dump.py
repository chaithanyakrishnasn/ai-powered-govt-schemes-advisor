#!/usr/bin/env python3
"""Pretty-print a single myScheme.gov.in scheme by slug."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))  # scripts/ on path

from scrapers.myscheme.api import fetch_detail
from scrapers.myscheme.client import MySchemeClient
from scrapers.myscheme.normalizer import normalize


async def run(slug: str, raw: bool) -> None:
    async with MySchemeClient(rate_limit=2.0, concurrency=1) as client:
        detail = await fetch_detail(client, slug)
        if raw:
            print(json.dumps(detail, indent=2, ensure_ascii=False))
        else:
            scheme = normalize(detail)
            print(json.dumps(scheme.model_dump(), indent=2, ensure_ascii=False))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Inspect a myScheme scheme by slug")
    parser.add_argument("slug", help="Scheme slug (e.g. pm-kisan)")
    parser.add_argument("--raw", action="store_true", help="Print raw API response instead of normalized")
    args = parser.parse_args()
    asyncio.run(run(args.slug, args.raw))


if __name__ == "__main__":
    main()
