"""
Stats protocol definitions for type-safe stats handling.

This module defines the contracts that stats objects must implement
to be used with display and reporting functions. Using protocols
instead of concrete types allows different stats implementations
(full BuildStats, minimal subprocess results) to be used interchangeably.

Architecture:
    - CoreStats: Minimal contract for any stats object
    - DisplayableStats: Full contract for display_build_stats()

Related:
    - bengal/utils/build_stats.py: Full BuildStats implementation
    - bengal/utils/stats_minimal.py: Lightweight MinimalStats implementation
    - bengal/server/build_trigger.py: Uses MinimalStats for subprocess results

See Also:
    - plan/drafted/rfc-stats-architecture.md: Design rationale
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CoreStats(Protocol):
    """
    Minimal contract for any stats object.

    This protocol defines the absolute minimum attributes that any
    build stats object must provide. Used for basic logging and
    simple display scenarios.
    """

    total_pages: int
    build_time_ms: float
    incremental: bool


@runtime_checkable
class DisplayableStats(CoreStats, Protocol):
    """
    Contract for stats objects usable with display_build_stats().

    This protocol defines all attributes that display_build_stats()
    may access. Implementations must provide all these attributes,
    though timing values can be 0 (display skips them if 0).

    Attributes:
        # Core counts
        total_pages: Total number of pages built
        regular_pages: Number of regular content pages
        generated_pages: Number of generated pages (tags, archives, etc.)
        total_assets: Number of assets processed
        total_sections: Number of content sections
        taxonomies_count: Number of taxonomy terms
        total_directives: Number of directives processed
        directives_by_type: Directive counts by type name

        # Build flags
        build_time_ms: Total build duration in milliseconds
        incremental: Whether this was an incremental build
        parallel: Whether parallel rendering was used
        skipped: Whether the build was skipped (no changes)

        # Warnings
        warnings: List of build warnings

        # Phase timings (display skips if 0)
        discovery_time_ms: Content discovery phase duration
        taxonomy_time_ms: Taxonomy building phase duration
        rendering_time_ms: Template rendering phase duration
        assets_time_ms: Asset processing phase duration
        postprocess_time_ms: Post-processing phase duration
        health_check_time_ms: Health check phase duration

    Methods:
        has_errors: Property that returns True if build has errors
        get_error_summary: Returns dict with error/warning counts
    """

    # Core counts
    regular_pages: int
    generated_pages: int
    total_assets: int
    total_sections: int
    taxonomies_count: int
    total_directives: int
    directives_by_type: dict[str, int]

    # Build flags
    parallel: bool
    skipped: bool

    # Warnings
    warnings: list[Any]

    # Phase timings (display checks > 0 before showing)
    discovery_time_ms: float
    taxonomy_time_ms: float
    rendering_time_ms: float
    assets_time_ms: float
    postprocess_time_ms: float
    health_check_time_ms: float

    # Error tracking
    @property
    def has_errors(self) -> bool:
        """Check if build has any errors."""
        ...

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of all errors."""
        ...
