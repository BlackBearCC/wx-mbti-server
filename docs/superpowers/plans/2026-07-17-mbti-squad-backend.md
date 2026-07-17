# MBTI 人格小分队 - 后端实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 MBTI 人格小分队前端提供完整后端 API——角色池、话题库、用户聊天室、流式发言、化身设置。

**Architecture:** 在现有 FastAPI 应用中新增 `squad` 模块（模型 + API + 服务），不污染现有 `characters`/`chat`/`rooms` 代码。新模型继承现有 `Base`，启动时 `Base.metadata.create_all` 自动建表。流式发言复用现有 `AIService.stream_chat`，通过 SSE（Server-Sent Events）流式推送 token。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL + Redis + MiniMax M3 (via OpenAI-compatible provider) + pytest + TestClient

## Global Constraints

- AI 模型必须用 MiniMax M3，禁用 Ark/Doubao
- MiniMax 关闭思考模式：`"thinking": {"type": "disabled"}`
- AI 输出 token 上限 8192
- JWT 认证依赖 `get_current_user_jwt`（位于 `app/core/security.py`）
- 数据库建表靠 `Base.metadata.create_all`（项目无 alembic migrations 目录）
- 测试用 `TestClient` + `dependency_overrides` 替换 AI service
- 测试 token 用 `dev-token`，但 `get_current_user_jwt` 不接受 dev-token（它要求真实 JWT），所以测试 fixture 必须同时 override `get_current_user_jwt` 返回假用户 dict，并懒加载创建一条 User 行（Task 6 的 `set_avatar_character` 会直接查 User 表）
- 测试假用户 ID 用 `test-squad-user`
- 代码注释用英文
- HTTP 响应统一格式 `{"code": 200, "data": {...}}` 或 `{"code": 200, "message": "...", "data": {...}}`

## File Structure

**新增文件：**
- `app/models/squad.py` — SquadCharacter / Topic / UserChatRoom / UserChatMessage 模型
- `app/api/squad.py` — squad 路由（characters / topics / rooms / messages）
- `app/services/squad_service.py` — 聊天室业务逻辑（流式发言调度 + SSE 推送）
- `app/services/squad_seed.py` — 16 角色 + 7 话题 seed 数据
- `tests/test_squad_api.py` — squad API 测试

**修改文件：**
- `app/models/user.py` — 加 `avatar_character_id` 和 `mbti_type` 字段
- `app/api/users.py` — 加化身设置/获取接口，UserProfileResponseData 加字段
- `app/core/security.py` — `get_current_user_jwt` 返回 dict 加 `mbtiType` 和 `avatarCharacterId`
- `app/main.py` — 注册 squad router + 启动时跑 seed

---

## Task 1: SquadCharacter 模型 + 16 角色 seed + GET /api/squad/characters

**Files:**
- Create: `app/models/squad.py`
- Create: `app/services/squad_seed.py`
- Create: `app/api/squad.py` (本任务只加 characters 路由)
- Modify: `app/main.py` (注册 router + 启动 seed)
- Test: `tests/test_squad_api.py`

**Interfaces:**
- Produces: `SquadCharacter` model, `GET /api/squad/characters` endpoint, `seed_squad_characters(session)` function

- [ ] **Step 1: Write the failing test**

Create `tests/test_squad_api.py`:

