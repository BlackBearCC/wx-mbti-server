"""WebSocket endpoints for chat"""
from typing import List

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.services.ai import AIService, ChatMessage, CharacterProfile, get_ai_service

router = APIRouter()


@router.websocket("/chat/{character_name}")
async def websocket_endpoint(
    websocket: WebSocket,
    character_name: str,
    model_alias: str = "default",
    ai_service: AIService = Depends(get_ai_service),
) -> None:
    """Demonstration chat endpoint. Extend with auth/context loading as needed."""
    await websocket.accept()
    history: List[ChatMessage] = []
    try:
        while True:
            payload = await websocket.receive_text()
            history.append(ChatMessage(content=payload, is_ai=False))
            character = CharacterProfile(
                name=character_name,
                system_prompt="You are a friendly and empathetic AI companion who responds succinctly.",
                tag=None,
            )
            result = await ai_service.chat(character=character, history=history, model_alias=model_alias)
            history.append(ChatMessage(content=result.text, is_ai=True))
            await websocket.send_text(result.text)
    except WebSocketDisconnect:
        await websocket.close()
    except Exception:
        await websocket.close()
