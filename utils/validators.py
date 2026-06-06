from __future__ import annotations

from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_FIELDS: dict[str, type] = {
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


class BriefValidationError(ValueError):
    """Raised when the parsed brief JSON does not meet the required schema."""


def validate_brief(data: Any) -> dict:
    """Validate that *data* is a dict with all required brief fields.

    Returns the validated dict on success; raises BriefValidationError otherwise.
    """
    if not isinstance(data, dict):
        raise BriefValidationError(
            f"Expected a JSON object at the top level, got {type(data).__name__}."
        )

    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        raise BriefValidationError(
            f"Missing required field(s): {', '.join(missing)}."
        )

    type_errors: list[str] = []
    for field, expected_type in REQUIRED_FIELDS.items():
        value = data[field]
        if not isinstance(value, expected_type):
            type_errors.append(
                f"  • '{field}': expected {expected_type.__name__}, "
                f"got {type(value).__name__} ({value!r})"
            )

    if type_errors:
        raise BriefValidationError(
            "Type mismatch in the following fields:\n" + "\n".join(type_errors)
        )

    # Ensure list fields contain only strings
    list_fields = [f for f, t in REQUIRED_FIELDS.items() if t is list]
    for field in list_fields:
        bad_items = [
            item for item in data[field] if not isinstance(item, str)
        ]
        if bad_items:
            type_errors.append(
                f"  • '{field}' must be a list of strings, "
                f"but contains: {bad_items!r}"
            )

    if type_errors:
        raise BriefValidationError(
            "List items must be strings:\n" + "\n".join(type_errors)
        )

    logger.debug("Brief JSON passed validation — all %d fields OK.", len(REQUIRED_FIELDS))
    return data
