import asyncio
import time
import statistics
import typer
from rich.console import Console
from rich.table import Table
from app.db.session import async_session_maker
from app.schemas.user_profile import UserProfile
from app.services.matching.service import MatchingService
import json
from pathlib import Path

app = typer.Typer()
console = Console()

PROFILE_DIR = Path(__file__).parent.parent / "data" / "test_profiles"

async def run_benchmark(profile_path: str, iterations: int):
    with open(profile_path, "r") as f:
        profile_data = json.load(f)
    
    profile = UserProfile(**profile_data)
    
    latencies = []
    
    console.print(f"[bold blue]Benchmarking with profile: {profile_path}[/bold blue]")

    # Warm-up run
    async with async_session_maker() as session:
        service = MatchingService(session)
        await service.match_profile(profile)

    for i in range(iterations):
        start_time = time.monotonic()
        async with async_session_maker() as session:
            service = MatchingService(session)
            await service.match_profile(profile)
        
        latency = (time.monotonic() - start_time) * 1000  # in ms
        latencies.append(latency)
        if (i+1) % 10 == 0:
            console.print(f"Iteration {i+1}/{iterations}: {latency:.2f} ms")

    p50 = statistics.median(latencies)
    p95 = sorted(latencies)[int(iterations * 0.95)] if iterations > 20 else latencies[-1]
    p99 = sorted(latencies)[int(iterations * 0.99)] if iterations > 100 else latencies[-1]


    table = Table(title=f"Benchmark Results ({profile_path})")
    table.add_column("Metric", style="cyan")
    table.add_column("Value (ms)", style="green")
    table.add_row("Iterations", str(iterations))
    table.add_row("p50 (Median)", f"{p50:.2f}")
    table.add_row("p95", f"{p95:.2f}")
    table.add_row("p99", f"{p99:.2f}")
    
    console.print(table)


@app.command()
def bench(
    iterations: int = typer.Option(10, "--iterations", "-n"),
):
    """Benchmarks the matching service with sample profiles."""
    profiles = [
        PROFILE_DIR / "farmer_karnataka.json",
        PROFILE_DIR / "student_sc.json",
        PROFILE_DIR / "disabled_woman.json",
    ]
    
    loop = asyncio.get_event_loop()
    for profile_path in profiles:
        loop.run_until_complete(run_benchmark(str(profile_path), iterations))


if __name__ == "__main__":
    app()
