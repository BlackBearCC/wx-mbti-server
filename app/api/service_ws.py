"""WebSocket Gateway for multi-op protocol (LLM + others).

Path: /service/ws

Protocol (client -> server): JSON envelope per message
{
  "reqId": "r-123",                      // required for correlation
  "op": "ai.chat" | "ai.stream" | "ping" | "room.join" | "room.leave" | "room.typing",
  "data": {                               // operation-specific payload
    // ai.* payload:
    "messages": [{"role": "system|user|assistant", "content": "..."}],
    "modelAlias": "default|...",          // maps to provider+model server-side
    "temperature": 0.7,                    // optional
    "maxTokens": 512,                      // optional
    "metadata": {"traceId": "..."},       // optional
    "characterName": "external",          // optional
    "systemPrompt": "You are ...",         // optional (overrides first system msg)
    "userId": "u1", "roomId": "r1", "characterId": "c1" // optional
  }
}

Protocol (server -> client): JSON frames
- ai.chat -> single response:
  {"reqId": "r-123", "op": "ai.chat", "event": "result", "text": "...", "model": "...", "usage": {...}}

- ai.stream -> streaming:
  {"reqId": "r-123", "op": "ai.stream", "event": "start"}
  {"reqId": "r-123", "op": "ai.stream", "event": "chunk", "text": "..."}     // repeated
  {"reqId": "r-123", "op": "ai.stream", "event": "final", "text": "..."}
  {"reqId": "r-123", "op": "ai.stream", "event": "done", "model": null, "usage": null}

- room.join/leave -> ack:
  {"reqId": "r-124", "op": "room.join", "event": "result", "roomId": "r1"}
  {"reqId": "r-125", "op": "room.leave", "event": "result", "roomId": "r1"}

- room.typing -> broadcast to room (excluding sender):
  {"op": "room.typing", "event": "update", "roomId": "r1", "userId": "u1"}

- Errors:
  {"reqId": "r-123", "op": "ai.chat", "event": "error", "detail": "..."}
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.config.settings import get_settings
from app.services.ai import AIService, ChatMessage, CharacterProfile, get_ai_service
from app.core.security import ws_extract_token, ws_validate_token, enforce_rate_limit
import structlog


router = APIRouter()
logger = structlog.get_logger()

# Minimal in-memory room registry for demo purposes
ROOM_MEMBERS: Dict[str, Set[int]] = {}
WS_REGISTRY: Dict[int, WebSocket] = {}
WS_ROOMS: Dict[int, Set[str]] = {}


def _build_profile_and_history(data: Dict[str, Any]) -> tuple[CharacterProfile, List[ChatMessage]]:
    messages = data.get("messages") or []
    system_prompt = data.get("systemPrompt")
    history: List[ChatMessage] = []
    for m in messages:
        role = (m.get("role") or "").lower()
        content = m.get("content") or ""
        if role == "system" and system_prompt is None:
            system_prompt = content
            continue
        history.append(ChatMessage(content=content, is_ai=(role == "assistant")))
    name = data.get("characterName") or "external"
    profile = CharacterProfile(
        name=name,
        system_prompt=(system_prompt or "Stay helpful, concise and consistent."),
        tag=None,
    )
    return profile, history


async def _send_json(ws: WebSocket, payload: Dict[str, Any]) -> None:
    await ws.send_text(json.dumps(payload, ensure_ascii=False))


def _room_join(ws_id: int, room_id: str) -> None:
    ROOM_MEMBERS.setdefault(room_id, set()).add(ws_id)
    WS_ROOMS.setdefault(ws_id, set()).add(room_id)


def _room_leave(ws_id: int, room_id: str) -> None:
    if room_id in ROOM_MEMBERS:
        ROOM_MEMBERS[room_id].discard(ws_id)
        if not ROOM_MEMBERS[room_id]:
            del ROOM_MEMBERS[room_id]
    if ws_id in WS_ROOMS:
        WS_ROOMS[ws_id].discard(room_id)
        if not WS_ROOMS[ws_id]:
            del WS_ROOMS[ws_id]


async def _room_broadcast(room_id: str, message: Dict[str, Any], exclude: Optional[int] = None) -> None:
    member_ids = ROOM_MEMBERS.get(room_id) or set()
    for mid in list(member_ids):
        if exclude is not None and mid == exclude:
            continue
        ws = WS_REGISTRY.get(mid)
        if ws is None:
            continue
        try:
            await _send_json(ws, message)
        except Exception:
            # Best-effort: ignore broken connection
            pass


@router.websocket("/ws")
async def external_ws(
    websocket: WebSocket,
    ai_service: AIService = Depends(get_ai_service),
):
    settings = get_settings()
    await websocket.accept()
    ws_id = id(websocket)
    WS_REGISTRY[ws_id] = websocket
    # auth state per connection
    token = ws_extract_token(websocket)
    authed = ws_validate_token(token)
    subject = token or f"ip:{getattr(websocket.client, 'host', 'unknown')}"
    try:
        logger.info("ws.connected", ws_id=ws_id)
    except Exception:
        pass
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError:
                await _send_json(websocket, {"event": "error", "detail": "invalid JSON"})
                try:
                    logger.warning("ws.invalid_json", ws_id=ws_id)
                except Exception:
                    pass
                continue

            op = (envelope.get("op") or "").lower()
            req_id = envelope.get("reqId")
            data = envelope.get("data") or {}
            try:
                logger.info("ws.message", ws_id=ws_id, req_id=req_id, op=op)
            except Exception:
                pass

            # Auth op: {op: "auth", data: {token: "..."}}
            if op == "auth":
                t = data.get("token")
                if ws_validate_token(t):
                    token = t
                    authed = True
                    subject = token or subject
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "result"})
                else:
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "code": 401, "detail": "未授权"})
                continue

            # Ping
            if op == "ping":
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "pong"})
                try:
                    logger.debug("ws.pong", ws_id=ws_id, req_id=req_id)
                except Exception:
                    pass
                continue

            # Room ops
            if op == "room.join":
                if not authed:
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "code": 401, "detail": "未授权"})
                    continue
                room_id = data.get("roomId") or data.get("room_id")
                if not room_id:
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "detail": "roomId required"})
                    continue
                _room_join(ws_id, room_id)
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "result", "roomId": room_id})
                try:
                    logger.info("ws.room.join", ws_id=ws_id, room_id=room_id)
                except Exception:
                    pass
                continue
            if op == "room.leave":
                if not authed:
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "code": 401, "detail": "未授权"})
                    continue
                room_id = data.get("roomId") or data.get("room_id")
                if not room_id:
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "detail": "roomId required"})
                    continue
                _room_leave(ws_id, room_id)
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "result", "roomId": room_id})
                try:
                    logger.info("ws.room.leave", ws_id=ws_id, room_id=room_id)
                except Exception:
                    pass
                continue
            if op == "room.typing":
                if not authed:
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "code": 401, "detail": "未授权"})
                    continue
                room_id = data.get("roomId") or data.get("room_id")
                user_id = data.get("userId") or data.get("user_id")
                if room_id:
                    await _room_broadcast(room_id, {"op": op, "event": "update", "roomId": room_id, "userId": user_id}, exclude=ws_id)
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "ack", "roomId": room_id})
                try:
                    logger.debug("ws.room.typing", ws_id=ws_id, room_id=room_id, user_id=user_id)
                except Exception:
                    pass
                continue

            # AI ops (require auth)
            if op not in {"ai.chat", "ai.stream"}:
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "detail": "unsupported op"})
                continue
            if not authed:
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "code": 401, "detail": "未授权"})
                continue

            profile, history = _build_profile_and_history(data)
            model_alias = data.get("modelAlias") or data.get("model_alias")
            temperature = data.get("temperature")
            max_tokens = data.get("maxTokens") or data.get("max_tokens")
            metadata = data.get("metadata")
            character_id = data.get("characterId") or data.get("character_id")
            room_id = data.get("roomId") or data.get("room_id")
            user_id = data.get("userId") or data.get("user_id")

            if op == "ai.chat":
                # Rate limit per subject
                try:
                    await enforce_rate_limit(subject, scope="service:ws:ai.chat")
                except Exception as rle:
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "code": 429, "detail": str(rle)})
                    continue
                try:
                    logger.info("ws.ai.chat.start", ws_id=ws_id, req_id=req_id, model_alias=model_alias)
                except Exception:
                    pass
                try:
                    result = await ai_service.chat(
                        character=profile,
                        history=history,
                        model_alias=model_alias,
                        character_id=character_id,
                        room_id=room_id,
                        user_id=user_id,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        metadata=metadata,
                    )
                except Exception as exc:
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "detail": f"AI error: {exc}"})
                    try:
                        logger.warning("ws.ai.chat.error", ws_id=ws_id, req_id=req_id, detail=str(exc))
                    except Exception:
                        pass
                    continue
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "result", "text": result.text, "model": result.model, "usage": result.usage})
                try:
                    logger.info("ws.ai.chat.result", ws_id=ws_id, req_id=req_id, model=result.model, chars=len(result.text or ""))
                except Exception:
                    pass
                continue

            # ai.stream
            if not settings.AI_STREAM_ENABLED:
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "detail": "stream disabled"})
                continue
            # Rate limit per subject
            try:
                await enforce_rate_limit(subject, scope="service:ws:ai.stream")
            except Exception as rle:
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "code": 429, "detail": str(rle)})
                continue
            await _send_json(websocket, {"reqId": req_id, "op": op, "event": "start"})
            try:
                logger.info("ws.ai.stream.start", ws_id=ws_id, req_id=req_id, model_alias=model_alias)
            except Exception:
                pass
            full_text_parts: List[str] = []
            model_report: Optional[str] = None
            usage_report: Optional[Dict[str, int]] = None
            try:
                async for chunk in ai_service.stream_chat(
                    character=profile,
                    history=history,
                    model_alias=model_alias,
                    character_id=character_id,
                    room_id=room_id,
                    user_id=user_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    metadata=metadata,
                ):
                    if not chunk:
                        continue
                    full_text_parts.append(chunk)
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "chunk", "text": chunk})
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "detail": f"AI error: {exc}"})
                try:
                    logger.warning("ws.ai.stream.error", ws_id=ws_id, req_id=req_id, detail=str(exc))
                except Exception:
                    pass
                continue
            finally:
                final_text = "".join(full_text_parts)
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "final", "text": final_text})
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "done", "model": model_report, "usage": usage_report})
                try:
                    logger.info("ws.ai.stream.done", ws_id=ws_id, req_id=req_id, chars=len(final_text))
                except Exception:
                    pass

    except WebSocketDisconnect:
        try:
            await websocket.close()
        except Exception:
            pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        # cleanup room registry
        try:
            if ws_id in WS_ROOMS:
                for rid in list(WS_ROOMS[ws_id]):
                    _room_leave(ws_id, rid)
            WS_REGISTRY.pop(ws_id, None)
            try:
                logger.info("ws.disconnected", ws_id=ws_id)
            except Exception:
                pass
        except Exception:
            pass
