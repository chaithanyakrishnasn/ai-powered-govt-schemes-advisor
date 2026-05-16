#!/usr/bin/env python3
"""Scrape myScheme.gov.in and write normalized scheme JSON to JSONL.

Default output: data/raw/myscheme/schemes.jsonl
With --state Karnataka: data/raw/myscheme_karnataka/schemes.jsonl
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))  # scripts/ on path

from scrapers._common.jsonl_writer import JsonlWriter
from scrapers.myscheme.api import fetch_detail, iter_listing_items
from scrapers.myscheme.client import MySchemeClient
from scrapers.myscheme.normalizer import normalize

_REPO_ROOT = Path(__file__).parents[3]


async def _scrape_slug(
    client: MySchemeClient,
    slug: str,
    listing_fields: dict,  # type: ignore[type-arg]
    writer: JsonlWriter,
    sem: asyncio.Semaphore,
    counter: list[int],
    total: int,
    state_filter: str | None = None,
) -> None:
    async with sem:
        try:
            detail = await fetch_detail(client, slug)
            scheme = normalize(detail, listing_fields)
            # Multi-state schemes may normalize to a different state — skip them.
            if state_filter and (scheme.state != state_filter or scheme.level != "state"):
                return
            await writer.append(scheme)
            counter[0] += 1
            print(f"  [{counter[0]}/{total}] {slug}", flush=True)
        except Exception as exc:
            writer.mark_failed()
            print(f"  [ERROR] {slug}: {exc}", file=sys.stderr, flush=True)


async def run(args: argparse.Namespace) -> None:
    # Resolve output directory
    if args.out_dir is not None:
        out_dir = Path(args.out_dir)
    elif args.state:
        out_dir = _REPO_ROOT / "data" / "raw" / f"myscheme_{args.state.lower()}"
    else:
        out_dir = _REPO_ROOT / "data" / "raw" / "myscheme"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "schemes.jsonl"

    writer = JsonlWriter(out_file)
    done_slugs: set[str] = set()
    if args.resume:
        done_slugs = writer.load_done()
        print(f"Resume mode: {len(done_slugs)} already scraped")

    state_msg = f" state={args.state}" if args.state else ""
    print(f"Collecting up to {args.limit} scheme slugs{state_msg} …")
    if args.state:
        print("  (scanning all listing pages for matching beneficiaryState)")

    # Phase 1: collect listing items
    listing_by_slug: dict[str, dict] = {}  # type: ignore[type-arg]
    async with MySchemeClient(rate_limit=2.0, concurrency=1) as list_client:
        async for fields in iter_listing_items(list_client, args.limit, state_filter=args.state):
            slug = fields.get("slug", "")
            if slug:
                listing_by_slug[slug] = fields

    slugs_to_scrape = [s for s in listing_by_slug if s not in done_slugs]
    print(f"Fetching details for {len(slugs_to_scrape)} schemes …")

    # Phase 2: fetch details with configured concurrency
    sem = asyncio.Semaphore(args.concurrency)
    counter = [0]
    total = len(slugs_to_scrape)

    async with MySchemeClient(rate_limit=2.0, concurrency=args.concurrency) as detail_client:
        tasks = [
            _scrape_slug(
                detail_client,
                slug,
                listing_by_slug[slug],
                writer,
                sem,
                counter,
                total,
                state_filter=args.state,
            )
            for slug in slugs_to_scrape
        ]
        await asyncio.gather(*tasks)

    writer.write_index(extra={"source": "myscheme", "state_filter": args.state})
    print(f"\nDone. {writer.success_count} schemes written to {out_file}")
    if writer.failed_count:
        print(f"  {writer.failed_count} failed", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape myScheme.gov.in schemes")
    parser.add_argument(
        "--limit", type=int, default=300,
        help="Max schemes to collect (default 300; use a large number with --state to get all)",
    )
    parser.add_argument("--resume", action="store_true", help="Skip already-scraped slugs")
    parser.add_argument("--concurrency", type=int, default=4, help="Parallel detail fetches (default 4)")
    parser.add_argument(
        "--state", default=None,
        help="Filter by state name (e.g. Karnataka). Scans all listing pages client-side.",
    )
    parser.add_argument(
        "--out-dir", default=None,
        help="Output directory override (default: data/raw/myscheme/ or data/raw/myscheme_<state>/)",
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
