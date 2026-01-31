"""
Table of contents helper functions.

Provides get_toc_grouped(), build_toc_tree(), and combine_track_toc_items() for TOC generation.
"""

from __future__ import annotations

from typing import Any


def build_toc_tree(toc_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert flat TOC items into a nested tree structure with children arrays.

    This function builds a proper tree where each node contains its children
    directly, enabling recursive template rendering with count badges.

    Args:
        toc_items: Flat list of TOC items with id, title, and level

    Returns:
        Nested list where each item has a 'children' array containing
        its sub-items. Items at level 1 (H2) become root nodes, and
        deeper levels become nested children.

    Example:
        Input (flat):
            [
                {"id": "intro", "title": "Introduction", "level": 1},
                {"id": "setup", "title": "Setup", "level": 2},
                {"id": "config", "title": "Configuration", "level": 2},
                {"id": "api", "title": "API", "level": 1},
                {"id": "endpoints", "title": "Endpoints", "level": 2},
            ]

        Output (nested):
            [
                {
                    "id": "intro", "title": "Introduction", "level": 1,
                    "children": [
                        {"id": "setup", "title": "Setup", "level": 2, "children": []},
                        {"id": "config", "title": "Configuration", "level": 2, "children": []},
                    ]
                },
                {
                    "id": "api", "title": "API", "level": 1,
                    "children": [
                        {"id": "endpoints", "title": "Endpoints", "level": 2, "children": []},
                    ]
                },
            ]

    Template usage:
        {% for item in build_toc_tree(toc_items) %}
          {{ toc_node(item) }}
        {% endfor %}

    """
    if not toc_items:
        return []

    # Stack-based tree building for arbitrary depth
    # Each stack entry: (level, node_with_children)
    root: list[dict[str, Any]] = []
    stack: list[tuple[int, dict[str, Any]]] = []

    for item in toc_items:
        level = item.get("level", 1)
        # Create node with children array
        node = {
            "id": item.get("id", ""),
            "title": item.get("title", ""),
            "level": level,
            "children": [],
        }

        # Pop stack until we find parent level
        while stack and stack[-1][0] >= level:
            stack.pop()

        if stack:
            # Add as child to parent
            stack[-1][1]["children"].append(node)
        else:
            # Root level item
            root.append(node)

        # Push current node for potential children
        stack.append((level, node))

    return root


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

    groups: list[dict[str, Any]] = []
    current_group: dict[str, Any] | None = None

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


def combine_track_toc_items(track_items: list[str], get_page_func: Any) -> list[dict[str, Any]]:
    """
    Combine TOC items from all track section pages into a single TOC.

    Each track section becomes a level-1 TOC item, and its headings become
    nested items with incremented levels.

    Args:
        track_items: List of page paths/slugs for track items
        get_page_func: Function to get page by path (from template context)

    Returns:
        Combined list of TOC items with section headers and nested headings

    Performance:
        Uses local cache to avoid redundant get_page() calls within a single
        TOC generation. With per-render caching in get_page(), this provides
        defense-in-depth optimization.

    """
    combined: list[dict[str, Any]] = []
    # Local cache for pages within this function call.
    # Provides defense-in-depth: even if per-render cache is bypassed,
    # this ensures we don't fetch the same page multiple times.
    page_cache: dict[str, Any] = {}

    for index, item_slug in enumerate(track_items, start=1):
        # Check local cache first
        if item_slug not in page_cache:
            page_cache[item_slug] = get_page_func(item_slug)
        page = page_cache[item_slug]

        if not page:
            continue

        # Add section header as level 1 item
        section_id = f"track-section-{index}"
        section_prefix = f"s{index}-"  # Must match template's prefix_heading_ids
        combined.append({"id": section_id, "title": page.title, "level": 1})

        # Add all TOC items from this section, with prefixed IDs and incremented levels
        if hasattr(page, "toc_items") and page.toc_items:
            for toc_item in page.toc_items:
                original_id = toc_item.get("id", "")
                combined.append(
                    {
                        "id": f"{section_prefix}{original_id}" if original_id else "",
                        "title": toc_item.get("title", ""),
                        "level": toc_item.get("level", 2) + 1,  # Increment level
                    }
                )

    return combined
