"""
Build statistics data models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.health.report import HealthReport


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

        from bengal.utils.paths import format_path_for_display

        # Try CWD first for backward compatibility
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

    # Cache bypass statistics (RFC: rfc-incremental-hot-reload-invariants)
    cache_bypass_hits: int = 0  # Pages that bypassed cache (in changed_sources or is_changed)
    cache_bypass_misses: int = 0  # Pages that used cache (not changed)

    # Additional phase timings (Phase 2)
    menu_time_ms: float = 0
    related_posts_time_ms: float = 0
    fonts_time_ms: float = 0

    # Output directory (for display)
    output_dir: str | None = None

    # Strict mode flag (fail on validation errors)
    strict_mode: bool = False

    # Optional: builder-provided list of changed output paths (relative to output dir)
    # When provided, the dev server will prefer this over snapshot diffing for reload decisions.
    changed_outputs: list[str] | None = None

    # Health check report (set after health checks run)
    health_report: HealthReport | None = None

    # Warnings and errors
    warnings: list[Any] = field(default_factory=list)
    template_errors: list[Any] = field(default_factory=list)  # Rich template errors

    def add_warning(self, file_path: str, message: str, warning_type: str = "other") -> None:
        """Add a warning to the build."""
        self.warnings.append(BuildWarning(file_path, message, warning_type))

    def add_template_error(self, error: Any) -> None:
        """Add a rich template error."""
        self.template_errors.append(error)

    def add_directive(self, directive_type: str) -> None:
        """Track a directive usage."""
        self.total_directives += 1
        self.directives_by_type[directive_type] = self.directives_by_type.get(directive_type, 0) + 1

    @property
    def has_errors(self) -> bool:
        """Check if build has any errors."""
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
        }
