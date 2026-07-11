from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.chat.providers.base import ProviderChunk
from app.core.config import get_settings
from app.schemas.chat import ToolCall


class GeminiProvider:
    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or get_settings().GEMINI_API_KEY
        self.model = model

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[ProviderChunk]:
        import google.generativeai as _genai

        genai: Any = _genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model, tools=tools)
        response = await model.generate_content_async(messages, stream=True)
        async for chunk in response:
            if getattr(chunk, "text", None):
                yield ProviderChunk(type="token", text=chunk.text)
            for call in getattr(chunk, "function_calls", None) or []:
                yield ProviderChunk(
                    type="tool_call",
                    tool_call=ToolCall(name=call.name, arguments=dict(call.args)),
                )
