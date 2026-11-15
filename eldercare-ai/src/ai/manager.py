"""AIManager: the single gatekeeper between the app and any cloud LLM.

Everything that protects the API quota lives here:
  manual switch -> cooldown after errors -> cache -> daily limit -> minimum spacing -> ONE call.
It is only ever called from an explicit user action, never on page load or refresh.
Local (no-API) behaviour is the fallback for every refusal, and local text is never labelled as Gemini.
"""
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from src.database.connection import get_connection

from .providers.base import AUTH, BLOCKED, MODEL_NOT_FOUND, NETWORK, QUOTA, AIRequest, LLMProvider, ProviderError

MAX_USER_CHARS = 400


@dataclass(frozen=True)
class Limits:
    daily_limit: int = 20
    min_interval_s: int = 5
    cache_ttl_h: int = 24
    quota_cooldown_min: int = 30


@dataclass(frozen=True)
class AIOutcome:
    text: Optional[str]            # None means "use the local reply"
    source: str                    # gemini | gemini_cache | local
    model: Optional[str] = None
    notice: Optional[str] = None   # honest, user-facing reason when Gemini was not used


@dataclass(frozen=True)
class AIStatus:
    state: str        # local | off | ready | paused | limit
    label: str
    detail: str
    used_today: int
    daily_limit: int


