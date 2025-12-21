"""
Shared utility functions for card directives.

Contains helper functions for column/gap normalization, link resolution,
icon rendering, HTML escaping, and child collection.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Valid option values
VALID_LAYOUTS = frozenset(["default", "horizontal", "portrait", "compact"])
VALID_GAPS = frozenset(["small", "medium", "large"])
VALID_STYLES = frozenset(["default", "minimal", "bordered"])
VALID_COLORS = frozenset(
    ["blue", "green", "red", "yellow", "orange", "purple", "gray", "pink", "indigo"]
)


def normalize_columns(columns: str) -> str:
    """Normalize columns specification."""
    columns = str(columns).strip()

    if columns in ("auto", ""):
        return "auto"

    if columns.isdigit():
        num = int(columns)
        return str(num) if 1 <= num <= 6 else "auto"

    if "-" in columns:
        parts = columns.split("-")
        if all(p.isdigit() and 1 <= int(p) <= 6 for p in parts) and len(parts) in (2, 3, 4):
            return columns

    return "auto"


def extract_octicon(title: str) -> tuple[str, str]:
    """Extract octicon from title."""
    pattern = r"\{octicon\}`([^;`]+)(?:;[^`]*)?`\s*"
    match = re.search(pattern, title)

    if match:
        icon_name = match.group(1).strip()
        clean_title = re.sub(pattern, "", title).strip()
        return icon_name, clean_title

    return "", title


def pull_from_linked_page(renderer: Any, link: str, fields: list[str]) -> dict[str, Any]:
    """Pull metadata from a linked page."""
    page = None

    # Object tree for relative paths
    if link.startswith("./"):
        current_page = getattr(renderer, "_current_page", None)
        if current_page:
            section = getattr(current_page, "_section", None)
            if section:
                child_name = link[2:].rstrip("/").split("/")[0]

                for subsection in getattr(section, "subsections", []):
                    if getattr(subsection, "name", "") == child_name:
                        page = getattr(subsection, "index_page", None)
                        if page:
                            break

                if not page:
                    for p in getattr(section, "pages", []):
                        source_str = str(getattr(p, "source_path", ""))
                        if f"/{child_name}." in source_str or f"/{child_name}/" in source_str:
                            page = p
                            break

    # Fall back to xref_index
    if not page:
        xref_index = getattr(renderer, "_xref_index", None)
        current_page_dir = getattr(renderer, "_current_page_dir", None)
        if xref_index:
            page = resolve_page(xref_index, link, current_page_dir)

    if not page:
        return {}

    return extract_page_fields(page, fields)


def extract_page_fields(page: Any, fields: list[str]) -> dict[str, Any]:
    """Extract requested fields from a page object."""
    result: dict[str, Any] = {}

    for field in fields:
        if field == "title":
            result["title"] = getattr(page, "title", "")
        elif field == "description":
            result["description"] = (
                page.metadata.get("description", "") if hasattr(page, "metadata") else ""
            )
        elif field == "icon":
            result["icon"] = page.metadata.get("icon", "") if hasattr(page, "metadata") else ""
        elif field == "image":
            result["image"] = page.metadata.get("image", "") if hasattr(page, "metadata") else ""
        elif field == "badge":
            result["badge"] = page.metadata.get("badge", "") if hasattr(page, "metadata") else ""

    return result


def resolve_page(xref_index: dict[str, Any], link: str, current_page_dir: str | None = None) -> Any:
    """Resolve a link to a page object."""
    # Relative path
    if link.startswith("./") or link.startswith("../"):
        if current_page_dir:
            clean_link = link.replace(".md", "").rstrip("/")
            if clean_link.startswith("./"):
                resolved_path = f"{current_page_dir}/{clean_link[2:]}"
            else:
                parts = current_page_dir.split("/")
                up_count = 0
                remaining = clean_link
                while remaining.startswith("../"):
                    up_count += 1
                    remaining = remaining[3:]
                if up_count < len(parts):
                    parent = "/".join(parts[:-up_count]) if up_count > 0 else current_page_dir
                    resolved_path = f"{parent}/{remaining}" if remaining else parent
                else:
                    resolved_path = remaining

            page = xref_index.get("by_path", {}).get(resolved_path)
            if page:
                return page
        return None

    # Custom ID
    if link.startswith("id:"):
        return xref_index.get("by_id", {}).get(link[3:])

    # Path lookup
    if "/" in link or link.endswith(".md"):
        clean_path = link.replace(".md", "").strip("/")
        return xref_index.get("by_path", {}).get(clean_path)

    # Slug lookup
    pages = xref_index.get("by_slug", {}).get(link, [])
    return pages[0] if pages else None


def resolve_link_url(renderer: Any, link: str) -> str:
    """Resolve a link reference to a URL."""
    if link.startswith("/") or link.startswith("http://") or link.startswith("https://"):
        return link

    xref_index = getattr(renderer, "_xref_index", None)
    if not xref_index:
        return link

    current_page_dir = getattr(renderer, "_current_page_dir", None)
    page = resolve_page(xref_index, link, current_page_dir)

    if page and hasattr(page, "href"):
        return page.href

    return link


def render_icon(icon_name: str, card_title: str = "") -> str:
    """
    Render icon using Bengal SVG icons.

    Args:
        icon_name: Name of the icon to render
        card_title: Title of the card (for warning context)

    Returns:
        SVG HTML string, or empty string if not found
    """
    from bengal.directives._icons import render_icon as _render_icon
    from bengal.directives._icons import warn_missing_icon

    icon_html = _render_icon(icon_name, size=20)

    if not icon_html and icon_name:
        warn_missing_icon(icon_name, directive="card", context=card_title)

    return icon_html


def collect_children(section: Any, current_page: Any, include: str) -> list[dict[str, Any]]:
    """Collect child sections/pages from section."""
    children: list[dict[str, Any]] = []

    if include in ("sections", "all"):
        for subsection in getattr(section, "subsections", []):
            # Skip hidden sections
            if hasattr(subsection, "metadata") and subsection.metadata.get("hidden", False):
                continue
            has_weight = hasattr(subsection, "metadata") and "weight" in subsection.metadata
            children.append(
                {
                    "type": "section",
                    "title": getattr(subsection, "title", subsection.name),
                    "description": (
                        subsection.metadata.get("description", "")
                        if hasattr(subsection, "metadata")
                        else ""
                    ),
                    "icon": (
                        subsection.metadata.get("icon", "")
                        if hasattr(subsection, "metadata")
                        else ""
                    ),
                    "url": get_section_url(subsection),
                    "weight": (
                        subsection.metadata.get("weight", 0)
                        if hasattr(subsection, "metadata")
                        else 0
                    ),
                    "_has_explicit_weight": has_weight,
                }
            )

    if include in ("pages", "all"):
        for page in getattr(section, "pages", []):
            source_str = str(getattr(page, "source_path", ""))
            if source_str.endswith("_index.md") or source_str.endswith("index.md"):
                continue
            if (
                hasattr(current_page, "source_path")
                and hasattr(page, "source_path")
                and page.source_path == current_page.source_path
            ):
                continue
            # Skip hidden pages
            if hasattr(page, "metadata") and page.metadata.get("hidden", False):
                continue
            has_weight = hasattr(page, "metadata") and "weight" in page.metadata
            children.append(
                {
                    "type": "page",
                    "title": getattr(page, "title", ""),
                    "description": (
                        page.metadata.get("description", "") if hasattr(page, "metadata") else ""
                    ),
                    "icon": page.metadata.get("icon", "") if hasattr(page, "metadata") else "",
                    "url": getattr(page, "href", ""),
                    "weight": page.metadata.get("weight", 0) if hasattr(page, "metadata") else 0,
                    "_has_explicit_weight": has_weight,
                }
            )

    # Warn if some children have weights and others don't (likely unintentional)
    warn_mixed_weights(children, current_page)

    # Sort by weight, then title
    children.sort(key=lambda c: (c.get("weight", 0), c.get("title", "").lower()))

    # Clean up internal tracking field
    for child in children:
        child.pop("_has_explicit_weight", None)

    return children


def warn_mixed_weights(children: list[dict[str, Any]], current_page: Any) -> None:
    """Warn if some children have explicit weights and others don't."""
    if len(children) < 2:
        return

    with_weight = [c for c in children if c.get("_has_explicit_weight")]
    without_weight = [c for c in children if not c.get("_has_explicit_weight")]

    # Only warn if there's a mix (some have weights, some don't)
    if with_weight and without_weight:
        page_path = getattr(current_page, "source_path", "unknown") if current_page else "unknown"
        missing_titles = ", ".join(c.get("title", "Untitled") for c in without_weight[:3])
        if len(without_weight) > 3:
            missing_titles += f" (+{len(without_weight) - 3} more)"

        logger.warning(
            "child_cards_mixed_weights",
            page=str(page_path),
            weighted=len(with_weight),
            unweighted=len(without_weight),
            unweighted_items=missing_titles,
            hint="Unweighted items default to weight=0 and sort first. "
            "Add 'weight:' to frontmatter for consistent ordering.",
        )


