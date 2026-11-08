from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    output_text: str
    tool_calls: list[dict[str, Any]] | None = None
    """None means "adapter doesn't know" -- the structural scorer will then
    fall back to a Langfuse trace lookup via `simulate.tool_calls`."""
    correlation_id: str
    raw: dict[str, Any] = Field(default_factory=dict)


class AgentAdapter(Protocol):
    """Implement this against your actual production/staging agent API.
    `http_adapter.HttpAgentAdapter` is a reference implementation; swap in
    your own if your agent isn't a simple JSON-over-HTTP endpoint."""

    async def invoke(self, *, input: dict[str, Any], correlation_id: str) -> AgentResult: ...
