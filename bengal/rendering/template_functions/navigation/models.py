"""
Navigation dataclasses for template functions.

Provides type-safe dataclasses for navigation elements while maintaining
backward compatibility with dict-style access used in Jinja templates.

All dataclasses implement:
- Type safety with explicit field types
- Dict-style access via __getitem__ and keys() for template compatibility
- Memory efficiency with __slots__

Example:
    >>> from bengal.rendering.template_functions.navigation.models import BreadcrumbItem
    >>>
    >>> # Create with type safety
    >>> item = BreadcrumbItem(title="Home", url="/", is_current=False)
    >>>
    >>> # Access as object (preferred in Python)
    >>> print(item.title)
    'Home'
    >>>
    >>> # Access as dict (for Jinja template compatibility)
    >>> print(item["title"])
    'Home'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BreadcrumbItem:
    """
    Single breadcrumb in navigation trail.

    Attributes:
        title: Display text for the breadcrumb
        url: URL to link to
        is_current: True if this is the current page (should not be a link)

    Example (Jinja template):
        {% for item in get_breadcrumbs(page) %}
          {% if item.is_current %}
            <span>{{ item.title }}</span>
          {% else %}
            <a href="{{ item.href }}">{{ item.title }}</a>
          {% endif %}
        {% endfor %}
    """

    title: str
    url: str
    is_current: bool = False

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for template compatibility."""
        return getattr(self, key)

    def keys(self) -> list[str]:
        """Return field names for dict-style iteration."""
        return ["title", "url", "is_current"]

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style get with default for template compatibility."""
        return getattr(self, key, default)


@dataclass(slots=True)
class PaginationItem:
    """
    Single page in pagination.

    Attributes:
        num: Page number (None for ellipsis)
        url: URL to page (None for ellipsis)
        is_current: True if this is the current page
        is_ellipsis: True if this represents an ellipsis (...)

    Example (Jinja template):
        {% for item in pagination.pages %}
          {% if item.is_ellipsis %}
            <span>...</span>
          {% elif item.is_current %}
            <strong>{{ item.num }}</strong>
          {% else %}
            <a href="{{ item.href }}">{{ item.num }}</a>
          {% endif %}
        {% endfor %}
    """

    num: int | None
    url: str | None
    is_current: bool = False
    is_ellipsis: bool = False

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for template compatibility."""
        return getattr(self, key)

    def keys(self) -> list[str]:
        """Return field names for dict-style iteration."""
        return ["num", "url", "is_current", "is_ellipsis"]

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style get with default for template compatibility."""
        return getattr(self, key, default)


@dataclass(slots=True)
class PaginationInfo:
    """
    Complete pagination data structure.

    Attributes:
        pages: List of PaginationItem objects
        prev: Previous page info (num, url) or None
        next: Next page info (num, url) or None
        first: First page info (num, url)
        last: Last page info (num, url)

    Example (Jinja template):
        {% set p = get_pagination_items(current_page, total_pages, base_url) %}
        {% if p.prev %}
          <a href="{{ p.prev.href }}">Previous</a>
        {% endif %}
    """

    pages: list[PaginationItem]
    prev: dict[str, Any] | None = None
    next: dict[str, Any] | None = None
    first: dict[str, Any] = field(default_factory=dict)
    last: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for template compatibility."""
        return getattr(self, key)

    def keys(self) -> list[str]:
        """Return field names for dict-style iteration."""
        return ["pages", "prev", "next", "first", "last"]

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style get with default for template compatibility."""
        return getattr(self, key, default)


@dataclass(slots=True)
class TocGroupItem:
    """
    Grouped TOC item for collapsible sections.

    Attributes:
        header: The group header item (dict with id, title, level)
        children: List of child TOC items
        is_group: True if has children, False for standalone items

    Example (Jinja template):
        {% for group in get_toc_grouped(page.toc_items) %}
          {% if group.is_group %}
            <details>
              <summary>
                <a href="#{{ group.header.id }}">{{ group.header.title }}</a>
              </summary>
              <ul>
                {% for child in group.children %}
                  <li><a href="#{{ child.id }}">{{ child.title }}</a></li>
                {% endfor %}
              </ul>
            </details>
          {% else %}
            <a href="#{{ group.header.id }}">{{ group.header.title }}</a>
          {% endif %}
        {% endfor %}
    """

    header: dict[str, Any]
    children: list[dict[str, Any]] = field(default_factory=list)
    is_group: bool = False

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for template compatibility."""
        return getattr(self, key)

    def keys(self) -> list[str]:
        """Return field names for dict-style iteration."""
        return ["header", "children", "is_group"]

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style get with default for template compatibility."""
        return getattr(self, key, default)


@dataclass(slots=True)
class AutoNavItem:
    """
    Auto-discovered navigation item.

    Attributes:
        name: Display name
        url: Link URL
        weight: Sort weight (lower = higher priority)
        identifier: Unique identifier (usually section name)
        parent: Parent item identifier (for hierarchy)
        icon: Optional icon identifier

    Example (Jinja template):
        {% set auto_items = get_auto_nav() %}
        {% for item in auto_items %}
          <a href="{{ item.href }}"
             {% if item.icon %}class="icon-{{ item.icon }}"{% endif %}>
            {{ item.name }}
          </a>
        {% endfor %}
    """

    name: str
    url: str
    weight: int = 0
    identifier: str = ""
    parent: str | None = None
    icon: str | None = None

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for template compatibility."""
        return getattr(self, key)

    def keys(self) -> list[str]:
        """Return field names for dict-style iteration."""
        return ["name", "url", "weight", "identifier", "parent", "icon"]

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style get with default for template compatibility."""
        return getattr(self, key, default)
