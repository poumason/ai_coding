"""Replay a golden set (Langfuse Dataset) against an agent build and score it.

Built on `dataset.run_experiment(...)`, Langfuse's own experiment runner: it
loops the dataset, calls our `task` per item, scores with our evaluators, and
creates a comparable Dataset Run in the Langfuse UI automatically -- we don't
hand-roll any trace/score plumbing here, just the task + evaluator functions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langfuse import get_client
from rich.console import Console
from rich.table import Table

from agent_eval.simulate.adapters.base import AgentAdapter
from agent_eval.simulate.judge import llm_judge_evaluator
from agent_eval.simulate.structural import average_score_evaluator, structural_evaluator
from agent_eval.simulate.tool_calls import ToolCallSource

console = Console()


@dataclass
class SimulationOutcome:
    aggregate_score: float | None
    passed: bool
    report_path: Path


def _make_task(adapter: AgentAdapter, tool_call_source: ToolCallSource):
    async def task(*, item: Any, **_: Any) -> dict[str, Any]:
        correlation_id = str(getattr(item, "id", None) or "")
        result = await adapter.invoke(input=item.input, correlation_id=correlation_id)
        tool_calls = await tool_call_source.get_tool_calls(result)
        return {"text": result.output_text, "tool_calls": tool_calls}

    return task


def _extract_aggregate(result: Any) -> float | None:
    """`average_score_evaluator` is registered as a run_evaluator, so Langfuse
    computes it once and attaches it to `result.run_evaluations` (verified
    against the installed langfuse==5.0.4 `ExperimentResult` class) -- read it
    back from there rather than recomputing it."""
    for evaluation in result.run_evaluations:
        if evaluation.name == "aggregate_score":
            return evaluation.value
    return None


def run_simulation(
    *,
    dataset_name: str,
    adapter: AgentAdapter,
    tool_call_source: ToolCallSource,
    run_name: str,
    fail_under: float | None = None,
    max_concurrency: int = 5,
    report_dir: Path,
) -> SimulationOutcome:
    client = get_client()
    dataset = client.get_dataset(dataset_name)

    result = dataset.run_experiment(
        name=run_name,
        description=f"agent-eval simulation run against golden set '{dataset_name}'",
        task=_make_task(adapter, tool_call_source),
        evaluators=[llm_judge_evaluator, structural_evaluator],
        run_evaluators=[average_score_evaluator],
        max_concurrency=max_concurrency,
    )
    client.flush()

    console.print(result.format())
    if result.experiment_url:
        console.print(f"View in Langfuse: {result.experiment_url}")

    aggregate = _extract_aggregate(result)
    _print_summary_table(result, aggregate)

    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{run_name.replace(' ', '_')}.json"
    _write_report(report_path, run_name=run_name, dataset_name=dataset_name, result=result, aggregate=aggregate)

    passed = aggregate is None or fail_under is None or aggregate >= fail_under
    return SimulationOutcome(aggregate_score=aggregate, passed=passed, report_path=report_path)


def _print_summary_table(result: Any, aggregate: float | None) -> None:
    table = Table(title="Simulation summary")
    table.add_column("metric")
    table.add_column("value")
    item_results = getattr(result, "item_results", None) or []
    table.add_row("items", str(len(item_results)))
    table.add_row("aggregate_score", f"{aggregate:.3f}" if aggregate is not None else "n/a")
    console.print(table)


def _write_report(path: Path, *, run_name: str, dataset_name: str, result: Any, aggregate: float | None) -> None:
    rows = [
        {
            "item_id": getattr(r.item, "id", None),
            "trace_id": r.trace_id,
            "scores": {e.name: e.value for e in r.evaluations},
            "comments": {e.name: e.comment for e in r.evaluations},
        }
        for r in result.item_results
    ]
    payload = {
        "run_name": run_name,
        "dataset_name": dataset_name,
        "experiment_url": result.experiment_url,
        "aggregate_score": aggregate,
        "items": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
