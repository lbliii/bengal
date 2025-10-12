"""
Navigation helper functions for templates.

Provides functions for breadcrumbs, navigation trails, and hierarchical navigation.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.page import Page
    from bengal.core.site import Site


def register(env: "Environment", site: "Site") -> None:
    """Register navigation functions with Jinja2 environment."""
    env.globals.update(
        {
            "get_breadcrumbs": get_breadcrumbs,
            "get_toc_grouped": get_toc_grouped,
            "get_pagination_items": get_pagination_items,
            "get_nav_tree": get_nav_tree,
        }
    )


def get_breadcrumbs(page: "Page") -> list[dict[str, Any]]:
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
            <a href="{{ item.url }}">{{ item.title }}</a>
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
                  <a href="{{ item.url }}">{{ item.title }}</a>
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
              "item": "{{ item.url | absolute_url }}"
            }{{ "," if not loop.last else "" }}
            {% endfor %}
          ]
        }
        </script>
    """
    if not hasattr(page, "ancestors") or not page.ancestors:
        return []

    items = []

    # Add home (always first)
    items.append({"title": "Home", "url": "/", "is_current": False})

    # Get ancestors in reverse order (root to current)
    reversed_ancestors = list(reversed(page.ancestors))

    # Check if current page is the index page of the last ancestor
    # (This prevents duplication like "Docs / Markdown / Markdown")
    last_ancestor = reversed_ancestors[-1] if reversed_ancestors else None
    is_section_index = False

    if last_ancestor and hasattr(page, "url"):
        # Use url_for function from the ancestor if available
        if hasattr(last_ancestor, "url"):
            ancestor_url = last_ancestor.url
        else:
            # Fallback to slug-based URL
            ancestor_url = f"/{getattr(last_ancestor, 'slug', '')}/"

        is_section_index = ancestor_url == page.url

    # Add all ancestors
    for i, ancestor in enumerate(reversed_ancestors):
        is_last = i == len(reversed_ancestors) - 1
        is_current_item = is_last and is_section_index

        # Get ancestor URL
        url = ancestor.url if hasattr(ancestor, "url") else f"/{getattr(ancestor, 'slug', '')}/"

        items.append(
            {
                "title": getattr(ancestor, "title", "Untitled"),
                "url": url,
                "is_current": is_current_item,
            }
        )

    # Only add the current page if it's not a section index
    if not is_section_index:
        page_url = page.url if hasattr(page, "url") else f"/{page.slug}/"
        items.append(
            {"title": getattr(page, "title", "Untitled"), "url": page_url, "is_current": True}
        )

    return items


