"""Provider abstraction. To add another LLM, subclass LLMProvider and raise ProviderError on failure."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Error kinds the rest of the app understands. Messages are fixed, safe strings.
QUOTA, AUTH, MODEL_NOT_FOUND, NETWORK, BLOCKED, BAD_RESPONSE, UNKNOWN = (
    "quota", "auth", "model_not_found", "network", "blocked", "bad_response", "unknown")


@dataclass(frozen=True)
class AIRequest:
    feature: str          # e.g. "companion_chat", used for usage logs and cache keys
    system: str
    user: str
    max_tokens: int = 200
    max_input_chars: int = 400   # chat messages stay short; app-built prompts (RAG, summaries) raise this


@dataclass(frozen=True)
class AIResult:
    text: str
    provider: str
    model: str


class ProviderError(Exception):
    """Failure with a machine-readable kind and a message that is safe to show. Never contains secrets."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind, self.message = kind, message


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResult:
        """Return generated text or raise ProviderError. Must never retry on its own."""
