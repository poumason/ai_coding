from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from agent_eval.config import GOLDEN_SETS_DIR, get_settings
from agent_eval.golden_set.extract import extract_candidates
from agent_eval.golden_set.publish import publish_golden_set
from agent_eval.simulate.adapters.http_adapter import HttpAgentAdapter
from agent_eval.simulate.run import run_simulation
from agent_eval.simulate.tool_calls import DirectSource, LangfuseTraceLookupSource

app = typer.Typer(help="Golden-set extraction and pre-release simulation for Langfuse-logged agents.")


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


@app.command("extract-candidates")
def extract_candidates_cmd(
    name: str = typer.Option(..., help="Golden set name, e.g. support-v1"),
    from_: str = typer.Option(..., "--from", help="Start date, YYYY-MM-DD"),
    to: str = typer.Option(..., help="End date, YYYY-MM-DD"),
    tag: list[str] = typer.Option([], help="Langfuse tag filter (repeatable)"),
    limit: Optional[int] = typer.Option(200, help="Max distinct conversations to pull"),
) -> None:
    """Pull production traces from Langfuse into a reviewable candidates.jsonl."""
    out_path = extract_candidates(
        name=name,
        from_time=_parse_date(from_),
        to_time=_parse_date(to),
        tags=tag or None,
        limit=limit,
    )
    typer.echo(f"Wrote candidates -> {out_path}")
    typer.echo("Review it, set status to \"approved\" on the rows you want, then run publish-golden-set.")


@app.command("publish-golden-set")
def publish_golden_set_cmd(
    name: str = typer.Option(..., help="Golden set name, matching extract-candidates --name"),
) -> None:
    """Push approved candidates to a Langfuse Dataset + a committed JSONL snapshot."""
    count, snapshot_path = publish_golden_set(name=name)
    typer.echo(f"Published {count} case(s) to Langfuse dataset '{name}' and {snapshot_path}")


@app.command("run-simulation")
def run_simulation_cmd(
    dataset: str = typer.Option(..., help="Golden set / Langfuse dataset name"),
    agent_endpoint: Optional[str] = typer.Option(None, help="Overrides AGENT_ENDPOINT from .env"),
    run_name: str = typer.Option(..., help="Label for this run, e.g. pr-123-new-mcp-tool"),
    fail_under: Optional[float] = typer.Option(
        None, help="Exit non-zero if the aggregate score is below this (0-1)"
    ),
    tool_calls_from: str = typer.Option(
        "direct", help="Where to read actual tool calls from: 'direct' (adapter response) or 'langfuse' (trace lookup by correlation id)"
    ),
    max_concurrency: int = typer.Option(5, help="Max concurrent agent invocations"),
) -> None:
    """Replay a golden set against an agent build and score it (LLM-judge + structural)."""
    settings = get_settings()
    endpoint = agent_endpoint or settings.agent_endpoint
    if not endpoint:
        typer.echo("No agent endpoint: pass --agent-endpoint or set AGENT_ENDPOINT in .env", err=True)
        raise typer.Exit(2)

    adapter = HttpAgentAdapter(endpoint=endpoint, api_key=settings.agent_api_key)
    tool_call_source = DirectSource() if tool_calls_from == "direct" else LangfuseTraceLookupSource()

    outcome = asyncio.run(
        run_simulation(
            dataset_name=dataset,
            adapter=adapter,
            tool_call_source=tool_call_source,
            run_name=run_name,
            fail_under=fail_under,
            max_concurrency=max_concurrency,
            report_dir=GOLDEN_SETS_DIR / dataset / "reports",
        )
    )

    typer.echo(f"Report written to {outcome.report_path}")
    if not outcome.passed:
        typer.echo(
            f"FAILED: aggregate score {outcome.aggregate_score:.3f} is below --fail-under {fail_under}",
            err=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    app()
