"""Squad models for MBTI personality squad feature."""
from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.config.database import Base
import uuid


class SquadCharacter(Base):
    """Squad character definition - 16 characters across 8 MBTI dimensions."""
    __tablename__ = "squad_characters"

    character_id = Column(String, primary_key=True)
    name = Column(String(64), nullable=False)
    dimension = Column(String(1), nullable=False, index=True)  # E/I/S/N/T/F/J/P
    persona = Column(Text, nullable=False)
    avatar = Column(String(256), nullable=False)
    voice_style = Column(String(64), nullable=False)
    signature = Column(String(256), nullable=False)
    unlock_type = Column(String(16), default="free", nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())


class Topic(Base):
    """Discussion topic library."""
    __tablename__ = "squad_topics"

    topic_id = Column(String, primary_key=True)
    title = Column(String(256), nullable=False)
    recommended_character_ids = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())


class UserChatRoom(Base):
    """User's personal chat room with selected characters."""
    __tablename__ = "user_chat_rooms"

    room_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    title = Column(String(256), nullable=False)
    topic = Column(Text, nullable=False)
    character_ids = Column(JSON, nullable=False)  # ["char_n_1", "char_t_1", ...]
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    last_active_time = Column(DateTime(timezone=True), server_default=func.now())


class UserChatMessage(Base):
    """Messages in user chat rooms."""
    __tablename__ = "user_chat_messages"

    message_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, nullable=False, index=True)
    sender_type = Column(String(16), nullable=False)  # 'user' | 'character'
    sender_id = Column(String, nullable=False)  # user_id or character_id
    content = Column(Text, nullable=False)
    mentioned_character_ids = Column(JSON, nullable=True)  # for @ summons
    create_time = Column(DateTime(timezone=True), server_default=func.now())
