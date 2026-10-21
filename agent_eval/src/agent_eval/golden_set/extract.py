"""Pull production conversations out of Langfuse and reconstruct them into
candidate GoldenCase rows for human review.

Built on the Observations API v2 (`langfuse.api.observations.get_many`,
verified against installed `langfuse==5.0.4`) rather than the legacy
traces/observations read endpoints, which Langfuse is sunsetting on
2026-11-16. Each Langfuse *trace* is one conversation turn; we group its
observation rows (`ObservationV2`) by `trace_id` and reconstruct:

  - the root observation (`is_root_observation` true, or no
    `parent_observation_id`) gives us `input` / `expected_output`
  - every other observation in the trace becomes a candidate
    `expected_tool_call` (name = observation name, input = observation
    input), ordered by start time
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langfuse import get_client
from langfuse.api.commons.types.observation_v2 import ObservationV2

from agent_eval.config import GOLDEN_SETS_DIR
from agent_eval.schema import GoldenCase, ToolCall

# core: id, traceId, startTime, parentObservationId, type
# basic: name, isRootObservation, userId, sessionId
# io: input, output
# trace_context: tags, traceName
_FIELDS = "core,basic,io,trace_context"


def _tag_filter(tags: list[str]) -> str:
    return json.dumps(
        [{"type": "arrayOptions", "column": "tags", "operator": "any of", "value": tags}]
    )


def _fetch_observations(
    *,
    from_time: datetime,
    to_time: datetime,
    tags: list[str] | None,
    page_size: int = 200,
) -> list[ObservationV2]:
    client = get_client()
    rows: list[ObservationV2] = []
    cursor: str | None = None
    while True:
        response = client.api.observations.get_many(
            fields=_FIELDS,
            limit=page_size,
            cursor=cursor,
            from_start_time=from_time,
            to_start_time=to_time,
            filter=_tag_filter(tags) if tags else None,
        )
        rows.extend(response.data)
        cursor = response.meta.cursor
        if not cursor:
            break
    return rows


def _group_by_trace(rows: list[ObservationV2]) -> dict[str, list[ObservationV2]]:
    grouped: dict[str, list[ObservationV2]] = {}
    for row in rows:
        if row.trace_id:
            grouped.setdefault(row.trace_id, []).append(row)
    return grouped


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "content", "output", "message"):
            if key in value and isinstance(value[key], str):
                return value[key]
    return json.dumps(value, ensure_ascii=False, default=str)


def _trace_to_case(trace_id: str, observations: list[ObservationV2]) -> GoldenCase | None:
    observations_sorted = sorted(observations, key=lambda o: o.start_time)
    roots = [o for o in observations_sorted if o.is_root_observation or not o.parent_observation_id]
    root = roots[0] if roots else observations_sorted[0]
    children = [o for o in observations_sorted if o is not root]

    if root.input is None and root.output is None:
        return None

    tool_calls = [
        ToolCall(name=child.name or "unknown_tool", input=child.input or {})
        for child in children
    ]

    raw_input = root.input
    input_payload = (
        raw_input
        if isinstance(raw_input, dict) and "messages" in raw_input
        else {"messages": [{"role": "user", "content": _as_text(raw_input)}]}
    )

    return GoldenCase(
        id=str(uuid.uuid4()),
        source_trace_id=trace_id,
        source_observation_id=root.id,
        input=input_payload,
        expected_output={"text": _as_text(root.output)},
        expected_tool_calls=tool_calls,
        tags=list(root.tags or []),
        extracted_at=datetime.now(timezone.utc),
        metadata={"trace_id": trace_id, "root_observation_name": root.name},
    )


def extract_candidates(
    *,
    name: str,
    from_time: datetime,
    to_time: datetime,
    tags: list[str] | None = None,
    limit: int | None = None,
) -> Path:
    """Fetch observations in [from_time, to_time], reconstruct up to `limit`
    distinct traces into GoldenCase rows, and write them to
    data/golden_sets/<name>/candidates.jsonl for human review."""
    rows = _fetch_observations(from_time=from_time, to_time=to_time, tags=tags)
    grouped = _group_by_trace(rows)

    cases: list[GoldenCase] = []
    for trace_id, observations in grouped.items():
        case = _trace_to_case(trace_id, observations)
        if case is not None:
            cases.append(case)
        if limit is not None and len(cases) >= limit:
            break

    out_dir = GOLDEN_SETS_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "candidates.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(case.model_dump_json() + "\n")
    return out_path
