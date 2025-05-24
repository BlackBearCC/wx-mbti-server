"""
聊天室相关数据模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, DECIMAL
from sqlalchemy.sql import func
from app.config.database import Base
import uuid


class Room(Base):
    """聊天室表"""
    __tablename__ = "rooms"
    
    room_id = Column(String, primary_key=True)
    name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # emoji图标
    background = Column(String(255), nullable=True)  # 背景样式
    category = Column(String(50), nullable=False, index=True)  # 房间分类
    
    # 相关技能配置 (JSON格式)
    related_skills = Column(JSON, nullable=True)
    # 示例: ["investment_analysis", "data_analysis"]
    
    # 技能经验加成 (JSON格式)
    skill_bonus_multiplier = Column(JSON, nullable=True)
    # 示例: {"investment_analysis": 1.5, "data_analysis": 1.2}
    
    # 房间设置 (JSON格式)
    settings = Column(JSON, nullable=True)
    # 示例: {"maxMembers": 50, "allowGuestJoin": true, "moderationLevel": "low"}
    
    # 统计数据
    total_members = Column(Integer, default=0, nullable=False)
    active_characters = Column(Integer, default=0, nullable=False)
    skill_evolution_count = Column(Integer, default=0, nullable=False)
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Room(room_id='{self.room_id}', name='{self.name}')>"


class RoomMembership(Base):
    """房间成员关系表"""
    __tablename__ = "room_memberships"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # 成员状态
    join_time = Column(DateTime(timezone=True), server_default=func.now())
    last_active_time = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 成员统计
    message_count = Column(Integer, default=0, nullable=False)
    likes_given = Column(Integer, default=0, nullable=False)
    likes_received = Column(Integer, default=0, nullable=False)
    
    # 当前使用的角色
    current_character_id = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<RoomMembership(room_id='{self.room_id}', user_id='{self.user_id}')>"


class RoomStatistics(Base):
    """房间统计表"""
    __tablename__ = "room_statistics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # 活跃度统计
    active_members = Column(Integer, default=0, nullable=False)
    total_messages = Column(Integer, default=0, nullable=False)
    average_message_length = Column(DECIMAL(5, 2), default=0, nullable=False)
    
    # 角色活跃度 (JSON格式)
    character_activity = Column(JSON, nullable=True)
    # 示例: {"intj_scientist_001": {"messages": 50, "likes": 25}}
    
    # 话题分析 (JSON格式)
    topic_distribution = Column(JSON, nullable=True)
    # 示例: {"investment": 0.4, "technology": 0.3, "lifestyle": 0.3}
    
    # 技能提升统计
    skill_levelups = Column(Integer, default=0, nullable=False)
    
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<RoomStatistics(room_id='{self.room_id}', date='{self.date}')>"