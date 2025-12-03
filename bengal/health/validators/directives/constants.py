"""
Directive validation constants and configuration.

Defines known directive types, performance thresholds, and validation settings.
"""

from __future__ import annotations

# Directive types we know about
# This should match all directive types registered in bengal/rendering/plugins/directives/
KNOWN_DIRECTIVES = {
    # Admonitions
    "admonition",  # Generic admonition directive
    "note",
    "tip",
    "warning",
    "danger",
    "error",
    "info",
    "example",
    "success",
    "caution",
    # Badges
    "badge",
    "bdg",  # Alias for badge (Sphinx-Design compatibility)
    # Buttons
    "button",
    # Cards
    "card",
    "cards",
    "grid",  # Sphinx-Design compatibility
    # Tabs
    "tabs",
    "tab-set",
    "tab-item",
    # Code tabs
    "code-tabs",
    "code_tabs",
    # Dropdowns
    "dropdown",
    "details",
    # Tables
    "list-table",
    "data-table",
    "data_table",  # Alternative naming
    # Checklists
    "checklist",
    # Steps
    "steps",
    "step",
    # Rubric
    "rubric",
    # Includes
    "include",
    "literalinclude",
    # Marimo (if installed)
    "marimo",
}

# Admonition types (should use colon fences)
ADMONITION_TYPES = {
    "note",
    "tip",
    "warning",
    "danger",
    "error",
    "info",
    "example",
    "success",
    "caution",
}

# Directives that are code-related and can reasonably use backtick fences
CODE_BLOCK_DIRECTIVES = {
    "code-tabs",
    "code_tabs",
    "literalinclude",
}

# Performance thresholds
MAX_DIRECTIVES_PER_PAGE = 10  # Warn if page has more than this
MAX_NESTING_DEPTH = 5  # Warn if nesting deeper than this
MAX_TABS_PER_BLOCK = 10  # Warn if single tabs block has more than this
