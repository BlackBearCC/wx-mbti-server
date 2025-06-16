from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Placeholder for user authentication dependency
async def get_current_user_placeholder():
    # In a real app, this would validate a token and return user info
    return {"userId": "mock_user_123", "username": "testuser"}

router = APIRouter()

# --- Pydantic Models for Chat --- 

class ChatMessageRequest(BaseModel):
    room_id: str
    character_id: str # The character the user is chatting with
    content: str
    message_type: str = "text" # e.g., text, image_url, action
    metadata: Optional[Dict[str, Any]] = None

class ChatMessageResponseData(BaseModel):
    message_id: str
    timestamp: datetime
    sender_id: str # User or Character ID
    sender_type: str # "user" or "character"
    content: str
    message_type: str
    # Potentially character's response if it's a user message
    character_response: Optional[str] = None 
    character_response_message_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    code: int = 200
    data: ChatMessageResponseData

# Mock database for chat messages (very simplified)
fake_chat_log: Dict[str, List[Dict[str, Any]]] = {}

@router.post("/send", response_model=ChatMessageResponse)
async def send_chat_message(message_data: ChatMessageRequest, current_user: dict = Depends(get_current_user_placeholder)):
    """发送聊天消息"""
    # This is a placeholder. 
    # A real implementation would involve: 
    # 1. Storing the user's message.
    # 2. Triggering a character AI response (potentially asynchronously).
    # 3. Storing the character's response.
    # 4. Returning both or just the user's message confirmation.
    # For now, we'll just mock a simple echo and a canned character response.

    user_id = current_user["userId"]
    room_id = message_data.room_id
    timestamp = datetime.utcnow()
    message_id = f"msg_{timestamp.timestamp()}_{user_id[:5]}"

    # Store user message (mock)
    if room_id not in fake_chat_log:
        fake_chat_log[room_id] = []
    fake_chat_log[room_id].append({
        "message_id": message_id,
        "timestamp": timestamp,
        "sender_id": user_id,
        "sender_type": "user",
        "character_id": message_data.character_id,
        "content": message_data.content,
        "message_type": message_data.message_type
    })

    # Mock character response
    char_response_content = f"Ah, {message_data.content}! That's an interesting point, {current_user['username']}. Let me ponder that."
    char_message_id = f"msg_{datetime.utcnow().timestamp()}_{message_data.character_id[:5]}"
    
    fake_chat_log[room_id].append({
        "message_id": char_message_id,
        "timestamp": datetime.utcnow(),
        "sender_id": message_data.character_id,
        "sender_type": "character",
        "character_id": message_data.character_id, # Responding to self in a way
        "content": char_response_content,
        "message_type": "text"
    })

    return ChatMessageResponse(data=ChatMessageResponseData(
        message_id=message_id,
        timestamp=timestamp,
        sender_id=user_id,
        sender_type="user",
        content=message_data.content,
        message_type=message_data.message_type,
        character_response=char_response_content,
        character_response_message_id=char_message_id
    ))

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