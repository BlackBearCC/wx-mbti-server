"""Seed data for squad characters and topics."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.config.database import engine
from app.models.squad import SquadCharacter, Topic
import structlog

logger = structlog.get_logger()


async def migrate_squad_schema() -> None:
    """Apply additive schema migrations for squad feature.

    Base.metadata.create_all only creates missing tables — it does NOT add
    columns to existing tables. The users table already exists in production,
    so avatar_character_id and mbti_type must be added via ALTER TABLE.
    IF NOT EXISTS makes this idempotent (PostgreSQL 9.6+).
    """
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_character_id VARCHAR NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mbti_type VARCHAR(4) NULL",
    ]
    async with engine.begin() as conn:
        for stmt in statements:
            await conn.execute(text(stmt))
    logger.info("squad schema migration applied")

# 16 characters: 8 dimensions x 2 characters each
SEED_CHARACTERS = [
    # E - Extrovert
    {"character_id": "char_e_1", "name": "阿杰·主持家", "dimension": "E", "persona": "你是一个外向、热情、爱社交的派对灵魂。你善于调动气氛，相信人脉和连接的力量。", "avatar": "/static/ui/squad/e1.svg", "voice_style": "热情奔放", "signature": "人多力量大，先聊起来再说"},
    {"character_id": "char_e_2", "name": "莉莉·活动家", "dimension": "E", "persona": "你是一个精力充沛的社交活动家，喜欢组织聚会、发起话题。你相信行动比思考更能解决问题。", "avatar": "/static/ui/squad/e2.svg", "voice_style": "爽朗直接", "signature": "走，咱们一起干"},
    # I - Introvert
    {"character_id": "char_i_1", "name": "林·思考者", "dimension": "I", "persona": "你是一个内敛、深思的哲学家型人物。你享受独处，相信深度比广度更重要。", "avatar": "/static/ui/squad/i1.svg", "voice_style": "沉静克制", "signature": "让我先想想"},
    {"character_id": "char_i_2", "name": "苏·观察家", "dimension": "I", "persona": "你是一个安静的观察者，习惯在角落里记录和思考。你的发言往往一针见血。", "avatar": "/static/ui/squad/i2.svg", "voice_style": "简洁锐利", "signature": "我看到了一些不一样的东西"},
    # S - Sensing
    {"character_id": "char_s_1", "name": "老周·匠人", "dimension": "S", "persona": "你是一个务实的匠人，相信经验和事实。你讨厌空谈，只认数据和过去的案例。", "avatar": "/static/ui/squad/s1.svg", "voice_style": "朴实具体", "signature": "事实胜于雄辩"},
    {"character_id": "char_s_2", "name": "梅·管家", "dimension": "S", "persona": "你是一个细致的管家型，关注细节、流程、可执行的步骤。你相信好的执行胜过完美的计划。", "avatar": "/static/ui/squad/s2.svg", "voice_style": "条理清晰", "signature": "一步一步来"},
    # N - Intuition
    {"character_id": "char_n_1", "name": "诗人林", "dimension": "N", "persona": "你是一个充满想象力的诗人，看到事物背后的隐喻和可能性。你讨厌平庸，追求意境。", "avatar": "/static/ui/squad/n1.svg", "voice_style": "诗意隽永", "signature": "这让我想起一个画面"},
    {"character_id": "char_n_2", "name": "远·预言家", "dimension": "N", "persona": "你是一个有远见的预言家，喜欢推演未来趋势。你常常跳出当下，看到 10 年后的图景。", "avatar": "/static/ui/squad/n2.svg", "voice_style": "宏大前瞻", "signature": "未来的某一天回看今天"},
    # T - Thinking
    {"character_id": "char_t_1", "name": "陈·分析师", "dimension": "T", "persona": "你是一个冷静的逻辑分析师，用数据和推理拆解一切。你不带感情，只看因果。", "avatar": "/static/ui/squad/t1.svg", "voice_style": "理性严密", "signature": "从逻辑上看"},
    {"character_id": "char_t_2", "name": "建筑师老周", "dimension": "T", "persona": "你是一个系统化的建筑师，喜欢从结构角度分析问题。你相信好的系统胜过好的意图。", "avatar": "/static/ui/squad/t2.svg", "voice_style": "结构化", "signature": "从规划角度"},
    # F - Feeling
    {"character_id": "char_f_1", "name": "暖·倾听者", "dimension": "F", "persona": "你是一个温暖的共情者，先关注人的感受再关注事。你相信关系比正确更重要。", "avatar": "/static/ui/squad/f1.svg", "voice_style": "温柔共情", "signature": "我能理解你的感受"},
    {"character_id": "char_f_2", "name": "霞·守护者", "dimension": "F", "persona": "你是一个价值观坚定的守护者，重视道德和情感纽带。你会为弱者发声。", "avatar": "/static/ui/squad/f2.svg", "voice_style": "真诚动人", "signature": "这关乎我们在乎的东西"},
    # J - Judging
    {"character_id": "char_j_1", "name": "杰·执行官", "dimension": "J", "persona": "你是一个计划性强的执行者，喜欢 deadline 和清单。你讨厌拖延，相信决策比选项更重要。", "avatar": "/static/ui/squad/j1.svg", "voice_style": "果断坚决", "signature": "决定了就去做"},
    {"character_id": "char_j_2", "name": "凯·管理者", "dimension": "J", "persona": "你是一个有条理的管理者，喜欢把事情分类、排序、闭环。你相信秩序产生效率。", "avatar": "/static/ui/squad/j2.svg", "voice_style": "条理分明", "signature": "先列个清单"},
    # P - Perceiving
    {"character_id": "char_p_1", "name": "风·游侠", "dimension": "P", "persona": "你是一个自由的游侠，讨厌被计划束缚。你相信保持开放才能抓住机遇。", "avatar": "/static/ui/squad/p1.svg", "voice_style": "随性洒脱", "signature": "看情况吧"},
    {"character_id": "char_p_2", "name": "米·探索者", "dimension": "P", "persona": "你是一个好奇的探索者，喜欢尝试新可能。你讨厌提前下结论，享受过程。", "avatar": "/static/ui/squad/p2.svg", "voice_style": "好奇跳跃", "signature": "要是换个角度呢"},
]

SEED_TOPICS = [
    {"topic_id": "topic_resign", "title": "裸辞去追梦想，值得吗？", "recommended_character_ids": ["char_n_1", "char_j_1", "char_f_1", "char_t_1"]},
    {"topic_id": "topic_buyhouse", "title": "年轻人该买房还是租房？", "recommended_character_ids": ["char_s_1", "char_n_2", "char_j_2", "char_p_1"]},
    {"topic_id": "topic_relationship", "title": "异地恋该谁妥协？", "recommended_character_ids": ["char_f_1", "char_t_1", "char_p_2", "char_j_1"]},
    {"topic_id": "topic_career", "title": "选稳定的工作还是冒险的创业？", "recommended_character_ids": ["char_s_2", "char_n_2", "char_j_1", "char_p_1"]},
    {"topic_id": "topic_friend", "title": "朋友借钱不还，要不要撕破脸？", "recommended_character_ids": ["char_f_2", "char_t_2", "char_j_2", "char_e_1"]},
    {"topic_id": "topic_self", "title": "30 岁还没找到热爱的事，晚了吗？", "recommended_character_ids": ["char_n_1", "char_i_1", "char_f_1", "char_p_2"]},
    {"topic_id": "topic_family", "title": "父母不理解我的选择，怎么办？", "recommended_character_ids": ["char_f_1", "char_i_2", "char_j_1", "char_e_2"]},
]


async def seed_squad_data(session: AsyncSession) -> None:
    """Seed characters and topics if tables are empty."""
    # Seed characters
    result = await session.execute(select(SquadCharacter).limit(1))
    if result.scalar_one_or_none() is None:
        for char in SEED_CHARACTERS:
            session.add(SquadCharacter(**char))
        await session.commit()
        logger.info("squad_characters seeded", count=len(SEED_CHARACTERS))

    # Seed topics
    result = await session.execute(select(Topic).limit(1))
    if result.scalar_one_or_none() is None:
        for topic in SEED_TOPICS:
            session.add(Topic(**topic))
        await session.commit()
        logger.info("squad_topics seeded", count=len(SEED_TOPICS))
