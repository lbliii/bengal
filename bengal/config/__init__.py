"""
Configuration management for Bengal SSG.
"""

from __future__ import annotations

from bengal.config.deprecation import (
    DEPRECATED_KEYS,
    RENAMED_KEYS,
    check_deprecated_keys,
    get_deprecation_summary,
    migrate_deprecated_keys,
    print_deprecation_warnings,
)
from bengal.config.loader import ConfigLoader

__all__ = [
    "ConfigLoader",
    "DEPRECATED_KEYS",
    "RENAMED_KEYS",
    "check_deprecated_keys",
    "get_deprecation_summary",
    "migrate_deprecated_keys",
    "print_deprecation_warnings",
]
