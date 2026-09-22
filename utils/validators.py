from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union

from utils.logger import get_logger

logger = get_logger(__name__)


class BriefValidationError(ValueError):
    """Raised when a parsed JSON response does not meet the required schema."""


# ── Field specs ─────────────────────────────────────────────────────────────
#
# Bounds are modest and practical for a business-dialog brief/report — large
# enough for real narrative text, small enough that a pathological model
# response cannot balloon into an unusable PDF.

@dataclass(frozen=True)
class _StrField:
    max_len: int


@dataclass(frozen=True)
class _ListField:
    max_items: int
    item_max_len: int


_SHORT = _StrField(max_len=200)         # names, dates, budget, single-line labels
_MEDIUM = _StrField(max_len=600)        # short descriptive text
_LONG = _StrField(max_len=3000)         # narrative paragraphs (summary, main request, ...)
_IMAGE_PROMPT = _StrField(max_len=1500)  # English image-generation prompt
_LIST = _ListField(max_items=25, item_max_len=400)

_FieldSpec = Union[_StrField, _ListField]

# ── client_report schema ───────────────────────────────────────────────────

BRIEF_SCHEMA: dict[str, _FieldSpec] = {
    "client_name": _SHORT,
    "company_or_project": _SHORT,
    "topic": _SHORT,
    "main_request": _LONG,
    "client_pain_points": _LIST,
    "requirements": _LIST,
    "deadline": _SHORT,
    "budget": _SHORT,
    "risks_or_open_questions": _LIST,
    "next_steps": _LIST,
    "summary": _LONG,
}

# ── design_report schema ───────────────────────────────────────────────────

DESIGN_SCHEMA: dict[str, _FieldSpec] = {
    "client_name": _SHORT,
    "company_or_project": _SHORT,
    "project_type": _SHORT,
    "design_goal": _LONG,
    "target_audience": _MEDIUM,
    "preferred_style": _SHORT,
    "key_sections": _LIST,
    "colors_or_visual_preferences": _MEDIUM,
    "functional_requirements": _LIST,
    "deadline": _SHORT,
    "budget": _SHORT,
    "risks_or_open_questions": _LIST,
    "next_steps": _LIST,
    "summary": _LONG,
    "image_prompt": _IMAGE_PROMPT,
}


# ── Generic validator ──────────────────────────────────────────────────────

def _validate(data: Any, schema: dict[str, _FieldSpec], label: str) -> dict:
    """Validate *data* against *schema* and return a normalized dict.

    Only fields declared in *schema* are ever returned — unknown top-level
    fields from the model response are logged and silently discarded so
    only the expected, normalized shape reaches templates/rendering code.
    """
    if not isinstance(data, dict):
        raise BriefValidationError(
            f"Expected a JSON object at the top level for {label}, got {type(data).__name__}."
        )

    missing = [field for field in schema if field not in data]
    if missing:
        raise BriefValidationError(
            f"Missing required field(s) in {label}: {', '.join(missing)}."
        )

    unknown = sorted(set(data) - set(schema))
    if unknown:
        logger.warning(
            "%s: discarding %d unexpected top-level field(s): %s",
            label, len(unknown), ", ".join(unknown),
        )

    errors: list[str] = []
    normalized: dict[str, Any] = {}

    for field, spec in schema.items():
        value = data[field]

        if isinstance(spec, _StrField):
            if not isinstance(value, str):
                errors.append(f"  '{field}': expected str, got {type(value).__name__}.")
                continue
            cleaned = value.strip()
            if not cleaned:
                errors.append(f"  '{field}': must not be blank or whitespace-only.")
                continue
            if len(cleaned) > spec.max_len:
                errors.append(
                    f"  '{field}': too long ({len(cleaned)} chars, max {spec.max_len})."
                )
                continue
            normalized[field] = cleaned

        else:  # _ListField
            if not isinstance(value, list):
                errors.append(f"  '{field}': expected list, got {type(value).__name__}.")
                continue
            if len(value) > spec.max_items:
                errors.append(
                    f"  '{field}': too many items ({len(value)}, max {spec.max_items})."
                )
                continue

            item_errors: list[str] = []
            cleaned_items: list[str] = []
            for i, item in enumerate(value):
                if not isinstance(item, str):
                    item_errors.append(f"    [{i}]: expected str, got {type(item).__name__}.")
                    continue
                cleaned_item = item.strip()
                if not cleaned_item:
                    item_errors.append(f"    [{i}]: must not be blank or whitespace-only.")
                    continue
                if len(cleaned_item) > spec.item_max_len:
                    item_errors.append(
                        f"    [{i}]: too long ({len(cleaned_item)} chars, max {spec.item_max_len})."
                    )
                    continue
                cleaned_items.append(cleaned_item)

            if item_errors:
                errors.append(f"  '{field}':\n" + "\n".join(item_errors))
                continue
            normalized[field] = cleaned_items

    if errors:
        raise BriefValidationError(
            f"Validation failed for {label}:\n" + "\n".join(errors)
        )

    logger.debug("%s JSON passed validation — %d fields OK.", label, len(schema))
    return normalized


# ── Public validators ──────────────────────────────────────────────────────

def validate_brief(data: Any) -> dict:
    """Validate a client_report JSON response."""
    return _validate(data, BRIEF_SCHEMA, "client_report")


def validate_design_report(data: Any) -> dict:
    """Validate a design_report JSON response."""
    return _validate(data, DESIGN_SCHEMA, "design_report")
