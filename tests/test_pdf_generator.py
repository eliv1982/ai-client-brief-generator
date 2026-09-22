from __future__ import annotations

import datetime as real_datetime
import re

import pytest

from tests.conftest import MINIMAL_PNG_BYTES


class _FixedDateTime(real_datetime.datetime):
    """A datetime subclass whose now() is frozen, for deterministic filenames."""

    @classmethod
    def now(cls, tz=None):
        return real_datetime.datetime(2026, 1, 1, 12, 0, 0)


# ── Real WeasyPrint rendering (offline — no network access) ────────────────

def test_render_client_brief_pdf_produces_valid_pdf(monkeypatch, tmp_path, valid_brief_payload):
    from utils import pdf_generator

    monkeypatch.setattr(pdf_generator, "REPORTS_DIR", tmp_path)

    output_path = pdf_generator.render_client_brief_pdf(valid_brief_payload)

    assert output_path.exists()
    assert output_path.parent == tmp_path
    assert output_path.read_bytes().startswith(b"%PDF")
    assert re.match(r"^client_report_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(_\d+)?\.pdf$", output_path.name)


def test_render_design_report_pdf_without_image(monkeypatch, tmp_path, valid_design_payload):
    from utils import pdf_generator

    monkeypatch.setattr(pdf_generator, "REPORTS_DIR", tmp_path)

    output_path = pdf_generator.render_design_report_pdf(valid_design_payload, None)

    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")


def test_render_design_report_pdf_with_image(monkeypatch, tmp_path, valid_design_payload):
    from utils import pdf_generator

    monkeypatch.setattr(pdf_generator, "REPORTS_DIR", tmp_path)

    image_path = tmp_path / "concept.png"
    image_path.write_bytes(MINIMAL_PNG_BYTES)

    output_path = pdf_generator.render_design_report_pdf(valid_design_payload, image_path)

    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")


# ── Output naming: collisions and no-overwrite ──────────────────────────────

def test_render_client_brief_pdf_does_not_overwrite_existing_output(
    monkeypatch, tmp_path, valid_brief_payload
):
    from utils import pdf_generator

    monkeypatch.setattr(pdf_generator, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(pdf_generator, "datetime", _FixedDateTime)

    existing = tmp_path / "client_report_2026-01-01_12-00-00.pdf"
    existing.write_bytes(b"PRE-EXISTING CONTENT")

    output_path = pdf_generator.render_client_brief_pdf(valid_brief_payload)

    # The pre-existing file must be untouched ...
    assert existing.read_bytes() == b"PRE-EXISTING CONTENT"
    # ... and a suffixed file must be created instead.
    assert output_path == tmp_path / "client_report_2026-01-01_12-00-00_2.pdf"
    assert output_path.read_bytes().startswith(b"%PDF")


def test_unique_path_helper_appends_suffix_on_collision(tmp_path):
    from utils.pdf_generator import _unique_path

    base = tmp_path / "report.pdf"
    base.write_bytes(b"existing")

    assert _unique_path(base) == tmp_path / "report_2.pdf"


def test_unique_path_helper_returns_base_when_free(tmp_path):
    from utils.pdf_generator import _unique_path

    base = tmp_path / "report.pdf"

    assert _unique_path(base) == base


def test_unique_path_helper_stays_in_same_directory(tmp_path):
    from utils.pdf_generator import _unique_path

    base = tmp_path / "report.pdf"
    base.write_bytes(b"1")
    (tmp_path / "report_2.pdf").write_bytes(b"2")

    result = _unique_path(base)

    assert result == tmp_path / "report_3.pdf"
    assert result.parent == tmp_path


# ── Failure propagation ──────────────────────────────────────────────────────

def test_render_client_brief_pdf_missing_template_raises(monkeypatch, tmp_path, valid_brief_payload):
    from utils import pdf_generator

    monkeypatch.setattr(pdf_generator, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(pdf_generator, "TEMPLATES_DIR", tmp_path / "missing_templates")

    with pytest.raises(FileNotFoundError):
        pdf_generator.render_client_brief_pdf(valid_brief_payload)

    assert list(tmp_path.glob("*.pdf")) == []


def test_render_client_brief_pdf_write_failure_propagates_cleanly(
    monkeypatch, tmp_path, valid_brief_payload
):
    from utils import pdf_generator

    monkeypatch.setattr(pdf_generator, "REPORTS_DIR", tmp_path)

    class _FailingHTML:
        def __init__(self, *args, **kwargs):
            pass

        def write_pdf(self, *args, **kwargs):
            raise RuntimeError("simulated WeasyPrint failure")

    monkeypatch.setattr(pdf_generator, "HTML", _FailingHTML)

    with pytest.raises(RuntimeError):
        pdf_generator.render_client_brief_pdf(valid_brief_payload)

    # No PDF must exist — a rendering failure must never look like success.
    assert list(tmp_path.glob("*.pdf")) == []


def test_render_client_brief_pdf_permission_error_propagates(
    monkeypatch, tmp_path, valid_brief_payload
):
    from utils import pdf_generator

    monkeypatch.setattr(pdf_generator, "REPORTS_DIR", tmp_path)

    class _DeniedHTML:
        def __init__(self, *args, **kwargs):
            pass

        def write_pdf(self, *args, **kwargs):
            raise PermissionError("Access is denied")

    monkeypatch.setattr(pdf_generator, "HTML", _DeniedHTML)

    with pytest.raises(PermissionError):
        pdf_generator.render_client_brief_pdf(valid_brief_payload)
