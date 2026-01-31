"""
Type definitions for build orchestration.

This module provides TypedDict and Protocol definitions for orchestration types,
enabling type-safe build context, phase tracking, and inter-orchestrator
communication.

Common build types (PhaseStats, PhaseTiming, BuildContextDict, etc.) are
defined in bengal.protocols.build and re-exported here for convenience.

Note:
BuildStats is defined as a dataclass in bengal.orchestration.stats.models.
This module provides complementary TypedDicts for dict-based patterns.

See Also:
- :mod:`bengal.protocols.build`: Canonical location for shared build types
- :mod:`bengal.orchestration.stats.models`: BuildStats dataclass
- :mod:`bengal.utils.observability.progress`: ProgressReporter protocol

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, TypedDict, runtime_checkable

# Re-export shared build types from protocols
from bengal.protocols.build import (
    BuildContextDict,
    BuildOptionsDict,
    PhaseStats,
    PhaseTiming,
    RenderContext,
    RenderResult,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Last Build Stats (site-specific)
# =============================================================================


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

    def update_phase(
        self,
        phase_id: str,
        current: int | None = None,
        current_item: str | None = None,
        **metadata: object,
    ) -> None:
        """Update phase progress."""
        ...


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
    "AssetManifest",
    "AssetResult",
    "AutodocModuleInfo",
    "AutodocResult",
    "BuildContextDict",
    "BuildOptionsDict",
    "CacheEntry",
    "CacheStats",
    # Local types
    "LastBuildStats",
    "OutputRecord",
    "OutputStats",
    # Re-exported from protocols.build
    "PhaseStats",
    "PhaseTiming",
    # Protocols
    "ProgressManagerProtocol",
    "RenderContext",
    "RenderResult",
]
