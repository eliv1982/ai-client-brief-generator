from __future__ import annotations

from pathlib import Path

import pytest

import main


# ── read_dialog_file: filesystem edge cases ─────────────────────────────────

def test_read_dialog_file_missing_path_exits(tmp_path):
    missing = tmp_path / "does_not_exist.txt"
    with pytest.raises(SystemExit) as exc_info:
        main.read_dialog_file(missing)
    assert exc_info.value.code == 1


def test_read_dialog_file_rejects_directory(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        main.read_dialog_file(tmp_path)
    assert exc_info.value.code == 1


def test_read_dialog_file_rejects_empty_file(tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("   \n\t  ", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main.read_dialog_file(f)
    assert exc_info.value.code == 1


def test_read_dialog_file_rejects_undecodable_bytes(tmp_path):
    f = tmp_path / "bad_encoding.txt"
    f.write_bytes(b"\x80\x81\x82\x83 not valid utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main.read_dialog_file(f)
    assert exc_info.value.code == 1


def test_read_dialog_file_handles_mocked_read_failure(tmp_path, monkeypatch):
    f = tmp_path / "dialog.txt"
    f.write_text("Диалог с клиентом.", encoding="utf-8")

    def _raise_permission_error(self, *args, **kwargs):
        raise PermissionError("Access is denied")

    monkeypatch.setattr(Path, "read_text", _raise_permission_error)

    with pytest.raises(SystemExit) as exc_info:
        main.read_dialog_file(f)
    assert exc_info.value.code == 1


def test_read_dialog_file_accepts_valid_utf8(tmp_path):
    f = tmp_path / "dialog.txt"
    f.write_text("Привет, это диалог с клиентом.", encoding="utf-8")
    text = main.read_dialog_file(f)
    assert "Привет" in text


def test_read_dialog_file_accepts_utf8_bom(tmp_path):
    f = tmp_path / "dialog.txt"
    f.write_text("Привет, это диалог с клиентом.", encoding="utf-8-sig")
    text = main.read_dialog_file(f)
    assert text.startswith("Привет")


def test_read_dialog_file_rejects_oversized_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "MAX_DIALOG_CHARS", 50)
    f = tmp_path / "big.txt"
    f.write_text("x" * 200, encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main.read_dialog_file(f)
    assert exc_info.value.code == 1


def test_run_client_report_oversized_file_makes_no_openai_call(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "MAX_DIALOG_CHARS", 50)
    f = tmp_path / "big.txt"
    f.write_text("x" * 200, encoding="utf-8")

    calls = []
    monkeypatch.setattr(
        "utils.ai_processor.extract_brief_from_dialog",
        lambda text: calls.append(text) or {},
    )

    with pytest.raises(SystemExit):
        main.run_client_report(f)

    assert calls == []


# ── design report flow (mocked) ─────────────────────────────────────────────

def _wire_design_mocks(monkeypatch, tmp_path, valid_design_payload, *, generate_design_image):
    dialog = tmp_path / "dialog.txt"
    dialog.write_text("Диалог о дизайне лендинга для студии йоги.", encoding="utf-8")

    monkeypatch.setattr(
        "utils.ai_processor.extract_design_report_from_dialog",
        lambda text: valid_design_payload,
    )
    monkeypatch.setattr("utils.image_generator.generate_design_image", generate_design_image)

    rendered = {}

    def fake_render(design_data, image_path):
        rendered["design_data"] = design_data
        rendered["image_path"] = image_path
        out = tmp_path / "out.pdf"
        out.write_bytes(b"%PDF-1.4 fake")
        return out

    monkeypatch.setattr("utils.pdf_generator.render_design_report_pdf", fake_render)
    return dialog, rendered


def test_run_design_report_normal_flow_calls_image_api(monkeypatch, tmp_path, valid_design_payload):
    fake_image_path = tmp_path / "image.png"
    fake_image_path.write_bytes(b"PNGDATA")
    calls = []

    def fake_generate(prompt):
        calls.append(prompt)
        return fake_image_path

    dialog, rendered = _wire_design_mocks(
        monkeypatch, tmp_path, valid_design_payload, generate_design_image=fake_generate
    )

    main.run_design_report(dialog, no_image=False)

    assert len(calls) == 1
    assert calls[0] == valid_design_payload["image_prompt"]
    assert rendered["image_path"] == fake_image_path


def test_run_design_report_no_image_flag_skips_image_call(monkeypatch, tmp_path, valid_design_payload):
    def fail_if_called(prompt):
        raise AssertionError("generate_design_image must not be called with --no-image")

    dialog, rendered = _wire_design_mocks(
        monkeypatch, tmp_path, valid_design_payload, generate_design_image=fail_if_called
    )

    main.run_design_report(dialog, no_image=True)

    assert rendered["image_path"] is None


def test_run_design_report_image_failure_falls_back_to_no_image(
    monkeypatch, tmp_path, valid_design_payload
):
    dialog, rendered = _wire_design_mocks(
        monkeypatch, tmp_path, valid_design_payload, generate_design_image=lambda prompt: None
    )

    main.run_design_report(dialog, no_image=False)

    # PDF must still be produced, without an image.
    assert rendered["image_path"] is None
    assert "design_data" in rendered
