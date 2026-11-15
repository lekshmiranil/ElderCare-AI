"""Central configuration. Reads environment variables once; never logs secrets."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _bool(value: str, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    demo_mode: bool
    ai_provider: str          # "local" or "gemini"
    gemini_api_key: str       # kept private; use has_gemini_key for display
    db_path: Path
    log_level: str
    gemini_model: str
    ai_daily_limit: int
    ai_min_interval_s: int
    ai_cache_ttl_h: int
    ai_cooldown_min: int

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.gemini_api_key)

    def __repr__(self) -> str:  # prevents accidental key exposure in logs
        return (f"Settings(demo_mode={self.demo_mode}, ai_provider={self.ai_provider!r}, "
                f"has_gemini_key={self.has_gemini_key}, db_path={str(self.db_path)!r})")


def _clean(name: str, default: str) -> str:
    # strip inline comments such as "local   # local | gemini"
    return os.getenv(name, default).split("#")[0].strip()


def _int(name: str, default: int) -> int:
    try:
        return max(0, int(_clean(name, str(default))))
    except ValueError:
        return default


def load_settings() -> Settings:
    provider = _clean("AI_PROVIDER", "local").lower()
    if provider not in {"local", "gemini"}:
        provider = "local"
    db_path = Path(_clean("DB_PATH", "data/eldercare.db"))
    if not db_path.is_absolute():
        db_path = ROOT / db_path
    return Settings(
        demo_mode=_bool(_clean("DEMO_MODE", "true"), True),
        ai_provider=provider,
        gemini_api_key=_clean("GEMINI_API_KEY", ""),
        db_path=db_path,
        log_level=_clean("LOG_LEVEL", "INFO").upper(),
        gemini_model=_clean("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        ai_daily_limit=_int("AI_DAILY_LIMIT", 20),
        ai_min_interval_s=_int("AI_MIN_INTERVAL_SECONDS", 5),
        ai_cache_ttl_h=_int("AI_CACHE_TTL_HOURS", 24),
        ai_cooldown_min=_int("AI_QUOTA_COOLDOWN_MINUTES", 30),
    )
