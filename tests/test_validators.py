from __future__ import annotations

import copy

import pytest

from utils.validators import (
    BriefValidationError,
    validate_brief,
    validate_design_report,
)


# ── Valid payloads ──────────────────────────────────────────────────────────

def test_validate_brief_accepts_valid_payload(valid_brief_payload):
    result = validate_brief(valid_brief_payload)
    assert result["client_name"] == "Иван Иванов"
    assert result["client_pain_points"] == valid_brief_payload["client_pain_points"]


def test_validate_design_report_accepts_valid_payload(valid_design_payload):
    result = validate_design_report(valid_design_payload)
    assert result["project_type"] == "Лендинг"
    assert result["image_prompt"] == valid_design_payload["image_prompt"]


def test_validate_brief_strips_whitespace(valid_brief_payload):
    valid_brief_payload["client_name"] = "  Иван Иванов  "
    result = validate_brief(valid_brief_payload)
    assert result["client_name"] == "Иван Иванов"


# ── Top-level shape ─────────────────────────────────────────────────────────

def test_validate_brief_rejects_non_dict():
    with pytest.raises(BriefValidationError):
        validate_brief(["not", "a", "dict"])


def test_validate_brief_rejects_missing_fields(valid_brief_payload):
    del valid_brief_payload["summary"]
    with pytest.raises(BriefValidationError, match="summary"):
        validate_brief(valid_brief_payload)


def test_validate_brief_discards_unknown_fields(valid_brief_payload):
    valid_brief_payload["unexpected_field"] = "should be dropped"
    result = validate_brief(valid_brief_payload)
    assert "unexpected_field" not in result


# ── Blank / whitespace-only required strings ────────────────────────────────

def test_validate_brief_rejects_blank_required_string(valid_brief_payload):
    valid_brief_payload["client_name"] = ""
    with pytest.raises(BriefValidationError, match="client_name"):
        validate_brief(valid_brief_payload)


def test_validate_brief_rejects_whitespace_only_string(valid_brief_payload):
    valid_brief_payload["summary"] = "   \n\t  "
    with pytest.raises(BriefValidationError, match="summary"):
        validate_brief(valid_brief_payload)


# ── Wrong types ──────────────────────────────────────────────────────────────

def test_validate_brief_rejects_wrong_type_for_string_field(valid_brief_payload):
    valid_brief_payload["client_name"] = 12345
    with pytest.raises(BriefValidationError, match="client_name"):
        validate_brief(valid_brief_payload)


def test_validate_brief_rejects_wrong_type_for_list_field(valid_brief_payload):
    valid_brief_payload["requirements"] = "should be a list"
    with pytest.raises(BriefValidationError, match="requirements"):
        validate_brief(valid_brief_payload)


def test_validate_brief_rejects_non_string_list_items(valid_brief_payload):
    valid_brief_payload["requirements"] = ["valid item", 42]
    with pytest.raises(BriefValidationError, match="requirements"):
        validate_brief(valid_brief_payload)


# ── Oversized values ─────────────────────────────────────────────────────────

def test_validate_brief_rejects_oversized_string_field(valid_brief_payload):
    valid_brief_payload["client_name"] = "x" * 5000
    with pytest.raises(BriefValidationError, match="client_name"):
        validate_brief(valid_brief_payload)


def test_validate_brief_rejects_oversized_long_field(valid_brief_payload):
    valid_brief_payload["summary"] = "x" * 10_000
    with pytest.raises(BriefValidationError, match="summary"):
        validate_brief(valid_brief_payload)


def test_validate_brief_rejects_too_many_list_items(valid_brief_payload):
    valid_brief_payload["next_steps"] = [f"step {i}" for i in range(100)]
    with pytest.raises(BriefValidationError, match="next_steps"):
        validate_brief(valid_brief_payload)


def test_validate_brief_rejects_oversized_list_item(valid_brief_payload):
    valid_brief_payload["next_steps"] = ["x" * 5000]
    with pytest.raises(BriefValidationError, match="next_steps"):
        validate_brief(valid_brief_payload)


def test_validate_brief_rejects_blank_list_item(valid_brief_payload):
    valid_brief_payload["requirements"] = ["valid item", "   "]
    with pytest.raises(BriefValidationError, match="requirements"):
        validate_brief(valid_brief_payload)


def test_validate_brief_accepts_empty_lists(valid_brief_payload):
    valid_brief_payload["client_pain_points"] = []
    valid_brief_payload["requirements"] = []
    valid_brief_payload["risks_or_open_questions"] = []
    valid_brief_payload["next_steps"] = []
    result = validate_brief(valid_brief_payload)
    assert result["requirements"] == []


# ── Design-report-specific ──────────────────────────────────────────────────

def test_validate_design_report_rejects_blank_image_prompt(valid_design_payload):
    valid_design_payload["image_prompt"] = ""
    with pytest.raises(BriefValidationError, match="image_prompt"):
        validate_design_report(valid_design_payload)


def test_validate_design_report_rejects_missing_fields(valid_design_payload):
    del valid_design_payload["key_sections"]
    with pytest.raises(BriefValidationError, match="key_sections"):
        validate_design_report(valid_design_payload)


def test_validate_design_report_does_not_mutate_input(valid_design_payload):
    original = copy.deepcopy(valid_design_payload)
    validate_design_report(valid_design_payload)
    assert valid_design_payload == original
