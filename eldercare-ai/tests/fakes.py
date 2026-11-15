"""Test doubles. They live in tests/, so the app itself can never select a fake provider."""
from src.ai.providers.base import AIRequest, AIResult, LLMProvider, ProviderError


class FakeProvider(LLMProvider):
    name, model = "gemini", "fake-model"

    def __init__(self, replies=None, error_kind=None):
        self.replies, self.error_kind, self.calls, self.requests = list(replies or ["Fake Gemini answer."]), error_kind, 0, []

    def generate(self, request: AIRequest) -> AIResult:
        self.calls += 1
        self.requests.append(request)
        if self.error_kind:
            raise ProviderError(self.error_kind, "fake error")
        text = self.replies[min(self.calls - 1, len(self.replies) - 1)]
        return AIResult(text=text, provider=self.name, model=self.model)


class FakeResponse:
    def __init__(self, status=200, payload=None, bad_json=False):
        self.status_code, self._payload, self._bad = status, payload if payload is not None else {}, bad_json

    def json(self):
        if self._bad:
            raise ValueError("bad json")
        return self._payload
