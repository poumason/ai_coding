"""Reference AgentAdapter that POSTs to a JSON HTTP endpoint.

Request:  {"input": <golden case input>, "correlation_id": "<uuid>"}
Response: {"output": "<text>", "tool_calls": [{"name": str, "input": dict}, ...]}
          `tool_calls` is optional -- omit it if your API doesn't return it and
          rely on the Langfuse trace-lookup strategy in `simulate.tool_calls`
          instead (pass `correlation_id` through to your agent as a tag/
          metadata field so the lookup can find the matching trace).

This almost certainly needs adjusting to match your real agent's actual
request/response shape and auth scheme -- treat it as a starting point.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from agent_eval.simulate.adapters.base import AgentResult


class HttpAgentAdapter:
    def __init__(self, *, endpoint: str, api_key: str = "", timeout: float = 60.0):
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout

    async def invoke(self, *, input: dict[str, Any], correlation_id: str | None = None) -> AgentResult:
        correlation_id = correlation_id or str(uuid.uuid4())
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.endpoint,
                json={"input": input, "correlation_id": correlation_id},
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()

        return AgentResult(
            output_text=body.get("output", ""),
            tool_calls=body.get("tool_calls"),
            correlation_id=correlation_id,
            raw=body,
        )
