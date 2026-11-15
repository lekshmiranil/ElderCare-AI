"""Builds the AIManager from settings. Gemini is only created when explicitly configured with a key."""
from config.settings import Settings

from .manager import AIManager, Limits
from .providers.gemini import GeminiProvider


def build_manager(settings: Settings) -> AIManager:
    provider = None
    if settings.ai_provider == "gemini" and settings.has_gemini_key:
        provider = GeminiProvider(settings.gemini_api_key, settings.gemini_model)
    limits = Limits(settings.ai_daily_limit, settings.ai_min_interval_s, settings.ai_cache_ttl_h, settings.ai_cooldown_min)
    return AIManager(settings.db_path, provider, limits)
