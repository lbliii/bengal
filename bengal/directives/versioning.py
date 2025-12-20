"""Version-aware directives for since, deprecated, changed."""

from __future__ import annotations

from bengal.rendering.plugins.directives.versioning import (
    ChangedDirective,
    DeprecatedDirective,
    SinceDirective,
)

__all__ = [
    "SinceDirective",
    "DeprecatedDirective",
    "ChangedDirective",
]

DIRECTIVE_NAMES = (
    SinceDirective.DIRECTIVE_NAMES
    + DeprecatedDirective.DIRECTIVE_NAMES
    + ChangedDirective.DIRECTIVE_NAMES
)
