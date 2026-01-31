"""Shared types for image resource processing.

This module contains types shared between image.py and processor.py
to break the circular import between them.

Types:
    ProcessParams: Parsed image processing parameters
    ProcessedImageData: Data class for processed image results

"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@dataclass
class ProcessParams:
    """Parsed image processing parameters.

    Parsed from Hugo-style spec strings like "800x600 webp q80 center".

    """

    width: int | None = None
    height: int | None = None
    format: str | None = None
    quality: int = 85
    anchor: str = "center"

    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.quality < 1 or self.quality > 100:
            logger.warning(
                "Quality must be 1-100, using 85",
                event="invalid_quality",
                quality=self.quality,
            )
            self.quality = 85


def parse_spec(spec: str) -> ProcessParams | None:
    """Parse Hugo-style spec string.

    Args:
        spec: Spec string like "800x600 webp q80 center"

    Returns:
        ProcessParams if valid, None if invalid

    Examples:
            >>> parse_spec("800x600")
        ProcessParams(width=800, height=600)
            >>> parse_spec("800x webp q80")
        ProcessParams(width=800, height=None, format='webp', quality=80)

    """
    parts = spec.split()
    params = ProcessParams()

    valid_formats = {"webp", "avif", "jpeg", "jpg", "png", "gif"}
    valid_anchors = {
        "center",
        "smart",
        "top",
        "bottom",
        "left",
        "right",
        "topleft",
        "topright",
        "bottomleft",
        "bottomright",
    }

    for part in parts:
        part_lower = part.lower()

        # Try to parse as dimension (WIDTHxHEIGHT or WIDTHx or xHEIGHT)
        if "x" in part_lower:
            try:
                w_str, h_str = part_lower.split("x", 1)
                params.width = int(w_str) if w_str else None
                params.height = int(h_str) if h_str else None
                continue
            except ValueError:
                logger.error("invalid_dimension_spec", spec=part)
                return None

        # Try to parse as format
        if part_lower in valid_formats:
            params.format = "jpeg" if part_lower == "jpg" else part_lower
            continue

        # Try to parse as quality (q80, q75, etc.)
        if part_lower.startswith("q") and part_lower[1:].isdigit():
            params.quality = int(part_lower[1:])
            continue

        # Try to parse as anchor
        if part_lower in valid_anchors:
            params.anchor = part_lower
            continue

        # Unknown part - log warning but continue
        logger.warning("unknown_spec_part", part=part, full_spec=spec)

    return params


@dataclass
class ProcessedImageData:
    """Data for a processed image result.

    This is a simple data class without the source reference to avoid cycles.
    ProcessedImage in image.py wraps this with the source reference.

    """

    output_path: Path
    rel_permalink: str
    width: int
    height: int
    format: str
    file_size: int