def get_toc_grouped(
    toc_items: list[dict[str, Any]], group_by_level: int = 1
) -> list[dict[str, Any]]:
    """
    Group TOC items hierarchically for collapsible sections.

    This function takes flat TOC items and groups them by a specific heading
    level, making it easy to create collapsible sections. For example, grouping
    by level 1 (H2 headings) creates expandable sections with H3+ as children.

    Args:
        toc_items: List of TOC items from page.toc_items
        group_by_level: Level to group by (1 = H2 sections, default)

    Returns:
        List of groups, each with:
        - header: The group header item (dict with id, title, level)
        - children: List of child items (empty list if standalone)
        - is_group: True if has children, False for standalone items

    Example (basic):
        {% for group in get_toc_grouped(page.toc_items) %}
          {% if group.is_group %}
            <details>
              <summary>
                <a href="#{{ group.header.id }}">{{ group.header.title }}</a>
                <span class="count">{{ group.children|length }}</span>
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

    Example (with custom styling):
        {% for group in get_toc_grouped(page.toc_items) %}
          <div class="toc-group">
            <div class="toc-header">
              <button class="toggle" aria-expanded="false">▶</button>
              <a href="#{{ group.header.id }}">{{ group.header.title }}</a>
            </div>
            {% if group.children %}
              <ul class="toc-children">
                {% for child in group.children %}
                  <li class="level-{{ child.level }}">
                    <a href="#{{ child.id }}">{{ child.title }}</a>
                  </li>
                {% endfor %}
              </ul>
            {% endif %}
          </div>
        {% endfor %}
    """
    if not toc_items:
        return []

    groups = []
    current_group = None

    for item in toc_items:
        item_level = item.get("level", 0)

        if item_level == group_by_level:
            # Start a new group
            if current_group is not None:
                # Save the previous group
                groups.append(current_group)

            # Create new group
            current_group = {
                "header": item,
                "children": [],
                "is_group": False,  # Will be set to True if children are added
            }
        elif item_level > group_by_level:
            # Add to current group as child
            if current_group is not None:
                current_group["children"].append(item)
                current_group["is_group"] = True
        else:
            # Item is a higher level (e.g., H1 when grouping by H2)
            # Treat as standalone item
            if current_group is not None:
                groups.append(current_group)
                current_group = None

            groups.append({"header": item, "children": [], "is_group": False})

    # Don't forget the last group
    if current_group is not None:
        groups.append(current_group)

    return groups


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
            <a href="{{ pagination.prev.url }}">← Prev</a>
          {% endif %}

          {% for item in pagination.pages %}
            {% if item.is_ellipsis %}
              <span>...</span>
            {% elif item.is_current %}
              <strong>{{ item.num }}</strong>
            {% else %}
              <a href="{{ item.url }}">{{ item.num }}</a>
            {% endif %}
          {% endfor %}

          {% if pagination.next %}
            <a href="{{ pagination.next.url }}">Next →</a>
          {% endif %}
        </nav>

    Example (Bootstrap):
        {% set p = get_pagination_items(current_page, total_pages, base_url) %}

        <ul class="pagination">
          {% if p.prev %}
            <li class="page-item">
              <a class="page-link" href="{{ p.prev.url }}">Previous</a>
            </li>
          {% endif %}

          {% for item in p.pages %}
            <li class="page-item {{ 'active' if item.is_current }}">
              {% if item.is_ellipsis %}
                <span class="page-link">...</span>
              {% else %}
                <a class="page-link" href="{{ item.url }}">{{ item.num }}</a>
              {% endif %}
            </li>
          {% endfor %}

          {% if p.next %}
            <li class="page-item">
              <a class="page-link" href="{{ p.next.url }}">Next</a>
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
    pages = []

    if total_pages == 1:
        # Single page - just return it
        return {
            "pages": [{"num": 1, "url": page_url(1), "is_current": True, "is_ellipsis": False}],
            "prev": None,
            "next": None,
            "first": {"num": 1, "url": page_url(1)},
            "last": {"num": 1, "url": page_url(1)},
        }

    # Calculate range
    start = max(2, current_page - window)
    end = min(total_pages - 1, current_page + window)

    # First page (always shown)
    pages.append(
        {"num": 1, "url": page_url(1), "is_current": current_page == 1, "is_ellipsis": False}
    )

    # Ellipsis after first page if needed
    if start > 2:
        pages.append({"num": None, "url": None, "is_current": False, "is_ellipsis": True})

    # Middle pages
    for page_num in range(start, end + 1):
        pages.append(
            {
                "num": page_num,
                "url": page_url(page_num),
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
                "url": page_url(total_pages),
                "is_current": current_page == total_pages,
                "is_ellipsis": False,
            }
        )

    # Previous/next links
    prev_info = None
    if current_page > 1:
        prev_info = {"num": current_page - 1, "url": page_url(current_page - 1)}

    next_info = None
    if current_page < total_pages:
        next_info = {"num": current_page + 1, "url": page_url(current_page + 1)}

    return {
        "pages": pages,
        "prev": prev_info,
        "next": next_info,
        "first": {"num": 1, "url": page_url(1)},
        "last": {"num": total_pages, "url": page_url(total_pages)},
    }


