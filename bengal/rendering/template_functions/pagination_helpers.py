"""
Pagination helper functions for templates.

Provides 3 functions for building pagination controls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register pagination helper functions with Jinja2 environment."""
    env.filters.update(
        {
            "paginate": paginate_items,
        }
    )

    env.globals.update(
        {
            "page_url": page_url,
            "page_range": page_range,
        }
    )


def paginate_items(items: list[Any], per_page: int = 10, current_page: int = 1) -> dict[str, Any]:
    """
    Paginate a list of items.

    Args:
        items: List to paginate
        per_page: Items per page (default: 10)
        current_page: Current page number (1-indexed)

    Returns:
        Dictionary with pagination data

    Example:
        {% set pagination = posts | paginate(10, current_page) %}
        {% for post in pagination.items %}
          ...
        {% endfor %}
    """
    if not items or per_page <= 0:
        return {
            "items": [],
            "total_pages": 0,
            "current_page": 1,
            "has_prev": False,
            "has_next": False,
            "prev_page": None,
            "next_page": None,
        }

    total_pages = (len(items) + per_page - 1) // per_page
    current_page = max(1, min(current_page, total_pages))

    start_idx = (current_page - 1) * per_page
    end_idx = start_idx + per_page

    return {
        "items": items[start_idx:end_idx],
        "total_pages": total_pages,
        "current_page": current_page,
        "has_prev": current_page > 1,
        "has_next": current_page < total_pages,
        "prev_page": current_page - 1 if current_page > 1 else None,
        "next_page": current_page + 1 if current_page < total_pages else None,
        "total_items": len(items),
    }


def page_url(base_path: str, page_num: int) -> str:
    """
    Generate URL for a pagination page.

    Args:
        base_path: Base path (e.g., "/posts/")
        page_num: Page number

    Returns:
        URL for that page

    Example:
        <a href="{{ page_url('/posts/', 2) }}">Page 2</a>
        # <a href="/posts/page/2/">Page 2</a>
    """
    base_path = base_path.rstrip("/")

    if page_num <= 1:
        return base_path + "/"

    return f"{base_path}/page/{page_num}/"


def page_range(current_page: int, total_pages: int, window: int = 2) -> list[int | None]:
    """
    Generate page range with ellipsis for pagination controls.

    Args:
        current_page: Current page number
        total_pages: Total number of pages
        window: Number of pages to show around current (default: 2)

    Returns:
        List of page numbers with None for ellipsis

    Example:
        {% for page_num in page_range(5, 20, window=2) %}
          {% if page_num is none %}
            <span>...</span>
          {% else %}
            <a href="{{ page_url(base_path, page_num) }}">{{ page_num }}</a>
          {% endif %}
        {% endfor %}
        # Outputs: 1 ... 3 4 5 6 7 ... 20
    """
    if total_pages <= 1:
        return [1]

    # Calculate range around current page
    start = max(2, current_page - window)
    end = min(total_pages - 1, current_page + window)

    # If we can show all pages, do it
    if total_pages <= (window * 2 + 5):
        # Return list[int] which is compatible with list[int | None]
        return list(range(1, total_pages + 1))  # type: ignore[return-value]

    pages = []

    # Add first page
    pages.append(1)

    # Add ellipsis after first page if needed
    if start > 2:
        pages.append(None)  # Ellipsis

    # Add pages around current
    for page in range(start, end + 1):
        pages.append(page)

    # Add ellipsis before last page if needed
    if end < total_pages - 1:
        pages.append(None)  # Ellipsis

    # Add last page if not first
    if total_pages > 1:
        pages.append(total_pages)

    return pages
