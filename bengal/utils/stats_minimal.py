"""
Lightweight stats implementation for subprocess build results.

This module provides MinimalStats, a lightweight implementation of
the DisplayableStats protocol for use when full BuildStats data
is not available (e.g., subprocess rebuilds via BuildResult).

Architecture:
    MinimalStats implements DisplayableStats with sensible defaults
    for attributes not available from the build result. This allows
    display_build_stats() to work uniformly with both full builds
    and subprocess rebuilds.

Related:
    - bengal/utils/stats_protocol.py: Protocol definitions
    - bengal/utils/build_stats.py: Full BuildStats implementation
    - bengal/server/build_executor.py: BuildResult that this wraps

See Also:
    - plan/drafted/rfc-stats-architecture.md: Design rationale
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.server.build_executor import BuildResult


@dataclass
class MinimalStats:
    """
    Lightweight stats for subprocess build results.

    Implements the DisplayableStats protocol with sensible defaults
    for attributes not available from BuildResult. This replaces
    ad-hoc local stub classes with a tested, protocol-compliant
    implementation.

    Attributes:
        total_pages: Number of pages built (from BuildResult.pages_built)
        build_time_ms: Build duration in ms (from BuildResult.build_time_ms)
        incremental: Whether this was an incremental build

    All other attributes default to appropriate zero/empty values,
    which display_build_stats() handles gracefully (skips if 0).

    Example:
        >>> from bengal.server.build_executor import BuildResult
        >>> result = BuildResult(success=True, pages_built=50, build_time_ms=500.0)
        >>> stats = MinimalStats.from_build_result(result, incremental=True)
        >>> stats.total_pages
        50
    """

    # Required: from BuildResult
    total_pages: int
    build_time_ms: float
    incremental: bool

    # Counts: defaults for display compatibility
    regular_pages: int = 0
    generated_pages: int = 0
    total_assets: int = 0
    total_sections: int = 0
    taxonomies_count: int = 0
    total_directives: int = 0
    directives_by_type: dict[str, int] = field(default_factory=dict)

    # Flags
    parallel: bool = True
    skipped: bool = False

    # Warnings
    warnings: list[Any] = field(default_factory=list)

    # Phase timings: default to 0 (display skips if 0)
    discovery_time_ms: float = 0.0
    taxonomy_time_ms: float = 0.0
    rendering_time_ms: float = 0.0
    assets_time_ms: float = 0.0
    postprocess_time_ms: float = 0.0
    health_check_time_ms: float = 0.0

    @property
    def has_errors(self) -> bool:
        """
        Check if build has any errors.

        MinimalStats doesn't track errors (subprocess builds report
        success/failure via BuildResult.success), so this always
        returns False for successfully completed subprocess builds.
        """
        return False

    def get_error_summary(self) -> dict[str, Any]:
        """
        Get summary of all errors.

        MinimalStats doesn't track errors, so this returns an empty
        summary. Error handling for subprocess builds is done via
        BuildResult.success and BuildResult.error_message.

        Returns:
            Dictionary with zero error/warning counts
        """
        return {
            "total_errors": 0,
            "total_warnings": 0,
            "by_category": {},
        }

    @classmethod
    def from_build_result(
        cls,
        result: BuildResult,
        incremental: bool = True,
    ) -> MinimalStats:
        """
        Create MinimalStats from a subprocess BuildResult.

        This factory method is the primary way to create MinimalStats.
        It extracts available data from BuildResult and uses sensible
        defaults for everything else.

        Args:
            result: BuildResult from subprocess executor
            incremental: Whether this was an incremental build

        Returns:
            MinimalStats instance implementing DisplayableStats

        Example:
            >>> result = BuildResult(success=True, pages_built=100, build_time_ms=250.0)
            >>> stats = MinimalStats.from_build_result(result)
            >>> stats.total_pages
            100
        """
        return cls(
            total_pages=result.pages_built,
            regular_pages=result.pages_built,  # Assume all regular for subprocess
            build_time_ms=result.build_time_ms,
            incremental=incremental,
        )
