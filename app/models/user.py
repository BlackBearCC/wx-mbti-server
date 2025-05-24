"""
用户相关数据模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.config.database import Base
import uuid
import enum


class UserLevel(str, enum.Enum):
    """用户等级枚举"""
    NORMAL = "normal"
    VIP = "vip"
    PREMIUM = "premium"


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    openid = Column(String(64), unique=True, nullable=False, index=True)
    unionid = Column(String(64), nullable=True, index=True)
    
    # 基本信息
    nick_name = Column(String(50), nullable=False)
    avatar_url = Column(String(255), nullable=True)
    gender = Column(Integer, default=0)  # 0未知 1男 2女
    country = Column(String(50), nullable=True)
    province = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    
    # 用户等级和经验
    user_level = Column(Enum(UserLevel), default=UserLevel.NORMAL, nullable=False)
    experience = Column(Integer, default=0, nullable=False)
    
    # 统计数据
    total_messages = Column(Integer, default=0, nullable=False)
    total_likes = Column(Integer, default=0, nullable=False)
    total_characters = Column(Integer, default=16, nullable=False)  # 拥有角色数
    total_skill_level = Column(Integer, default=0, nullable=False)  # 所有技能等级总和
    
    # 时间戳
    last_login_time = Column(DateTime(timezone=True), server_default=func.now())
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f"<User(user_id='{self.user_id}', nick_name='{self.nick_name}')>"


class UserSession(Base):
    """用户会话表"""
    __tablename__ = "user_sessions"
    
    session_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    session_key = Column(String(255), nullable=True)  # 微信session_key
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    
    # 会话信息
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    platform = Column(String(50), nullable=True)  # 微信小程序平台信息
    
    # 时间管理
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_active_time = Column(DateTime(timezone=True), server_default=func.now())
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)


class UserStatistics(Base):
    """用户统计表"""
    __tablename__ = "user_statistics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # 每日统计
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    messages_count = Column(Integer, default=0, nullable=False)
    likes_received = Column(Integer, default=0, nullable=False)
    likes_given = Column(Integer, default=0, nullable=False)
    active_minutes = Column(Integer, default=0, nullable=False)  # 活跃分钟数
    rooms_visited = Column(JSON, nullable=True)  # 访问的房间列表
    
    # 技能相关统计
    skill_experience_gained = Column(Integer, default=0, nullable=False)
    skill_levelups = Column(Integer, default=0, nullable=False)
    
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<UserStatistics(user_id='{self.user_id}', date='{self.date}')>"


class UserAchievement(Base):
    """用户成就表"""
    __tablename__ = "user_achievements"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    achievement_id = Column(String(100), nullable=False)
    
    # 成就信息
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    category = Column(String(50), nullable=True)  # 成就分类
    rarity = Column(String(20), nullable=True)  # 稀有度
    
    # 解锁信息
    unlock_time = Column(DateTime(timezone=True), server_default=func.now())
    progress = Column(Integer, default=100, nullable=False)  # 完成进度百分比
    metadata = Column(JSON, nullable=True)  # 额外元数据
    
    def __repr__(self):
        return f"<UserAchievement(user_id='{self.user_id}', achievement_id='{self.achievement_id}')>" 