"""External service endpoints to access the LLM.

These endpoints expose a simple API for 3rd-party callers:
- POST /service/chat        -> single-shot completion
- POST /service/streamchat  -> Server-Sent Events streaming tokens

Both endpoints delegate to the shared AIService which handles provider
selection (e.g., Doubao/OpenAI) and model alias resolution.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator

from app.config.settings import get_settings
from app.services.ai import AIService, ChatMessage, CharacterProfile, get_ai_service
from app.core.security import require_auth, enforce_rate_limit, AuthContext


router = APIRouter()


# ---- Pydantic Schemas ----

class MessageItem(BaseModel):
    role: str = Field(..., description="system|user|assistant")
    content: str

    @validator("role")
    def _role_lower(cls, v: str) -> str:  # normalize
        return v.lower()


class ChatRequest(BaseModel):
    messages: List[MessageItem]
    # Optional routing/override knobs
    model_alias: Optional[str] = Field(default=None, alias="modelAlias")
    temperature: Optional[float] = None
    max_tokens: Optional[int] = Field(default=None, alias="maxTokens")
    metadata: Optional[Dict[str, Any]] = None
    # Optional hints for persona
    character_name: Optional[str] = Field(default=None, alias="characterName")
    system_prompt: Optional[str] = Field(default=None, alias="systemPrompt")

    class Config:
        allow_population_by_field_name = True


class ChatResponseData(BaseModel):
    text: str
    model: str
    usage: Optional[Dict[str, int]] = None
    created: datetime


class ChatResponse(BaseModel):
    code: int = 200
    data: ChatResponseData


# ---- Helpers ----

def _build_profile_and_history(payload: ChatRequest) -> tuple[CharacterProfile, List[ChatMessage]]:
    """Convert external request into persona + history.

    - First `system` message (if present) is used as the system prompt unless an
      explicit `systemPrompt` is supplied.
    - Remaining messages become ChatMessage history.
    """
    system_prompt = payload.system_prompt
    history: List[ChatMessage] = []
    for m in payload.messages:
        if m.role == "system" and system_prompt is None:
            system_prompt = m.content
            continue
        history.append(ChatMessage(content=m.content, is_ai=(m.role == "assistant")))

    name = payload.character_name or "external"
    profile = CharacterProfile(
        name=name,
        system_prompt=(system_prompt or "Stay helpful, concise and consistent."),
        tag=None,
    )
    return profile, history


def _sse(iterable: AsyncIterator[str]) -> StreamingResponse:
    """Wrap an async iterator of text chunks into SSE format."""

    async def event_source() -> AsyncIterator[bytes]:
        try:
            async for chunk in iterable:
                if not chunk:
                    continue
                yield f"data: {chunk}\n\n".encode("utf-8")
        finally:
            # Signal completion to the client
            yield b"data: [DONE]\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


# ---- Endpoints ----

@router.post("/chat", response_model=ChatResponse)
async def external_chat(
    req: ChatRequest,
    ai_service: AIService = Depends(get_ai_service),
    auth: AuthContext = Depends(require_auth),
):
    """Single-shot completion endpoint for external callers."""
    profile, history = _build_profile_and_history(req)

    # Rate limit per subject (token)
    await enforce_rate_limit(auth.subject, scope="service:http:chat")

    try:
        result = await ai_service.chat(
            character=profile,
            history=history,
            model_alias=req.model_alias,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            metadata=req.metadata,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    return ChatResponse(
        data=ChatResponseData(
            text=result.text,
            model=result.model,
            usage=result.usage,
            created=datetime.utcnow(),
        )
    )


@router.post("/streamchat")
async def external_stream_chat(
    req: ChatRequest,
    ai_service: AIService = Depends(get_ai_service),
    auth: AuthContext = Depends(require_auth),
):
    """SSE streaming completion endpoint.

    Yields `text/event-stream` with `data: <chunk>` lines and a terminal
    `data: [DONE]`.
    """
    settings = get_settings()
    if not settings.AI_STREAM_ENABLED:
        raise HTTPException(status_code=400, detail="Streaming is disabled")

    # Rate limit per subject (token)
    await enforce_rate_limit(auth.subject, scope="service:http:stream")

    profile, history = _build_profile_and_history(req)
    try:
        stream_iter = ai_service.stream_chat(
            character=profile,
            history=history,
            model_alias=req.model_alias,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            metadata=req.metadata,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    return _sse(stream_iter)
