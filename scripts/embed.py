"""
Embedding pipeline for Yojana AI — Phase 2 Step 2.3.

Subcommands:
    refresh-search-text  Re-compute search_text for all schemes (no Gemini calls)
    populate             Embed all schemes missing embeddings
    populate --force     Re-embed everything
    search <query>       Semantic search (requires populated embeddings)

Usage (run from backend/):
    uv run python ../scripts/embed.py refresh-search-text
    uv run python ../scripts/embed.py populate
    uv run python ../scripts/embed.py populate --force
    uv run python ../scripts/embed.py search "schemes for small farmers in Karnataka" --top-k 10
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.logging import setup_logging  # type: ignore[import-untyped]


async def cmd_refresh_search_text(args: argparse.Namespace) -> None:
    from app.db.session import async_session_maker
    from app.services.embedding.embedder import GeminiEmbedder
    from app.services.embedding.populator import EmbeddingPopulator
    from app.services.llm.gemini import GeminiClient

    embedder = GeminiEmbedder(GeminiClient())
    populator = EmbeddingPopulator(async_session_maker, embedder)
    stats = await populator.refresh_search_text()

    print("\n── search_text refresh ──────────────────────────────")
    print(f"  Updated       : {stats['updated']} schemes")
    print(f"  Avg length    : {stats['avg_before']:.0f} → {stats['avg_after']:.0f} chars")
    print(f"  Time elapsed  : {stats['elapsed_seconds']:.1f}s")
    print("────────────────────────────────────────────────────\n")


async def cmd_populate(args: argparse.Namespace) -> None:
    from app.db.session import async_session_maker
    from app.services.embedding.embedder import GeminiEmbedder
    from app.services.embedding.populator import EmbeddingPopulator
    from app.services.llm.gemini import GeminiClient

    embedder = GeminiEmbedder(GeminiClient())
    populator = EmbeddingPopulator(async_session_maker, embedder)
    report = await populator.populate(force=args.force)

    print("\n── Embedding report ─────────────────────────────────")
    print(f"  Schemes       : {report.scheme_count}")
    print(f"  Embedded      : {report.total_embedded}")
    print(f"  Skipped       : {report.skipped}")
    print(f"  Failed        : {report.failed}")
    print(f"  Truncated     : {report.truncated}")
    print(f"  Est. cost     : ${report.estimated_cost_usd:.4f} USD")
    print(f"  Time elapsed  : {report.elapsed_seconds:.1f}s")
    print("────────────────────────────────────────────────────\n")

    if report.failed > 0:
        sys.exit(1)


async def cmd_search(args: argparse.Namespace) -> None:
    from app.db.session import async_session_maker
    from app.services.embedding.embedder import GeminiEmbedder
    from app.services.embedding.retriever import SchemeFilters, SemanticRetriever
    from app.services.llm.gemini import GeminiClient

    embedder = GeminiEmbedder(GeminiClient())
    async with async_session_maker() as session:
        retriever = SemanticRetriever(session, embedder)
        filters = SchemeFilters(
            level=args.level if hasattr(args, "level") and args.level else None,
            state=args.state if hasattr(args, "state") and args.state else None,
        )
        results = await retriever.search(
            args.query,
            top_k=args.top_k,
            min_similarity=args.min_similarity,
            filters=filters,
        )

    if not results:
        print(f"No results for: {args.query!r} (min_similarity={args.min_similarity})")
        return

    print(f"\nTop {len(results)} results for: {args.query!r}\n")
    print(f"{'#':<3} {'Score':<7} {'Name':<55} {'Level':<8} {'State'}")
    print("─" * 100)
    for i, m in enumerate(results, 1):
        cats = ", ".join(m.categories[:2]) if m.categories else ""
        state_str = (m.state or "all")[:20]
        name_str = m.name[:54]
        print(f"{i:<3} {m.similarity:<7.3f} {name_str:<55} {m.level:<8} {state_str}")
        if cats:
            print(f"    {'':7} {cats}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Embedding pipeline for Yojana AI.")
    subs = parser.add_subparsers(dest="command", required=True)

    # refresh-search-text
    subs.add_parser("refresh-search-text", help="Re-compute search_text for all schemes (no Gemini)")

    # populate
    pop = subs.add_parser("populate", help="Embed schemes into pgvector")
    pop.add_argument("--force", action="store_true", help="Re-embed even if already populated")
    pop.add_argument("--batch-size", type=int, default=100)

    # search
    search = subs.add_parser("search", help="Semantic search")
    search.add_argument("query", nargs="+", help="Query text")
    search.add_argument("--top-k", type=int, default=10)
    search.add_argument("--min-similarity", type=float, default=0.3)
    search.add_argument("--level", choices=["central", "state"], default=None)
    search.add_argument("--state", default=None)

    args = parser.parse_args()
    # Join multi-word query
    if args.command == "search":
        args.query = " ".join(args.query)

    setup_logging()

    if args.command == "refresh-search-text":
        asyncio.run(cmd_refresh_search_text(args))
    elif args.command == "populate":
        asyncio.run(cmd_populate(args))
    elif args.command == "search":
        asyncio.run(cmd_search(args))


if __name__ == "__main__":
    main()