```python
"""Tests for squad API endpoints."""
import pytest
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient

from app.config.database import get_db
from app.core.security import get_current_user_jwt
from app.main import app
from app.models.user import User
from app.services.ai import get_ai_service
from app.services.ai.providers.base import AIChatResponse

TEST_TOKEN = "dev-token"
FAKE_USER_ID = "test-squad-user"


class _FakeAIService:
    async def chat(self, **kwargs) -> AIChatResponse:
        return AIChatResponse(text="fake", model="fake", usage={})

    async def stream_chat(self, **kwargs):
        for c in "hello":
            yield c


async def _override_auth(db: AsyncSession = Depends(get_db)) -> dict:
    """Override get_current_user_jwt: dev-token is not a real JWT, so we
    bypass decode_access_token and lazily ensure a User row exists for
    Task 6's set_avatar_character (which queries the User table directly)."""
    result = await db.execute(select(User).where(User.user_id == FAKE_USER_ID))
    if result.scalar_one_or_none() is None:
        db.add(User(
            user_id=FAKE_USER_ID,
            openid="test-openid-squad",
            nick_name="SquadTestUser",
        ))
        await db.commit()
    return {
        "userId": FAKE_USER_ID,
        "openid": "test-openid-squad",
        "nickName": "SquadTestUser",
        "avatarUrl": "",
        "gender": 0,
        "country": "",
        "province": "",
        "city": "",
        "userLevel": "normal",
        "totalMessages": 0,
        "totalLikes": 0,
        "ownedCharacters": 16,
        "totalSkillLevel": 0,
        "joinedRooms": [],
        "favoriteCharacters": [],
        "createTime": 0.0,
        "lastLoginTime": 0.0,
        "avatarCharacterId": "",
        "mbtiType": "",
    }


@pytest.fixture()
def client():
    async def _override_ai():
        return _FakeAIService()
    app.dependency_overrides[get_ai_service] = _override_ai
    app.dependency_overrides[get_current_user_jwt] = _override_auth
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_ai_service, None)
    app.dependency_overrides.pop(get_current_user_jwt, None)


def test_list_characters(client: TestClient):
    resp = client.get(
        "/api/squad/characters",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    chars = body["data"]["characters"]
    assert len(chars) == 16
    # 8 dimensions each has 2 characters
    dims = {c["dimension"] for c in chars}
    assert dims == set("EISNTFJP")
    # Each character has required fields
    for c in chars:
        assert "characterId" in c
        assert "name" in c
        assert "dimension" in c
        assert "persona" in c
        assert "avatar" in c
        assert "voiceStyle" in c
        assert "signature" in c
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_list_characters -v`
Expected: FAIL with 404 (route not registered)

- [ ] **Step 3: Create squad models**

Create `app/models/squad.py`:

```python
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
```

- [ ] **Step 4: Create seed data**

Create `app/services/squad_seed.py`:

```python
"""Seed data for squad characters and topics."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.squad import SquadCharacter, Topic
import structlog

logger = structlog.get_logger()

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
```

- [ ] **Step 5: Create squad API (characters route only)**

Create `app/api/squad.py`:

```python
"""Squad API routes for MBTI personality squad feature."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.security import get_current_user_jwt
from app.models.squad import SquadCharacter
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
```

- [ ] **Step 6: Register router + run seed on startup**

Modify `app/main.py` — add import and register router. Find the existing import line:

```python
from app.api import auth, users, characters, rooms, skills, chat, items, feedback, admin, home, service, service_ws
```

Change to:

```python
from app.api import auth, users, characters, rooms, skills, chat, items, feedback, admin, home, service, service_ws, squad
```

Add router registration after the existing `service_ws` line:

```python
app.include_router(squad.router, prefix="/api/squad", tags=["Squad"])
```

Add seed call inside the `lifespan` function, after `await init_db()` and `logger.info("✅ 数据库初始化完成")`:

```python
        # Seed squad data
        from app.config.database import AsyncSessionLocal
        from app.services.squad_seed import seed_squad_data
        async with AsyncSessionLocal() as session:
            await seed_squad_data(session)
        logger.info("✅ Squad seed 完成")
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_list_characters -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
cd wx-mbti-server
git add app/models/squad.py app/services/squad_seed.py app/api/squad.py app/main.py tests/test_squad_api.py
git commit -m "feat(squad): add SquadCharacter model, 16-char seed, GET /api/squad/characters"
```

---

## Task 2: Topic 模型 + GET /api/squad/topics

**Files:**
- Modify: `app/api/squad.py` (add topics route)
- Modify: `tests/test_squad_api.py` (add topic test)

**Interfaces:**
- Produces: `GET /api/squad/topics` endpoint
- Consumes: `Topic` model from Task 1, `seed_squad_data` from Task 1

- [ ] **Step 1: Write the failing test**

Append to `tests/test_squad_api.py`:

```python
def test_list_topics(client: TestClient):
    resp = client.get(
        "/api/squad/topics",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    topics = body["data"]["topics"]
    assert len(topics) == 7
    for t in topics:
        assert "topicId" in t
        assert "title" in t
        assert "recommendedCharacterIds" in t
        assert isinstance(t["recommendedCharacterIds"], list)
        assert len(t["recommendedCharacterIds"]) >= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_list_topics -v`
