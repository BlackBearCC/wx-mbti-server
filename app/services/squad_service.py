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
