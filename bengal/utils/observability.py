"""
Observability utilities for systematic stats collection across Bengal's build pipeline.

Provides standardized stats collection and formatting for debugging performance issues,
cache effectiveness, and processing bottlenecks.

This module implements the observability improvements from RFC: rfc-observability-improvements.md

Key Concepts:
    - ComponentStats: Standardized stats container with counts, cache metrics, and sub-timings
    - HasStats: Protocol for components that expose observability stats
    - Consistent formatting for CLI output and structured logging

Usage:
    >>> from bengal.utils.observability import ComponentStats, HasStats
    >>> stats = ComponentStats(items_total=100, items_processed=80)
    >>> stats.items_skipped["filtered"] = 20
    >>> print(stats.format_summary("MyComponent"))
    MyComponent: processed=80/100 | skipped=[filtered=20]

Related:
    - bengal/health/report.py: ValidatorStats (extends ComponentStats pattern)
    - bengal/orchestration/build/finalization.py: CLI output integration
    - plan/active/rfc-observability-improvements.md: Design rationale
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class HasStats(Protocol):
    """
    Protocol for components that expose observability stats.

    Components implementing this protocol can have their stats displayed
    automatically when phases exceed performance thresholds.

    Example:
        >>> class DirectiveValidator(HasStats):
        ...     last_stats: ComponentStats | None = None
        ...
        ...     def validate(self, site):
        ...         stats = ComponentStats(items_total=len(site.pages))
        ...         # ... validation logic ...
        ...         self.last_stats = stats
    """

    last_stats: ComponentStats | None


@dataclass
class ComponentStats:
    """
    Standardized stats container for any build component.

    Provides a uniform interface for tracking:
    - Processing counts (total, processed, skipped by reason)
    - Cache effectiveness (hits, misses, hit rate)
    - Sub-operation timings (analyze, render, validate, etc.)
    - Custom metrics (component-specific values)

    Attributes:
        items_total: Total items to process
        items_processed: Items actually processed
        items_skipped: Dict of skip reasons and counts (e.g., {"autodoc": 450, "draft": 3})
        cache_hits: Number of cache hits (if applicable)
        cache_misses: Number of cache misses (if applicable)
        sub_timings: Dict of sub-operation names to duration_ms
        metrics: Custom metrics (component-specific, e.g., {"pages_per_sec": 375})

    Example:
        >>> stats = ComponentStats(items_total=100)
        >>> stats.items_processed = 80
        >>> stats.items_skipped["no_links"] = 15
        >>> stats.items_skipped["filtered"] = 5
        >>> stats.cache_hits = 80
        >>> stats.cache_misses = 0
        >>> stats.sub_timings["validate"] = 150.0
        >>> print(stats.format_summary("Links"))
        Links: processed=80/100 | skipped=[no_links=15, filtered=5] | cache=80/80 (100%) | timings=[validate=150ms]
    """

    # Counts
    items_total: int = 0
    items_processed: int = 0
    items_skipped: dict[str, int] = field(default_factory=dict)

    # Cache effectiveness
    cache_hits: int = 0
    cache_misses: int = 0

    # Timing breakdown
    sub_timings: dict[str, float] = field(default_factory=dict)

    # Custom metrics (component-specific)
    metrics: dict[str, int | float | str] = field(default_factory=dict)

    @property
    def cache_hit_rate(self) -> float:
        """
        Cache hit rate as percentage (0-100).

        Returns:
            Percentage of cache hits, or 0.0 if no cache operations.
        """
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    @property
    def skip_rate(self) -> float:
        """
        Skip rate as percentage (0-100).

        Returns:
            Percentage of items skipped, or 0.0 if no items.
        """
        if self.items_total == 0:
            return 0.0
        skipped = sum(self.items_skipped.values())
        return skipped / self.items_total * 100

    @property
    def total_skipped(self) -> int:
        """Total number of skipped items across all reasons."""
        return sum(self.items_skipped.values())

    def format_summary(self, name: str = "") -> str:
        """
        Format stats for CLI output.

        Produces a compact, informative summary suitable for terminal display.
        Only includes sections with actual data.

        Args:
            name: Component name prefix (e.g., "Directives", "Links")

        Returns:
            Formatted string like "processed=80/100 | skipped=[autodoc=450] | cache=80/80 (100%)"

        Example:
            >>> stats = ComponentStats(items_total=100, items_processed=80)
            >>> stats.format_summary("Test")
            "Test: processed=80/100"
        """
        parts = []

        # Processing stats
        if self.items_total > 0:
            parts.append(f"processed={self.items_processed}/{self.items_total}")

        # Skip breakdown
        if self.items_skipped:
            skip_str = ", ".join(f"{k}={v}" for k, v in self.items_skipped.items())
            parts.append(f"skipped=[{skip_str}]")

        # Cache stats
        if self.cache_hits or self.cache_misses:
            total = self.cache_hits + self.cache_misses
            parts.append(f"cache={self.cache_hits}/{total} ({self.cache_hit_rate:.0f}%)")

        # Sub-timings
        if self.sub_timings:
            timing_str = ", ".join(f"{k}={v:.0f}ms" for k, v in self.sub_timings.items())
            parts.append(f"timings=[{timing_str}]")

        # Custom metrics
        if self.metrics:
            metrics_str = ", ".join(f"{k}={v}" for k, v in self.metrics.items())
            parts.append(f"metrics=[{metrics_str}]")

        prefix = f"{name}: " if name else ""
        return prefix + " | ".join(parts) if parts else f"{prefix}(no data)"

    def to_log_context(self) -> dict[str, int | float | str]:
        """
        Convert to flat dict for structured logging.

        Flattens nested data structures for log aggregation systems.

        Returns:
            Flat dictionary suitable for structured logging kwargs.

        Example:
            >>> stats = ComponentStats(items_total=100, cache_hits=80)
            >>> stats.to_log_context()
            {'items_total': 100, 'items_processed': 0, 'cache_hits': 80, ...}
        """
        ctx: dict[str, int | float | str] = {
            "items_total": self.items_total,
            "items_processed": self.items_processed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "skip_rate": self.skip_rate,
        }

        # Flatten sub-timings
        for timing_key, timing_val in self.sub_timings.items():
            ctx[f"timing_{timing_key}_ms"] = timing_val

        # Flatten skip reasons
        for skip_key, skip_val in self.items_skipped.items():
            ctx[f"skipped_{skip_key}"] = skip_val

        # Flatten metrics
        for metric_key, metric_val in self.metrics.items():
            ctx[f"metric_{metric_key}"] = metric_val

        return ctx


def format_phase_stats(
    phase_name: str, duration_ms: float, component: HasStats | None, slow_threshold_ms: float = 1000
) -> str | None:
    """
    Format stats for a slow phase, if applicable.

    Returns formatted stats string only if the phase exceeded the threshold
    AND the component has stats available.

    Args:
        phase_name: Name of the phase (e.g., "Directives", "Links")
        duration_ms: How long the phase took
        component: Component with HasStats protocol (or None)
        slow_threshold_ms: Threshold for considering a phase "slow"

    Returns:
        Formatted stats string, or None if phase was fast or no stats available.

    Example:
        >>> validator = DirectiveValidator()
        >>> validator.validate(site)  # Sets last_stats
        >>> stats_str = format_phase_stats("Directives", 7554, validator)
        >>> if stats_str:
        ...     print(f"   📊 {stats_str}")
    """
    if duration_ms <= slow_threshold_ms:
        return None

    if component is None:
        return None

    if not isinstance(component, HasStats):
        return None

    if component.last_stats is None:
        return None

    return component.last_stats.format_summary(phase_name)
