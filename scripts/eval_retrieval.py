"""
Retrieval quality evaluation for Yojana AI semantic search.

Measures Recall@5, Recall@10, MRR against a hand-curated eval set.
Run from backend/:
    RUN_LIVE_RETRIEVAL=1 uv run python ../scripts/eval_retrieval.py

Eval set curation process (2026-05-04):
  - Queried DB for schemes by category/keyword
  - Selected 2-3 expected slugs per query from actual schemes in the DB
  - Covered: farmer, scholarship, women, disability, Karnataka, pension, startup, skill, housing
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@dataclass
class Query:
    text: str
    expected_slugs: list[str]
    description: str = ""


# Hand-curated eval set — slugs verified against actual DB content (2026-05-04)
# Coverage: farmer, scholarship, women, disability, Karnataka, pension, startup, training, housing
EVAL_SET: list[Query] = [
    Query(
        text="schemes for farmers agricultural subsidy",
        expected_slugs=["ascfiscmpa", "beds", "mmkssy-assam", "isfsr", "ky"],
        description="Farmer / agriculture schemes",
    ),
    Query(
        text="scholarship for SC ST students post matric",
        expected_slugs=["post-st", "post-dis", "csspremsobcsi", "aamgsiscs"],
        description="SC/ST scholarship schemes",
    ),
    Query(
        text="Karnataka women empowerment entrepreneurship",
        expected_slugs=["ssws", "cs", "kssk", "gls", "bys"],
        description="Karnataka women's schemes",
    ),
    Query(
        text="disability assistance medical treatment PwD",
        expected_slugs=["drfdamt", "mj-fapm", "post-dis", "nos-swd", "hepsn"],
        description="Disability / PwD assistance",
    ),
    Query(
        text="old age pension social welfare elderly",
        expected_slugs=["sssps", "nps-tsep", "ignoaps-sikkim", "oasas", "copkbocwwb"],
        description="Pension / old age",
    ),
    Query(
        text="startup loan entrepreneur business self employment",
        expected_slugs=["sui", "dlsk", "dlbe", "issscste", "mkuy", "rgsry"],
        description="Startup / business loan",
    ),
    Query(
        text="skill development training vocational employment",
        expected_slugs=["pmkvy-stt", "sdtk", "supk", "cbts", "fataps", "sdtk"],
        description="Skill training",
    ),
    Query(
        text="widow pension financial assistance",
        expected_slugs=["ignwpsmp", "ptwadwc", "wpwb", "issspwd", "apwesmc"],
        description="Widow assistance",
    ),
    Query(
        text="education loan scholarship Karnataka SC ST",
        expected_slugs=["aels", "pdos", "fatlclnbsmec", "issscste"],
        description="Education loan / Karnataka",
    ),
    Query(
        text="marriage assistance incentive scheme",
        expected_slugs=["mranmas1", "ifticmc", "iftsm", "iicmscc", "iscwr"],
        description="Marriage assistance",
    ),
    Query(
        text="construction workers welfare building BOCWWB",
        expected_slugs=[
            "kaabocwwb",
            "copkbocwwb",
            "dpaexgkbocwwb",
            "faexgkbocwwb",
            "amakcbkassistance-for-major-ailments-karmika-chikitsa-bhagya-kbocwwb",
        ],
        description="Construction worker welfare",
    ),
    Query(
        text="sericulture silk Karnataka business incentive",
        expected_slugs=["isfsr"],
        description="Karnataka sericulture scheme",
    ),
    Query(
        text="housing construction SC community shelter",
        expected_slugs=["dbjrlcwscs", "ps-west-bengal"],
        description="Housing / shelter",
    ),
    Query(
        text="research fellowship doctoral PhD science",
        expected_slugs=["pmfdr", "aktinf", "ef", "btlpdfp", "ddkfs"],
        description="Research fellowship",
    ),
]


@dataclass
class EvalResult:
    query: str
    expected: list[str]
    top5: list[str]
    top10: list[str]
    hit_at_5: bool = False
    hit_at_10: bool = False
    reciprocal_rank: float = 0.0
    description: str = ""


def _recall_at_k(results: list[str], expected: list[str]) -> bool:
    expected_set = set(expected)
    return any(s in expected_set for s in results)


def _reciprocal_rank(results: list[str], expected: list[str]) -> float:
    expected_set = set(expected)
    for i, s in enumerate(results, 1):
        if s in expected_set:
            return 1.0 / i
    return 0.0


def _print_table(eval_results: list[EvalResult]) -> None:
    print("\n" + "═" * 90)
    print("  RETRIEVAL EVAL RESULTS")
    print("═" * 90)
    header = f"{'Query':<48} {'R@5':<5} {'R@10':<5} {'MRR':<6} {'Top-3 results'}"
    print(header)
    print("─" * 90)
    for r in eval_results:
        hit5 = "✓" if r.hit_at_5 else "✗"
        hit10 = "✓" if r.hit_at_10 else "✗"
        top3 = ", ".join(r.top5[:3])
        q = r.query[:47]
        print(f"{q:<48} {hit5:<5} {hit10:<5} {r.reciprocal_rank:<6.2f} {top3}")
    print("─" * 90)

    n = len(eval_results)
    r5 = sum(1 for r in eval_results if r.hit_at_5) / n
    r10 = sum(1 for r in eval_results if r.hit_at_10) / n
    mrr = sum(r.reciprocal_rank for r in eval_results) / n
    print(f"\n  Recall@5  : {r5:.2f}  (target ≥ 0.70)")
    print(f"  Recall@10 : {r10:.2f}  (target ≥ 0.85)")
    print(f"  MRR       : {mrr:.2f}  (target ≥ 0.50)")

    passed = r5 >= 0.7 and r10 >= 0.85 and mrr >= 0.5
    print(f"\n  {'✓ All targets met' if passed else '✗ Some targets missed'}")
    print("═" * 90)

    # Failures
    failures = [r for r in eval_results if not r.hit_at_10]
    if failures:
        print("\n  Failed queries (not in top 10):")
        for r in failures:
            print(f"    Query     : {r.query!r}")
            print(f"    Expected  : {r.expected}")
            print(f"    Top-10    : {r.top10}")
            print()

    return r5, r10, mrr  # type: ignore[return-value]


async def run_eval() -> None:
    from app.core.logging import setup_logging
    from app.db.session import async_session_maker
    from app.services.embedding.embedder import GeminiEmbedder
    from app.services.embedding.retriever import SemanticRetriever
    from app.services.llm.gemini import GeminiClient

    setup_logging()
    embedder = GeminiEmbedder(GeminiClient())
    eval_results: list[EvalResult] = []

    print(f"\nRunning retrieval eval on {len(EVAL_SET)} queries…\n")
    start = time.monotonic()

    async with async_session_maker() as session:
        retriever = SemanticRetriever(session, embedder)
        for q in EVAL_SET:
            matches = await retriever.search(q.text, top_k=10, min_similarity=0.0)
            slugs = [m.slug for m in matches]

            result = EvalResult(
                query=q.text,
                expected=q.expected_slugs,
                top5=slugs[:5],
                top10=slugs[:10],
                description=q.description,
            )
            result.hit_at_5 = _recall_at_k(slugs[:5], q.expected_slugs)
            result.hit_at_10 = _recall_at_k(slugs[:10], q.expected_slugs)
            result.reciprocal_rank = _reciprocal_rank(slugs[:10], q.expected_slugs)
            eval_results.append(result)
            print(f"  [{'+' if result.hit_at_5 else '-'}] {q.description}: {q.text[:50]!r}")

    elapsed = time.monotonic() - start
    r5, r10, mrr = _print_table(eval_results)

    # Save JSON
    output_dir = Path(__file__).parent.parent / "data" / "eval"
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"retrieval_eval_{ts}.json"
    out_path.write_text(
        json.dumps(
            {
                "timestamp": ts,
                "metrics": {"recall_at_5": r5, "recall_at_10": r10, "mrr": mrr},
                "elapsed_seconds": elapsed,
                "queries": [
                    {
                        "query": r.query,
                        "description": r.description,
                        "expected": r.expected,
                        "top10": r.top10,
                        "hit_at_5": r.hit_at_5,
                        "hit_at_10": r.hit_at_10,
                        "reciprocal_rank": r.reciprocal_rank,
                    }
                    for r in eval_results
                ],
            },
            indent=2,
        )
    )
    print(f"\n  Results saved to: {out_path}")
    print(f"  Total time: {elapsed:.1f}s\n")

    # Exit non-zero if targets missed
    if r5 < 0.7 or r10 < 0.85 or mrr < 0.5:
        sys.exit(1)


if __name__ == "__main__":
    if not os.environ.get("RUN_LIVE_RETRIEVAL"):
        print(
            "Set RUN_LIVE_RETRIEVAL=1 to run. "
            "Requires populated embeddings in the DB."
        )
        sys.exit(0)
    asyncio.run(run_eval())
