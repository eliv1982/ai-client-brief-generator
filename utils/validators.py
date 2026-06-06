from __future__ import annotations

from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

# ── client_report schema ───────────────────────────────────────────────────────

BRIEF_REQUIRED_FIELDS: dict[str, type] = {
    "client_name": str,
    "company_or_project": str,
    "topic": str,
    "main_request": str,
    "client_pain_points": list,
    "requirements": list,
    "deadline": str,
    "budget": str,
    "risks_or_open_questions": list,
    "next_steps": list,
    "summary": str,
}

# ── design_report schema ───────────────────────────────────────────────────────

DESIGN_REQUIRED_FIELDS: dict[str, type] = {
    "client_name": str,
    "company_or_project": str,
    "project_type": str,
    "design_goal": str,
    "target_audience": str,
    "preferred_style": str,
    "key_sections": list,
    "colors_or_visual_preferences": str,
    "functional_requirements": list,
    "deadline": str,
    "budget": str,
    "risks_or_open_questions": list,
    "next_steps": list,
    "summary": str,
    "image_prompt": str,
}


class BriefValidationError(ValueError):
    """Raised when a parsed JSON response does not meet the required schema."""


# ── Generic validator ──────────────────────────────────────────────────────────

def _validate(data: Any, schema: dict[str, type], label: str) -> dict:
    if not isinstance(data, dict):
        raise BriefValidationError(
            f"Expected a JSON object at the top level, got {type(data).__name__}."
        )

    missing = [field for field in schema if field not in data]
    if missing:
        raise BriefValidationError(
            f"Missing required field(s) in {label}: {', '.join(missing)}."
        )

    type_errors: list[str] = []
    for field, expected_type in schema.items():
        value = data[field]
        if not isinstance(value, expected_type):
            type_errors.append(
                f"  '{field}': expected {expected_type.__name__}, "
                f"got {type(value).__name__} ({value!r})"
            )

    if type_errors:
        raise BriefValidationError(
            f"Type mismatch in {label}:\n" + "\n".join(type_errors)
        )

    list_fields = [f for f, t in schema.items() if t is list]
    for field in list_fields:
        bad_items = [item for item in data[field] if not isinstance(item, str)]
        if bad_items:
            type_errors.append(
                f"  '{field}' must be a list of strings, but contains: {bad_items!r}"
            )

    if type_errors:
        raise BriefValidationError(
            f"List items must be strings in {label}:\n" + "\n".join(type_errors)
        )

    logger.debug("%s JSON passed validation — all %d fields OK.", label, len(schema))
    return data


# ── Public validators ──────────────────────────────────────────────────────────

def validate_brief(data: Any) -> dict:
    """Validate a client_report JSON response."""
    return _validate(data, BRIEF_REQUIRED_FIELDS, "client_report")


def validate_design_report(data: Any) -> dict:
    """Validate a design_report JSON response."""
    return _validate(data, DESIGN_REQUIRED_FIELDS, "design_report")
