from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic
from langfuse import Evaluation

from agent_eval.config import get_settings

RUBRIC = """\
You are grading one turn of an AI agent's reply against a known-good reference \
reply from the same agent in production. Judge whether the new reply is at \
least as good: same factual content, same resolution/outcome for the user, \
same tone. Minor wording differences are fine and should not lower the score.

User input:
{input}

Reference (golden) reply:
{expected_output}

New reply to grade:
{actual_output}

Respond with ONLY a JSON object: {{"score": <float 0.0-1.0>, "reason": "<one \
sentence, in the same language as the input>"}}. 1.0 = equivalent or better \
than the reference. 0.0 = wrong, unhelpful, or materially worse.\
"""


def _text_of(value: Any) -> Any:
    """Our task/publish steps wrap replies as {"text": ..., "tool_calls": [...]}.
    The judge only cares about the reply text, not the tool-call trace."""
    if isinstance(value, dict) and "text" in value:
        return value["text"]
    return value


async def llm_judge_evaluator(
    *, input: Any, output: Any, expected_output: Any, metadata: Any = None, **_: Any
) -> Evaluation:
    settings = get_settings()
    client = AsyncAnthropic()

    prompt = RUBRIC.format(
        input=json.dumps(input, ensure_ascii=False),
        expected_output=json.dumps(_text_of(expected_output), ensure_ascii=False),
        actual_output=json.dumps(_text_of(output), ensure_ascii=False),
    )
    response = await client.messages.create(
        model=settings.judge_model,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text if response.content else "{}"

    try:
        parsed = json.loads(text)
        score = float(parsed["score"])
        reason = str(parsed.get("reason", ""))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        score = 0.0
        reason = f"judge returned unparseable output: {text!r}"

    return Evaluation(name="llm_judge", value=score, comment=reason)
