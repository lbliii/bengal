"""Re-export ImageProcessor from services layer.

Image processing with I/O was moved to bengal.services.image_processor
for core model purity (no I/O in core/). This module provides backward
compatibility for imports.
"""

from __future__ import annotations

from bengal.services.image_processor import (
    CACHE_SCHEMA_VERSION,
    ImageProcessor,
    clear_cache,
    get_cache_stats,
)

__all__ = ["CACHE_SCHEMA_VERSION", "ImageProcessor", "clear_cache", "get_cache_stats"]
