"""
Rendering utilities - consolidated helpers for the rendering package.

This module provides shared utilities to reduce code duplication across
the rendering subsystem.

Modules:
    contextvar: Generic ContextVarManager[T] for thread-safe context management
    url: URL manipulation and baseurl handling
    safe_access: Safe attribute/dict access with Jinja2 Undefined handling
"""

from bengal.rendering.utils.contextvar import ContextVarManager
from bengal.rendering.utils.safe_access import safe_get, safe_get_nested
from bengal.rendering.utils.url import apply_baseurl, normalize_url_path

__all__ = [
    # ContextVar management
    "ContextVarManager",
    # URL utilities
    "apply_baseurl",
    "normalize_url_path",
    # Safe access utilities
    "safe_get",
    "safe_get_nested",
]
