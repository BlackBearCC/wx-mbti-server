"""AI service orchestrating provider selection"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional

from app.config.settings import get_settings

from .providers.base import AIChatRequest, AIChatResponse, AIMessage, AIProvider
from .providers.doubao import DoubaoProvider
from .providers.openai import OpenAIProvider


@dataclass
class CharacterProfile:
    """Minimal character information required to build prompts."""

    name: str
    dimension: str
    persona: Optional[str] = None


@dataclass
class ChatMessage:
    """Simplified chat message for prompt reconstruction."""

    content: str
    is_ai: bool


@dataclass
class ModelAlias:
    """Maps a friendly model name to provider-level parameters."""

    provider: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class AIService:
    """Routes chat requests to the configured LLM provider."""

    def __init__(
        self,
        providers: Dict[str, AIProvider],
        default_provider: str,
        fallback_provider: Optional[str] = None,
        default_max_tokens: int = 1024,
        model_aliases: Optional[Dict[str, ModelAlias]] = None,
        default_model_alias: Optional[str] = None,
    ):
        if default_provider not in providers:
            raise ValueError(f"Default provider '{default_provider}' is not registered")
        if fallback_provider and fallback_provider not in providers:
            raise ValueError(f"Fallback provider '{fallback_provider}' is not registered")
        self.providers = providers
        self.default_provider = default_provider
        self.fallback_provider = fallback_provider
        self.default_max_tokens = default_max_tokens
        self.model_aliases = model_aliases or {}
        if default_model_alias and default_model_alias not in self.model_aliases:
            raise ValueError(f"Default model alias '{default_model_alias}' is not registered")
        self.default_model_alias = default_model_alias

    def _build_prompt(self, character: CharacterProfile, history: Iterable[ChatMessage]) -> List[AIMessage]:
        """Construct provider-agnostic message history."""
        persona = character.persona or "Stay in character and provide helpful, consistent replies."
        messages: List[AIMessage] = [
            AIMessage(
                role="system",
                content=(
                    f"You are {character.name}, MBTI type {character.dimension}. "
                    f"Keep responses aligned with the role's established tone. {persona}"
                ),
            )
        ]
        for msg in history:
            role = "assistant" if msg.is_ai else "user"
            messages.append(AIMessage(role=role, content=msg.content))
        return messages

    async def chat(
        self,
        character: CharacterProfile,
        history: Iterable[ChatMessage],
        provider_name: Optional[str] = None,
        model_alias: Optional[str] = None,
        character_id: Optional[str] = None,
        room_id: Optional[str] = None,
        user_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AIChatResponse:
        alias_name = model_alias or self.default_model_alias
        alias_spec = self.model_aliases.get(alias_name) if alias_name else None

        resolved_provider_name = provider_name or (alias_spec.provider if alias_spec else self.default_provider)
        provider = self.providers.get(resolved_provider_name)
        if provider is None and self.fallback_provider:
            provider = self.providers.get(self.fallback_provider)
        if provider is None:
            raise ValueError(f"Provider '{resolved_provider_name}' is not registered")

        effective_max_tokens = max_tokens or self.default_max_tokens
        effective_temperature = temperature
        effective_metadata: Dict[str, Any] = metadata.copy() if metadata else {}
        model_override = None

        if alias_spec:
            model_override = alias_spec.model or model_override
            if alias_spec.max_tokens is not None:
                effective_max_tokens = alias_spec.max_tokens
            if alias_spec.temperature is not None and effective_temperature is None:
                effective_temperature = alias_spec.temperature
            if alias_spec.metadata:
                effective_metadata = {**alias_spec.metadata, **effective_metadata}

        request = AIChatRequest(
            messages=self._build_prompt(character, history),
            model=model_override,
            character_id=character_id,
            room_id=room_id,
            user_id=user_id,
            max_tokens=effective_max_tokens,
            temperature=effective_temperature,
            metadata=effective_metadata or None,
        )
        return await provider.complete(request)


def _load_json(text: Optional[str]) -> Dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _extract_aliases(
    overrides: Dict[str, Any],
    settings_aliases: Dict[str, Any],
    default_provider: str,
    providers: Dict[str, AIProvider],
) -> Dict[str, ModelAlias]:
    alias_source: Dict[str, Any] = dict(settings_aliases)
    for provider_name, config in overrides.items():
        aliases = config.get("aliases")
        if isinstance(aliases, dict):
            for alias_name, spec in aliases.items():
                entry = dict(spec)
                entry.setdefault("provider", provider_name)
                alias_source[alias_name] = entry

    model_aliases: Dict[str, ModelAlias] = {}
    for alias_name, spec in alias_source.items():
        if not isinstance(spec, dict):
            continue
        provider_name = spec.get("provider", default_provider)
        if provider_name not in providers:
            continue
        metadata = spec.get("metadata") if isinstance(spec.get("metadata"), dict) else None
        model_aliases[alias_name] = ModelAlias(
            provider=provider_name,
            model=spec.get("model"),
            max_tokens=spec.get("max_tokens"),
            temperature=spec.get("temperature"),
            metadata=metadata,
        )
    return model_aliases


@lru_cache(maxsize=1)
def build_ai_service() -> AIService:
    settings = get_settings()
    providers: Dict[str, AIProvider] = {}

    overrides = _load_json(settings.AI_PROVIDER_OVERRIDES)

    doubao_config: Dict[str, Any] = overrides.get("doubao", {}) if isinstance(overrides, dict) else {}
    doubao_key = doubao_config.get("api_key") or settings.DOUBAO_API_KEY
    if doubao_key:
        providers["doubao"] = DoubaoProvider(
            api_key=doubao_key,
            model=doubao_config.get("model", settings.DOUBAO_MODEL),
            base_url=doubao_config.get("base_url", settings.DOUBAO_BASE_URL),
            timeout=doubao_config.get("timeout", settings.AI_RESPONSE_TIMEOUT),
        )

    openai_config: Dict[str, Any] = overrides.get("openai", {}) if isinstance(overrides, dict) else {}
    openai_key = openai_config.get("api_key") or settings.OPENAI_API_KEY
    if openai_key:
        providers["openai"] = OpenAIProvider(
            api_key=openai_key,
            model=openai_config.get("model", settings.OPENAI_MODEL),
            base_url=openai_config.get("base_url", settings.OPENAI_BASE_URL),
            timeout=openai_config.get("timeout", settings.AI_RESPONSE_TIMEOUT),
        )

    default_provider = settings.AI_DEFAULT_PROVIDER or "doubao"
    fallback_provider = settings.AI_FALLBACK_PROVIDER
    if default_provider not in providers:
        raise RuntimeError(
            f"Configured default AI provider '{default_provider}' is unavailable."
            " Check API keys or AI_PROVIDER_OVERRIDES settings."
        )

    settings_aliases = _load_json(settings.AI_MODEL_ALIASES)
    model_aliases = _extract_aliases(overrides if isinstance(overrides, dict) else {}, settings_aliases, default_provider, providers)

    default_model_alias = settings.AI_DEFAULT_MODEL_ALIAS
    if default_model_alias and default_model_alias not in model_aliases:
        raise RuntimeError(f"Default model alias '{default_model_alias}' is not defined in AI_MODEL_ALIASES.")

    if not model_aliases:
        model_aliases["default"] = ModelAlias(provider=default_provider)
        if not default_model_alias:
            default_model_alias = "default"
    elif not default_model_alias:
        if "default" in model_aliases:
            default_model_alias = "default"
        else:
            default_model_alias = next(iter(model_aliases))

    return AIService(
        providers=providers,
        default_provider=default_provider,
        fallback_provider=fallback_provider,
        default_max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
        model_aliases=model_aliases,
        default_model_alias=default_model_alias,
    )


async def get_ai_service() -> AIService:
    """FastAPI dependency wrapper to keep AI service as a singleton."""
    return build_ai_service()
