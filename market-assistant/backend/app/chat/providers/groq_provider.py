from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from app.chat.providers.base import ProviderChunk
from app.core.config import get_settings
from app.schemas.chat import ToolCall


class GroqProvider:
    def __init__(self, api_key: str | None = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or get_settings().GROQ_API_KEY
        self.model = model

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[ProviderChunk]:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=self.api_key)
        stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[{"type": "function", "function": t} for t in tools],
            stream=True,
        )
        async for event in stream:
            delta = event.choices[0].delta
            if delta.content:
                yield ProviderChunk(type="token", text=delta.content)
            for tc in delta.tool_calls or []:
                yield ProviderChunk(
                    type="tool_call",
                    tool_call=ToolCall(
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments or "{}"),
                    ),
                )
