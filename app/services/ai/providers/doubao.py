"""Doubao (Ark/DeepSeek) provider"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Optional

import httpx

from .base import AIChatRequest, AIChatResponse, AIProvider


class DoubaoProvider(AIProvider):
    """Simple HTTP wrapper for ByteDance Doubao chat models."""

    name = "doubao"

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
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    def _build_payload(self, request: AIChatRequest, stream: bool = False) -> Dict[str, Any]:
        model_name = request.model or self.model
        payload: Dict[str, Any] = {"model": model_name}
        payload["messages"] = [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ]
        parameters: Dict[str, Any] = {}
        if request.max_tokens is not None:
            parameters["max_output_tokens"] = request.max_tokens
        if request.temperature is not None:
            parameters["temperature"] = request.temperature
        if parameters:
            payload["parameters"] = parameters
        if request.metadata:
            payload["metadata"] = request.metadata
        if stream:
            payload["stream"] = True
        return payload

    async def complete(self, request: AIChatRequest) -> AIChatResponse:
        client = await self._get_client()
        response = await client.post("/chat/completions", json=self._build_payload(request))
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]["message"]
        usage = data.get("usage")
        return AIChatResponse(text=choice["content"], model=data.get("model", self.model), usage=usage)

    async def stream(self, request: AIChatRequest) -> AsyncIterator[str]:
        client = await self._get_client()
        async with client.stream("POST", "/chat/completions", json=self._build_payload(request, stream=True)) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line.split("data: ", 1)[1].strip()
                if not data:
                    continue
                if data == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue
                for choice in payload.get("choices", []):
                    delta = choice.get("delta") or choice.get("message") or {}
                    content = delta.get("content")
                    if isinstance(content, str):
                        yield content
                    elif isinstance(content, list):
                        for segment in content:
                            if isinstance(segment, dict) and segment.get("type") == "text":
                                yield segment.get("text", "")

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
