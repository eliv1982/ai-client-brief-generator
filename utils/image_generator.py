"""image_generator.py — AI image generation for design reports.

Generates a cover concept image using the OpenAI Images API.
Falls back gracefully: on any failure returns None so the PDF is still produced.

Supported models (as of 2026):
  gpt-image-2      — preferred, higher quality, returns b64_json
  gpt-image-1      — reliable fallback, returns b64_json
  chatgpt-image-latest — alias for the current GPT Image flagship

  dall-e-3 / dall-e-2 are previous-generation models and may not be
  available in all OpenAI projects; not recommended for new projects.

Configure via .env:
  IMAGE_MODEL=gpt-image-2
  IMAGE_SIZE=1024x1024      # 1024x1024 | 1536x1024 | 1024x1536
  IMAGE_QUALITY=medium      # low | medium | high | auto
"""
from __future__ import annotations

import base64
import os
import urllib.request
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

IMAGES_DIR = Path("generated_images")

# Safe defaults that work across all model tiers
_DEFAULT_MODEL = "gpt-image-2"
_DEFAULT_SIZE = "1024x1024"
_DEFAULT_QUALITY = "medium"

_TEST_PROMPT = (
    "A clean, minimal workspace with a laptop, a cup of coffee, and a notebook, "
    "soft natural light from the left, top-down view, warm neutral tones, "
    "professional business atmosphere, digital illustration style."
)


def _unique_image_path(base: Path) -> Path:
    """Return *base* if free, otherwise add _2, _3 … suffix."""
    if not base.exists():
        return base
    stem, suffix, parent = base.stem, base.suffix, base.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _save_image(raw: bytes, label: str) -> Path:
    """Write *raw* PNG bytes to a unique path under IMAGES_DIR."""
    IMAGES_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_path = IMAGES_DIR / f"{label}_{timestamp}.png"
    output_path = _unique_image_path(base_path)
    output_path.write_bytes(raw)
    return output_path


class ImageGenError(Exception):
    """Raised when image generation fails; carries human-readable details."""

    def __init__(self, message: str, *, status_code: int | None = None, raw_repr: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.raw_repr = raw_repr


def _generate_raw(prompt: str, model: str, size: str, quality: str) -> bytes:
    """Call OpenAI Images API and return raw PNG bytes.

    Raises ImageGenError on any failure — caller decides whether to propagate
    (diagnostic mode) or swallow (graceful fallback for reports).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ImageGenError("OPENAI_API_KEY не задан в .env — генерация изображений недоступна.")

    prompt_preview = prompt[:200] + ("..." if len(prompt) > 200 else "")
    logger.info("Image API call: model=%s  size=%s  quality=%s", model, size, quality)
    logger.info("Prompt preview: %s", prompt_preview)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size=size,      # type: ignore[arg-type]
            quality=quality,  # type: ignore[arg-type]
        )
    except Exception as exc:
        status_code: int | None = getattr(exc, "status_code", None)
        logger.warning(
            "Image API request failed: %s | status=%s | %s",
            type(exc).__name__, status_code, repr(exc),
        )
        raise ImageGenError(
            str(exc),
            status_code=status_code,
            raw_repr=repr(exc),
        ) from exc

    item = response.data[0] if response.data else None
    if item is None:
        raise ImageGenError("Image API вернул пустой список данных.")

    # ── Try b64_json first (gpt-image-1, gpt-image-2) ─────────────────────────
    b64_data: str | None = getattr(item, "b64_json", None)
    if b64_data:
        logger.debug("Response format: b64_json (%d chars)", len(b64_data))
        try:
            return base64.b64decode(b64_data)
        except Exception as exc:
            raise ImageGenError(f"Ошибка декодирования b64_json: {exc}") from exc

    # ── Fall back to URL (dall-e-3, dall-e-2) ─────────────────────────────────
    url: str | None = item.url
    if url:
        logger.debug("Response format: URL")
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
                return resp.read()
        except Exception as exc:
            raise ImageGenError(f"Ошибка скачивания изображения по URL: {exc}") from exc

    # ── Neither format available ───────────────────────────────────────────────
    attrs = [a for a in dir(item) if not a.startswith("_")]
    raise ImageGenError(
        f"API вернул ответ без b64_json и без url. "
        f"Тип элемента: {type(item).__name__}, атрибуты: {attrs}"
    )


def generate_design_image(image_prompt: str) -> Path | None:
    """Generate a design concept image from *image_prompt* and save to disk.

    Returns the Path to the saved PNG on success, or None on any failure.
    The caller must handle None gracefully (PDF renders a placeholder instead).
    """
    model = os.getenv("IMAGE_MODEL", _DEFAULT_MODEL)
    size = os.getenv("IMAGE_SIZE", _DEFAULT_SIZE)
    quality = os.getenv("IMAGE_QUALITY", _DEFAULT_QUALITY)

    try:
        raw = _generate_raw(image_prompt, model, size, quality)
    except ImageGenError as exc:
        logger.warning("Image generation failed: %s", exc)
        return None
    except Exception as exc:
        logger.warning(
            "Unexpected image generation error: %s | %s", type(exc).__name__, repr(exc)
        )
        return None

    try:
        output_path = _save_image(raw, "design_concept")
        logger.info("Image saved: %s", output_path)
        return output_path
    except Exception as exc:
        logger.warning(
            "Failed to save image file: %s | %s", type(exc).__name__, repr(exc)
        )
        return None


def list_available_image_models() -> list[str]:
    """Return image-capable model IDs for the current API key, or [] on error."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        keywords = ("dall", "image", "gpt-image")
        return sorted(
            m.id
            for m in client.models.list().data
            if any(kw in m.id.lower() for kw in keywords)
        )
    except Exception as exc:
        logger.debug("Could not list models: %s", exc)
        return []


def generate_test_image() -> tuple[Path | None, str | None]:
    """Generate a simple test image to verify image API connectivity.

    Returns:
        (path, None)        on success
        (None, error_text)  on failure — error_text is human-readable
    """
    model = os.getenv("IMAGE_MODEL", _DEFAULT_MODEL)
    size = os.getenv("IMAGE_SIZE", _DEFAULT_SIZE)
    quality = os.getenv("IMAGE_QUALITY", _DEFAULT_QUALITY)

    logger.info("Running image API diagnostic test ...")
    logger.info("Model: %s | Size: %s | Quality: %s", model, size, quality)

    try:
        raw = _generate_raw(_TEST_PROMPT, model, size, quality)
    except ImageGenError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

    try:
        output_path = _save_image(raw, "test_image")
        logger.info("Test image saved: %s", output_path)
        return output_path, None
    except Exception as exc:
        return None, f"Файл сохранить не удалось: {type(exc).__name__}: {exc}"
