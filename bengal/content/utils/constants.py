"""
Content-related constants.

Centralizes constants used across the content package to ensure consistency.
"""

from __future__ import annotations

# File extensions recognized as content files
CONTENT_EXTENSIONS: frozenset[str] = frozenset({".md", ".markdown", ".rst", ".txt"})
