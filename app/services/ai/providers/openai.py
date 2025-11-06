"""OpenAI provider implementation"""
from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Optional

import httpx

from .base import AIChatRequest, AIChatResponse, AIProvider


class OpenAIProvider(AIProvider):
    """Wraps the OpenAI-compatible chat completion endpoint."""

    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 30.0):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        return self._client

    async def complete(self, request: AIChatRequest) -> AIChatResponse:
        client = await self._get_client()
        model_name = request.model or self.model
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
        choice = data["choices"][0]["message"]
        usage = data.get("usage")
        return AIChatResponse(text=choice["content"], model=data.get("model", self.model), usage=usage)

    async def stream(self, request: AIChatRequest) -> AsyncIterator[str]:
        client = await self._get_client()
        model_name = request.model or self.model
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "stream": True,
        }
        async with client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line.split("data: ", 1)[1]
                    if data == "[DONE]":
                        break
                    yield data

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
