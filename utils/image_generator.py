"""image_generator.py — placeholder for future image generation support.

TODO: implement DALL-E / Stable Diffusion integration for design reports.
      This module is intentionally left as a stub for Phase 2.
"""
from __future__ import annotations

from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

IMAGES_DIR = Path("generated_images")


def generate_cover_image(prompt: str, filename: str) -> Path:
    """Generate a cover image for a report.

    Args:
        prompt: Text description of the desired image.
        filename: Output filename (without directory).

    Returns:
        Path to the saved image file.

    Raises:
        NotImplementedError: Always — this feature is not yet implemented.
    """
    raise NotImplementedError(
        "Image generation is not implemented yet. "
        "It is planned for Phase 2 using the OpenAI Images API."
    )