def get_nav_tree(
    page: "Page", root_section: Any | None = None, mark_active_trail: bool = True
) -> list[dict[str, Any]]:
    """
    Build navigation tree with active trail marking.

    This function builds a hierarchical navigation tree from sections and pages,
    automatically detecting which items are in the active trail (path to current
    page). Returns a flat list with depth information, making it easy to render
    with indentation or as nested structures.

    Args:
        page: Current page for active trail detection
        root_section: Section to build tree from (defaults to page's root section)
        mark_active_trail: Whether to mark active trail (default: True)

    Returns:
        List of navigation items, each with:
        - title: Display title
        - url: Link URL
        - is_current: True if this is the current page
        - is_in_active_trail: True if in path to current page
        - is_section: True if this is a section (vs regular page)
        - depth: Nesting level (0 = top level)
        - children: List of child items (for nested rendering)
        - has_children: Boolean shortcut

    Example (flat rendering with indentation):
        {% for item in get_nav_tree(page) %}
          <a href="{{ item.url }}"
             class="nav-link depth-{{ item.depth }}
                    {{ 'active' if item.is_current }}
                    {{ 'in-trail' if item.is_in_active_trail }}"
             style="padding-left: {{ item.depth * 20 }}px">
            {{ item.title }}
            {% if item.has_children %}
              <span class="has-children">▶</span>
            {% endif %}
          </a>
        {% endfor %}

    Example (nested rendering with macro):
        {% macro render_nav_item(item) %}
          <li class="{{ 'active' if item.is_current }}
                     {{ 'in-trail' if item.is_in_active_trail }}">
            <a href="{{ item.url }}">
              {% if item.is_section %}📁{% endif %}
              {{ item.title }}
            </a>
            {% if item.children %}
              <ul class="nav-children">
                {% for child in item.children %}
                  {{ render_nav_item(child) }}
                {% endfor %}
              </ul>
            {% endif %}
          </li>
        {% endmacro %}

        <ul class="nav-tree">
          {% for item in get_nav_tree(page) %}
            {{ render_nav_item(item) }}
          {% endfor %}
        </ul>
    """
    if not hasattr(page, "_section"):
        return []

    # Determine root section
    if root_section is None:
        if page._section and hasattr(page._section, "root"):
            root_section = page._section.root
        else:
            root_section = page._section

    if not root_section:
        return []

    # Build active trail (set of URLs in path to current page)
    active_trail = set()
    if mark_active_trail and hasattr(page, "ancestors"):
        for ancestor in page.ancestors:
            if hasattr(ancestor, "url"):
                active_trail.add(ancestor.url)

    # Add current page URL to active trail
    if hasattr(page, "url"):
        active_trail.add(page.url)

    def build_tree_recursive(section: Any, depth: int = 0) -> list[dict[str, Any]]:
        """Recursively build navigation tree."""
        items = []

        # Add section's index page if it exists
        if hasattr(section, "index_page") and section.index_page:
            index_page = section.index_page
            index_url = getattr(index_page, "url", "")

            items.append(
                {
                    "title": getattr(index_page, "title", "Untitled"),
                    "url": index_url,
                    "is_current": index_url == page.url if hasattr(page, "url") else False,
                    "is_in_active_trail": index_url in active_trail,
                    "is_section": False,
                    "depth": depth,
                    "children": [],
                    "has_children": False,
                }
            )

        # Add regular pages (excluding index page)
        if hasattr(section, "regular_pages"):
            for p in section.regular_pages:
                p_url = getattr(p, "url", "")

                # Skip index page (already added above)
                if (
                    hasattr(section, "index_page")
                    and section.index_page
                    and p_url == getattr(section.index_page, "url", "")
                ):
                    continue

                items.append(
                    {
                        "title": getattr(p, "title", "Untitled"),
                        "url": p_url,
                        "is_current": p_url == page.url if hasattr(page, "url") else False,
                        "is_in_active_trail": p_url in active_trail,
                        "is_section": False,
                        "depth": depth,
                        "children": [],
                        "has_children": False,
                    }
                )

        # Add subsections recursively
        if hasattr(section, "sections"):
            for subsection in section.sections:
                subsection_url = getattr(subsection, "url", "")

                # Build children first
                children = build_tree_recursive(subsection, depth + 1)

                # Add subsection as a navigation item
                subsection_item = {
                    "title": getattr(subsection, "title", "Untitled"),
                    "url": subsection_url,
                    "is_current": subsection_url == page.url if hasattr(page, "url") else False,
                    "is_in_active_trail": subsection_url in active_trail,
                    "is_section": True,
                    "depth": depth,
                    "children": children,
                    "has_children": len(children) > 0,
                }

                items.append(subsection_item)

        return items

    return build_tree_recursive(root_section)
