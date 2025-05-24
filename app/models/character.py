"""
角色相关数据模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Enum, JSON, DECIMAL, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base
import uuid
import enum


class CharacterRarity(str, enum.Enum):
    """角色稀有度"""
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class UnlockType(str, enum.Enum):
    """解锁类型"""
    FREE = "free"
    PAID = "paid"
    VIP = "vip"
    LIMITED = "limited"


class CharacterDefinition(Base):
    """角色定义表"""
    __tablename__ = "character_definitions"
    
    character_id = Column(String, primary_key=True)
    dimension = Column(String(4), nullable=False, index=True)  # MBTI维度
    
    # 基本信息
    name = Column(String(50), nullable=False)
    english_name = Column(String(50), nullable=True)
    avatar = Column(String(255), nullable=True)
    background = Column(String(100), nullable=False)
    background_story = Column(Text, nullable=True)
    
    # 角色属性
    rarity = Column(Enum(CharacterRarity), default=CharacterRarity.COMMON, nullable=False)
    unlock_type = Column(Enum(UnlockType), default=UnlockType.FREE, nullable=False)
    price = Column(DECIMAL(10, 2), default=0, nullable=False)
    
    # 性格特征 (JSON格式)
    personality = Column(JSON, nullable=True)
    # 示例: {"traits": ["理性", "独立"], "catchphrase": "...", "communication": "..."}
    
    # 天赋技能 (JSON格式)
    talents = Column(JSON, nullable=True)
    # 示例: [{"skillId": "data_analysis", "level": 1, "maxLevel": 10}]
    
    # 可学习技能 (JSON格式)
    learnable_skills = Column(JSON, nullable=True)
    # 示例: [{"skillId": "investment_analysis", "unlockCondition": {...}}]
    
    # 状态
    is_enabled = Column(Boolean, default=True, nullable=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<CharacterDefinition(character_id='{self.character_id}', name='{self.name}')>"


class UserCharacter(Base):
    """用户角色关系表"""
    __tablename__ = "user_characters"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    character_id = Column(String, nullable=False, index=True)
    
    # 角色状态
    level = Column(Integer, default=1, nullable=False)
    experience = Column(Integer, default=0, nullable=False)
    
    # 解锁信息
    unlock_time = Column(DateTime(timezone=True), server_default=func.now())
    unlock_type = Column(Enum(UnlockType), nullable=False)
    
    # 使用统计
    total_messages = Column(Integer, default=0, nullable=False)
    total_likes = Column(Integer, default=0, nullable=False)
    last_active_time = Column(DateTime(timezone=True), nullable=True)
    
    # 状态标识
    is_active = Column(Boolean, default=False, nullable=False)  # 是否当前使用
    is_favorite = Column(Boolean, default=False, nullable=False)  # 是否收藏
    
    # 时间戳
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<UserCharacter(user_id='{self.user_id}', character_id='{self.character_id}')>"


class SkillDefinition(Base):
    """技能定义表"""
    __tablename__ = "skill_definitions"
    
    skill_id = Column(String, primary_key=True)
    skill_name = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # 技能分类
    
    # 技能描述
    description = Column(Text, nullable=True)
    max_level = Column(Integer, default=10, nullable=False)
    
    # 相关话题
    related_topics = Column(JSON, nullable=True)  # 相关话题列表
    
    # 级别效果描述 (JSON格式)
    level_effects = Column(JSON, nullable=True)
    # 示例: {"1": "基础能力", "5": "高级能力", "10": "专家级能力"}
    
    # 升级条件 (JSON格式)
    upgrade_conditions = Column(JSON, nullable=True)
    # 示例: [{"level": 2, "requirements": [...], "fastUpgrade": {...}}]
    
    is_enabled = Column(Boolean, default=True, nullable=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SkillDefinition(skill_id='{self.skill_id}', skill_name='{self.skill_name}')>"


class SkillProgress(Base):
    """技能进度表"""
    __tablename__ = "skill_progress"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    character_id = Column(String, nullable=False, index=True)
    skill_id = Column(String, nullable=False, index=True)
    
    # 技能状态
    level = Column(Integer, default=0, nullable=False)
    experience = Column(Integer, default=0, nullable=False)
    
    # 时间管理
    unlock_time = Column(DateTime(timezone=True), nullable=True)
    last_upgrade_time = Column(DateTime(timezone=True), nullable=True)
    
    # 使用统计
    total_usage_count = Column(Integer, default=0, nullable=False)
    total_experience_gained = Column(Integer, default=0, nullable=False)
    
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SkillProgress(user_id='{self.user_id}', character_id='{self.character_id}', skill_id='{self.skill_id}')>"


class SkillExperienceLog(Base):
    """技能经验记录表"""
    __tablename__ = "skill_experience_log"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    character_id = Column(String, nullable=False, index=True)
    skill_id = Column(String, nullable=False, index=True)
    
    # 关联信息
    message_id = Column(String, nullable=True, index=True)
    room_id = Column(String, nullable=True, index=True)
    
    # 经验详情
    experience_gained = Column(Integer, nullable=False)
    source = Column(String(50), nullable=False)  # topic_match, like, mention, room_bonus
    topic_relevance = Column(DECIMAL(3, 2), nullable=True)  # 话题相关度 0.00-1.00
    
    # 额外信息
    metadata = Column(JSON, nullable=True)  # 额外元数据
    
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<SkillExperienceLog(user_id='{self.user_id}', skill_id='{self.skill_id}', experience='{self.experience_gained}')>"


class CharacterStatistics(Base):
    """角色统计表"""
    __tablename__ = "character_statistics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    character_id = Column(String, nullable=False, index=True)
    
    # 使用统计
    total_users = Column(Integer, default=0, nullable=False)  # 拥有用户数
    total_messages = Column(Integer, default=0, nullable=False)  # 总消息数
    total_likes = Column(Integer, default=0, nullable=False)  # 总获赞数
    average_response_time = Column(DECIMAL(5, 2), default=0, nullable=False)  # 平均响应时间
    user_rating = Column(DECIMAL(3, 2), default=0, nullable=False)  # 用户评分
    
    # 话题专长度 (JSON格式)
    topic_expertise = Column(JSON, nullable=True)
    # 示例: {"investment": 0.85, "technology": 0.92}
    
    # 流行度统计
    popularity_score = Column(DECIMAL(5, 2), default=0, nullable=False)
    purchase_count = Column(Integer, default=0, nullable=False)  # 购买次数
    
    # 统计时间
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<CharacterStatistics(character_id='{self.character_id}', date='{self.date}')>" 