from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

from app.chat.providers.base import ProviderChunk
from app.core.config import get_settings
from app.schemas.chat import ToolCall


class AnthropicProvider:
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-5"):
        self.api_key = api_key or get_settings().ANTHROPIC_API_KEY
        self.model = model

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[ProviderChunk]:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)
        anthropic_tools = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t["parameters"],
            }
            for t in tools
        ]
        async with client.messages.stream(
            model=self.model,
            max_tokens=1024,
            messages=cast(Any, messages),
            tools=cast(Any, anthropic_tools),
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield ProviderChunk(type="token", text=event.delta.text)
                elif event.type == "content_block_stop" and (
                    getattr(event.content_block, "type", None) == "tool_use"
                ):
                    block: Any = event.content_block
                    yield ProviderChunk(
                        type="tool_call",
                        tool_call=ToolCall(name=block.name, arguments=dict(block.input)),
                    )
