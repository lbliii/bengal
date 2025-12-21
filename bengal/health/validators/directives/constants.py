"""
Directive validation constants and configuration.

Imports directive type definitions from the rendering package (single source of truth)
and adds health-check-specific thresholds and configuration.
"""

from __future__ import annotations

# Import from the single source of truth (rendering/plugins/directives/__init__.py)
# This ensures the health check stays in sync with actually registered directives.
from bengal.directives import (
    ADMONITION_TYPES,
    CODE_BLOCK_DIRECTIVES,
    KNOWN_DIRECTIVE_NAMES,
)

# Re-export for backward compatibility with existing imports
# These are now imported from the rendering package
KNOWN_DIRECTIVES = KNOWN_DIRECTIVE_NAMES

# Re-export type-specific constants
__all__ = [
    "KNOWN_DIRECTIVES",
    "ADMONITION_TYPES",
    "CODE_BLOCK_DIRECTIVES",
    "MAX_DIRECTIVES_PER_PAGE",
    "MAX_NESTING_DEPTH",
    "MAX_TABS_PER_BLOCK",
]

# Performance thresholds
MAX_DIRECTIVES_PER_PAGE = 10  # Warn if page has more than this
MAX_NESTING_DEPTH = 5  # Warn if nesting deeper than this
MAX_TABS_PER_BLOCK = 10  # Warn if single tabs block has more than this
