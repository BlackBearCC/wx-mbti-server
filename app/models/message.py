"""
消息相关数据模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, DECIMAL, Enum
from sqlalchemy.sql import func
from app.config.database import Base
import uuid
import enum


class MessageType(str, enum.Enum):
    """消息类型"""
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class Message(Base):
    """消息表"""
    __tablename__ = "messages"
    
    message_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, nullable=False, index=True)
    
    # 发送者信息
    from_user_id = Column(String, nullable=True, index=True)  # 用户消息时非空
    from_type = Column(Enum(MessageType), nullable=False)
    character_id = Column(String, nullable=True, index=True)  # AI消息时非空
    
    # 消息内容
    content = Column(Text, nullable=False)
    reply_to_message_id = Column(String, nullable=True, index=True)  # 回复的消息ID
    
    # 提及和技能 (JSON格式)
    mentions = Column(JSON, nullable=True)  # @的角色ID列表
    skills_used = Column(JSON, nullable=True)  # 使用的技能列表
    
    # AI相关数据
    topic_relevance = Column(DECIMAL(3, 2), nullable=True)  # 话题相关度
    experience_gained = Column(JSON, nullable=True)  # 获得的经验分配
    
    # 互动统计
    total_likes = Column(Integer, default=0, nullable=False)
    
    # 状态
    is_deleted = Column(Boolean, default=False, nullable=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Message(message_id='{self.message_id}', from_type='{self.from_type}')>"


class MessageLike(Base):
    """消息点赞表"""
    __tablename__ = "message_likes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # 点赞信息
    like_time = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)  # 是否有效（取消点赞时设为False）
    
    def __repr__(self):
        return f"<MessageLike(message_id='{self.message_id}', user_id='{self.user_id}')>"


class MessageReport(Base):
    """消息举报表"""
    __tablename__ = "message_reports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, nullable=False, index=True)
    reporter_user_id = Column(String, nullable=False, index=True)
    
    # 举报信息
    report_type = Column(String(50), nullable=False)  # 举报类型
    report_reason = Column(Text, nullable=True)  # 举报原因
    
    # 处理状态
    status = Column(String(20), default="pending", nullable=False)  # pending, reviewed, resolved
    admin_notes = Column(Text, nullable=True)  # 管理员备注
    
    # 时间戳
    report_time = Column(DateTime(timezone=True), server_default=func.now())
    review_time = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<MessageReport(message_id='{self.message_id}', report_type='{self.report_type}')>"


class ConversationContext(Base):
    """对话上下文表"""
    __tablename__ = "conversation_contexts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    character_id = Column(String, nullable=False, index=True)
    
    # 上下文数据 (JSON格式)
    context_data = Column(JSON, nullable=True)
    # 示例: {"recent_topics": [...], "mood": "friendly", "conversation_stage": "greeting"}
    
    # 对话历史摘要
    conversation_summary = Column(Text, nullable=True)
    last_message_id = Column(String, nullable=True)
    
    # 上下文状态
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 上下文过期时间
    
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<ConversationContext(room_id='{self.room_id}', user_id='{self.user_id}', character_id='{self.character_id}')>" 