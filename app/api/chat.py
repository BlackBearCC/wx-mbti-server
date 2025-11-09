from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

# Placeholder for user authentication dependency
async def get_current_user_placeholder():
    # In a real app, this would validate a token and return user info
    return {"userId": "mock_user_123", "username": "testuser"}

router = APIRouter()

# Mock database for chat messages (very simplified)
fake_chat_log: Dict[str, List[Dict[str, Any]]] = {}

# Placeholder for other chat-related endpoints like /history, /typing_indicator etc.
# --- Pydantic Models for Chat History ---
class ChatHistoryMessage(BaseModel):
    message_id: str
    timestamp: datetime
    sender_id: str
    sender_type: str # "user" or "character"
    content: str
    message_type: str
    metadata: Optional[Dict[str, Any]] = None

class GetChatHistoryResponseData(BaseModel):
    room_id: str
    messages: List[ChatHistoryMessage]
    has_more: bool
    total_messages: int

class GetChatHistoryResponse(BaseModel):
    code: int = 200
    data: GetChatHistoryResponseData

@router.get("/{room_id}/history", response_model=GetChatHistoryResponse)
async def get_chat_history(
    room_id: str,
    before_message_id: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user_placeholder)
):
    """获取聊天历史记录"""
    if room_id not in fake_chat_log:
        # Return empty history for new rooms
        return GetChatHistoryResponse(data=GetChatHistoryResponseData(
            room_id=room_id,
            messages=[],
            has_more=False,
            total_messages=0
        ))

    # Get all messages for the room
    room_messages = fake_chat_log[room_id]
    total_messages = len(room_messages)

    # If before_message_id is provided, find its index
    start_idx = 0
    if before_message_id:
        for idx, msg in enumerate(room_messages):
            if msg["message_id"] == before_message_id:
                start_idx = idx
                break

    # Get messages before the specified message, limited by count
    messages_slice = room_messages[max(0, start_idx - limit):start_idx] if before_message_id \
        else room_messages[max(0, total_messages - limit):]

    # Convert to response format
    history_messages = [
        ChatHistoryMessage(
            message_id=msg["message_id"],
            timestamp=msg["timestamp"],
            sender_id=msg["sender_id"],
            sender_type=msg["sender_type"],
            content=msg["content"],
            message_type=msg["message_type"],
            metadata=msg.get("metadata")
        ) for msg in messages_slice
    ]

    # Determine if there are more messages
    has_more = start_idx > limit if before_message_id else total_messages > limit

    return GetChatHistoryResponse(data=GetChatHistoryResponseData(
        room_id=room_id,
        messages=history_messages,
        has_more=has_more,
        total_messages=total_messages
    ))

# Placeholder for other chat-related endpoints
