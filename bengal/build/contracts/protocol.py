"""
Change detector protocol.

All detectors implement this interface, enabling:
- Uniform testing
- Composable pipelines
- Swappable implementations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bengal.build.contracts.results import ChangeDetectionResult

if TYPE_CHECKING:
    from bengal.build.contracts.keys import CacheKey
    from bengal.cache import BuildCache
    from bengal.core.site import Site
    from bengal.orchestration.build.coordinator import CacheCoordinator


@dataclass(frozen=True, slots=True)
class DetectionContext:
    """
    Immutable context passed to detectors.

    Contains everything a detector needs to detect changes.
    Accumulated results from previous detectors are available
    for cascade detection (e.g., template changes affect pages).
    """

    # Core dependencies
    cache: BuildCache
    site: Site
    coordinator: CacheCoordinator | None = None

    # Accumulated results from previous detectors
    previous: ChangeDetectionResult = field(default_factory=ChangeDetectionResult.empty)

    # Configuration
    verbose: bool = False

    # Forced changes (from file watcher)
    forced_changed: frozenset[CacheKey] = field(default_factory=frozenset)

    # Nav-affecting changes (structural)
    nav_changed: frozenset[CacheKey] = field(default_factory=frozenset)

    def with_previous(self, result: ChangeDetectionResult) -> DetectionContext:
        """Create new context with updated previous results."""
        return DetectionContext(
            cache=self.cache,
            site=self.site,
            coordinator=self.coordinator,
            previous=self.previous.merge(result),
            verbose=self.verbose,
            forced_changed=self.forced_changed,
            nav_changed=self.nav_changed,
        )


@runtime_checkable
class ChangeDetector(Protocol):
    """
    Protocol for change detection components.

    Each detector:
    1. Receives context with cache, site, and previous results
    2. Returns immutable ChangeDetectionResult
    3. Does NOT mutate shared state
    """

    def detect(self, ctx: DetectionContext) -> ChangeDetectionResult:
        """
        Detect changes and return result.

        Args:
            ctx: Detection context with cache, site, and accumulated results

        Returns:
            ChangeDetectionResult with detected changes
        """
        ...
