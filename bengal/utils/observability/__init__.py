"""
Observability utilities for Bengal.

This sub-package provides logging, metrics collection, progress reporting,
and performance analysis utilities.

Modules:
    logger: Structured logging system with phase tracking
    rich_console: Rich console wrapper with profile-aware output
    progress: Progress reporting protocol and implementations
    observability: Standardized stats collection and formatting
    performance_collector: Build performance metrics collection
    performance_report: Performance metrics analysis and reporting
    profile: Build profile system for persona-based observability

Example:
    >>> from bengal.utils.observability.observability import get_logger, get_console, ProgressReporter
    >>> logger = get_logger(__name__)
    >>> console = get_console()
    >>> logger.info("build_started", pages=100)

"""

from bengal.utils.observability.logger import (
    BengalLogger,
    LazyLogger,
    LogEvent,
    LogLevel,
    close_all_loggers,
    configure_logging,
    get_logger,
    print_all_summaries,
    reset_loggers,
    set_console_quiet,
    truncate_error,
    truncate_str,
)
from bengal.utils.observability.observability import (
    ComponentStats,
    HasStats,
    format_phase_stats,
)
from bengal.utils.observability.performance_collector import (
    PerformanceCollector,
    format_memory,
)
from bengal.utils.observability.performance_report import (
    BuildMetric,
    PerformanceReport,
)
from bengal.utils.observability.profile import (
    BuildProfile,
    get_current_profile,
    get_enabled_health_checks,
    is_validator_enabled,
    set_current_profile,
    should_collect_metrics,
    should_show_debug,
    should_track_memory,
)
from bengal.utils.observability.progress import (
    LiveProgressReporterAdapter,
    NoopReporter,
    ProgressReporter,
)
from bengal.utils.observability.cli_progress import (
    LiveProgressManager,
    PhaseProgress,
    PhaseStatus,
)
from bengal.utils.observability.rich_console import (
    PALETTE,
    bengal_theme,
    detect_environment,
    get_console,
    is_live_display_active,
    reset_console,
    should_use_emoji,
    should_use_rich,
)

__all__ = [
    # logger
    "BengalLogger",
    "LazyLogger",
    "LogLevel",
    "LogEvent",
    "get_logger",
    "configure_logging",
    "set_console_quiet",
    "close_all_loggers",
    "reset_loggers",
    "print_all_summaries",
    "truncate_str",
    "truncate_error",
    # rich_console
    "PALETTE",
    "bengal_theme",
    "get_console",
    "should_use_rich",
    "should_use_emoji",
    "detect_environment",
    "reset_console",
    "is_live_display_active",
    # progress
    "ProgressReporter",
    "NoopReporter",
    "LiveProgressReporterAdapter",
    # cli_progress (moved from cli.progress)
    "LiveProgressManager",
    "PhaseProgress",
    "PhaseStatus",
    # observability
    "ComponentStats",
    "HasStats",
    "format_phase_stats",
    # performance_collector
    "PerformanceCollector",
    "format_memory",
    # performance_report
    "BuildMetric",
    "PerformanceReport",
    # profile
    "BuildProfile",
    "set_current_profile",
    "get_current_profile",
    "should_show_debug",
    "should_track_memory",
    "should_collect_metrics",
    "get_enabled_health_checks",
    "is_validator_enabled",
]
