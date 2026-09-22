from __future__ import annotations

import base64

import pytest

from tests.conftest import MINIMAL_PNG_BYTES


# ── Fakes — no real network access is ever performed ────────────────────────

class _FakeImageItem:
    def __init__(self, b64_json: str | None = None, url: str | None = None):
        self.b64_json = b64_json
        self.url = url


class _FakeImagesResponse:
    def __init__(self, items):
        self.data = items


class _FakeImages:
    def __init__(self, response=None, error: Exception | None = None, captured: dict | None = None):
        self._response = response
        self._error = error
        self._captured = captured if captured is not None else {}

    def generate(self, **kwargs):
        self._captured.update(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


def _make_fake_openai_cls(*, items=None, error: Exception | None = None, captured: dict | None = None):
    captured = captured if captured is not None else {}
    response = _FakeImagesResponse(items) if items is not None else None

    class FakeOpenAI:
        def __init__(self, **init_kwargs):
            captured["init_kwargs"] = init_kwargs
            self.images = _FakeImages(response=response, error=error, captured=captured)

    return FakeOpenAI, captured


# ── Normal mocked image generation ──────────────────────────────────────────

def test_generate_design_image_success(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("utils.image_generator.IMAGES_DIR", tmp_path)

    b64 = base64.b64encode(MINIMAL_PNG_BYTES).decode("ascii")
    fake_cls, captured = _make_fake_openai_cls(items=[_FakeImageItem(b64_json=b64)])
    monkeypatch.setattr("utils.image_generator.OpenAI", fake_cls)

    from utils.image_generator import generate_design_image

    result = generate_design_image("a clean minimal hero concept, no text")

    assert result is not None
    assert result.exists()
    assert result.read_bytes() == MINIMAL_PNG_BYTES
    assert result.parent == tmp_path
    assert captured["init_kwargs"]["timeout"] == 90.0
    assert captured["init_kwargs"]["max_retries"] == 2


# ── Failure fallback ─────────────────────────────────────────────────────────

def test_generate_design_image_returns_none_on_api_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("utils.image_generator.IMAGES_DIR", tmp_path)

    fake_cls, _ = _make_fake_openai_cls(error=RuntimeError("simulated API failure"))
    monkeypatch.setattr("utils.image_generator.OpenAI", fake_cls)

    from utils.image_generator import generate_design_image

    result = generate_design_image("a clean minimal hero concept, no text")

    assert result is None
    assert list(tmp_path.iterdir()) == []


def test_generate_design_image_without_api_key_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr("utils.image_generator.IMAGES_DIR", tmp_path)

    from utils.image_generator import generate_design_image

    result = generate_design_image("a clean minimal hero concept, no text")

    assert result is None


def test_generate_design_image_handles_empty_response(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("utils.image_generator.IMAGES_DIR", tmp_path)

    fake_cls, _ = _make_fake_openai_cls(items=[])
    monkeypatch.setattr("utils.image_generator.OpenAI", fake_cls)

    from utils.image_generator import generate_design_image

    result = generate_design_image("a clean minimal hero concept, no text")

    assert result is None


# ── Unique filenames ─────────────────────────────────────────────────────────

def test_unique_image_path_appends_suffix_on_collision(tmp_path):
    from utils.image_generator import _unique_image_path

    base = tmp_path / "design_concept_2026-01-01_12-00-00.png"
    base.write_bytes(b"existing")

    result = _unique_image_path(base)

    assert result == tmp_path / "design_concept_2026-01-01_12-00-00_2.png"
    assert result.parent == tmp_path


def test_unique_image_path_returns_base_when_free(tmp_path):
    from utils.image_generator import _unique_image_path

    base = tmp_path / "design_concept_2026-01-01_12-00-00.png"

    assert _unique_image_path(base) == base
