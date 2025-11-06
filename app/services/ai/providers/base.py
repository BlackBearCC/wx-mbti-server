"""AI provider base interfaces"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class AIMessage:
    """Normalized message item that can be converted to provider payloads."""

    role: str
    content: str


@dataclass
class AIChatRequest:
    """Service-level request format for chat completion."""

    messages: List[AIMessage]
    model: Optional[str] = None
    character_id: Optional[str] = None
    room_id: Optional[str] = None
    user_id: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AIChatResponse:
    """Raw response container produced by providers."""

    text: str
    model: str
    usage: Optional[Dict[str, int]] = None


class AIProvider(ABC):
    """Provider contract to unify different LLM vendors."""

    name: str

    @abstractmethod
    async def complete(self, request: AIChatRequest) -> AIChatResponse:
        """Return a single-shot completion for the given request."""

    async def stream(self, request: AIChatRequest) -> AsyncIterator[str]:
        """Yield partial tokens when the upstream provider supports streaming."""
        raise NotImplementedError("Streaming is not implemented for this provider")
