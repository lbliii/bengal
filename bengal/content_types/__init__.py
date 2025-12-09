"""
Content type strategies for Bengal SSG.

This module provides a strategy pattern for handling different content types
(blog, docs, api-reference, etc.) with type-specific behavior for sorting,
filtering, pagination, and templating.
"""

from __future__ import annotations

from .base import ContentTypeStrategy
from .registry import CONTENT_TYPE_REGISTRY, get_strategy, register_strategy

__all__ = [
    "ContentTypeStrategy",
    "get_strategy",
    "register_strategy",
    "CONTENT_TYPE_REGISTRY",
]
