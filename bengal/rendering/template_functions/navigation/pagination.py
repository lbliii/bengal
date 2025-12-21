"""
Pagination helper functions.

Provides get_pagination_items() for generating pagination structures.
"""

from __future__ import annotations

from typing import Any


def get_pagination_items(
    current_page: int, total_pages: int, base_url: str, window: int = 2
) -> dict[str, Any]:
    """
    Generate pagination data structure with URLs and ellipsis markers.

    This function handles all pagination logic including:
    - Page number range calculation with window
    - Ellipsis placement (represented as None)
    - URL generation (special case for page 1)
    - Previous/next links

    Args:
        current_page: Current page number (1-indexed)
        total_pages: Total number of pages
        base_url: Base URL for pagination (e.g., '/blog/')
        window: Number of pages to show around current (default: 2)

    Returns:
        Dictionary with:
        - pages: List of page items (num, url, is_current, is_ellipsis)
        - prev: Previous page info (num, url) or None
        - next: Next page info (num, url) or None
        - first: First page info (num, url)
        - last: Last page info (num, url)

    Example (basic):
        {% set pagination = get_pagination_items(current_page, total_pages, base_url) %}

        <nav class="pagination">
          {% if pagination.prev %}
            <a href="{{ pagination.prev.href }}">← Prev</a>
          {% endif %}

          {% for item in pagination.pages %}
            {% if item.is_ellipsis %}
              <span>...</span>
            {% elif item.is_current %}
              <strong>{{ item.num }}</strong>
            {% else %}
              <a href="{{ item.href }}">{{ item.num }}</a>
            {% endif %}
          {% endfor %}

          {% if pagination.next %}
            <a href="{{ pagination.next.href }}">Next →</a>
          {% endif %}
        </nav>

    Example (Bootstrap):
        {% set p = get_pagination_items(current_page, total_pages, base_url) %}

        <ul class="pagination">
          {% if p.prev %}
            <li class="page-item">
              <a class="page-link" href="{{ p.prev.href }}">Previous</a>
            </li>
          {% endif %}

          {% for item in p.pages %}
            <li class="page-item {{ 'active' if item.is_current }}">
              {% if item.is_ellipsis %}
                <span class="page-link">...</span>
              {% else %}
                <a class="page-link" href="{{ item.href }}">{{ item.num }}</a>
              {% endif %}
            </li>
          {% endfor %}

          {% if p.next %}
            <li class="page-item">
              <a class="page-link" href="{{ p.next.href }}">Next</a>
            </li>
          {% endif %}
        </ul>
    """
    if total_pages <= 0:
        total_pages = 1

    current_page = max(1, min(current_page, total_pages))
    base_url = base_url.rstrip("/")

    def page_url(page_num: int) -> str:
        """Generate URL for a page number."""
        if page_num <= 1:
            return base_url + "/"
        return f"{base_url}/page/{page_num}/"

    # Build page items list
    pages: list[dict[str, Any]] = []

    if total_pages == 1:
        # Single page - just return it
        return {
            "pages": [{"num": 1, "href": page_url(1), "is_current": True, "is_ellipsis": False}],
            "prev": None,
            "next": None,
            "first": {"num": 1, "href": page_url(1)},
            "last": {"num": 1, "href": page_url(1)},
        }

    # Calculate range
    start = max(2, current_page - window)
    end = min(total_pages - 1, current_page + window)

    # First page (always shown)
    pages.append(
        {"num": 1, "href": page_url(1), "is_current": current_page == 1, "is_ellipsis": False}
    )

    # Ellipsis after first page if needed
    if start > 2:
        pages.append({"num": None, "url": None, "is_current": False, "is_ellipsis": True})

    # Middle pages
    for page_num in range(start, end + 1):
        pages.append(
            {
                "num": page_num,
                "href": page_url(page_num),
                "is_current": page_num == current_page,
                "is_ellipsis": False,
            }
        )

    # Ellipsis before last page if needed
    if end < total_pages - 1:
        pages.append({"num": None, "url": None, "is_current": False, "is_ellipsis": True})

    # Last page (always shown, unless it's page 1)
    if total_pages > 1:
        pages.append(
            {
                "num": total_pages,
                "href": page_url(total_pages),
                "is_current": current_page == total_pages,
                "is_ellipsis": False,
            }
        )

    # Previous/next links
    prev_info = None
    if current_page > 1:
        prev_info = {"num": current_page - 1, "href": page_url(current_page - 1)}

    next_info = None
    if current_page < total_pages:
        next_info = {"num": current_page + 1, "href": page_url(current_page + 1)}

    return {
        "pages": pages,
        "prev": prev_info,
        "next": next_info,
        "first": {"num": 1, "url": page_url(1)},
        "last": {"num": total_pages, "url": page_url(total_pages)},
    }
