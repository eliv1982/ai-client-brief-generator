from __future__ import annotations

import json

import httpx
import pytest
from openai import APIConnectionError, OpenAIError

from utils.validators import BriefValidationError


# ── Fakes — no real network access is ever performed ────────────────────────

class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str, id_: str = "resp_test_123"):
        self.choices = [_FakeChoice(content)]
        self.id = id_


class _FakeCompletions:
    def __init__(self, response, captured_create_kwargs: dict, error: Exception | None = None):
        self._response = response
        self._captured = captured_create_kwargs
        self._error = error

    def create(self, **kwargs):
        self._captured.update(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


class _FakeChat:
    def __init__(self, completions: _FakeCompletions):
        self.completions = completions


def _make_fake_openai_cls(*, content: str = "{}", error: Exception | None = None, captured: dict | None = None):
    """Build a fake OpenAI client class capturing init + create() kwargs."""
    captured = captured if captured is not None else {}
    response = _FakeResponse(content)

    class FakeOpenAI:
        def __init__(self, **init_kwargs):
            captured["init_kwargs"] = init_kwargs
            self.chat = _FakeChat(_FakeCompletions(response, captured, error=error))

    return FakeOpenAI, captured


# ── Valid response ───────────────────────────────────────────────────────────

def test_extract_brief_from_dialog_with_valid_mocked_response(monkeypatch, valid_brief_payload):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_cls, captured = _make_fake_openai_cls(content=json.dumps(valid_brief_payload))
    monkeypatch.setattr("utils.ai_processor.OpenAI", fake_cls)

    from utils.ai_processor import extract_brief_from_dialog

    result = extract_brief_from_dialog("some dialog text")

    assert result["client_name"] == valid_brief_payload["client_name"]
    assert captured["init_kwargs"]["timeout"] == 60.0
    assert captured["init_kwargs"]["max_retries"] == 2
    assert captured["max_completion_tokens"] == 2000
    assert captured["response_format"] == {"type": "json_object"}


def test_extract_design_report_from_dialog_with_valid_mocked_response(
    monkeypatch, valid_design_payload
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_cls, captured = _make_fake_openai_cls(content=json.dumps(valid_design_payload))
    monkeypatch.setattr("utils.ai_processor.OpenAI", fake_cls)

    from utils.ai_processor import extract_design_report_from_dialog

    result = extract_design_report_from_dialog("some design dialog text")

    assert result["project_type"] == valid_design_payload["project_type"]
    assert captured["max_completion_tokens"] == 2500


# ── Missing API key ──────────────────────────────────────────────────────────

def test_extract_brief_from_dialog_without_api_key_raises(monkeypatch):
    from utils.ai_processor import extract_brief_from_dialog

    with pytest.raises(EnvironmentError):
        extract_brief_from_dialog("some dialog text")


# ── API failure ──────────────────────────────────────────────────────────────

def test_extract_brief_from_dialog_propagates_api_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    error = APIConnectionError(request=fake_request)
    fake_cls, _ = _make_fake_openai_cls(error=error)
    monkeypatch.setattr("utils.ai_processor.OpenAI", fake_cls)

    from utils.ai_processor import extract_brief_from_dialog

    with pytest.raises(OpenAIError):
        extract_brief_from_dialog("some dialog text")


# ── Malformed model response ──────────────────────────────────────────────────

def test_extract_brief_from_dialog_rejects_malformed_json(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    huge_garbage = "not valid json " * 2000  # deliberately large, non-JSON content
    fake_cls, _ = _make_fake_openai_cls(content=huge_garbage)
    monkeypatch.setattr("utils.ai_processor.OpenAI", fake_cls)

    from utils.ai_processor import extract_brief_from_dialog

    with pytest.raises(BriefValidationError) as exc_info:
        extract_brief_from_dialog("some dialog text")

    # The raw model response must never be embedded verbatim in the error.
    message = str(exc_info.value)
    assert huge_garbage not in message
    assert len(message) < len(huge_garbage)


def test_extract_brief_from_dialog_rejects_schema_violation(monkeypatch, valid_brief_payload):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    del valid_brief_payload["summary"]
    fake_cls, _ = _make_fake_openai_cls(content=json.dumps(valid_brief_payload))
    monkeypatch.setattr("utils.ai_processor.OpenAI", fake_cls)

    from utils.ai_processor import extract_brief_from_dialog

    with pytest.raises(BriefValidationError):
        extract_brief_from_dialog("some dialog text")
