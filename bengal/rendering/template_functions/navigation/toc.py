"""
Table of contents helper functions.

Provides get_toc_grouped() and combine_track_toc_items() for TOC generation.
"""

from __future__ import annotations

from typing import Any


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
    """
    combined: list[dict[str, Any]] = []

    for index, item_slug in enumerate(track_items, start=1):
        page = get_page_func(item_slug)
        if not page:
            continue

        # Add section header as level 1 item
        section_id = f"track-section-{index}"
        combined.append({"id": section_id, "title": page.title, "level": 1})

        # Add all TOC items from this section, incrementing level by 1
        if hasattr(page, "toc_items") and page.toc_items:
            for toc_item in page.toc_items:
                combined.append(
                    {
                        "id": toc_item.get("id", ""),
                        "title": toc_item.get("title", ""),
                        "level": toc_item.get("level", 2) + 1,  # Increment level
                    }
                )

    return combined
