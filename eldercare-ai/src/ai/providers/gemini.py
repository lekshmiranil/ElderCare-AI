"""Gemini via its public REST API (no extra SDK). Optional, off by default.

Safety rules implemented here:
- the API key goes in a request header, never in the URL, and never in any message or log
- one attempt per call: no retries, so a quota error cannot be hammered
- every failure becomes a ProviderError with a fixed, safe message
"""
import requests

from .base import (AUTH, BAD_RESPONSE, BLOCKED, MODEL_NOT_FOUND, NETWORK, QUOTA, UNKNOWN,
                   AIRequest, AIResult, LLMProvider, ProviderError)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

MESSAGES = {
    QUOTA: "Gemini usage limit reached",
    AUTH: "Gemini rejected the API key",
    MODEL_NOT_FOUND: "Gemini model name not found (check GEMINI_MODEL)",
    NETWORK: "Gemini could not be reached",
    BLOCKED: "Gemini declined to answer this message",
    BAD_RESPONSE: "Gemini returned an unreadable answer",
    UNKNOWN: "Gemini returned an unexpected error",
}


def classify_http_error(status: int, api_status: str = "") -> str:
    api_status = (api_status or "").upper()
    if status == 429 or api_status == "RESOURCE_EXHAUSTED":
        return QUOTA
    if status in (401, 403) or api_status in ("UNAUTHENTICATED", "PERMISSION_DENIED", "API_KEY_INVALID"):
        return AUTH
    if status == 400 and "API_KEY" in api_status:
        return AUTH
    if status == 404 or api_status == "NOT_FOUND":
        return MODEL_NOT_FOUND
    if status >= 500 or api_status in ("UNAVAILABLE", "DEADLINE_EXCEEDED"):
        return NETWORK
    return UNKNOWN


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float = 15.0, http_post=None):
        if not api_key:
            raise ValueError("GeminiProvider needs an API key")
        self._key = api_key
        self.model = model
        self.timeout = timeout
        self._post = http_post or requests.post   # injectable so tests never touch the network

    def generate(self, request: AIRequest) -> AIResult:
        body = {
            "systemInstruction": {"parts": [{"text": request.system}]},
            "contents": [{"role": "user", "parts": [{"text": request.user}]}],
            "generationConfig": {"maxOutputTokens": request.max_tokens, "temperature": 0.4},
        }
        try:
            resp = self._post(f"{BASE_URL}/{self.model}:generateContent",
                              headers={"x-goog-api-key": self._key, "Content-Type": "application/json"},
                              json=body, timeout=self.timeout)
        except (requests.Timeout, requests.ConnectionError):
            raise ProviderError(NETWORK, MESSAGES[NETWORK]) from None
        except requests.RequestException:
            raise ProviderError(UNKNOWN, MESSAGES[UNKNOWN]) from None

        try:
            data = resp.json()
        except ValueError:
            data = {}
        if resp.status_code != 200:
            api_status = (data.get("error") or {}).get("status", "") if isinstance(data, dict) else ""
            kind = classify_http_error(resp.status_code, api_status)
            raise ProviderError(kind, MESSAGES[kind])

        candidates = data.get("candidates") or []
        if not candidates:
            blocked = (data.get("promptFeedback") or {}).get("blockReason")
            raise ProviderError(BLOCKED if blocked else BAD_RESPONSE, MESSAGES[BLOCKED if blocked else BAD_RESPONSE])
        cand = candidates[0]
        if cand.get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
            raise ProviderError(BLOCKED, MESSAGES[BLOCKED])
        parts = (cand.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise ProviderError(BAD_RESPONSE, MESSAGES[BAD_RESPONSE])
        return AIResult(text=text, provider=self.name, model=self.model)
