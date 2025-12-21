"""
Breadcrumb navigation generation.

Provides get_breadcrumbs() for generating breadcrumb trails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page


def get_breadcrumbs(page: Page) -> list[dict[str, Any]]:
    """
    Get breadcrumb items for a page.

    Returns a list of breadcrumb items that can be styled and rendered
    however you want in your template. Each item is a dictionary with:
    - title: Display text for the breadcrumb
    - url: URL to link to
    - is_current: True if this is the current page (should not be a link)

    This function handles the logic of:
    - Building the ancestor chain
    - Detecting section index pages (to avoid duplication)
    - Determining which item is current

    Args:
        page: Page to generate breadcrumbs for

    Returns:
        List of breadcrumb items (dicts with title, url, is_current)

    Example (basic):
        {% for item in get_breadcrumbs(page) %}
          {% if item.is_current %}
            <span>{{ item.title }}</span>
          {% else %}
            <a href="{{ item.href }}">{{ item.title }}</a>
          {% endif %}
        {% endfor %}

    Example (with custom styling):
        <nav aria-label="Breadcrumb">
          <ol class="breadcrumb">
            {% for item in get_breadcrumbs(page) %}
              <li class="breadcrumb-item {{ 'active' if item.is_current else '' }}">
                {% if item.is_current %}
                  {{ item.title }}
                {% else %}
                  <a href="{{ item.href }}">{{ item.title }}</a>
                {% endif %}
              </li>
            {% endfor %}
          </ol>
        </nav>

    Example (JSON-LD structured data):
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "BreadcrumbList",
          "itemListElement": [
            {% for item in get_breadcrumbs(page) %}
            {
              "@type": "ListItem",
              "position": {{ loop.index }},
              "name": "{{ item.title }}",
              "item": "{{ item.href | absolute_url }}"
            }{{ "," if not loop.last else "" }}
            {% endfor %}
          ]
        }
        </script>
    """
    items: list[dict[str, Any]] = []

    # Handle tag index page (dynamically generated, no ancestors)
    if hasattr(page, "metadata") and page.metadata.get("type") == "tag-index":
        items.append({"title": "Home", "href": "/", "is_current": False})
        items.append({"title": "Tags", "href": "/tags/", "is_current": True})
        return items

    # Handle tag pages (dynamically generated, no ancestors)
    if hasattr(page, "metadata") and page.metadata.get("type") == "tag":
        tag_name = page.metadata.get("_tag", "Tag")
        items.append({"title": "Home", "href": "/", "is_current": False})
        items.append({"title": "Tags", "href": "/tags/", "is_current": False})
        page_url = getattr(page, "_path", None) or f"/tags/{page.metadata.get('_tag_slug', '')}/"
        items.append({"title": tag_name, "href": page_url, "is_current": True})
        return items

    # Handle pages without ancestors (fallback)
    if not hasattr(page, "ancestors") or not page.ancestors:
        # If page doesn't have enough info to generate breadcrumbs, return empty
        has_title = hasattr(page, "title") and isinstance(getattr(page, "title", None), str)
        has_url = hasattr(page, "_path") and isinstance(getattr(page, "_path", None), str)
        if not (has_title and has_url):
            return []
        # If page has a title and URL, add Home and the page
        items.append({"title": "Home", "href": "/", "is_current": False})
        page_url = getattr(page, "_path", None) or f"/{getattr(page, 'slug', '')}/"
        page_title = _derive_title(page, page_url)
        items.append({"title": page_title, "href": page_url, "is_current": True})
        return items

    # Get ancestors in reverse order (root to current)
    reversed_ancestors = list(reversed(page.ancestors))

    # Limit to last 2 ancestors (skip Home and deep nesting)
    # This prevents breadcrumbs from wrapping to 2 lines
    MAX_ANCESTORS = 2
    if len(reversed_ancestors) > MAX_ANCESTORS:
        reversed_ancestors = reversed_ancestors[-MAX_ANCESTORS:]

    # Check if current page is the index page of the last ancestor
    # (This prevents duplication like "Docs / Markdown / Markdown")
    last_ancestor = reversed_ancestors[-1] if reversed_ancestors else None
    is_section_index = False

    if last_ancestor and hasattr(page, "_path"):
        # Use _path for comparison (without baseurl)
        ancestor_url = (
            getattr(last_ancestor, "_path", None) or f"/{getattr(last_ancestor, 'slug', '')}/"
        )
        page_path = getattr(page, "_path", None) or f"/{getattr(page, 'slug', '')}/"
        is_section_index = ancestor_url == page_path

    # Add all ancestors
    for i, ancestor in enumerate(reversed_ancestors):
        is_last = i == len(reversed_ancestors) - 1
        is_current_item = is_last and is_section_index

        # Get ancestor URL (relative, without baseurl - templates apply | absolute_url)
        url = getattr(ancestor, "_path", None) or f"/{getattr(ancestor, 'slug', '')}/"

        # Get title, handling empty strings
        ancestor_title = _derive_title(ancestor, url)

        items.append(
            {
                "title": ancestor_title,
                "href": url,
                "is_current": is_current_item,
            }
        )

    # Only add the current page if it's not a section index
    if not is_section_index:
        page_url = getattr(page, "_path", None) or f"/{page.slug}/"
        page_title = _derive_title(page, page_url)
        items.append({"title": page_title, "href": page_url, "is_current": True})

    return items


def _derive_title(obj: Any, url: str) -> str:
    """
    Derive a title from an object, falling back to slug or URL if empty.

    Args:
        obj: Object with potential title/slug attributes
        url: URL to extract title from as last resort

    Returns:
        Title string
    """
    title = getattr(obj, "title", None)
    if title and str(title).strip():
        return str(title)

    # Try to derive title from slug
    slug = getattr(obj, "slug", None)
    if slug:
        return str(slug).replace("-", " ").replace("_", " ").title()

    # Extract from URL path as last resort
    url_parts = [p for p in url.strip("/").split("/") if p]
    if url_parts:
        return url_parts[-1].replace("-", " ").replace("_", " ").title()

    return "Untitled"
