"""
Directive validation constants and configuration.

Sources directive type definitions from the Patitas registry (single source of truth)
and adds health-check-specific thresholds and configuration.
"""

from __future__ import annotations

from bengal.parsing.backends.patitas.directives.builtins.admonition import (
    ADMONITION_TYPES,
)
from bengal.parsing.backends.patitas.directives.registry import create_default_registry

# Build known directive names from the Patitas registry (single source of truth)
_registry = create_default_registry()
KNOWN_DIRECTIVE_NAMES: frozenset[str] = _registry.names

# Code block directives (directives that contain code)
CODE_BLOCK_DIRECTIVES: frozenset[str] = frozenset(
    {"code-tabs", "literalinclude", "code", "code-block"}
)

# Re-export for backward compatibility
KNOWN_DIRECTIVES = KNOWN_DIRECTIVE_NAMES

__all__ = [
    "ADMONITION_TYPES",
    "CODE_BLOCK_DIRECTIVES",
    "KNOWN_DIRECTIVES",
    "KNOWN_DIRECTIVE_NAMES",
    "MAX_NESTING_DEPTH",
    "MAX_TABS_PER_BLOCK",
]

# Performance thresholds
MAX_NESTING_DEPTH = 5  # Warn if nesting deeper than this
MAX_TABS_PER_BLOCK = 10  # Warn if single tabs block has more than this
