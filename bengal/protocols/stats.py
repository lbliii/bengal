"""
Build statistics protocols.

Provides protocol definitions for build statistics, allowing lower layers
(core, errors, rendering) to depend on interfaces rather than concrete
implementations from orchestration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.core.output import OutputRecord
    from bengal.health.report import HealthReport


@runtime_checkable
class BuildStatsProtocol(Protocol):
    """Protocol for build statistics access.
    
    Defines the interface that lower layers can depend on for
    reading build statistics without importing the concrete
    BuildStats class from orchestration.
    """

    # Page statistics
    @property
    def total_pages(self) -> int: ...

    @property
    def regular_pages(self) -> int: ...

    @property
    def generated_pages(self) -> int: ...

    @property
    def tag_pages(self) -> int: ...

    @property
    def archive_pages(self) -> int: ...

    @property
    def pagination_pages(self) -> int: ...

    # Asset and section counts
    @property
    def total_assets(self) -> int: ...

    @property
    def total_sections(self) -> int: ...

    @property
    def taxonomies_count(self) -> int: ...

    # Build configuration
    @property
    def parallel(self) -> bool: ...

    @property
    def incremental(self) -> bool: ...

    @property
    def strict_mode(self) -> bool: ...

    @property
    def skipped(self) -> bool: ...

    # Timing metrics
    @property
    def build_time_ms(self) -> float: ...

    @property
    def discovery_time_ms(self) -> float: ...

    @property
    def rendering_time_ms(self) -> float: ...

    @property
    def assets_time_ms(self) -> float: ...

    # Error access
    @property
    def has_errors(self) -> bool: ...

    @property
    def template_errors(self) -> list[Any]: ...

    @property
    def warnings(self) -> list[Any]: ...

    @property
    def errors_by_category(self) -> dict[str, Any]: ...

    # Methods for error reporting
    def get_error_summary(self) -> dict[str, Any]: ...

    def add_warning(self, file_path: str, message: str, warning_type: str = "other") -> None: ...

    def add_error(self, error: Any, category: str = "general") -> None: ...

    def add_template_error(self, error: Any) -> None: ...

    # Output tracking
    @property
    def changed_outputs(self) -> list[OutputRecord]: ...

    @property
    def health_report(self) -> HealthReport | None: ...
