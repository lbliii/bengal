"""
DEPRECATED: Mistune parser has moved to mistune/ package.

This module provides backward-compatible imports. Update imports to:
    from bengal.rendering.parsers.mistune import MistuneParser

This redirect will be removed in a future release.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "Import from bengal.rendering.parsers.mistune instead of "
    "bengal.rendering.parsers.mistune (module). "
    "The mistune.py module is deprecated and will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export MistuneParser from new package
from bengal.rendering.parsers.mistune import MistuneParser  # noqa: E402

__all__ = ["MistuneParser"]
