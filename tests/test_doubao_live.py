"""Fire a live Doubao request through AIService."""
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config.settings import get_settings  # noqa: E402
from app.services.ai.service import (  # noqa: E402
    ChatMessage,
    CharacterProfile,
    build_ai_service,
)


@pytest.mark.asyncio
async def test_doubao_live_generation():
    settings = get_settings()
    if not settings.DOUBAO_API_KEY:
        pytest.skip("DOUBAO_API_KEY not set.")

    service = build_ai_service()
    response = await service.chat(
        character=CharacterProfile(
            name="即时测试",
            system_prompt="你是一位鼓励用户的中文 AI 助手，回复需积极、真诚。",
            tag="INTJ",
        ),
        history=[ChatMessage(content="请用中文写一句积极向上的话。", is_ai=False)],
    )
    assert response.text
    print(response.text)
