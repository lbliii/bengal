"""
Snapshot types for immutable site representation.

All snapshot types are frozen dataclasses with slots for memory efficiency.
They contain pre-computed values from the mutable Site/Page/Section objects,
enabling lock-free parallel rendering.

"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True, slots=True)
class PageSnapshot:
    """
    Immutable page snapshot for rendering.
    
    All properties pre-computed at snapshot time.
    Thread-safe by design (frozen = no mutation possible).
    """

    # Identity
    title: str
    href: str
    source_path: Path
    output_path: Path
    template_name: str

    # Content
    content: str  # Raw markdown source (for reference/debugging)
    parsed_html: str  # Pre-parsed HTML from parsing phase (rendering uses this)
    toc: str
    toc_items: tuple[dict[str, Any], ...]
    excerpt: str

    # Metadata (immutable view)
    metadata: MappingProxyType[str, Any]
    tags: tuple[str, ...]
    categories: tuple[str, ...]

    # Pre-computed values (no @cached_property needed)
    reading_time: int
    word_count: int
    content_hash: str  # For incremental builds

    # Navigation (pre-resolved, circular refs handled)
    section: SectionSnapshot | None = None
    next_page: PageSnapshot | None = None
    prev_page: PageSnapshot | None = None

    # Scheduling hints
    attention_score: float = 0.0
    estimated_render_ms: float = 0.0

    # Compatibility with existing templates
    @property
    def params(self) -> MappingProxyType[str, Any]:
        """Alias for metadata (template compatibility)."""
        return self.metadata


@dataclass(frozen=True, slots=True)
class SectionSnapshot:
    """
    Immutable section snapshot for rendering.
    
    Replaces: Section + SectionContext + TemplateSectionWrapper
    All three functionalities unified in one frozen type.
    """

    # Identity
    name: str
    title: str
    nav_title: str
    href: str
    path: Path | None

    # Collections (tuple = immutable, pre-sorted)
    pages: tuple[PageSnapshot, ...]
    sorted_pages: tuple[PageSnapshot, ...]
    regular_pages: tuple[PageSnapshot, ...]
    subsections: tuple[SectionSnapshot, ...]
    sorted_subsections: tuple[SectionSnapshot, ...]

    # Navigation (pre-resolved)
    parent: SectionSnapshot | None = None
    root: SectionSnapshot | None = None  # Set after construction
    index_page: PageSnapshot | None = None

    # Metadata (immutable view)
    metadata: MappingProxyType[str, Any] = MappingProxyType({})
    icon: str | None = None
    weight: float = float("inf")
    depth: int = 1
    hierarchy: tuple[str, ...] = ()
    is_virtual: bool = False

    # Scheduling hints
    template_name: str = ""  # Most common template
    total_pages: int = 0  # Including subsections

    # Template compatibility
    @property
    def params(self) -> MappingProxyType[str, Any]:
        """Alias for metadata (template compatibility)."""
        return self.metadata

    def __bool__(self) -> bool:
        """Always truthy (replaces SectionContext None-safety)."""
        return True


# Sentinel for "no section" (replaces SectionContext(None))
NO_SECTION = SectionSnapshot(
    name="",
    title="",
    nav_title="",
    href="",
    path=None,
    pages=(),
    sorted_pages=(),
    regular_pages=(),
    subsections=(),
    sorted_subsections=(),
)


@dataclass(frozen=True, slots=True)
class SiteSnapshot:
    """
    Immutable site snapshot - the complete render context.
    
    Created once after content discovery, used by all render phases.
    """

    # Content
    pages: tuple[PageSnapshot, ...]
    regular_pages: tuple[PageSnapshot, ...]
    sections: tuple[SectionSnapshot, ...]
    root_section: SectionSnapshot

    # Configuration (immutable views)
    config: MappingProxyType[str, Any]
    params: MappingProxyType[str, Any]  # Site params shortcut

    # Data (from data/ directory)
    data: MappingProxyType[str, Any]

    # Navigation
    menus: MappingProxyType[str, tuple[MenuItemSnapshot, ...]]
    taxonomies: MappingProxyType[str, MappingProxyType[str, tuple[PageSnapshot, ...]]]

    # Pre-computed scheduling structures
    topological_order: tuple[tuple[PageSnapshot, ...], ...]
    template_groups: MappingProxyType[str, tuple[PageSnapshot, ...]]
    attention_order: tuple[PageSnapshot, ...]
    scout_hints: tuple[ScoutHint, ...]

    # Metadata
    snapshot_time: float  # time.time() when snapshot created
    page_count: int
    section_count: int


@dataclass(frozen=True, slots=True)
class ScoutHint:
    """Hint for scout thread cache warming."""

    template_path: Path
    partial_paths: tuple[Path, ...]
    pages_using: int
    priority: float  # Higher = warm earlier


@dataclass(frozen=True, slots=True)
class MenuItemSnapshot:
    """Immutable menu item."""

    name: str
    title: str
    href: str
    weight: float
    children: tuple[MenuItemSnapshot, ...]
    page: PageSnapshot | None = None
    section: SectionSnapshot | None = None
    is_active: bool = False
