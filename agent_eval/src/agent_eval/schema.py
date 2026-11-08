from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ToolCall(BaseModel):
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class CaseStatus(str, Enum):
    candidate = "candidate"
    approved = "approved"
    rejected = "rejected"


class GoldenCase(BaseModel):
    """One row of a golden set.

    Produced by `golden_set.extract`, hand-edited by a human reviewer in
    candidates.jsonl, then turned into a Langfuse dataset item (and a git
    snapshot) by `golden_set.publish`.
    """

    id: str
    source_trace_id: str
    source_observation_id: str | None = None

    input: dict[str, Any]
    expected_output: dict[str, Any]
    expected_tool_calls: list[ToolCall] = Field(default_factory=list)

    tags: list[str] = Field(default_factory=list)
    status: CaseStatus = CaseStatus.candidate
    notes: str = ""

    extracted_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
