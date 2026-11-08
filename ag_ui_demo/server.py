"""
AG-UI (Agent-User Interaction) Protocol demo backend.

Wraps a real Claude Agent SDK conversation and re-emits everything as AG-UI
protocol events over SSE, so you can see how the wire format works for:

- streaming text            (TEXT_MESSAGE_START/CONTENT/END)
- tool calls                (TOOL_CALL_START/ARGS/END, TOOL_CALL_RESULT)
- human-in-the-loop pauses  (RUN_FINISHED with an "interrupt" outcome, resumed
                              via the `resume` field of a new RunAgentInput)
- shared state              (STATE_SNAPSHOT / STATE_DELTA as JSON Patch)

One HTTP POST to /agent = one "run". A run either finishes normally, or pauses
mid-flight when the agent wants to call a tool that needs confirmation; the
underlying Claude conversation keeps running in the background (blocked on an
asyncio.Future) until a follow-up POST resumes it with the user's decision.
"""

import asyncio
import json
import random
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import dotenv
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

import claude_agent_sdk as sdk
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server, tool

from ag_ui.core import (
    Interrupt,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunFinishedInterruptOutcome,
    RunFinishedSuccessOutcome,
    RunStartedEvent,
    StateDeltaEvent,
    StateSnapshotEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder

dotenv.load_dotenv()

EMAIL_TOOL_NAME = "send_email"  # the one tool that requires human confirmation


@tool("get_weather", "查詢城市目前天氣狀況（示範用，直接回傳假資料，不需要使用者確認）", {"city": str})
async def get_weather(args: dict) -> dict:
    condition = random.choice(["晴天", "多雲", "陣雨", "颱風警報"])
    temp = random.randint(18, 32)
    return {"content": [{"type": "text", "text": f"{args['city']} 目前{condition}，氣溫 {temp}°C"}]}


@tool(
    EMAIL_TOOL_NAME,
    "代替使用者寄送一封 email 通知（示範用，不會真的寄出；執行前必須取得使用者確認）",
    {"to": str, "subject": str, "body": str},
)
async def send_email(args: dict) -> dict:
    return {
        "content": [
            {"type": "text", "text": f"（模擬寄信）已寄給 {args['to']}，主旨：{args['subject']}"}
        ]
    }


SYSTEM_PROMPT = (
    "你是一個 AG-UI 協定示範用的助理。你有兩個工具：get_weather（查天氣，可直接呼叫）"
    "與 send_email（代替使用者寄信，這是敏感操作，系統會先向使用者確認）。"
    "當使用者要求查天氣就呼叫 get_weather；要求寄信/通知某人就呼叫 send_email。"
    "用簡短的繁體中文回覆。"
)


class ThreadSession:
    """One Claude Agent SDK conversation, keyed by AG-UI thread_id.

    Bridges Claude's own async generator to the AG-UI event queue so a run can
    span more than one HTTP request (needed for human-in-the-loop resume).
    """

    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.client: ClaudeSDKClient | None = None
        self.queue: asyncio.Queue = asyncio.Queue()
        self.pending: dict[str, asyncio.Future] = {}
        self.state = {"messagesSent": 0, "toolCalls": 0, "pendingApprovals": 0}
        self.state_sent = False

    async def _ensure_client(self) -> None:
        if self.client is not None:
            return
        server = create_sdk_mcp_server("demo", tools=[get_weather, send_email])
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"demo": server},
            can_use_tool=self._can_use_tool,
            include_partial_messages=True,
            cwd="./",
        )
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()

    async def _can_use_tool(self, tool_name: str, input_data: dict, context) -> sdk.PermissionResult:
        if not tool_name.endswith(EMAIL_TOOL_NAME):
            return sdk.PermissionResultAllow()

        interrupt_id = str(uuid.uuid4())
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self.pending[interrupt_id] = fut
        await self._bump_state("pendingApprovals", +1)

        await self.queue.put((
            "interrupt",
            Interrupt(
                id=interrupt_id,
                reason="tool_confirmation",
                message=f"Agent 想呼叫 {tool_name}，參數：{json.dumps(input_data, ensure_ascii=False)}。是否允許？",
                tool_call_id=getattr(context, "tool_use_id", None),
            ),
        ))

        approved = await fut
        self.pending.pop(interrupt_id, None)
        await self._bump_state("pendingApprovals", -1)

        if approved:
            return sdk.PermissionResultAllow()
        return sdk.PermissionResultDeny(message="使用者拒絕了這個操作。")

    async def _bump_state(self, key: str, delta: int) -> None:
        self.state[key] += delta
        await self.queue.put((
            "event",
            StateDeltaEvent(delta=[{"op": "replace", "path": f"/{key}", "value": self.state[key]}]),
        ))

    async def _emit(self, event) -> None:
        await self.queue.put(("event", event))

    async def run_turn(self, user_text: str) -> None:
        """Drive one user message through Claude, translating the stream to AG-UI events."""
        await self._ensure_client()

        if not self.state_sent:
            await self._emit(StateSnapshotEvent(snapshot=dict(self.state)))
            self.state_sent = True

        await self._bump_state("messagesSent", +1)
        await self.client.query(user_text, session_id=self.thread_id)

        text_blocks: dict[int, str] = {}  # content-block index -> AG-UI message_id
        tool_blocks: dict[int, str] = {}  # content-block index -> AG-UI tool_call_id

        async for message in self.client.receive_response():
            if isinstance(message, sdk.StreamEvent):
                await self._handle_stream_event(message.event, text_blocks, tool_blocks)
            elif isinstance(message, sdk.UserMessage):
                await self._handle_tool_results(message)
            # AssistantMessage / ResultMessage carry nothing we don't already
            # have from the finer-grained StreamEvents above.

        await self.queue.put(("done", None))

    async def _handle_stream_event(self, event: dict, text_blocks: dict, tool_blocks: dict) -> None:
        """Translate a raw Anthropic Messages API stream event into AG-UI events.

        This is the direct 1:1 mapping the whole demo hinges on: Claude already
        streams text/tool-args as incremental deltas, and so does AG-UI.
        """
        etype = event.get("type")

        if etype == "content_block_start":
            index = event["index"]
            block = event["content_block"]
            if block["type"] == "text":
                message_id = str(uuid.uuid4())
                text_blocks[index] = message_id
                await self._emit(TextMessageStartEvent(message_id=message_id, role="assistant"))
            elif block["type"] == "tool_use":
                tool_blocks[index] = block["id"]
                await self._bump_state("toolCalls", +1)
                await self._emit(ToolCallStartEvent(tool_call_id=block["id"], tool_call_name=block["name"]))

        elif etype == "content_block_delta":
            index = event["index"]
            delta = event["delta"]
            if delta.get("type") == "text_delta" and index in text_blocks:
                await self._emit(TextMessageContentEvent(message_id=text_blocks[index], delta=delta["text"]))
            elif delta.get("type") == "input_json_delta" and index in tool_blocks:
                await self._emit(ToolCallArgsEvent(tool_call_id=tool_blocks[index], delta=delta["partial_json"]))

        elif etype == "content_block_stop":
            index = event["index"]
            if index in text_blocks:
                await self._emit(TextMessageEndEvent(message_id=text_blocks.pop(index)))
            elif index in tool_blocks:
                await self._emit(ToolCallEndEvent(tool_call_id=tool_blocks.pop(index)))

    async def _handle_tool_results(self, message) -> None:
        content = message.content
        if isinstance(content, str):
            return
        for block in content:
            if isinstance(block, sdk.ToolResultBlock):
                result_text = block.content if isinstance(block.content, str) else json.dumps(block.content)
                await self._emit(
                    ToolCallResultEvent(
                        message_id=str(uuid.uuid4()),
                        tool_call_id=block.tool_use_id,
                        content=result_text,
                        role="tool",
                    )
                )


