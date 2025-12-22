"""
Content type strategy registry.

This module provides the central registry for content type strategies, mapping
type names (like ``"blog"``, ``"doc"``) to their strategy instances. It also
provides detection functions to auto-detect content types from section structure.

Registry:
    CONTENT_TYPE_REGISTRY: Global dict mapping type names to strategy instances.
    Pre-populated with built-in strategies for common content types.

Public Functions:
    - get_strategy: Retrieve a strategy by type name (with fallback)
    - register_strategy: Register custom strategies
    - detect_content_type: Auto-detect content type from section heuristics
    - normalize_page_type_to_content_type: Map page types to content types

Built-in Content Types:
    - blog: Chronological posts (newest first)
    - archive: Similar to blog with simpler template
    - changelog: Release notes (date-sorted)
    - doc: Documentation (weight-sorted)
    - autodoc-python: API reference for Python
    - autodoc-cli: CLI command reference
    - tutorial: Step-by-step guides (weight-sorted)
    - track: Learning tracks (weight-sorted)
    - page: Generic pages (default fallback)
    - list: Alias for generic page listings

Example:
    >>> from bengal.content_types.registry import get_strategy, detect_content_type
    >>> strategy = get_strategy("blog")
    >>> sorted_posts = strategy.sort_pages(posts)

    >>> # Auto-detect content type
    >>> content_type = detect_content_type(section, site.config)

Related:
    - bengal/content_types/base.py: ContentTypeStrategy base class
    - bengal/content_types/strategies.py: Concrete strategy implementations
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
    TrackStrategy,
    TutorialStrategy,
)

if TYPE_CHECKING:
    from bengal.core.section import Section


#: Global registry mapping content type names to strategy instances.
#:
#: This registry is pre-populated with built-in strategies for common content
#: types. Custom strategies can be added via ``register_strategy()``.
#:
#: Keys are lowercase content type names (e.g., ``"blog"``, ``"doc"``).
#: Values are singleton strategy instances.
CONTENT_TYPE_REGISTRY: dict[str, ContentTypeStrategy] = {
    "blog": BlogStrategy(),
    "archive": ArchiveStrategy(),
    "changelog": ChangelogStrategy(),
    "doc": DocsStrategy(),
    "autodoc-python": ApiReferenceStrategy(),
    "autodoc-cli": CliReferenceStrategy(),
    "tutorial": TutorialStrategy(),
    "track": TrackStrategy(),
    "page": PageStrategy(),
    "list": PageStrategy(),  # Alias for generic lists
}


def normalize_page_type_to_content_type(page_type: str) -> str | None:
    """
    Normalize a page type to a content type.

    Handles special cases where page types (from frontmatter) map to content types:
    - python-module -> autodoc-python
    - cli-command -> autodoc-cli
    - Other types pass through if registered

    Args:
        page_type: Page type from frontmatter (e.g., "python-module", "blog")

    Returns:
        Content type name if recognized, None otherwise

    Example:
        >>> normalize_page_type_to_content_type("python-module")
        'autodoc-python'
        >>> normalize_page_type_to_content_type("blog")
        'blog'
        >>> normalize_page_type_to_content_type("unknown")
        None
    """
    # Special mappings for autodoc-generated types
    special_mappings = {
        "python-module": "autodoc-python",
        "cli-command": "autodoc-cli",
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

    Retrieves a strategy instance from the registry by name. If the content
    type is not found, returns a ``PageStrategy`` instance as the default
    fallback, ensuring graceful degradation for unknown types.

    Args:
        content_type: Type name to look up (e.g., ``"blog"``, ``"doc"``).
            Case-sensitive; use lowercase.

    Returns:
        ContentTypeStrategy instance for the requested type, or a
        ``PageStrategy`` if the type is not registered.

    Example:
        >>> strategy = get_strategy("blog")
        >>> sorted_posts = strategy.sort_pages(posts)
        >>> template = strategy.get_template(page, template_engine)

        >>> # Unknown types fall back to PageStrategy
        >>> strategy = get_strategy("unknown-type")
        >>> isinstance(strategy, PageStrategy)
        True
    """
    return CONTENT_TYPE_REGISTRY.get(content_type, PageStrategy())


def detect_content_type(section: Section, config: dict[str, Any] | None = None) -> str:
    """
    Auto-detect content type from section characteristics.

    Uses a priority-based detection algorithm that checks multiple sources
    in order, returning the first match. This allows explicit configuration
    to override auto-detection while still providing intelligent defaults.

    Detection Priority:
        1. **Explicit metadata**: ``content_type`` in section's ``_index.md``
        2. **Parent cascade**: ``cascade.type`` from parent section metadata
        3. **Auto-detection**: Strategy heuristics (name patterns, page metadata)
        4. **Config default**: ``content.default_type`` or legacy ``site.default_content_type``
        5. **Fallback**: ``"list"`` for generic page listings

    Auto-detection Order:
        Strategies are tried in this order to prioritize specificity:
        ``autodoc-python`` → ``autodoc-cli`` → ``blog`` → ``tutorial`` → ``doc``

    Args:
        section: Section to analyze for content type.
        config: Optional site configuration dict for default type lookup.
            Checks ``config["content"]["default_type"]`` first, then
            ``config["site"]["default_content_type"]`` for backward compatibility.

    Returns:
        Content type name string (e.g., ``"blog"``, ``"doc"``, ``"list"``).

    Example:
        >>> # Auto-detect from section characteristics
        >>> content_type = detect_content_type(blog_section)
        >>> assert content_type == "blog"

        >>> # With config-based default
        >>> config = {"content": {"default_type": "doc"}}
        >>> content_type = detect_content_type(generic_section, config)
        >>> # Returns "doc" if auto-detection fails

        >>> # Legacy config still supported
        >>> config = {"site": {"default_content_type": "doc"}}
        >>> content_type = detect_content_type(section, config)

    Note:
        To force a specific content type, set ``content_type`` in the
        section's ``_index.md`` frontmatter:

        .. code-block:: yaml

            ---
            content_type: tutorial
            ---
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
        ("autodoc-python", ApiReferenceStrategy()),
        ("autodoc-cli", CliReferenceStrategy()),
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

    Adds a new content type to the global registry, making it available
    for use in section metadata and auto-detection. Can also override
    built-in strategies by registering with an existing type name.

    Args:
        content_type: Type name to register. Use lowercase, hyphenated names
            (e.g., ``"custom-docs"``, ``"project-showcase"``).
        strategy: Strategy instance to register. Should be a subclass of
            ``ContentTypeStrategy`` with appropriate method overrides.

    Example:
        >>> from bengal.content_types import ContentTypeStrategy, register_strategy
        >>>
        >>> class ProjectStrategy(ContentTypeStrategy):
        ...     default_template = "projects/list.html"
        ...     allows_pagination = True
        ...
        ...     def sort_pages(self, pages):
        ...         # Sort by status (active first), then by name
        ...         return sorted(pages, key=lambda p: (
        ...             p.metadata.get("status") != "active",
        ...             p.title.lower()
        ...         ))
        ...
        ...     def detect_from_section(self, section):
        ...         return section.name.lower() == "projects"
        >>>
        >>> register_strategy("project", ProjectStrategy())

    Note:
        Strategies should be registered early in the build process,
        typically in a plugin or site configuration hook, before
        content discovery runs.

    Warning:
        Registering with an existing type name will override the built-in
        strategy. This is intentional to allow customization but should
        be done with care.
    """
    CONTENT_TYPE_REGISTRY[content_type] = strategy
