"""
Content type strategy registry.

Maps content type names to their strategies and provides lookup functionality.
"""


from __future__ import annotations

from typing import TYPE_CHECKING

from .base import ContentTypeStrategy
from .strategies import (
    ApiReferenceStrategy,
    ArchiveStrategy,
    BlogStrategy,
    ChangelogStrategy,
    CliReferenceStrategy,
    DocsStrategy,
    PageStrategy,
    TutorialStrategy,
)

if TYPE_CHECKING:
    from bengal.core.section import Section


# Global registry of content type strategies
CONTENT_TYPE_REGISTRY: dict[str, ContentTypeStrategy] = {
    "blog": BlogStrategy(),
    "archive": ArchiveStrategy(),
    "changelog": ChangelogStrategy(),
    "doc": DocsStrategy(),
    "api-reference": ApiReferenceStrategy(),
    "cli-reference": CliReferenceStrategy(),
    "tutorial": TutorialStrategy(),
    "page": PageStrategy(),
    "list": PageStrategy(),  # Alias for generic lists
}


def get_strategy(content_type: str) -> ContentTypeStrategy:
    """
    Get the strategy for a content type.

    Args:
        content_type: Type name (e.g., "blog", "doc", "api-reference")

    Returns:
        ContentTypeStrategy instance

    Example:
        >>> strategy = get_strategy("blog")
        >>> sorted_posts = strategy.sort_pages(posts)
    """
    return CONTENT_TYPE_REGISTRY.get(content_type, PageStrategy())


def detect_content_type(section: Section) -> str:
    """
    Auto-detect content type from section characteristics.

    Uses heuristics from each strategy to determine the best type.

    Priority order:
    1. Explicit type in section metadata
    2. Cascaded type from parent section
    3. Auto-detection via strategy heuristics
    4. Default to "list"

    Args:
        section: Section to analyze

    Returns:
        Content type name

    Example:
        >>> content_type = detect_content_type(blog_section)
        >>> assert content_type == "blog"
    """
    # 1. Explicit override (highest priority)
    if "content_type" in section.metadata:
        return section.metadata["content_type"]

    # 2. Check for cascaded type from parent section
    if section.parent and hasattr(section.parent, "metadata"):
        parent_cascade = section.parent.metadata.get("cascade", {})
        if "type" in parent_cascade:
            return parent_cascade["type"]

    # 3. Auto-detect using strategy heuristics
    # Try strategies in priority order
    detection_order = [
        ("api-reference", ApiReferenceStrategy()),
        ("cli-reference", CliReferenceStrategy()),
        ("blog", BlogStrategy()),
        ("tutorial", TutorialStrategy()),
        ("doc", DocsStrategy()),
    ]

    for content_type, strategy in detection_order:
        if strategy.detect_from_section(section):
            return content_type

    # 4. Default fallback
    return "list"


def register_strategy(content_type: str, strategy: ContentTypeStrategy) -> None:
    """
    Register a custom content type strategy.

    Allows users to add their own content types.

    Args:
        content_type: Type name
        strategy: Strategy instance

    Example:
        >>> class CustomStrategy(ContentTypeStrategy):
        ...     default_template = "custom/list.html"
        >>> register_strategy("custom", CustomStrategy())
    """
    CONTENT_TYPE_REGISTRY[content_type] = strategy
