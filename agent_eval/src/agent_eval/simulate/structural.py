from __future__ import annotations

from typing import Any

from langfuse import Evaluation


def _tool_calls_of(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return value.get("tool_calls") or []
    return []


def structural_evaluator(
    *, input: Any, output: Any, expected_output: Any, metadata: Any = None, **_: Any
) -> Evaluation:
    """Compares the ordered sequence of tool/skill/MCP calls the agent made
    against the golden case's expected sequence. Scores 1.0 for an exact
    name-sequence match, partial credit for a reordered/subset match, 0.0 for
    completely different tools, with a diff explaining the gap."""
    expected = _tool_calls_of(expected_output)
    actual = _tool_calls_of(output)

    expected_names = [tc.get("name") for tc in expected]
    actual_names = [tc.get("name") for tc in actual]

    if not expected_names and not actual_names:
        return Evaluation(name="tool_call_match", value=1.0, comment="no tool calls expected or made")

    if expected_names == actual_names:
        arg_mismatches = [
            e.get("name")
            for e, a in zip(expected, actual)
            if e.get("input") != a.get("input")
        ]
        if not arg_mismatches:
            return Evaluation(name="tool_call_match", value=1.0, comment="exact match")
        return Evaluation(
            name="tool_call_match",
            value=0.75,
            comment=f"right tools, right order, but args differ for: {arg_mismatches}",
        )

    expected_set, actual_set = set(expected_names), set(actual_names)
    overlap = expected_set & actual_set
    score = len(overlap) / len(expected_set) if expected_set else 0.0
    return Evaluation(
        name="tool_call_match",
        value=round(score * 0.5, 2),  # order/content wrong -> cap below 0.5
        comment=(
            f"expected {expected_names}, got {actual_names} "
            f"(missing: {sorted(expected_set - actual_set)}, "
            f"unexpected: {sorted(actual_set - expected_set)})"
        ),
    )


def average_score_evaluator(*, item_results: Any, **_: Any) -> Evaluation:
    """Run-level evaluator: averages every per-item Evaluation value across
    both scorers into one aggregate used for the CLI's --fail-under gate."""
    values = [
        e.value
        for r in item_results
        for e in r.evaluations
        if isinstance(e.value, (int, float))
    ]
    if not values:
        return Evaluation(name="aggregate_score", value=None, comment="no scored items")
    avg = sum(values) / len(values)
    return Evaluation(name="aggregate_score", value=avg, comment=f"{len(values)} scores averaged to {avg:.3f}")
