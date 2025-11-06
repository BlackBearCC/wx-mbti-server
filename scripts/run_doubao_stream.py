"""Stream Doubao responses character by character."""
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.ai.service import (  # noqa: E402
    AIChatRequest,
    AIMessage,
    build_ai_service,
)


async def main() -> None:
    service = build_ai_service()
    provider = service.providers[service.default_provider]

    request = AIChatRequest(
        messages=[
            AIMessage(role="system", content="你是一位积极向上的中文助手。"),
            AIMessage(role="user", content="请用中文写一句鼓舞人心的话。"),
        ],
        max_tokens=200,
    )

    async for chunk in provider.stream(request):
        for char in chunk:
            print(char, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