COOLDOWN_MINUTES = {AUTH: 24 * 60, MODEL_NOT_FOUND: 24 * 60, NETWORK: 1}
NOTICES = {
    QUOTA: "Gemini usage limit reached. Using local replies until {until}.",
    AUTH: "Gemini rejected the API key. Using local replies. Fix the key, then use Retry.",
    MODEL_NOT_FOUND: "Gemini model name not found. Using local replies. Check GEMINI_MODEL, then use Retry.",
    NETWORK: "Gemini could not be reached. Using a local reply.",
    BLOCKED: "Gemini declined to answer that message. Using a local reply.",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


class AIManager:
    def __init__(self, db_path, provider: Optional[LLMProvider], limits: Limits = Limits()):
        self.db_path, self.provider, self.limits = db_path, provider, limits

    # ---- settings kept in the database so the switch survives reruns -------------------------
    def _get(self, key, default=None):
        with get_connection(self.db_path) as c:
            row = c.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def _set(self, key, value):
        with get_connection(self.db_path) as c:
            c.execute("INSERT INTO app_settings (key,value) VALUES (?,?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def _delete(self, key):
        with get_connection(self.db_path) as c:
            c.execute("DELETE FROM app_settings WHERE key=?", (key,))

    @property
    def configured(self) -> bool:
        return self.provider is not None

    def is_enabled(self) -> bool:
        return self.configured and self._get("ai_enabled", "false") == "true"

    def set_enabled(self, on: bool) -> None:
        self._set("ai_enabled", "true" if on and self.configured else "false")

    def clear_pause(self) -> None:
        """Manual retry only. Nothing in the app calls this automatically."""
        self._delete("ai_pause_until")
        self._delete("ai_pause_reason")

    # ---- usage ---------------------------------------------------------------------------------
    def _live_calls_today(self, now) -> int:
        with get_connection(self.db_path) as c:
            return c.execute("SELECT COUNT(*) FROM ai_usage WHERE substr(ts,1,10)=? AND outcome!='cache'",
                             (now.date().isoformat(),)).fetchone()[0]

    def _last_live_call(self):
        with get_connection(self.db_path) as c:
            row = c.execute("SELECT ts FROM ai_usage WHERE outcome!='cache' ORDER BY id DESC LIMIT 1").fetchone()
        return datetime.fromisoformat(row["ts"]) if row else None

    def _log(self, now, feature, outcome):
        with get_connection(self.db_path) as c:
            c.execute("INSERT INTO ai_usage (ts,provider,model,feature,outcome) VALUES (?,?,?,?,?)",
                      (now.isoformat(timespec="seconds"), self.provider.name, self.provider.model, feature, outcome))

    def _pause_until(self, now):
        raw = self._get("ai_pause_until")
        until = datetime.fromisoformat(raw) if raw else None
        return until if until and until > now else None

    def status(self, now=None) -> AIStatus:
        now = now or datetime.now()
        used, limit = (self._live_calls_today(now) if self.configured else 0), self.limits.daily_limit
        if not self.configured:
            return AIStatus("local", "AI: local mode", "No cloud AI is configured. Local ML and rules only.", 0, limit)
        if not self.is_enabled():
            return AIStatus("off", "AI: OFF (local mode)", "Gemini is configured but switched off.", used, limit)
        until = self._pause_until(now)
        if until:
            return AIStatus("paused", "AI: paused", f"Gemini paused until {until:%H:%M}: {self._get('ai_pause_reason', '')}",
                            used, limit)
        if used >= limit:
            return AIStatus("limit", "AI: daily limit", "Daily Gemini limit reached. Local replies only today.", used, limit)
        return AIStatus("ready", "AI: Gemini ready", "Open-ended questions may be sent to Gemini.", used, limit)

    # ---- the one entry point -----------------------------------------------------------------
    def complete(self, request: AIRequest, now=None) -> AIOutcome:
        now = now or datetime.now()
        if not self.is_enabled():
            return AIOutcome(None, "local")
        until = self._pause_until(now)
        if until:
            return AIOutcome(None, "local", notice=f"Gemini is paused until {until:%H:%M}. Using a local reply.")

        request = AIRequest(request.feature, request.system, request.user[:request.max_input_chars], request.max_tokens,
                            request.max_input_chars)
        key = hashlib.sha256("|".join([self.provider.name, self.provider.model, request.feature,
                                       hashlib.sha256(request.system.encode()).hexdigest(),
                                       _norm(request.user)]).encode()).hexdigest()
        cached = self._cache_get(key, now)
        if cached:
            self._log(now, request.feature, "cache")
            return AIOutcome(cached, "gemini_cache", self.provider.model)

        if self._live_calls_today(now) >= self.limits.daily_limit:
            return AIOutcome(None, "local", notice="The daily Gemini limit set for this app is reached. Using a local reply.")
        last = self._last_live_call()
        if last and (now - last).total_seconds() < self.limits.min_interval_s:
            return AIOutcome(None, "local", notice="Please wait a few seconds between Gemini questions. Using a local reply.")

        try:
            result = self.provider.generate(request)
        except ProviderError as e:
            self._log(now, request.feature, e.kind)
            minutes = (self.limits.quota_cooldown_min if e.kind == QUOTA else COOLDOWN_MINUTES.get(e.kind, 0))
            until = None
            if minutes:
                until = now + timedelta(minutes=minutes)
                self._set("ai_pause_until", until.isoformat(timespec="seconds"))
                self._set("ai_pause_reason", e.message)
            return AIOutcome(None, "local", notice=NOTICES.get(e.kind, "Gemini was not available. Using a local reply.")
                             .format(until=f"{until:%H:%M}" if until else ""))
        self._log(now, request.feature, "ok")
        self._cache_put(key, result.text, now)
        return AIOutcome(result.text, "gemini", result.model)

    # ---- cache -----------------------------------------------------------------------------------
    def _cache_get(self, key, now):
        with get_connection(self.db_path) as c:
            row = c.execute("SELECT response, created_at FROM ai_cache WHERE cache_key=?", (key,)).fetchone()
        if row and now - datetime.fromisoformat(row["created_at"]) < timedelta(hours=self.limits.cache_ttl_h):
            return row["response"]
        return None

    def _cache_put(self, key, text, now):
        with get_connection(self.db_path) as c:
            c.execute("INSERT INTO ai_cache (cache_key,created_at,response) VALUES (?,?,?) "
                      "ON CONFLICT(cache_key) DO UPDATE SET created_at=excluded.created_at, response=excluded.response",
                      (key, now.isoformat(timespec="seconds"), text))
