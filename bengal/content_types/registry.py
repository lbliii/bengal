"""
Content type strategy registry.

Maps content type names to their strategies and provides lookup functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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


def normalize_page_type_to_content_type(page_type: str) -> str | None:
    """
    Normalize a page type to a content type.

    Handles special cases where page types (from frontmatter) map to content types:
    - python-module -> api-reference
    - cli-command -> cli-reference
    - Other types pass through if registered

    Args:
        page_type: Page type from frontmatter (e.g., "python-module", "blog")

    Returns:
        Content type name if recognized, None otherwise

    Example:
        >>> normalize_page_type_to_content_type("python-module")
        'api-reference'
        >>> normalize_page_type_to_content_type("blog")
        'blog'
        >>> normalize_page_type_to_content_type("unknown")
        None
    """
    # Special mappings for autodoc-generated types
    special_mappings = {
        "python-module": "api-reference",
        "cli-command": "cli-reference",
    }

    if page_type in special_mappings:
        return special_mappings[page_type]

    # If it's already a registered content type, return as-is
    if page_type in CONTENT_TYPE_REGISTRY:
        return page_type

    # Not recognized
    return None


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


def detect_content_type(section: Section, config: dict[str, Any] | None = None) -> str:
    """
    Auto-detect content type from section characteristics.

    Uses heuristics from each strategy to determine the best type.

    Priority order:
    1. Explicit type in section metadata
    2. Cascaded type from parent section
    3. Auto-detection via strategy heuristics
    4. Config-based default (content.default_type or site.default_content_type)
    5. Default to "list"

    Args:
        section: Section to analyze
        config: Optional site config for default_content_type lookup

    Returns:
        Content type name

    Example:
        >>> content_type = detect_content_type(blog_section)
        >>> assert content_type == "blog"

    Example with config default:
        >>> config = {"content": {"default_type": "doc"}}
        >>> content_type = detect_content_type(section, config)
        >>> # Returns "doc" if no other detection succeeds

    Example with legacy config (backward compatible):
        >>> config = {"site": {"default_content_type": "doc"}}
        >>> content_type = detect_content_type(section, config)
        >>> # Also works for backward compatibility
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

    # 4. Config-based default (NEW!)
    if config:
        # Try new location first: content.default_type
        content_config = config.get("content", {})
        default_type = content_config.get("default_type")

        # Fall back to legacy location: site.default_content_type (backward compat)
        if not default_type:
            site_config = config.get("site", {})
            default_type = site_config.get("default_content_type")

        if default_type and default_type in CONTENT_TYPE_REGISTRY:
            return default_type

    # 5. Final fallback
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
