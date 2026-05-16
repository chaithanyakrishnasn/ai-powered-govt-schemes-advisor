import asyncio
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.db.session import async_session_maker
from app.schemas.user_profile import UserProfile
from app.services.matching.service import MatchingService

console = Console()

# Corrected path
EVAL_SET_PATH = Path(__file__).parent.parent / "data" / "eval" / "retrieval_eval_20260504_135229.json"

def calculate_metrics(results, expected_slug):
    recall_at_5 = 0
    recall_at_10 = 0
    mrr = 0.0
    for i, res in enumerate(results):
        if res.slug == expected_slug:
            if i < 5:
                recall_at_5 = 1
            if i < 10:
                recall_at_10 = 1
            mrr = 1.0 / (i + 1)
            break
    return recall_at_5, recall_at_10, mrr


async def run_eval(alpha: float, eval_set: dict):
    total_recall_at_5 = 0
    total_recall_at_10 = 0
    total_mrr = 0.0
    
    profile = UserProfile(state="Karnataka")

    async with async_session_maker() as session:
        service = MatchingService(session)
        service.semantic_reranker.alpha = alpha

        for item in eval_set["queries"]:
            query = item["query"]
            expected_slug = item["expected"][0]

            results, _, _ = await service.match_profile(profile, query=query, max_results=100)
            
            r5, r10, mrr = calculate_metrics(results, expected_slug)
            total_recall_at_5 += r5
            total_recall_at_10 += r10
            total_mrr += mrr

    num_queries = len(eval_set["queries"])
    return (
        total_recall_at_5 / num_queries,
        total_recall_at_10 / num_queries,
        total_mrr / num_queries,
    )


async def main():
    """Evaluates the semantic re-ranking with different alpha values."""
    if not EVAL_SET_PATH.exists():
        console.print(f"[bold red]Error: Eval set not found at {EVAL_SET_PATH}[/bold red]")
        return

    with open(EVAL_SET_PATH, "r") as f:
        eval_set = json.load(f)

    alphas = [0.3, 0.5, 0.6, 0.7, 0.9]
    
    table = Table(title="Alpha Tuning Results")
    table.add_column("Alpha", style="cyan")
    table.add_column("Recall@5", style="green")
    table.add_column("Recall@10", style="green")
    table.add_column("MRR", style="green")

    for alpha in alphas:
        r5, r10, mrr = await run_eval(alpha, eval_set)
        table.add_row(f"{alpha:.1f}", f"{r5:.2f}", f"{r10:.2f}", f"{mrr:.2f}")

    console.print(table)


if __name__ == "__main__":
    asyncio.run(main())