def get_section_url(section: Any) -> str:
    """Get URL for a section."""
    if hasattr(section, "index_page") and section.index_page:
        return getattr(section.index_page, "href", "/")
    path = getattr(section, "path", None)
    if path:
        return f"/{path}/"
    return "/"


def render_child_card(
    child: dict[str, Any],
    fields: list[str],
    layout: str,
    escape_html: Callable[[str], str],
) -> str:
    """Render a single card for a child section/page."""
    title = child.get("title", "") if "title" in fields else ""
    description = child.get("description", "") if "description" in fields else ""
    icon = child.get("icon", "") if "icon" in fields else ""
    url = child.get("url", "")
    child_type = child.get("type", "page")

    # Fallback icon
    if not icon and "icon" in fields:
        icon = "folder" if child_type == "section" else "file"

    classes = ["card"]
    if layout:
        classes.append(f"card-layout-{layout}")
    class_str = " ".join(classes)

    parts = [f'<a class="{class_str}" href="{escape_html(url)}">']

    if icon or title:
        parts.append('  <div class="card-header">')
        if icon:
            rendered_icon = render_icon(icon, card_title=title)
            if rendered_icon:
                parts.append(f'    <span class="card-icon" data-icon="{escape_html(icon)}">')
                parts.append(f"      {rendered_icon}")
                parts.append("    </span>")
        if title:
            parts.append(f'    <div class="card-title">{escape_html(title)}</div>')
        parts.append("  </div>")

    if description:
        parts.append('  <div class="card-content">')
        parts.append(f"    <p>{escape_html(description)}</p>")
        parts.append("  </div>")

    parts.append("</a>")

    return "\n".join(parts) + "\n"


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
