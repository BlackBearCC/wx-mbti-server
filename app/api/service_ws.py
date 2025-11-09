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


router = APIRouter()

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
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError:
                await _send_json(websocket, {"event": "error", "detail": "invalid JSON"})
                continue

            op = (envelope.get("op") or "").lower()
            req_id = envelope.get("reqId")
            data = envelope.get("data") or {}

            # Ping
            if op == "ping":
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "pong"})
                continue

            # Room ops
            if op == "room.join":
                room_id = data.get("roomId") or data.get("room_id")
                if not room_id:
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "detail": "roomId required"})
                    continue
                _room_join(ws_id, room_id)
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "result", "roomId": room_id})
                continue
            if op == "room.leave":
                room_id = data.get("roomId") or data.get("room_id")
                if not room_id:
                    await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "detail": "roomId required"})
                    continue
                _room_leave(ws_id, room_id)
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "result", "roomId": room_id})
                continue
            if op == "room.typing":
                room_id = data.get("roomId") or data.get("room_id")
                user_id = data.get("userId") or data.get("user_id")
                if room_id:
                    await _room_broadcast(room_id, {"op": op, "event": "update", "roomId": room_id, "userId": user_id}, exclude=ws_id)
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "ack", "roomId": room_id})
                continue

            # AI ops
            if op not in {"ai.chat", "ai.stream"}:
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "detail": "unsupported op"})
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
                    continue
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "result", "text": result.text, "model": result.model, "usage": result.usage})
                continue

            # ai.stream
            if not settings.AI_STREAM_ENABLED:
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "error", "detail": "stream disabled"})
                continue
            await _send_json(websocket, {"reqId": req_id, "op": op, "event": "start"})
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
                continue
            finally:
                final_text = "".join(full_text_parts)
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "final", "text": final_text})
                await _send_json(websocket, {"reqId": req_id, "op": op, "event": "done", "model": model_report, "usage": usage_report})

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
        except Exception:
            pass

