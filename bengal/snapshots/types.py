"""
Snapshot types for immutable site representation.

All snapshot types are frozen dataclasses with slots for memory efficiency.
They contain pre-computed values from the mutable Site/Page/Section objects,
enabling lock-free parallel rendering.

RFC: Snapshot-Enabled v2 Opportunities
- TemplateSnapshot: Pre-analyzed template with dependency graph (Opportunity 5)
- ConfigSnapshot: Frozen, typed configuration (Opportunity 6)

"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.config.snapshot import ConfigSnapshot
    from bengal.core.nav_tree import NavTree


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

    @property
    def type(self) -> str | None:
        """Get page type from metadata (template compatibility)."""
        return self.metadata.get("type")

    @property
    def variant(self) -> str | None:
        """Get page variant from metadata (template compatibility)."""
        return self.metadata.get("variant") or self.metadata.get("layout")

    def __hash__(self) -> int:
        """Hash based on source_path and content_hash for set operations."""
        return hash((self.source_path, self.content_hash))

    def __eq__(self, other: object) -> bool:
        """Equality based on source_path and content_hash."""
        if not isinstance(other, PageSnapshot):
            return NotImplemented
        return self.source_path == other.source_path and self.content_hash == other.content_hash


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
class TemplateSnapshot:
    """
    Pre-analyzed template with dependency graph.

    Created during snapshot phase via static template analysis.
    Enables O(1) template→page lookup for incremental builds.

    RFC: Snapshot-Enabled v2 Opportunities (Opportunity 5)
    """

    # Identity
    path: Path
    name: str

    # Template relationships (pre-resolved)
    extends: str | None  # {% extends "base.html" %}
    includes: tuple[str, ...]  # {% include "partial.html" %}
    imports: tuple[str, ...]  # {% from "macros.html" import ... %}

    # Block definitions
    blocks: tuple[str, ...]  # {% block content %}

    # Macros
    macros_defined: tuple[str, ...]  # {% macro name() %}
    macros_used: tuple[str, ...]  # {{ macros.name() }}

    # Incremental build support
    content_hash: str

    # All direct and transitive dependencies (for invalidation)
    all_dependencies: frozenset[str] = field(default_factory=frozenset)


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
    # Legacy dict access - preserved for backward compatibility
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

    # Metadata (required fields - must come before defaults)
    snapshot_time: float  # time.time() when snapshot created
    page_count: int
    section_count: int

    # Template snapshots with dependency graph (RFC: Snapshot-Enabled v2)
    # O(1) template→page lookup for incremental builds
    templates: MappingProxyType[str, TemplateSnapshot] = field(
        default_factory=lambda: MappingProxyType({})
    )
    # Reverse index: template_name → frozenset of dependent template names
    template_dependency_graph: MappingProxyType[str, frozenset[str]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    # Reverse index: template_name → pages that use it (directly or transitively)
    template_dependents: MappingProxyType[str, tuple[PageSnapshot, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )

    # Typed configuration snapshot (RFC: Snapshot-Enabled v2, Opportunity 6)
    # Provides typed attribute access: config_snapshot.site.title
    # None for backward compatibility - will be populated by snapshot builder
    config_snapshot: ConfigSnapshot | None = None

    # Pre-computed navigation trees keyed by version_id ("__default__" for unversioned).
    # Built at snapshot time from the fully-populated site, enabling lock-free
    # O(1) lookups during parallel rendering and eliminating NavTreeCache locks.
    nav_trees: MappingProxyType[str, NavTree] = field(
        default_factory=lambda: MappingProxyType({})
    )

    # Pre-computed top-level content (eliminates Renderer._cache_lock).
    # Pages and sections not nested in any parent section.
    top_level_pages: tuple[PageSnapshot, ...] = ()
    top_level_sections: tuple[SectionSnapshot, ...] = ()

    # Pre-computed tag→pages mapping (eliminates Renderer._cache_lock).
    # Maps tag slug to filtered, resolved page snapshots.
    tag_pages: MappingProxyType[str, tuple[PageSnapshot, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )


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
