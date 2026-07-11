"""Chat turn orchestrator: bounded tool-calling loop + guard enforcement.

Runs the LLM against the tool schemas (max 5 rounds), accumulates each tool
result as a "grounding fact", then applies the grounding guard (regenerate once,
then fall back) and the advice guard before persisting the turn.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

import app.chat.tools  # noqa: F401  (registers TOOL_IMPLS)
from app.chat.guards.advice import check_advice_language
from app.chat.guards.grounding import FALLBACK_MESSAGE, check_grounding
from app.chat.providers.base import LLMProvider
from app.chat.system_prompt import SYSTEM_PROMPT
from app.chat.tools.router import dispatch_tool_call
from app.chat.tools.schema import TOOL_SCHEMAS
from app.models.chat import ChatMessage
from app.schemas.chat import ToolResult

MAX_TOOL_ROUNDS = 5


@dataclass
class ChatTurnResult:
    answer: str
    tool_events: list[ToolResult] = field(default_factory=list)
    regenerated: bool = False


async def run_chat_turn(
    db: AsyncSession,
    session_id: str,
    user_message: str,
    provider: LLMProvider | None = None,
) -> ChatTurnResult:
    if provider is None:
        from app.chat.providers.factory import get_provider

        provider = get_provider()

    base_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    db.add(ChatMessage(session_id=session_id, role="user", content=user_message))

    answer, tool_events = await _run_rounds(provider, list(base_messages), db, session_id)

    regenerated = False
    if not check_grounding(answer, tool_events).grounded:
        answer2, events2 = await _run_rounds(provider, list(base_messages), db, session_id)
        tool_events += events2
        regenerated = True
        answer = answer2 if check_grounding(answer2, tool_events).grounded else FALLBACK_MESSAGE

    if answer != FALLBACK_MESSAGE and not check_advice_language(answer).ok:
        answer = FALLBACK_MESSAGE

    db.add(ChatMessage(session_id=session_id, role="assistant", content=answer))
    await db.commit()
    return ChatTurnResult(answer=answer, tool_events=tool_events, regenerated=regenerated)


async def _run_rounds(
    provider: LLMProvider,
    messages: list[dict[str, Any]],
    db: AsyncSession,
    session_id: str,
) -> tuple[str, list[ToolResult]]:
    tool_events: list[ToolResult] = []
    text_parts: list[str] = []
    for _round in range(MAX_TOOL_ROUNDS):
        round_text: list[str] = []
        round_calls: list[tuple[Any, ToolResult]] = []
        async for chunk in provider.stream(messages, TOOL_SCHEMAS):
            if chunk.type == "token" and chunk.text:
                text_parts.append(chunk.text)
                round_text.append(chunk.text)
            elif chunk.type == "tool_call" and chunk.tool_call:
                call = chunk.tool_call
                if not call.id:
                    call.id = f"call_{_round}_{len(round_calls)}"
                result = await dispatch_tool_call(call, ctx={"db": db})
                tool_events.append(result)
                round_calls.append((call, result))
                db.add(
                    ChatMessage(
                        session_id=session_id,
                        role="tool",
                        content=None,
                        tool_calls=[
                            {
                                "name": result.name,
                                "ok": result.ok,
                                "data": result.data,
                                "error": result.error,
                            }
                        ],
                    )
                )
        if not round_calls:
            break
        # Record the assistant's tool_use turn *and* the paired results in the
        # running transcript. Without the assistant turn the model can't tell
        # which call each result answers, so it re-issues the same calls every
        # round and never converges to a final answer. Canonical shape is
        # OpenAI-style; non-OpenAI providers translate it in their stream().
        messages.append(
            {
                "role": "assistant",
                "content": "".join(round_text),
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                    for call, _ in round_calls
                ],
            }
        )
        for call, result in round_calls:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": result.name,
                    "content": str(result.data if result.ok else result.error),
                }
            )
    return "".join(text_parts), tool_events
