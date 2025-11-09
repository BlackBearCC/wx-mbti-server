"""Public exports for the AI service package.

Notes:
- Upstream callers should supply only `modelAlias`; provider selection is
  handled internally via alias mapping. See AGENTS.md for the HTTP/WS gateway
  contract and environment configuration knobs.
"""
from .service import AIService, CharacterProfile, ChatMessage, ModelAlias, get_ai_service

__all__ = [
    "AIService",
    "CharacterProfile",
    "ChatMessage",
    "ModelAlias",
    "get_ai_service",
]
