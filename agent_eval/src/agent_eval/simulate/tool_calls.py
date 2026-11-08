"""Where the structural scorer gets the *actual* tool calls an agent run made.

Two strategies, pick whichever matches your production system:

  DirectSource            -- trust `AgentResult.tool_calls` as returned by the
                              adapter itself (simplest, works if your agent API
                              already returns a tool-call trace).
  LangfuseTraceLookupSource -- your staging agent is itself Langfuse-instrumented;
                              it just needs to tag the trace it creates with the
                              `correlation_id` we pass through (e.g. as a Langfuse
                              tag on the trace). We then poll the Observations API
                              v2 for observations whose trace has that tag and
                              read the non-root observation names/inputs as the
                              tool-call sequence -- symmetric with how
                              golden_set.extract reconstructs *expected* tool
                              calls from production traces.

Wire whichever one applies in `simulate/run.py`.
"""

from __future__ import annotations

import json
import time
from typing import Any, Protocol

from langfuse import get_client

from agent_eval.simulate.adapters.base import AgentResult


class ToolCallSource(Protocol):
    async def get_tool_calls(self, result: AgentResult) -> list[dict[str, Any]]: ...


class DirectSource:
    async def get_tool_calls(self, result: AgentResult) -> list[dict[str, Any]]:
        return result.tool_calls or []


class LangfuseTraceLookupSource:
    """Polls Observations API v2 for observations whose trace is tagged with
    `result.correlation_id`.

    Requires the external agent to tag the trace it emits (in staging) with
    the same correlation id the adapter sent it -- confirm that contract with
    whoever owns the production agent before relying on this.
    """

    def __init__(self, *, poll_timeout: float = 20.0, poll_interval: float = 1.0):
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval

    async def get_tool_calls(self, result: AgentResult) -> list[dict[str, Any]]:
        client = get_client()
        tag_filter = json.dumps(
            [
                {
                    "type": "arrayOptions",
                    "column": "tags",
                    "operator": "any of",
                    "value": [result.correlation_id],
                }
            ]
        )
        deadline = time.monotonic() + self.poll_timeout
        while time.monotonic() < deadline:
            response = client.api.observations.get_many(
                fields="core,basic,io,trace_context",
                limit=50,
                filter=tag_filter,
            )
            rows = response.data
            if rows:
                non_root = [r for r in rows if not r.is_root_observation]
                non_root.sort(key=lambda r: r.start_time)
                return [{"name": r.name, "input": r.input or {}} for r in non_root]
            time.sleep(self.poll_interval)
        return []
