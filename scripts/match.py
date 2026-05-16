import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.db.models import Scheme
from app.db.session import async_session_maker
from app.schemas.user_profile import UserProfile
from app.services.llm.gemini import GeminiClient
from app.services.matching.llm_reranker import LLMReranker, SchemeExplanation
from app.services.matching.scheme_matcher import EligibilityStatus, SchemeMatchResult
from app.services.matching.service import MatchingService

console = Console()

def pretty_print_results(
    results: list[SchemeMatchResult], 
    schemes: list[Scheme], 
    query: str | None = None
):
    table = Table(title=f"Scheme Matching Results{' for: ' + query if query else ''}")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Status", justify="left")
    table.add_column("Score", justify="right")
    if query:
        table.add_column("Sim", justify="right")
        table.add_column("Comb", justify="right")
    table.add_column("Scheme Name", style="white")
    table.add_column("Level/State", style="dim")
    table.add_column("Why/Why Not", style="italic")

    scheme_map = {s.id: s for s in schemes}

    for i, result in enumerate(results):
        scheme = scheme_map.get(result.scheme_id)
        if not scheme:
            continue
        
        status_color = {
            EligibilityStatus.ELIGIBLE: "green",
            EligibilityStatus.LIKELY_ELIGIBLE: "yellow",
            EligibilityStatus.NEED_MORE_INFO: "blue",
            EligibilityStatus.NOT_ELIGIBLE: "red",
        }.get(result.status, "white")

        reason = ""
        if result.status == EligibilityStatus.NOT_ELIGIBLE and result.failed_rules:
            failed_types = [r.rule.rule_type for r in result.failed_rules[:2]]
            reason = f"Fails: {', '.join(failed_types)}"
        elif result.status == EligibilityStatus.NEED_MORE_INFO and result.missing_fields:
            reason = f"Needs: {', '.join(result.missing_fields[:2])}"
        elif result.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE):
            pass_count = sum(1 for r in result.rule_evaluations if r.outcome == "pass")
            reason = f"Passed {pass_count} rules"

        if query:
            table.add_row(
                str(i + 1),
                f"[{status_color}]{result.status.value}[/]",
                f"{result.score:.2f}",
                f"{result.semantic_similarity or 0.0:.2f}",
                f"{result.combined_score or 0.0:.2f}",
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

def pretty_print_explanations(explanations: list[SchemeExplanation]):
    if not explanations:
        return
    console.print("\n[bold]Detailed Explanations:[/bold]")
    for exp in explanations[:5]:
        panel_content = f"""[bold]Why this matches you:[/bold] {exp.explanation}

[bold]Key benefits:[/bold]
- {"\n- ".join(exp.key_benefits)}

[bold]Next steps:[/bold]
- {"\n- ".join(exp.action_steps)}
        """
        if exp.custom_rule_assessment:
            panel_content += f"\n[bold]Custom criteria:[/bold] {exp.custom_rule_assessment}"
        
        console.print(Panel(
            panel_content,
            title=f"#{exp.final_rank} — {exp.name} ([cyan]{exp.slug}[/])",
            subtitle=f"Status: [bold]{exp.eligibility_verdict}[/] (confidence: {exp.confidence:.2f})",
            border_style="green" if exp.eligibility_verdict == "eligible" else "yellow",
            expand=False,
        ))

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-file", required=True)
    parser.add_argument("--query", help="Optional search query for Stage-2 re-ranking")
    parser.add_argument("--explain", action="store_true", help="Run Stage-3 LLM explanation")
    parser.add_argument("--language", default="en", help="Language for explanations")
    parser.add_argument("--max-results", type=int, default=20)
    args = parser.parse_args()

    # Load profile
    with open(args.profile_file) as f:
        profile_data = json.load(f)
    profile = UserProfile(**profile_data)

    async with async_session_maker() as session:
        llm_reranker = None
        if args.explain:
            gemini_client = GeminiClient()
            llm_reranker = LLMReranker(gemini_client, session)

        service = MatchingService(session, llm_reranker=llm_reranker)
        
        console.print(f"Matching profile: [cyan]{args.profile_file}[/]")
        if args.query:
            console.print(f"Query: [cyan]{args.query}[/]")
        
        start_time = asyncio.get_event_loop().time()
        results, candidates, explanations = await service.match_profile(
            profile, 
            query=args.query, 
            max_results=args.max_results,
            explain=args.explain,
            language=args.language
        )
        duration = asyncio.get_event_loop().time() - start_time

        pretty_print_results(results, candidates, query=args.query)
        
        if explanations:
            pretty_print_explanations(explanations)
            
            # Print stats
            input_tokens = sum(1 for _ in range(1000)) # Placeholder
            if llm_reranker:
                console.print(f"\n[dim][Stage-3: {llm_reranker.input_tokens} in / {llm_reranker.output_tokens} out / {llm_reranker.input_tokens + llm_reranker.output_tokens} total tokens][/dim]")

        console.print(f"\n[dim]Matched {len(results)} schemes in {duration:.2f}s[/dim]")

if __name__ == "__main__":
    asyncio.run(main())
