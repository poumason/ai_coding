# AG-UI Protocol Demo

A small, real (not mocked) demo of the [AG-UI protocol](https://ag-ui.com)
(Agent-User Interaction Protocol) — the open, event-based wire format that
standardizes how an agent backend streams to a frontend.

It wraps a live [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)
conversation and re-emits everything it does as AG-UI events over SSE, using
the official `ag-ui-protocol` Python package for the event types and encoder.

## Run it

```bash
uv run python ag_ui_demo/server.py
```

Then open http://localhost:8000 in a browser. Requires the `claude` CLI to be
installed and logged in (same as `cc_agent_sdk/chat.py`).

## What to try

- **"台北天氣如何？"** — a plain tool call. Watch the right-hand event log:
  `TOOL_CALL_START` → `TOOL_CALL_ARGS` (streamed JSON) → `TOOL_CALL_END` →
  `TOOL_CALL_RESULT`, then the answer streams in as
  `TEXT_MESSAGE_START/CONTENT/END`.
- **"幫我寄信給 alice@example.com 提醒她開會"** — this tool needs a human
  decision. The run pauses: it ends with `RUN_FINISHED` whose `outcome.type`
  is `"interrupt"`, carrying an `Interrupt` describing what's being asked.
  The page shows Approve/Deny buttons; either choice starts a *new* run on
  the same `threadId`, carrying a `resume` entry — and the paused Claude
  conversation picks up exactly where it left off.
- Watch the **state panel**: `STATE_SNAPSHOT` seeds it once per thread,
  `STATE_DELTA` (JSON Patch) updates counters as messages/tool calls happen.

## How it maps to AG-UI

| AG-UI event | Where it comes from |
|---|---|
| `RUN_STARTED` / `RUN_FINISHED` / `RUN_ERROR` | one per POST `/agent` ("run") |
| `TEXT_MESSAGE_START/CONTENT/END` | Claude's raw `content_block_start/delta/stop` stream events (`type: text`) — enabled via `include_partial_messages=True` |
| `TOOL_CALL_START/ARGS/END` | the same raw stream events, `type: tool_use` |
| `TOOL_CALL_RESULT` | the `ToolResultBlock` the SDK sends back after running the tool |
| `STATE_SNAPSHOT` / `STATE_DELTA` | a small in-memory counter dict per thread |
| `RUN_FINISHED` with an `interrupt` outcome, then `resume` | a custom `get_weather`/`send_email` MCP tool pair, gated by `can_use_tool` |

## Architecture note

Claude's own `can_use_tool` permission callback blocks mid-conversation while
waiting for a decision — but the HTTP request that started the run has
already ended (it closed with `RUN_FINISHED`/interrupt). So each thread runs
its Claude conversation as a background `asyncio` task, feeding an
`asyncio.Queue`; every POST to `/agent` (new message *or* resume) just drains
that queue until the next run boundary. That's what lets a "resume" arrive as
a brand-new HTTP request and still continue the exact same paused tool call.

## Files

- `server.py` — FastAPI backend: Claude Agent SDK → AG-UI event translation,
  the interrupt/resume queue, and the two demo tools.
- `index.html` — single-file vanilla JS frontend: chat bubbles, tool-call
  cards, a confirm/deny UI for interrupts, a state panel, and a raw event log
  (useful for actually seeing the protocol, not just its effect).
