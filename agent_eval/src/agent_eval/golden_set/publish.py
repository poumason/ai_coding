"""Publish a human-reviewed candidates.jsonl into:

  1. a Langfuse Dataset (source of truth, used by `simulate.run` and
     comparable run-over-run in the Langfuse UI)
  2. an immutable, timestamped JSONL snapshot committed to this repo
     (data/golden_sets/<name>/<ISO-timestamp>.jsonl) for history/code review

Only rows with status == "approved" are published; `extract_candidates`
defaults every row to "candidate" so a reviewer has to explicitly mark rows
(or just delete the ones they don't want) before they ship.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from langfuse import get_client

from agent_eval.config import GOLDEN_SETS_DIR
from agent_eval.schema import CaseStatus, GoldenCase


def load_candidates(name: str) -> list[GoldenCase]:
    path = GOLDEN_SETS_DIR / name / "candidates.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"No candidates file at {path}. Run `extract-candidates --name {name}` first."
        )
    cases = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(GoldenCase.model_validate_json(line))
    return cases


def publish_golden_set(*, name: str) -> tuple[int, Path]:
    cases = load_candidates(name)
    approved = [c for c in cases if c.status == CaseStatus.approved]
    skipped = len(cases) - len(approved)
    if skipped:
        print(
            f"Skipping {skipped} case(s) not marked status=approved "
            f"(candidate/rejected) in candidates.jsonl."
        )
    if not approved:
        raise ValueError(
            "No approved cases to publish. Edit candidates.jsonl and set "
            'status to "approved" on the rows you want in the golden set.'
        )

    client = get_client()
    client.create_dataset(
        name=name,
        description=f"Golden set '{name}' curated from production Langfuse traces",
    )
    for case in approved:
        client.create_dataset_item(
            dataset_name=name,
            id=case.id,
            input=case.input,
            expected_output={
                **case.expected_output,
                "tool_calls": [tc.model_dump() for tc in case.expected_tool_calls],
            },
            metadata={**case.metadata, "tags": case.tags, "notes": case.notes},
            source_trace_id=case.source_trace_id,
            source_observation_id=case.source_observation_id,
        )
    client.flush()

    out_dir = GOLDEN_SETS_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = out_dir / f"{timestamp}.jsonl"
    with snapshot_path.open("w", encoding="utf-8") as f:
        for case in approved:
            f.write(case.model_dump_json() + "\n")

    return len(approved), snapshot_path
