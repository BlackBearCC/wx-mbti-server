"""Squad API routes for MBTI personality squad feature."""
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user_jwt
from app.models.squad import SquadCharacter, Topic, UserChatRoom, UserChatMessage
from app.services.ai import get_ai_service
from app.services.squad_service import SquadSpeechService
from app.utils.url import build_base_url

router = APIRouter()


class CharacterItem(BaseModel):
    characterId: str
    name: str
    dimension: str
    persona: str
    avatar: str
    voiceStyle: str
    signature: str
    unlockType: str


class ListCharactersResponseData(BaseModel):
    characters: List[CharacterItem]


class ListCharactersResponse(BaseModel):
    code: int = 200
    data: ListCharactersResponseData


@router.get("/characters", response_model=ListCharactersResponse)
async def list_characters(
    request: Request,
    current_user: dict = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """List all squad characters."""
    result = await db.execute(
        select(SquadCharacter)
        .where(SquadCharacter.is_enabled == True)
        .order_by(SquadCharacter.dimension, SquadCharacter.character_id)
    )
    chars = result.scalars().all()
    base = build_base_url(request, force_https=True)
    items = []
    for c in chars:
        avatar = c.avatar if c.avatar.startswith("http") else base + c.avatar
        items.append(CharacterItem(
            characterId=c.character_id,
            name=c.name,
            dimension=c.dimension,
            persona=c.persona,
            avatar=avatar,
            voiceStyle=c.voice_style,
            signature=c.signature,
            unlockType=c.unlock_type,
        ))
    return ListCharactersResponse(data=ListCharactersResponseData(characters=items))


class TopicItem(BaseModel):
    topicId: str
    title: str
    recommendedCharacterIds: List[str]


class ListTopicsResponseData(BaseModel):
    topics: List[TopicItem]


class ListTopicsResponse(BaseModel):
    code: int = 200
    data: ListTopicsResponseData


@router.get("/topics", response_model=ListTopicsResponse)
async def list_topics(
    current_user: dict = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """List all active topics."""
    result = await db.execute(
        select(Topic)
        .where(Topic.is_active == True)
        .order_by(Topic.create_time)
    )
    topics = result.scalars().all()
    items = [
        TopicItem(
            topicId=t.topic_id,
            title=t.title,
            recommendedCharacterIds=t.recommended_character_ids,
        )
        for t in topics
    ]
    return ListTopicsResponse(data=ListTopicsResponseData(topics=items))


class CreateRoomRequest(BaseModel):
    title: str
    topic: str
    characterIds: List[str]


class RoomItem(BaseModel):
    roomId: str
    title: str
    topic: str
    characterIds: List[str]
    createTime: float
    lastActiveTime: float


class CreateRoomResponseData(BaseModel):
    room: RoomItem


class CreateRoomResponse(BaseModel):
    code: int = 200
    data: CreateRoomResponseData


class ListRoomsResponseData(BaseModel):
    rooms: List[RoomItem]


class ListRoomsResponse(BaseModel):
    code: int = 200
    data: ListRoomsResponseData


def _room_to_item(room: UserChatRoom) -> RoomItem:
    return RoomItem(
        roomId=room.room_id,
        title=room.title,
        topic=room.topic,
        characterIds=room.character_ids,
        createTime=room.create_time.timestamp() if room.create_time else 0,
        lastActiveTime=room.last_active_time.timestamp() if room.last_active_time else 0,
    )


@router.post("/rooms", response_model=CreateRoomResponse)
async def create_room(
    req: CreateRoomRequest,
    current_user: dict = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Create a user chat room."""
    if len(req.characterIds) == 0:
        raise HTTPException(status_code=400, detail="至少选择 1 个角色")
    if len(req.characterIds) > 8:
        raise HTTPException(status_code=400, detail="最多选择 8 个角色")
    room = UserChatRoom(
        user_id=current_user["userId"],
        title=req.title,
        topic=req.topic,
        character_ids=req.characterIds,
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return CreateRoomResponse(data=CreateRoomResponseData(room=_room_to_item(room)))


@router.get("/rooms", response_model=ListRoomsResponse)
async def list_rooms(
    current_user: dict = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """List current user's chat rooms."""
    result = await db.execute(
        select(UserChatRoom)
        .where(UserChatRoom.user_id == current_user["userId"])
        .order_by(UserChatRoom.last_active_time.desc())
    )
    rooms = result.scalars().all()
    items = [_room_to_item(r) for r in rooms]
    return ListRoomsResponse(data=ListRoomsResponseData(rooms=items))


class MessageItem(BaseModel):
    messageId: str
    senderType: str  # 'user' | 'character'
    senderId: str
    content: str
    mentionedCharacterIds: List[str] = []
    createTime: float


class RoomDetailData(BaseModel):
    room: RoomItem
    messages: List[MessageItem]
    characters: List[CharacterItem]


class RoomDetailResponse(BaseModel):
    code: int = 200
    data: RoomDetailData


def _message_to_item(msg: UserChatMessage) -> MessageItem:
    return MessageItem(
        messageId=msg.message_id,
        senderType=msg.sender_type,
        senderId=msg.sender_id,
        content=msg.content,
        mentionedCharacterIds=msg.mentioned_character_ids or [],
        createTime=msg.create_time.timestamp() if msg.create_time else 0,
    )


@router.get("/rooms/{room_id}", response_model=RoomDetailResponse)
async def get_room_detail(
    room_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Get room detail with messages and characters."""
    result = await db.execute(
        select(UserChatRoom).where(UserChatRoom.room_id == room_id)
    )
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=404, detail="聊天室不存在")
    if room.user_id != current_user["userId"]:
        raise HTTPException(status_code=404, detail="聊天室不存在")

    # Get messages
    msg_result = await db.execute(
        select(UserChatMessage)
        .where(UserChatMessage.room_id == room_id)
        .order_by(UserChatMessage.create_time)
    )
    messages = [_message_to_item(m) for m in msg_result.scalars().all()]

    # Get characters
    base = build_base_url(request, force_https=True)
    char_result = await db.execute(
        select(SquadCharacter).where(SquadCharacter.character_id.in_(room.character_ids))
    )
    chars = []
    for c in char_result.scalars().all():
        avatar = c.avatar if c.avatar.startswith("http") else base + c.avatar
        chars.append(CharacterItem(
            characterId=c.character_id,
            name=c.name,
            dimension=c.dimension,
            persona=c.persona,
            avatar=avatar,
            voiceStyle=c.voice_style,
            signature=c.signature,
            unlockType=c.unlock_type,
        ))

    # Preserve order from room.character_ids
    char_map = {c.characterId: c for c in chars}
    ordered_chars = [char_map[cid] for cid in room.character_ids if cid in char_map]

    return RoomDetailResponse(data=RoomDetailData(
        room=_room_to_item(room),
        messages=messages,
        characters=ordered_chars,
    ))


class SendMessageRequest(BaseModel):
    content: str
    mentionedCharacterIds: Optional[List[str]] = None


@router.post("/rooms/{room_id}/messages")
async def send_room_message(
    room_id: str,
    req: SendMessageRequest,
    current_user: dict = Depends(get_current_user_jwt),
    db: AsyncSession = Depends(get_db),
    ai_service = Depends(get_ai_service),
):
    """Send a message and stream character speeches as SSE."""
    # Load room
    result = await db.execute(
        select(UserChatRoom).where(UserChatRoom.room_id == room_id)
    )
    room = result.scalar_one_or_none()
    if room is None or room.user_id != current_user["userId"]:
        raise HTTPException(status_code=404, detail="聊天室不存在")

    # Load characters in room order
    char_result = await db.execute(
        select(SquadCharacter).where(SquadCharacter.character_id.in_(room.character_ids))
    )
    char_map = {c.character_id: c for c in char_result.scalars().all()}
    speakers = [char_map[cid] for cid in room.character_ids if cid in char_map]

    # Persist user message
    user_msg = UserChatMessage(
        room_id=room_id,
        sender_type="user",
        sender_id=current_user["userId"],
        content=req.content,
        mentioned_character_ids=req.mentionedCharacterIds,
    )
    db.add(user_msg)
    await db.commit()

    # Stream speeches
    speech_service = SquadSpeechService(ai_service)

    async def event_stream():
        # Collect character speeches for persistence
        character_speeches: dict = {}  # character_id -> full content
        async for event in speech_service.stream_speeches(
            characters=speakers,
            topic=room.topic,
            user_content=req.content,
            mentioned_character_ids=req.mentionedCharacterIds,
        ):
            # Parse chunk events to accumulate content
            if event.startswith("data: ") and event.endswith("\n\n"):
                payload = event[6:].strip()
                if payload == "[DONE]":
                    yield event
                    break
                try:
                    data = json.loads(payload)
                    if data.get("type") == "chunk":
                        cid = data["characterId"]
                        character_speeches.setdefault(cid, [])
                        character_speeches[cid].append(data["content"])
                    elif data.get("type") == "end":
                        cid = data["characterId"]
                        content = "".join(character_speeches.get(cid, []))
                        if content:
                            # Persist character message
                            async with AsyncSessionLocal() as persist_session:
                                char_msg = UserChatMessage(
                                    room_id=room_id,
                                    sender_type="character",
                                    sender_id=cid,
                                    content=content,
                                )
                                persist_session.add(char_msg)
                                await persist_session.commit()
                except json.JSONDecodeError:
                    pass
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
