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
