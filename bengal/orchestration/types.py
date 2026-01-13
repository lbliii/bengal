"""
Type definitions for build orchestration.

This module provides TypedDict and Protocol definitions for orchestration types,
enabling type-safe build context, phase tracking, and inter-orchestrator
communication.

Note:
BuildStats is defined as a dataclass in bengal.orchestration.stats.models.
This module provides complementary TypedDicts for dict-based patterns.

See Also:
- :mod:`bengal.orchestration.stats.models`: BuildStats dataclass
- :mod:`bengal.utils.progress`: ProgressReporter protocol
- :mod:`bengal.utils.stats_protocol`: CoreStats, DisplayableStats protocols

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, TypedDict, runtime_checkable

if TYPE_CHECKING:
    from bengal.core import Page, Section


# =============================================================================
# Phase Statistics (dict form for JSON serialization)
# =============================================================================


class PhaseStats(TypedDict, total=False):
    """Statistics for a single build phase."""

    name: str
    duration_ms: float
    items_processed: int
    errors: int
    warnings: int


class PhaseTiming(TypedDict):
    """Timing record for a build phase."""

    phase: str
    start_ms: float
    end_ms: float
    duration_ms: float


# =============================================================================
# Build Context Types
# =============================================================================


class BuildContextDict(TypedDict, total=False):
    """Dict representation of build context for serialization."""

    parallel: bool
    incremental: bool
    strict_mode: bool
    verbose: bool
    quiet: bool
    profile: str | None
    changed_sources: list[str]
    nav_changed_sources: list[str]
    structural_changed: bool


class LastBuildStats(TypedDict, total=False):
    """Stats stored on Site after build completion."""

    build_time_ms: float
    rendering_time_ms: float
    total_pages: int
    total_assets: int


# =============================================================================
# Cache Types
# =============================================================================


class CacheEntry(TypedDict, total=False):
    """Generic cache entry structure."""

    key: str
    value: object
    timestamp: float
    ttl: int | None


class CacheStats(TypedDict, total=False):
    """Cache statistics for reporting."""

    hits: int
    misses: int
    hit_rate: float
    size: int
    evictions: int


# =============================================================================
# Render Context Types
# =============================================================================


class RenderContext(TypedDict, total=False):
    """Context passed to template rendering."""

    page: object  # Page instance
    site: object  # Site instance
    section: object  # Section instance
    baseurl: str
    now: str
    build_date: str
    is_production: bool


class RenderResult(TypedDict, total=False):
    """Result of rendering a single page."""

    page_path: str
    output_path: str
    success: bool
    duration_ms: float
    from_cache: bool
    error: str | None


# =============================================================================
# Asset Processing Types
# =============================================================================


class AssetResult(TypedDict, total=False):
    """Result of processing a single asset."""

    source_path: str
    output_path: str
    size_bytes: int
    optimized: bool
    fingerprinted: bool
    duration_ms: float


class AssetManifest(TypedDict, total=False):
    """Asset manifest for fingerprinting/cache busting."""

    version: int
    generated_at: str
    assets: dict[str, str]  # original path -> fingerprinted path


# =============================================================================
# Progress Manager Protocol
# =============================================================================


@runtime_checkable
class ProgressManagerProtocol(Protocol):
    """
    Protocol for progress manager objects.
    
    Used by orchestrators for live progress display.
    More flexible than ProgressReporter - includes task management.
        
    """

    def add_task(self, description: str, total: int | None = None) -> object:
        """Add a new task to track."""
        ...

    def update(
        self,
        task_id: object,
        *,
        advance: int | None = None,
        completed: int | None = None,
        description: str | None = None,
    ) -> None:
        """Update task progress."""
        ...

    def remove_task(self, task_id: object) -> None:
        """Remove a completed task."""
        ...


# =============================================================================
# Section Protocol (for menu building)
# =============================================================================


@runtime_checkable
class SectionLike(Protocol):
    """
    Protocol for section-like objects in menu building.
    
    Enables menu orchestrator to work with any section-compatible object.
        
    """

    @property
    def title(self) -> str:
        """Section title."""
        ...

    @property
    def pages(self) -> list[Page]:
        """Pages in this section."""
        ...

    @property
    def children(self) -> list[Section]:
        """Child sections."""
        ...

    @property
    def path(self) -> str:
        """Section path (URL path segment)."""
        ...


# =============================================================================
# Build Options Type
# =============================================================================


class BuildOptionsDict(TypedDict, total=False):
    """Dict form of build options for serialization."""

    parallel: bool
    incremental: bool
    verbose: bool
    quiet: bool
    strict: bool
    full_output: bool
    profile_templates: bool
    memory_optimized: bool
    profile: Literal["writer", "developer", "operator", "custom"] | None


# =============================================================================
# Output Types
# =============================================================================


class OutputStats(TypedDict, total=False):
    """Statistics about build output."""

    total_files: int
    total_size_bytes: int
    html_files: int
    css_files: int
    js_files: int
    image_files: int
    other_files: int


class OutputRecord(TypedDict):
    """Record of a single output file."""

    path: str
    content_hash: str
    size_bytes: int
    output_type: Literal["html", "css", "js", "image", "json", "other"]


# =============================================================================
# Autodoc Types
# =============================================================================


class AutodocModuleInfo(TypedDict, total=False):
    """Information about a module discovered for autodoc."""

    module_path: str
    package_name: str
    module_name: str
    has_docstring: bool
    class_count: int
    function_count: int


class AutodocResult(TypedDict, total=False):
    """Result of autodoc processing."""

    modules_discovered: int
    modules_processed: int
    pages_generated: int
    sections_generated: int
    duration_ms: float
    errors: list[str]


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Phase stats
    "PhaseStats",
    "PhaseTiming",
    # Build context
    "BuildContextDict",
    "LastBuildStats",
    "BuildOptionsDict",
    # Cache
    "CacheEntry",
    "CacheStats",
    # Render
    "RenderContext",
    "RenderResult",
    # Assets
    "AssetResult",
    "AssetManifest",
    # Output
    "OutputStats",
    "OutputRecord",
    # Autodoc
    "AutodocModuleInfo",
    "AutodocResult",
    # Protocols
    "ProgressManagerProtocol",
    "SectionLike",
]
