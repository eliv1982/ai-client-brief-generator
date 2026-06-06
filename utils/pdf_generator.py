from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from weasyprint import HTML

from utils.logger import get_logger

logger = get_logger(__name__)

REPORTS_DIR = Path("reports")
TEMPLATES_DIR = Path("templates")


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )


def _unique_path(base: Path) -> Path:
    """Return *base* if it does not exist, otherwise append _2, _3, … until free."""
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    parent = base.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def render_client_brief_pdf(brief_data: dict) -> Path:
    """Render *brief_data* into the client brief HTML template and save as PDF.

    Returns the path to the generated PDF file.

    Raises:
        FileNotFoundError: if the HTML template is missing.
        PermissionError: if the output file cannot be written (e.g. already open).
        RuntimeError: on other PDF generation failures.
    """
    REPORTS_DIR.mkdir(exist_ok=True)

    env = _get_jinja_env()
    template_name = "client_brief_template.html"

    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        raise FileNotFoundError(
            f"HTML-шаблон не найден: {TEMPLATES_DIR / template_name}"
        )

    logger.info("Rendering HTML template ...")
    generated_at = datetime.now().strftime("%d.%m.%Y, %H:%M")
    html_content = template.render(**brief_data, generated_at=generated_at)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_path = REPORTS_DIR / f"client_report_{timestamp}.pdf"
    output_path = _unique_path(base_path)

    logger.info("Generating PDF -> %s ...", output_path)
    try:
        HTML(string=html_content, base_url=str(Path.cwd())).write_pdf(str(output_path))
    except PermissionError as exc:
        logger.error("PermissionError saving PDF %s: %s", output_path, exc)
        raise PermissionError(output_path) from exc
    except Exception as exc:
        raise RuntimeError(f"PDF generation failed: {exc}") from exc

    logger.info("PDF saved: %s", output_path)
    return output_path


def render_design_report_pdf(design_data: dict, image_path: Path | None) -> Path:
    """Render *design_data* into the design report HTML template and save as PDF.

    Args:
        design_data: Validated dict from extract_design_report_from_dialog().
        image_path: Path to the generated concept image, or None if unavailable.

    Returns the path to the generated PDF file.

    Raises:
        FileNotFoundError: if the HTML template is missing.
        PermissionError: if the output file cannot be written.
        RuntimeError: on other PDF generation failures.
    """
    REPORTS_DIR.mkdir(exist_ok=True)

    env = _get_jinja_env()
    template_name = "design_report_template.html"

    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        raise FileNotFoundError(
            f"HTML-шаблон не найден: {TEMPLATES_DIR / template_name}"
        )

    logger.info("Rendering design report HTML template ...")
    generated_at = datetime.now().strftime("%d.%m.%Y, %H:%M")

    image_uri: str | None = None
    if image_path and image_path.exists():
        image_uri = image_path.resolve().as_uri()

    html_content = template.render(
        **design_data,
        generated_at=generated_at,
        image_uri=image_uri,
    )

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_path = REPORTS_DIR / f"design_report_{timestamp}.pdf"
    output_path = _unique_path(base_path)

    logger.info("Generating PDF -> %s ...", output_path)
    try:
        HTML(string=html_content, base_url=str(Path.cwd())).write_pdf(str(output_path))
    except PermissionError as exc:
        logger.error("PermissionError saving PDF %s: %s", output_path, exc)
        raise PermissionError(output_path) from exc
    except Exception as exc:
        raise RuntimeError(f"PDF generation failed: {exc}") from exc

    logger.info("PDF saved: %s", output_path)
    return output_path
