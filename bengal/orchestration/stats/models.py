"""
Build statistics data models.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.output import OutputRecord
    from bengal.health.report import HealthReport
    from bengal.rendering.errors import ErrorDeduplicator


@dataclass
class ErrorCategory:
    """Error category for grouping errors by type."""

    name: str
    errors: list[Any] = field(default_factory=list)  # BengalError instances
    warnings: list[str] = field(default_factory=list)


@dataclass
class BuildWarning:
    """A build warning or error."""

    file_path: str
    message: str
    warning_type: str  # 'jinja2', 'preprocessing', 'link', 'other'

    @property
    def short_path(self) -> str:
        """Get shortened path for display."""
        from pathlib import Path

        from bengal.utils.primitives.text import format_path_for_display

        # Try CWD first
        try:
            return str(Path(self.file_path).relative_to(Path.cwd()))
        except (ValueError, OSError):
            # Use centralized fallback formatting
            return format_path_for_display(self.file_path) or self.file_path


@dataclass
class BuildStats:
    """Container for build statistics."""

    total_pages: int = 0
    regular_pages: int = 0
    generated_pages: int = 0
    tag_pages: int = 0
    archive_pages: int = 0
    pagination_pages: int = 0
    total_assets: int = 0
    total_sections: int = 0
    taxonomies_count: int = 0
    build_time_ms: float = 0
    parallel: bool = True
    incremental: bool = False
    skipped: bool = False
    dry_run: bool = False

    # Directive statistics
    total_directives: int = 0
    directives_by_type: dict[str, int] = field(default_factory=dict)

    # Phase timings
    discovery_time_ms: float = 0
    taxonomy_time_ms: float = 0
    rendering_time_ms: float = 0
    assets_time_ms: float = 0
    postprocess_time_ms: float = 0
    health_check_time_ms: float = 0

    # Memory metrics (Phase 1 - Performance Tracking)
    memory_rss_mb: float = 0  # Process RSS (Resident Set Size) memory
    memory_heap_mb: float = 0  # Python heap memory from tracemalloc
    memory_peak_mb: float = 0  # Peak memory during build

    # Cache statistics (Phase 2 - Intelligence)
    cache_hits: int = 0  # Pages/assets served from cache
    cache_misses: int = 0  # Pages/assets rebuilt
    time_saved_ms: float = 0  # Estimated time saved by caching

    # Cache bypass statistics
    cache_bypass_hits: int = 0  # Pages that bypassed cache (in changed_sources or is_changed)
    cache_bypass_misses: int = 0  # Pages that used cache (not changed)

    # Block cache statistics - tracks site-wide template block caching (nav, footer, etc.)
    block_cache_hits: int = 0  # Times cached block was reused
    block_cache_misses: int = 0  # Times block wasn't in cache
    block_cache_site_blocks: int = 0  # Number of site-scoped blocks cached
    block_cache_time_saved_ms: float = 0.0  # Estimated time saved by block caching

    # Additional phase timings (Phase 2)
    menu_time_ms: float = 0
    related_posts_time_ms: float = 0
    fonts_time_ms: float = 0

    # Output directory (for display)
    output_dir: str | None = None

    # Strict mode flag (fail on validation errors)
    strict_mode: bool = False

    # Builder-provided list of typed output records for hot reload decisions.
    # When provided, the dev server uses this for CSS-only reload detection
    # instead of snapshot diffing.
    changed_outputs: list[OutputRecord] = field(default_factory=list)

    # Health check report (set after health checks run)
    health_report: HealthReport | None = None

    # Incremental build decision (set during phase_incremental_filter)
    # RFC: rfc-incremental-build-observability
    incremental_decision: Any = None  # IncrementalDecision when set
    filter_decision_log: Any = None  # FilterDecisionLog when set
    merkle_advisory: dict[str, Any] | None = None

    # Warnings and errors
    warnings: list[Any] = field(default_factory=list)
    template_errors: list[Any] = field(
        default_factory=list
    )  # Rich template errors (TemplateRenderError instances)

    # Error deduplication for template errors (reduces noise during rendering)
    # Lazily initialized via get_error_deduplicator() to avoid circular imports
    _error_deduplicator: ErrorDeduplicator | None = field(default=None, repr=False)

    # Enhanced error collection by category
    errors_by_category: dict[str, ErrorCategory] = field(default_factory=dict)

    # Thread-safety lock for parallel pipeline task updates
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def get_error_deduplicator(self) -> ErrorDeduplicator:
        """
        Get the error deduplicator for this build.

        Lazily initialized to avoid circular imports.

        Returns:
            ErrorDeduplicator instance for this build
        """
        if self._error_deduplicator is None:
            from bengal.rendering.errors import ErrorDeduplicator

            self._error_deduplicator = ErrorDeduplicator()
        return self._error_deduplicator

    def add_warning(self, file_path: str, message: str, warning_type: str = "other") -> None:
        """Add a warning to the build."""
        self.warnings.append(BuildWarning(file_path, message, warning_type))

    def add_template_error(self, error: Any) -> None:
        """
        Add a rich template error.

        Args:
            error: TemplateRenderError instance (or compatible exception)
        """
        self.template_errors.append(error)
        # Also add to categorized errors
        self.add_error(error, category="rendering")

    def add_error(self, error: Any, category: str = "general") -> None:
        """
        Add error to category.

        Args:
            error: BengalError instance (or compatible exception)
            category: Error category name (e.g., "rendering", "discovery", "config")
        """
        if category not in self.errors_by_category:
            self.errors_by_category[category] = ErrorCategory(name=category)
        self.errors_by_category[category].errors.append(error)

    def get_error_summary(self) -> dict[str, Any]:
        """
        Get summary of all errors.

        Returns:
            Dictionary with error counts and breakdown by category
        """
        total_errors = sum(len(cat.errors) for cat in self.errors_by_category.values())
        total_warnings = sum(len(cat.warnings) for cat in self.errors_by_category.values())

        # Also count template_errors
        if self.template_errors:
            total_errors += len(self.template_errors)

        return {
            "total_errors": total_errors,
            "total_warnings": total_warnings + len(self.warnings),
            "by_category": {
                name: {
                    "errors": len(cat.errors),
                    "warnings": len(cat.warnings),
                }
                for name, cat in self.errors_by_category.items()
            },
        }

    def add_directive(self, directive_type: str) -> None:
        """Track a directive usage."""
        self.total_directives += 1
        self.directives_by_type[directive_type] = self.directives_by_type.get(directive_type, 0) + 1

    @property
    def pages_built(self) -> int:
        """Alias for total_pages for backwards compatibility."""
        return self.total_pages

    @property
    def has_errors(self) -> bool:
        """Check if build has any errors."""
        # Check categorized errors
        if any(len(cat.errors) > 0 for cat in self.errors_by_category.values()):
            return True
        # Check template_errors
        return len(self.template_errors) > 0

    @property
    def syntax_errors(self) -> list[Any]:
        """
        Get template errors that are syntax errors.

        Filters template_errors to return only those with error_type == "syntax".
        These are typically Jinja2 TemplateSyntaxError instances (missing endif,
        unclosed tags, etc.).

        Returns:
            List of TemplateRenderError objects with syntax errors.
        """
        return [e for e in self.template_errors if getattr(e, "error_type", None) == "syntax"]

    @property
    def not_found_errors(self) -> list[Any]:
        """
        Get template errors that are "not found" errors.

        Filters template_errors to return only those with error_type == "not_found".
        These occur when a page requests a template that doesn't exist in any
        template directory.

        Returns:
            List of TemplateRenderError objects for missing templates.
        """
        return [e for e in self.template_errors if getattr(e, "error_type", None) == "not_found"]

    @property
    def warnings_by_type(self) -> dict[str, list[BuildWarning]]:
        """Group warnings by type."""
        from collections import defaultdict

        grouped: defaultdict[str, list[BuildWarning]] = defaultdict(list)
        for warning in self.warnings:
            grouped[warning.warning_type].append(warning)
        return dict(grouped)

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_pages": self.total_pages,
            "regular_pages": self.regular_pages,
            "generated_pages": self.generated_pages,
            "total_assets": self.total_assets,
            "total_sections": self.total_sections,
            "taxonomies_count": self.taxonomies_count,
            "build_time_ms": self.build_time_ms,
            "parallel": self.parallel,
            "incremental": self.incremental,
            "skipped": self.skipped,
            "discovery_time_ms": self.discovery_time_ms,
            "taxonomy_time_ms": self.taxonomy_time_ms,
            "rendering_time_ms": self.rendering_time_ms,
            "assets_time_ms": self.assets_time_ms,
            "postprocess_time_ms": self.postprocess_time_ms,
            "memory_rss_mb": self.memory_rss_mb,
            "memory_heap_mb": self.memory_heap_mb,
            "memory_peak_mb": self.memory_peak_mb,
            # Block cache stats
            "block_cache_hits": self.block_cache_hits,
            "block_cache_misses": self.block_cache_misses,
            "block_cache_site_blocks": self.block_cache_site_blocks,
            "block_cache_time_saved_ms": self.block_cache_time_saved_ms,
        }