SESSIONS: dict[str, ThreadSession] = {}


def get_session(thread_id: str) -> ThreadSession:
    if thread_id not in SESSIONS:
        SESSIONS[thread_id] = ThreadSession(thread_id)
    return SESSIONS[thread_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for session in SESSIONS.values():
        if session.client is not None:
            await session.client.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse(str(Path(__file__).parent / "index.html"))


@app.post("/agent")
async def agent(run_input: RunAgentInput):
    session = get_session(run_input.thread_id)
    encoder = EventEncoder()

    if run_input.resume:
        for entry in run_input.resume:
            fut = session.pending.get(entry.interrupt_id)
            if fut and not fut.done():
                approved = bool((entry.payload or {}).get("approved"))
                fut.set_result(approved)
    else:
        user_text = next(
            (m.content for m in reversed(run_input.messages) if m.role == "user"),
            "",
        )
        asyncio.create_task(session.run_turn(str(user_text)))

    async def stream():
        yield encoder.encode(RunStartedEvent(thread_id=run_input.thread_id, run_id=run_input.run_id))
        try:
            while True:
                kind, payload = await session.queue.get()
                if kind == "event":
                    yield encoder.encode(payload)
                elif kind == "interrupt":
                    yield encoder.encode(
                        RunFinishedEvent(
                            thread_id=run_input.thread_id,
                            run_id=run_input.run_id,
                            outcome=RunFinishedInterruptOutcome(interrupts=[payload]),
                        )
                    )
                    return
                elif kind == "done":
                    yield encoder.encode(
                        RunFinishedEvent(
                            thread_id=run_input.thread_id,
                            run_id=run_input.run_id,
                            outcome=RunFinishedSuccessOutcome(),
                        )
                    )
                    return
        except Exception as exc:  # surface backend errors as a proper AG-UI event
            yield encoder.encode(RunErrorEvent(message=str(exc)))

    return StreamingResponse(stream(), media_type=encoder.get_content_type())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
