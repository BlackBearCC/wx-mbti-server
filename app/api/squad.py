"""Squad API routes for MBTI personality squad feature."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.security import get_current_user_jwt
from app.models.squad import SquadCharacter, Topic
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
