import pytest
import requests

from src.ai.providers.base import AIRequest, ProviderError
from src.ai.providers.gemini import GeminiProvider
from tests.fakes import FakeResponse

REQ = AIRequest("t", "system text", "hello", 150)
KEY = "SECRET-KEY-123"


def provider(resp=None, exc=None):
    calls = []

    def post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if exc:
            raise exc
        return resp
    return GeminiProvider(KEY, "model-x", http_post=post), calls


def ok_payload(text="Hello there"):
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]}


def test_success_and_request_shape():
    p, calls = provider(FakeResponse(200, ok_payload()))
    r = p.generate(REQ)
    assert r.text == "Hello there" and r.provider == "gemini" and r.model == "model-x"
    c = calls[0]
    assert c["url"].endswith("/model-x:generateContent")
    assert KEY not in c["url"] and c["headers"]["x-goog-api-key"] == KEY    # key only in header
    assert c["json"]["generationConfig"]["maxOutputTokens"] == 150
    assert c["json"]["systemInstruction"]["parts"][0]["text"] == "system text"


@pytest.mark.parametrize("status,api_status,kind", [
    (429, "RESOURCE_EXHAUSTED", "quota"), (200 + 229, "", "quota"),   # 429 by code alone
    (403, "PERMISSION_DENIED", "auth"), (401, "", "auth"), (400, "API_KEY_INVALID", "auth"),
    (404, "NOT_FOUND", "model_not_found"), (503, "UNAVAILABLE", "network"), (418, "", "unknown")])
def test_http_errors_are_classified_and_never_retried(status, api_status, kind):
    p, calls = provider(FakeResponse(status, {"error": {"status": api_status, "message": KEY}}))
    with pytest.raises(ProviderError) as e:
        p.generate(REQ)
    assert e.value.kind == kind and len(calls) == 1           # exactly one attempt
    assert KEY not in e.value.message and KEY not in str(e.value)


def test_quota_detected_from_status_text_even_with_other_code():
    p, _ = provider(FakeResponse(400, {"error": {"status": "RESOURCE_EXHAUSTED"}}))
    with pytest.raises(ProviderError) as e:
        p.generate(REQ)
    assert e.value.kind == "quota"


@pytest.mark.parametrize("payload,kind", [
    ({"promptFeedback": {"blockReason": "SAFETY"}}, "blocked"),
    ({"candidates": [{"finishReason": "SAFETY"}]}, "blocked"),
    ({}, "bad_response"), ({"candidates": [{"content": {"parts": [{"text": "  "}]}}]}, "bad_response")])
def test_unusable_answers(payload, kind):
    p, _ = provider(FakeResponse(200, payload))
    with pytest.raises(ProviderError) as e:
        p.generate(REQ)
    assert e.value.kind == kind


@pytest.mark.parametrize("exc", [requests.Timeout(KEY), requests.ConnectionError(KEY)])
def test_network_failures(exc):
    p, calls = provider(exc=exc)
    with pytest.raises(ProviderError) as e:
        p.generate(REQ)
    assert e.value.kind == "network" and KEY not in e.value.message and len(calls) == 1


def test_non_json_error_body_is_handled():
    p, _ = provider(FakeResponse(500, bad_json=True))
    with pytest.raises(ProviderError):
        p.generate(REQ)


def test_requires_key():
    with pytest.raises(ValueError):
        GeminiProvider("", "m")
