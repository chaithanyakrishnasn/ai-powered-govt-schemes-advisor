import asyncio
import json
from pathlib import Path
import typer
from app.db.models import Scheme
from app.db.session import async_session_maker
from app.schemas.user_profile import UserProfile
from app.services.matching.service import MatchingService
from app.services.matching.scheme_matcher import SchemeMatchResult, EligibilityStatus
from app.services.matching.semantic_reranker import SemanticReranker
from app.services.embedding.retriever import SemanticRetriever
from app.services.embedding.embedder import GeminiEmbedder
from app.services.llm.gemini import GeminiClient
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

# one .. to go from scripts to the root
PROFILE_DIR = Path(__file__).parent.parent / "data" / "test_profiles"

def pretty_print_results(results: list[SchemeMatchResult], schemes: dict[int, Scheme], limit: int = 20, show_semantic: bool = False):
    if not results:
        console.print("[yellow]No matching schemes found.[/yellow]")
        return

    table = Table(title="Scheme Matching Results")
    table.add_column("Rank", style="cyan")
    table.add_column("Status", style="magenta")
    if show_semantic:
        table.add_column("Rule Score", style="green")
        table.add_column("Semantic", style="yellow")
        table.add_column("Combined", style="bold green")
    else:
        table.add_column("Score", style="green")
    table.add_column("Name", style="bold blue")
    table.add_column("State/Level", style="yellow")
    table.add_column("Reason", style="dim")

    for i, result in enumerate(results[:limit]):
        scheme = schemes.get(result.scheme_id)
        if not scheme:
            continue

        status_color = {
            "eligible": "green",
            "likely_eligible": "yellow",
            "need_more_info": "cyan",
            "not_eligible": "red",
        }.get(result.status, "white")

        reason = ""
        if result.status == EligibilityStatus.NOT_ELIGIBLE and result.failed_rules:
            reason = f"Failed: {result.failed_rules[0].rule.rule_type} ({result.failed_rules[0].reason})"
        elif result.missing_fields:
            reason = f"Missing: {', '.join(result.missing_fields)}"

        if show_semantic:
            table.add_row(
                str(i + 1),
                f"[{status_color}]{result.status.value}[/]",
                f"{result.score:.2f}",
                f"{result.semantic_similarity:.2f}" if result.semantic_similarity is not None else "N/A",
                f"{result.combined_score:.2f}" if result.combined_score is not None else "N/A",
                result.name,
                f"{scheme.state}/{scheme.level}" if scheme.state else scheme.level,
                reason,
            )
        else:
            table.add_row(
                str(i + 1),
                f"[{status_color}]{result.status.value}[/]",
                f"{result.score:.2f}",
                result.name,
                f"{scheme.state}/{scheme.level}" if scheme.state else scheme.level,
                reason,
            )
    console.print(table)


async def main_async(
    profile: UserProfile,
    query: str | None = None,
    alpha: float = 0.6,
    include_ineligible: bool = False,
    max_results: int = 20,
):
    async with async_session_maker() as session:
        reranker = None
        if query:
            gemini_client = GeminiClient()
            embedder = GeminiEmbedder(gemini_client)
            retriever = SemanticRetriever(session, embedder)
            reranker = SemanticReranker(retriever, session, alpha=alpha)

        service = MatchingService(session, reranker=reranker)
        results, schemes = await service.match_profile(
            profile,
            query=query,
            include_ineligible=include_ineligible,
            max_results=max_results,
        )
        schemes_by_id = {s.id: s for s in schemes}
        pretty_print_results(results, schemes_by_id, max_results, show_semantic=bool(query))


@app.command()
def match(
    profile_file: Path = typer.Option(None, "--profile-file", help="Path to a user profile JSON file."),
    query: str = typer.Option(None, "--query", help="Natural language query for semantic re-ranking."),
    alpha: float = typer.Option(0.6, "--alpha", help="Weight for the rule-based score in combined ranking."),
    age: int = typer.Option(None),
    gender: str = typer.Option(None),
    state: str = typer.Option(None),
    is_farmer: bool = typer.Option(None),
    land_acres: float = typer.Option(None, "--land-acres"),
    annual_income: float = typer.Option(None, "--annual-income"),
    caste_category: str = typer.Option(None, "--caste-category"),
    include_ineligible: bool = typer.Option(False, "--include-ineligible"),
    max_results: int = typer.Option(20, "--max-results"),
):
    """Matches a user profile to government schemes."""
    if profile_file:
        if not profile_file.is_absolute():
            profile_file = PROFILE_DIR / profile_file.name
        with open(profile_file, "r") as f:
            profile_data = json.load(f)
            profile = UserProfile(**profile_data)
    else:
        profile = UserProfile(
            age=age,
            gender=gender,
            state=state,
            is_farmer=is_farmer,
            land_holding_acres=land_acres,
            annual_income=annual_income,
            caste_category=caste_category,
        )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_async(profile, query, alpha, include_ineligible, max_results))

if __name__ == "__main__":
    app()
