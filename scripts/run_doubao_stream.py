"""Stream Doubao responses character by character."""
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.ai.service import (  # noqa: E402
    ChatMessage,
    CharacterProfile,
    build_ai_service,
)


async def main() -> None:
    service = build_ai_service()

    async for chunk in service.stream_chat(
        character=CharacterProfile(
            name="stream-check",
            system_prompt="你是一位鼓舞人心的中文助理，逐步生成内容。",
            tag="INTJ",
        ),
        history=[ChatMessage(content="请用中文写一句鼓舞人心的话。", is_ai=False)],
        max_tokens=200,
    ):
        for char in chunk:
            print(char, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
