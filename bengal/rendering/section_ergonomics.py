"""Rendering-side helpers for Section template ergonomics.

``Section`` lives in ``bengal.core`` and remains the stable template-facing
surface. Helpers that derive theme-facing content views, rendered-word totals,
or section template output belong here so core stays a passive domain model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class SectionErgonomicsTarget(Protocol):
    """Structural Section surface needed by template ergonomic helpers."""

    sorted_pages: list[Any]
    regular_pages_recursive: list[Any]
    subsections: list[Any]
    metadata: dict[str, Any]
    title: str
    hierarchy: list[str]
    index_page: Any | None
    sorted_subsections: list[Any]

    def get_all_pages(self, recursive: bool = True) -> list[Any]:
        """Return pages in this section."""
        ...


def content_pages(section: SectionErgonomicsTarget) -> list[Any]:
    """Get content pages for template listings."""
    return section.sorted_pages


def icon(section: SectionErgonomicsTarget) -> str | None:
    """Get section icon from index page metadata, falling back to section metadata."""
    if (
        section.index_page
        and hasattr(section.index_page, "metadata")
        and (icon_value := section.index_page.metadata.get("icon"))
    ):
        return str(icon_value) if icon_value else None
    result = section.metadata.get("icon")
    return str(result) if result else None


def has_nav_children(section: SectionErgonomicsTarget) -> bool:
    """Return True when the section has pages or subsections for navigation."""
    return bool(section.sorted_pages or section.sorted_subsections)


def recent_pages(section: SectionErgonomicsTarget, limit: int = 10) -> list[Any]:
    """Get most recent dated pages, newest first."""
    dated_pages = [p for p in section.sorted_pages if getattr(p, "date", None)]
    dated_pages.sort(key=lambda p: p.date or datetime.min, reverse=True)
    return dated_pages[:limit]


def pages_with_tag(section: SectionErgonomicsTarget, tag: str) -> list[Any]:
    """Get pages containing a specific tag, case-insensitively."""
    tag_lower = tag.lower()
    return [
        p for p in section.sorted_pages if tag_lower in {t.lower() for t in getattr(p, "tags", [])}
    ]


def featured_posts(section: SectionErgonomicsTarget, limit: int = 5) -> list[Any]:
    """Get featured pages from this section, newest first when dates exist."""
    featured = [p for p in section.sorted_pages if p.metadata.get("featured")]
    featured.sort(key=lambda p: getattr(p, "date", None) or "", reverse=True)
    return featured[:limit]


def post_count(section: SectionErgonomicsTarget) -> int:
    """Get total number of content pages in this section."""
    return len(section.sorted_pages)


def post_count_recursive(section: SectionErgonomicsTarget) -> int:
    """Get total number of content pages in this section and all subsections."""
    return len(section.regular_pages_recursive)


def word_count(section: SectionErgonomicsTarget) -> int:
    """Get total word count across all rendered page content in this section."""
    from bengal.core.utils.text import strip_html

    total = 0
    for page in section.sorted_pages:
        content = getattr(page, "content", "")
        if content:
            clean = strip_html(content)
            total += len(clean.split())
    return total


def total_reading_time(section: SectionErgonomicsTarget) -> int:
    """Get total reading time for all pages in this section."""
    return sum(getattr(p, "reading_time", 0) for p in section.sorted_pages)


def aggregate_content(section: SectionErgonomicsTarget) -> dict[str, Any]:
    """Aggregate content stats for templates."""
    pages = section.get_all_pages(recursive=False)

    all_tags = set()
    for page in pages:
        all_tags.update(page.tags)

    return {
        "page_count": len(pages),
        "total_page_count": len(section.get_all_pages(recursive=True)),
        "subsection_count": len(section.subsections),
        "tags": sorted(all_tags),
        "title": section.title,
        "hierarchy": section.hierarchy,
    }


def apply_section_template(section: SectionErgonomicsTarget, template_engine: Any) -> str:
    """Apply a section template to generate a section index page."""
    _ = template_engine

    if section.index_page:
        return section.index_page.rendered_html
    return ""
