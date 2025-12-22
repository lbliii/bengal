"""
Content type strategies for Bengal SSG.

This package provides a strategy pattern implementation for handling different
content types (blog, docs, tutorial, changelog, API reference, etc.) with
type-specific behavior for:

- **Sorting**: How pages are ordered in list views (chronological, by weight, etc.)
- **Filtering**: Which pages appear in section listings
- **Pagination**: Whether pagination is enabled and how it's applied
- **Template Selection**: Which templates are used for different page types

Architecture:
    The package follows the Strategy Pattern with a Registry:

    - ContentTypeStrategy: Abstract base defining the strategy interface
    - Concrete strategies: BlogStrategy, DocsStrategy, TutorialStrategy, etc.
    - CONTENT_TYPE_REGISTRY: Maps type names to strategy instances
    - Auto-detection: Heuristics to infer content type from section structure

Public API:
    - ContentTypeStrategy: Base class for custom content type strategies
    - get_strategy: Retrieve a strategy by content type name
    - register_strategy: Register custom content type strategies
    - CONTENT_TYPE_REGISTRY: Direct access to the strategy registry

Example:
    >>> from bengal.content_types import get_strategy
    >>> strategy = get_strategy("blog")
    >>> sorted_posts = strategy.sort_pages(posts)

    >>> from bengal.content_types import ContentTypeStrategy, register_strategy
    >>> class CustomStrategy(ContentTypeStrategy):
    ...     default_template = "custom/list.html"
    >>> register_strategy("custom", CustomStrategy())

Related:
    - bengal/core/section.py: Section model that uses content types
    - bengal/rendering/: Template rendering that consumes strategy.get_template()
    - bengal/orchestration/: Build orchestration using content type detection

See Also:
    - architecture/content-types.md: Design documentation for content types
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
