"""
Scheduling and scoring functions for snapshot engine.

Handles wave computation, template grouping, attention scoring,
scout hints, menu/taxonomy snapshotting, and helper utilities used
during snapshot creation.

"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.menu import MenuItem
    from bengal.core.site import Site
    from bengal.protocols import PageLike, SiteLike

from bengal.snapshots.types import (
    MenuItemSnapshot,
    PageSnapshot,
    ScoutHint,
    SectionSnapshot,
)


def _compute_topological_waves(
    root: SectionSnapshot,
    all_pages: tuple[PageSnapshot, ...],
) -> tuple[tuple[PageSnapshot, ...], ...]:
    """
    Compute rendering waves following section topology.

    Each wave contains pages from the same section that share a template.
    Processing waves in order maximizes cache locality.

    Pages not assigned to any section are added as a final wave to ensure
    all pages get rendered.

    Args:
        root: Root section snapshot for tree traversal
        all_pages: All page snapshots (to detect orphan pages)

    Returns:
        Tuple of waves, where each wave is a tuple of PageSnapshots
    """
    waves: list[tuple[PageSnapshot, ...]] = []
    pages_in_sections: set[Path] = set()
    queue = [root]

    while queue:
        section = queue.pop(0)

        # All sorted_pages in section become one wave
        if section.sorted_pages:
            waves.append(section.sorted_pages)
            # Track which pages are in sections
            for page in section.sorted_pages:
                pages_in_sections.add(page.source_path)

        # Queue subsections (BFS order)
        queue.extend(section.sorted_subsections)

    # Find orphan pages (pages not in any section)
    orphan_pages = tuple(p for p in all_pages if p.source_path not in pages_in_sections)

    # Add orphan pages as final wave (ensures all pages get rendered)
    if orphan_pages:
        waves.append(orphan_pages)

    return tuple(waves)


def _compute_template_groups(
    pages: tuple[PageSnapshot, ...],
) -> MappingProxyType[str, tuple[PageSnapshot, ...]]:
    """Group pages by template for cache optimization."""
    groups: dict[str, list[PageSnapshot]] = {}

    for page in pages:
        template = page.template_name
        if template not in groups:
            groups[template] = []
        groups[template].append(page)

    return MappingProxyType({k: tuple(v) for k, v in groups.items()})


def _compute_attention_order(
    pages: tuple[PageSnapshot, ...],
) -> tuple[PageSnapshot, ...]:
    """
    Sort pages by attention score (importance).

    High attention pages rendered first for faster time-to-preview.
    """
    return tuple(sorted(pages, key=lambda p: -p.attention_score))


def _compute_scout_hints(
    waves: tuple[tuple[PageSnapshot, ...], ...],
    template_groups: MappingProxyType[str, tuple[PageSnapshot, ...]],
    site: Site,
) -> tuple[ScoutHint, ...]:
    """Pre-compute cache warming hints for scout thread."""
    from bengal.snapshots.templates import _get_template_partials

    hints: list[ScoutHint] = []
    seen_templates: set[str] = set()

    for wave in waves:
        if not wave:
            continue

        template = wave[0].template_name
        if template not in seen_templates:
            seen_templates.add(template)

            # Get partials for this template via template engine analysis
            partials = _get_template_partials(template, site)

            hints.append(
                ScoutHint(
                    template_path=Path(template),
                    partial_paths=tuple(partials),
                    pages_using=len(template_groups.get(template, ())),
                    priority=len(template_groups.get(template, ())),
                )
            )

    # Sort by priority (warm most-used templates first)
    return tuple(sorted(hints, key=lambda h: -h.priority))


def _snapshot_menus(
    site: SiteLike,
    page_cache: dict[int, PageSnapshot],
    section_cache: dict[int, SectionSnapshot],
) -> MappingProxyType[str, tuple[MenuItemSnapshot, ...]]:
    """Snapshot menus from site."""
    menus: dict[str, tuple[MenuItemSnapshot, ...]] = {}

    for menu_name, menu_items in site.menu.items():
        menus[menu_name] = tuple(
            _snapshot_menu_item(item, page_cache, section_cache) for item in menu_items
        )

    return MappingProxyType(menus)


def _snapshot_menu_item(
    item: MenuItem,
    page_cache: dict[int, PageSnapshot],
    section_cache: dict[int, SectionSnapshot],
) -> MenuItemSnapshot:
    """Snapshot a single menu item."""
    # Type narrowing: page, section, title, is_active may be optional attributes
    page_snapshot = None
    item_page = getattr(item, "page", None)
    if item_page and id(item_page) in page_cache:
        page_snapshot = page_cache[id(item_page)]

    section_snapshot = None
    item_section = getattr(item, "section", None)
    if item_section and id(item_section) in section_cache:
        section_snapshot = section_cache[id(item_section)]

    children = tuple(
        _snapshot_menu_item(child, page_cache, section_cache) for child in item.children
    )

    # Type narrowing: title and is_active may not be on MenuItem
    item_title = getattr(item, "title", item.name)  # Fallback to name if title not available
    item_is_active = getattr(item, "is_active", False)  # Default to False if not available

    return MenuItemSnapshot(
        name=item.name,
        title=item_title,
        href=item.href,
        weight=item.weight,
        children=children,
        page=page_snapshot,
        section=section_snapshot,
        is_active=item_is_active,
    )


def _snapshot_taxonomies(
    site: SiteLike,
    page_cache: dict[int, PageSnapshot],
) -> MappingProxyType[str, MappingProxyType[str, tuple[PageSnapshot, ...]]]:
    """Snapshot taxonomies from site."""
    taxonomies: dict[str, dict[str, tuple[PageSnapshot, ...]]] = {}

    for taxonomy_name, taxonomy_dict in site.taxonomies.items():
        taxonomy_snapshot: dict[str, tuple[PageSnapshot, ...]] = {}
        for term, pages_list in taxonomy_dict.items():
            taxonomy_snapshot[term] = tuple(
                page_cache[id(p)] for p in pages_list if id(p) in page_cache
            )
        taxonomies[taxonomy_name] = taxonomy_snapshot

    return MappingProxyType({k: MappingProxyType(v) for k, v in taxonomies.items()})


# Helper functions


def _compute_attention_score(page: PageLike) -> float:
    """Compute attention score for priority scheduling."""
    score = 0.0

    # Boost for index pages
    if page.source_path.stem in ("index", "_index"):
        score += 10.0

    # Boost for recent pages
    date = page.metadata.get("date")
    if date:
        try:
            from datetime import UTC, datetime

            if isinstance(date, datetime):
                days_ago = (datetime.now(UTC) - date).days
                score += max(0, 10.0 - days_ago / 10.0)
        except Exception:
            pass

    # Boost for featured pages
    if page.metadata.get("featured"):
        score += 5.0

    return score


def _estimate_render_time(page: PageLike) -> float:
    """Estimate render time in milliseconds."""
    # Simple heuristic: base time + word count factor
    base_ms = 10.0
    word_count = getattr(page, "word_count", 0) or 0
    return base_ms + (word_count / 100.0)


def _most_common_template(pages: tuple[PageSnapshot, ...]) -> str:
    """Find most common template in pages."""
    if not pages:
        return ""

    template_counts: dict[str, int] = {}
    for page in pages:
        template = page.template_name
        template_counts[template] = template_counts.get(template, 0) + 1

    return max(template_counts.items(), key=lambda x: x[1])[0] if template_counts else ""


def _find_index_page(pages: tuple[PageSnapshot, ...]) -> PageSnapshot | None:
    """Find index page in pages."""
    for page in pages:
        if page.source_path.stem in ("index", "_index"):
            return page
    return None
