"""Helper to invoke Doubao via AIService and print the response."""
import asyncio
import sys
from pathlib import Path

import httpx

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.ai.service import (  # noqa: E402
    ChatMessage,
    CharacterProfile,
    build_ai_service,
)


async def main() -> None:
    try:
        service = build_ai_service()
        response = await service.chat(
            character=CharacterProfile(
                name="live-check",
                system_prompt="你是一位鼓励用户的中文 AI 助手，回答要积极、真诚。",
                tag="INTJ",
            ),
            history=[ChatMessage(content="请用中文写一句积极向上的话。", is_ai=False)],
        )
        print(response.text)
    except httpx.HTTPStatusError as exc:
        print("HTTP error:", exc.response.status_code)
        print(exc.response.text)
        raise


if __name__ == "__main__":
    asyncio.run(main())