Expected: FAIL with 404

- [ ] **Step 3: Add topics route to squad API**

Add to `app/api/squad.py` (after `CharacterItem` class, before `list_characters`):

```python
from app.models.squad import Topic


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_list_topics -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd wx-mbti-server
git add app/api/squad.py tests/test_squad_api.py
git commit -m "feat(squad): add GET /api/squad/topics"
```

---

## Task 3: UserChatRoom CRUD - POST /api/squad/rooms + GET /api/squad/rooms

**Files:**
- Modify: `app/api/squad.py` (add rooms routes)
- Modify: `tests/test_squad_api.py` (add room tests)

**Interfaces:**
- Produces: `POST /api/squad/rooms` (create room), `GET /api/squad/rooms` (list user rooms)
- Consumes: `UserChatRoom` model from Task 1, `get_current_user_jwt`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_squad_api.py`:

```python
def test_create_and_list_rooms(client: TestClient):
    # Create a room
    create_resp = client.post(
        "/api/squad/rooms",
        json={
            "title": "裸辞讨论",
            "topic": "裸辞去追梦想，值得吗？",
            "characterIds": ["char_n_1", "char_j_1", "char_f_1"],
        },
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 200
    room = create_body["data"]["room"]
    assert room["roomId"]
    assert room["title"] == "裸辞讨论"
    assert room["topic"] == "裸辞去追梦想，值得吗？"
    assert room["characterIds"] == ["char_n_1", "char_j_1", "char_f_1"]

    # List rooms
    list_resp = client.get(
        "/api/squad/rooms",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["code"] == 200
    rooms = list_body["data"]["rooms"]
    assert len(rooms) >= 1
    assert any(r["roomId"] == room["roomId"] for r in rooms)


def test_create_room_validates_character_limit(client: TestClient):
    """Cannot create room with more than 8 characters."""
    too_many = [f"char_{d}_1" for d in "EISNTFJP"] + ["char_e_2"]
    resp = client.post(
        "/api/squad/rooms",
        json={
            "title": "too many",
            "topic": "test",
            "characterIds": too_many,
        },
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_create_and_list_rooms tests/test_squad_api.py::test_create_room_validates_character_limit -v`
Expected: FAIL with 404

- [ ] **Step 3: Add rooms routes**

Add to `app/api/squad.py`:

```python
from app.models.squad import UserChatRoom
from datetime import datetime


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_create_and_list_rooms tests/test_squad_api.py::test_create_room_validates_character_limit -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd wx-mbti-server
git add app/api/squad.py tests/test_squad_api.py
git commit -m "feat(squad): add POST/GET /api/squad/rooms for user chat rooms"
```

---

## Task 4: GET /api/squad/rooms/{id} - 聊天室详情 + 历史消息

**Files:**
- Modify: `app/api/squad.py` (add room detail route)
- Modify: `tests/test_squad_api.py` (add room detail test)

**Interfaces:**
- Produces: `GET /api/squad/rooms/{room_id}` returning room + messages
- Consumes: `UserChatRoom`, `UserChatMessage`, `SquadCharacter` from Task 1, `RoomItem` from Task 3

- [ ] **Step 1: Write the failing test**

Append to `tests/test_squad_api.py`:

```python
def test_get_room_detail(client: TestClient):
    # Create a room first
    create_resp = client.post(
        "/api/squad/rooms",
        json={
            "title": "test detail",
            "topic": "test topic",
            "characterIds": ["char_n_1"],
        },
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    room_id = create_resp.json()["data"]["room"]["roomId"]

    # Get room detail
    resp = client.get(
        f"/api/squad/rooms/{room_id}",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["room"]["roomId"] == room_id
    assert data["room"]["topic"] == "test topic"
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) == 0  # No messages yet
    # Characters included
    assert len(data["characters"]) == 1
    assert data["characters"][0]["characterId"] == "char_n_1"


def test_get_room_detail_404(client: TestClient):
    resp = client.get(
        "/api/squad/rooms/nonexistent",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_get_room_detail tests/test_squad_api.py::test_get_room_detail_404 -v`
Expected: FAIL with 404 or 405

- [ ] **Step 3: Add room detail route**

Add to `app/api/squad.py`:

```python
from app.models.squad import UserChatMessage


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_get_room_detail tests/test_squad_api.py::test_get_room_detail_404 -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd wx-mbti-server
git add app/api/squad.py tests/test_squad_api.py
git commit -m "feat(squad): add GET /api/squad/rooms/{id} with messages and characters"
```

---

## Task 5: POST /api/squad/rooms/{id}/messages - 发消息触发 LLM 流式

**Files:**
- Create: `app/services/squad_service.py`
- Modify: `app/api/squad.py` (add send message route)
- Modify: `tests/test_squad_api.py` (add send message test)

**Interfaces:**
- Produces: `POST /api/squad/rooms/{id}/messages` returning SSE stream of character speeches, `SquadSpeechService` class
- Consumes: `AIService.stream_chat` from `app.services.ai`, `UserChatRoom`, `UserChatMessage`, `SquadCharacter`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_squad_api.py`:

```python
def test_send_message_streams_character_speeches(client: TestClient):
    # Create a room
    create_resp = client.post(
        "/api/squad/rooms",
        json={
            "title": "stream test",
            "topic": "裸辞",
            "characterIds": ["char_n_1", "char_j_1"],
        },
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    room_id = create_resp.json()["data"]["room"]["roomId"]

    # Send message and stream response
    with client.stream(
        "POST",
        f"/api/squad/rooms/{room_id}/messages",
        json={"content": "我该裸辞吗？"},
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    ) as s:
        events = []
        for line in s.iter_lines():
            if line:
                events.append(line)
        # Should have at least 2 character speech events (one per character)
        speech_events = [e for e in events if e.startswith("data: ")]
        assert len(speech_events) >= 2
        # First event should be character_n_1 starting
        assert "char_n_1" in speech_events[0] or "char_j_1" in speech_events[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_send_message_streams_character_speeches -v`
Expected: FAIL with 404 or 405

- [ ] **Step 3: Create squad service**

Create `app/services/squad_service.py`:

```python
"""Squad speech service - orchestrates character streaming speeches."""
from __future__ import annotations

import asyncio
import json
import structlog
from typing import AsyncIterator, List, Optional

from app.services.ai import AIService
from app.services.ai.service import CharacterProfile, ChatMessage
from app.models.squad import SquadCharacter

logger = structlog.get_logger()


class SquadSpeechService:
    """Orchestrates sequential character speeches for a squad chat room."""

    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service

    def _build_system_prompt(
        self,
        character: SquadCharacter,
        topic: str,
        previous_speeches: List[dict],
    ) -> str:
        """Build system prompt for a character speech."""
        prev_text = ""
        if previous_speeches:
            prev_lines = [
                f"{p['name']}({p['dimension']}): {p['content']}"
                for p in previous_speeches
            ]
            prev_text = "\n前序角色发言：\n" + "\n".join(prev_lines)
        return (
            f"你是{character.name}，{character.persona}\n"
            f"你的维度是{character.dimension}，表达风格：{character.voice_style}\n"
            f"你的标志性观点：{character.signature}\n"
            f"当前话题：{topic}{prev_text}\n"
            f"请以你的视角发言，120字内，不要重复别人说过的观点，直接给出你的看法，不要加角色名前缀。"
        )

    async def stream_speeches(
        self,
        characters: List[SquadCharacter],
        topic: str,
        user_content: str,
        mentioned_character_ids: Optional[List[str]] = None,
        max_tokens: int = 600,
    ) -> AsyncIterator[str]:
        """Stream speeches from characters sequentially.

        Yields SSE-formatted events:
        - {"type":"start","characterId":"...","name":"...","dimension":"..."}
        - {"type":"chunk","characterId":"...","content":"..."}
        - {"type":"end","characterId":"..."}
        - {"type":"error","characterId":"...","message":"..."}
        - {"type":"done"}
        """
        # Filter by mentioned if any
        if mentioned_character_ids:
            speakers = [c for c in characters if c.character_id in mentioned_character_ids]
        else:
            speakers = list(characters)

        previous_speeches: List[dict] = []

        for char in speakers:
            system_prompt = self._build_system_prompt(char, topic, previous_speeches)
            character_profile = CharacterProfile(
                name=char.name,
                system_prompt=system_prompt,
                tag=char.dimension,
            )
            history = [ChatMessage(content=user_content, is_ai=False)]

            # Start event
            yield f"data: {json.dumps({'type': 'start', 'characterId': char.character_id, 'name': char.name, 'dimension': char.dimension})}\n\n"

            full_content = []
            try:
                async for chunk in self.ai_service.stream_chat(
                    character=character_profile,
                    history=history,
                    character_id=char.character_id,
                    max_tokens=max_tokens,
                    temperature=0.7,
                ):
                    full_content.append(chunk)
                    yield f"data: {json.dumps({'type': 'chunk', 'characterId': char.character_id, 'content': chunk})}\n\n"
            except Exception as e:
                logger.error("character speech failed", character_id=char.character_id, error=str(e))
                yield f"data: {json.dumps({'type': 'error', 'characterId': char.character_id, 'message': f'{char.name}暂时离线'})}\n\n"
                continue

            # End event
            yield f"data: {json.dumps({'type': 'end', 'characterId': char.character_id})}\n\n"

            # Record for next character's context
            previous_speeches.append({
                "name": char.name,
                "dimension": char.dimension,
                "content": "".join(full_content),
            })

            # 200ms delay between characters
            await asyncio.sleep(0.2)

        yield "data: [DONE]\n\n"
```

- [ ] **Step 4: Add send message route**

Add to `app/api/squad.py`:

```python
from fastapi.responses import StreamingResponse
from app.services.squad_service import SquadSpeechService
from app.services.ai import get_ai_service
from app.models.squad import UserChatMessage
import json


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
```

Add the import at the top of `app/api/squad.py`:

```python
from typing import List, Optional
from app.config.database import get_db, AsyncSessionLocal
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_send_message_streams_character_speeches -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd wx-mbti-server
git add app/services/squad_service.py app/api/squad.py tests/test_squad_api.py
git commit -m "feat(squad): add POST /api/squad/rooms/{id}/messages with SSE streaming"
```

---

## Task 6: User 加化身字段 + PUT/GET /api/user/avatar-character

**Files:**
- Modify: `app/models/user.py` (add fields)
- Modify: `app/core/security.py` (return dict adds fields)
- Modify: `app/api/users.py` (add avatar endpoints, extend profile)
- Modify: `tests/test_squad_api.py` (add avatar test)

**Interfaces:**
- Produces: `PUT /api/user/avatar-character`, `GET /api/user/avatar-character`, User model with `avatar_character_id` and `mbti_type` fields
- Consumes: `SquadCharacter` from Task 1, `get_current_user_jwt`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_squad_api.py`:

```python
def test_set_and_get_avatar_character(client: TestClient):
    # Set avatar
    set_resp = client.put(
        "/api/user/avatar-character",
        json={"avatarCharacterId": "char_n_1", "mbtiType": "INTJ"},
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert set_resp.status_code == 200
    set_body = set_resp.json()
    assert set_body["code"] == 200
    assert set_body["data"]["avatarCharacterId"] == "char_n_1"
    assert set_body["data"]["mbtiType"] == "INTJ"

    # Get avatar
    get_resp = client.get(
        "/api/user/avatar-character",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert get_resp.status_code == 200
    get_body = get_resp.json()
    assert get_body["code"] == 200
    assert get_body["data"]["avatarCharacterId"] == "char_n_1"
    assert get_body["data"]["mbtiType"] == "INTJ"


def test_set_avatar_validates_character_exists(client: TestClient):
    resp = client.put(
        "/api/user/avatar-character",
        json={"avatarCharacterId": "nonexistent", "mbtiType": "INTJ"},
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_set_and_get_avatar_character tests/test_squad_api.py::test_set_avatar_validates_character_exists -v`
Expected: FAIL with 404

- [ ] **Step 3: Add fields to User model**

Modify `app/models/user.py` — find the `User` class, add after `is_deleted` field (before `__repr__`):

```python
    # MBTI squad fields
    avatar_character_id = Column(String, nullable=True)  # Squad character ID
    mbti_type = Column(String(4), nullable=True)  # 'INTJ' etc
```

- [ ] **Step 4: Extend security.py return dict**

Modify `app/core/security.py` — in `get_current_user_jwt`, find the return dict and add fields. The return dict currently ends with:

```python
        "lastLoginTime": user.last_login_time.timestamp() if user.last_login_time else time.time(),
    }
```

Change to:

```python
        "lastLoginTime": user.last_login_time.timestamp() if user.last_login_time else time.time(),
        "avatarCharacterId": user.avatar_character_id or "",
        "mbtiType": user.mbti_type or "",
    }
```

- [ ] **Step 5: Add avatar endpoints to users API**

Modify `app/api/users.py` — add at the end of the file:

```python
from sqlalchemy import select as _select
from app.config.database import get_db as _get_db
from app.models.squad import SquadCharacter
from sqlalchemy.ext.asyncio import AsyncSession


class SetAvatarRequest(BaseModel):
    avatarCharacterId: str
    mbtiType: str


class AvatarResponseData(BaseModel):
    userId: str
    avatarCharacterId: str
    mbtiType: str


class AvatarResponse(BaseModel):
    code: int = 200
    data: AvatarResponseData


@router.put("/avatar-character", response_model=AvatarResponse)
async def set_avatar_character(
    req: SetAvatarRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db),
):
    """Set user's avatar character and MBTI type."""
    # Validate character exists
    char_result = await db.execute(
        _select(SquadCharacter).where(SquadCharacter.character_id == req.avatarCharacterId)
    )
    if char_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="角色不存在")

    # Load user and update
    user_result = await db.execute(
        _select(User).where(User.user_id == current_user["userId"])
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.avatar_character_id = req.avatarCharacterId
    user.mbti_type = req.mbtiType
    await db.commit()

    return AvatarResponse(data=AvatarResponseData(
        userId=user.user_id,
        avatarCharacterId=user.avatar_character_id,
        mbtiType=user.mbti_type,
    ))


@router.get("/avatar-character", response_model=AvatarResponse)
async def get_avatar_character(
    current_user: dict = Depends(get_current_user),
):
    """Get user's avatar character and MBTI type."""
    return AvatarResponse(data=AvatarResponseData(
        userId=current_user["userId"],
        avatarCharacterId=current_user.get("avatarCharacterId", ""),
        mbtiType=current_user.get("mbtiType", ""),
    ))
```

Add the `User` import at the top of `app/api/users.py` if not present:

```python
from app.models.user import User
```

Also extend `UserProfileResponseData` in `app/api/users.py` — find the class and add fields before `joinedRooms`:

```python
    mbtiType: Optional[str] = None
    avatarCharacterId: Optional[str] = None
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py::test_set_and_get_avatar_character tests/test_squad_api.py::test_set_avatar_validates_character_exists -v`
Expected: PASS

- [ ] **Step 7: Run all squad tests to verify no regressions**

Run: `cd wx-mbti-server && python -m pytest tests/test_squad_api.py -v`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
cd wx-mbti-server
git add app/models/user.py app/core/security.py app/api/users.py tests/test_squad_api.py
git commit -m "feat(squad): add avatar_character_id and mbti_type to User, PUT/GET /api/user/avatar-character"
```

---

## Self-Review Notes

**Spec coverage check:**
- §2 角色体系 → Task 1 (SquadCharacter + 16 seed)
- §3 调度逻辑 → Task 5 (SquadSpeechService stream_speeches, mentioned filter)
- §4 群聊泡泡流 UI → 后端不涉及（前端 plan）
- §5 测试与化身机制 → Task 6 (avatar_character_id, mbti_type)
- §6 首页与冷启动 → Task 1 (characters), Task 2 (topics), Task 3 (rooms)
- §7 数据流 → Task 1-5 全覆盖
- §7.1 数据表 → Task 1 创建 4 表，Task 6 加 users 字段
- §7.1 接口 → 全部 7 接口覆盖
- §7.2 流式机制 → Task 5 SSE 流式
- §7.3 LLM Prompt 注入 → Task 5 `_build_system_prompt`
- §7.5 错误恢复 → Task 5 try/except + error event

**Placeholder scan:** 无 TBD/TODO，所有代码完整。

**Type consistency check:**
- `CharacterItem` / `RoomItem` / `MessageItem` / `TopicItem` 在所有任务中字段名一致
- `SquadSpeechService.stream_speeches` 在 Task 5 定义，被 `send_room_message` 调用，签名匹配
- `seed_squad_data` 在 Task 1 定义，被 `lifespan` 调用
- `User.avatar_character_id` / `mbti_type` 在 Task 6 添加，security.py 和 users.py 都使用同名字段
