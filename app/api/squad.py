"""Squad API routes for MBTI personality squad feature."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.security import get_current_user_jwt
from app.models.squad import SquadCharacter, Topic, UserChatRoom
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
