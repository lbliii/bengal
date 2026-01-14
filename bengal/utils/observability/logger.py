"""
Structured logging system for Bengal SSG.

Provides phase-aware logging with context propagation, timing,
and structured event emission. Designed for observability into
the 22-phase build pipeline.

Example:

```python
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

with logger.phase("discovery", page_count=100):
    logger.info("discovered_content", files=len(files))
    logger.debug("parsed_frontmatter", page=page.path, keys=list(metadata.keys()))
```
"""

from __future__ import annotations

import json
import time
import traceback
import tracemalloc
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, TextIO, TypedDict


class LogLevel(Enum):
    """Log levels in order of severity."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogEvent:
    """Structured log event with context."""

    timestamp: str
    level: str
    logger_name: str
    event_type: str
    message: str
    phase: str | None = None
    phase_depth: int = 0
    duration_ms: float | None = None
    memory_mb: float | None = None  # Memory delta for phase
    peak_memory_mb: float | None = None  # Peak memory during phase
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def format_console(self, verbose: bool = False) -> str:
        """Format for console output using Rich markup."""
        indent = "  " * self.phase_depth

        # Level colors and indicators
        level_config = {
            "DEBUG": ("cyan", "·", ""),
            "INFO": ("green", "·", ""),
            "WARNING": ("yellow", "!", "Warning:"),
            "ERROR": ("red", "x", "Error:"),
            "CRITICAL": ("magenta", "x", "Critical:"),
        }

        style, icon, label = level_config.get(self.level, ("white", "·", ""))

        # Phase markers
        phase_marker = f" [bold]\\[{self.phase}][/bold]" if self.phase else ""

        # Timing and memory
        metrics = []
        if self.duration_ms is not None:
            metrics.append(f"{self.duration_ms:.1f}ms")
        if self.memory_mb is not None:
            if self.memory_mb >= 0:
                metrics.append(f"+{self.memory_mb:.1f}MB")
            else:
                metrics.append(f"{self.memory_mb:.1f}MB")
        if self.peak_memory_mb is not None:
            metrics.append(f"peak:{self.peak_memory_mb:.1f}MB")

        metrics_str = f" [dim]({', '.join(metrics)})[/dim]" if metrics else ""

        # Build prefix with label for warnings/errors
        label_str = f" {label}" if label else ""
        base = f"{indent}[{style}]{icon}{label_str}[/{style}]{phase_marker} {self.message}{metrics_str}"

        # Always show context for warnings and errors (actionable issues)
        # In verbose mode, show context for all levels
        show_context = verbose or self.level in ("WARNING", "ERROR", "CRITICAL")

        if show_context and self.context:
            context_str = " " + " ".join(f"{k}={v}" for k, v in self.context.items())
            base += f" [{style}]{context_str}[/{style}]"

        if verbose:
            # Add timestamp in verbose mode
            time_str = self.timestamp.split("T")[1].split(".")[0]  # HH:MM:SS
            base = f"[dim]{time_str}[/dim] {base}"

        return base


class BengalLogger:
    """
    Phase-aware structured logger for Bengal builds.
    
    Tracks build phases, emits structured events, and provides
    timing information. All logs are written to both console
    and a build log file.
        
    """

    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        log_file: Path | None = None,
        verbose: bool = False,
        quiet_console: bool = False,
    ):
        """
        Initialize logger.

        Args:
            name: Logger name (typically __name__)
            level: Minimum log level to emit
            log_file: Path to log file (optional)
            verbose: Whether to show verbose output
            quiet_console: Suppress console output (for live progress mode)
        """
        self.name = name
        self.level = level
        self.log_file = log_file
        self.verbose = verbose
        self.quiet_console = quiet_console

        # Phase tracking
        self._phase_stack: list[tuple[str, float, dict[str, Any]]] = []
        self._events: list[LogEvent] = []

        # File handle - properly closed in close() method
        # Open in append mode to allow multiple loggers to write to same file safely
        self._file_handle: TextIO | None = None
        if log_file:
            # Ensure parent directory exists before opening the log file
            from contextlib import suppress

            with suppress(Exception):
                log_file.parent.mkdir(parents=True, exist_ok=True)
            self._file_handle = open(log_file, "a", encoding="utf-8")  # noqa: SIM115

    @contextmanager
    def phase(self, name: str, **context: Any) -> Any:
        """
        Context manager for tracking build phases with timing and memory.

        Example:
            with logger.phase("discovery", page_count=100):
                # ... work ...
                pass

        Args:
            name: Phase name
            **context: Additional context to attach to all events in phase
        """
        start_time = time.time()

        # Track memory if tracemalloc is active
        start_memory = None
        memory_tracking = tracemalloc.is_tracing()
        if memory_tracking:
            start_memory = tracemalloc.get_traced_memory()[0]  # current

        self._phase_stack.append((name, start_time, context))

        # Emit phase start
        self.info("phase_start", phase_name=name, **context)

        try:
            yield
        except Exception as e:
            # Enhance error message for common issues
            enhanced_error = self._enhance_error_message(e, name, context)
            # Emit phase error
            self.error("phase_error", phase_name=name, error=enhanced_error, **context)
            raise
        finally:
            # Pop phase and calculate metrics
            phase_name, phase_start, phase_context = self._phase_stack.pop()
            duration_ms = (time.time() - phase_start) * 1000

            # Calculate memory metrics if tracking
            memory_mb = None
            peak_memory_mb = None
            if memory_tracking and start_memory is not None:
                current_memory, peak_memory = tracemalloc.get_traced_memory()
                memory_mb = (current_memory - start_memory) / 1024 / 1024  # MB
                peak_memory_mb = peak_memory / 1024 / 1024  # MB

            self.info(
                "phase_complete",
                phase_name=phase_name,
                duration_ms=duration_ms,
                memory_mb=memory_mb,
                peak_memory_mb=peak_memory_mb,
                **phase_context,
            )

    def _enhance_error_message(
        self, error: Exception, phase_name: str, context: dict[str, Any]
    ) -> str:
        """
        Enhance error messages with helpful context for common issues.

        Detects specific error patterns and adds context about what went wrong,
        what was expected, and how to fix it.

        Performance: Only runs when errors occur (rare). Uses lightweight checks
        before expensive traceback formatting.
        """
        error_msg = str(error)
        error_type = type(error).__name__

        # Fast path: Only enhance AttributeError with 'get' attribute
        if error_type != "AttributeError" or "'str' object has no attribute 'get'" not in error_msg:
            return error_msg

        # Check if site is in context first (fast check before traceback)
        site = context.get("site") if "site" in context else None
        has_site_config = site is not None and hasattr(site, "config")
        is_config_string = has_site_config and isinstance(site.config, str)

        # Format traceback once (only if we have a traceback)
        # This is typically <1ms and only happens during errors (rare)
        tb_str = None
        tb_lines = None
        if error.__traceback__ is not None:
            tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
            tb_str = "".join(tb_lines)

        # Check if it's related to site.config
        is_site_config_error = (
            tb_str is not None and ("site.config" in tb_str or "self.site.config" in tb_str)
        ) or is_config_string

        if is_site_config_error:
            # Extract the actual value if possible from context
            config_value_preview = None
            config_type_name = "unknown"
            if "site" in context:
                site = context.get("site")
                if hasattr(site, "config"):
                    config_value = site.config
                    config_type_name = type(config_value).__name__
                    if isinstance(config_value, str):
                        preview = (
                            config_value[:100] + "..." if len(config_value) > 100 else config_value
                        )
                        config_value_preview = f"'{preview}'"

            # Try to find the failing line and extract variable info
            failing_line = None
            if tb_lines:
                for line in tb_lines:
                    if ".get(" in line and ("site.config" in line or "self.site.config" in line):
                        # Extract just the code line, not the full traceback line
                        if "File" in line:
                            parts = line.split("\n")
                            if len(parts) > 1:
                                failing_line = parts[1].strip()
                        break

            enhanced = [
                error_msg,
                "",
                "Context:",
                "  Expected: dict (site configuration)",
                f"  Got: str (type: {config_type_name})",
            ]

            if failing_line:
                enhanced.append(f"  Failed at: {failing_line}")

            if config_value_preview:
                enhanced.append(f"  Config value: {config_value_preview}")

            enhanced.extend(
                [
                    "",
                    "Likely cause:",
                    "  • Configuration file parsing failed or returned a string",
                    "  • Config was set incorrectly during site initialization",
                    "  • Hot reload may have corrupted config state",
                    "",
                    "How to fix:",
                    "  1. Check bengal.yaml or config/ directory for syntax errors",
                    "  2. Verify config loader is returning a dict, not a string",
                    "  3. Restart dev server to clear corrupted state",
                    "  4. Check for YAML parsing errors in config files",
                ]
            )

            return "\n".join(enhanced)

        # Generic AttributeError with 'get' - might be other dict access
        # Only format traceback if we haven't already
        if tb_lines is None and error.__traceback__ is not None:
            tb_lines = traceback.format_exception(type(error), error, error.__traceback__)

        enhanced = [
            error_msg,
            "",
            "Context:",
            "  - Attempted to call .get() on a string instead of a dict",
            "",
            "How to fix:",
            "  - Check the variable type before calling .get()",
            "  - Ensure the value is a dict, not a string",
        ]

        # Try to find the variable name from traceback (if available)
        if tb_lines:
            for line in tb_lines:
                if ".get(" in line:
                    # Extract the line that failed
                    enhanced.insert(2, f"  - Failed at: {line.strip()}")
                    break

        return "\n".join(enhanced)

        # Return original error message if no enhancement applies
        return error_msg

    def _emit(self, level: LogLevel, message: str, **context: Any) -> None:
        """
        Emit a log event.

        Args:
            level: Log level
            message: Human-readable message
            **context: Additional context data
        """
        # Check if we should emit based on level
        if level.value < self.level.value:
            return

        # Get current phase context
        phase_name = None
        phase_depth = len(self._phase_stack)
        phase_context: dict[str, Any] = {}

        if self._phase_stack:
            phase_name, _, phase_context = self._phase_stack[-1]

        # Merge contexts (explicit context overrides phase context)
        merged_context = {**phase_context, **context}

        # Extract memory metrics from context if present
        memory_mb = merged_context.pop("memory_mb", None)
        peak_memory_mb = merged_context.pop("peak_memory_mb", None)
        duration_ms = merged_context.pop("duration_ms", None)

        # Create event
        event = LogEvent(
            timestamp=datetime.now().isoformat(),
            level=level.name,
            logger_name=self.name,
            event_type=message,  # Use message as event_type (e.g., "phase_start", "discovery_complete")
            message=message,
            phase=phase_name,
            phase_depth=phase_depth,
            duration_ms=duration_ms,
            memory_mb=memory_mb,
            peak_memory_mb=peak_memory_mb,
            context=merged_context,
        )

        # Store event
        self._events.append(event)

        # Output to console (unless suppressed for live progress)
        # Always show WARNING and above, even if quiet_console is True
        show_console = not self.quiet_console or level.value >= LogLevel.WARNING.value

        if show_console:
            # Add visual separation around warnings/errors
            needs_separation = level.value >= LogLevel.WARNING.value

            try:
                # Use Rich console for markup rendering
                from bengal.utils.observability.rich_console import get_console

                console = get_console()
                if needs_separation:
                    console.print()  # Blank line before warning/error
                console.print(event.format_console(verbose=self.verbose))
                if needs_separation:
                    console.print()  # Blank line after warning/error
            except ImportError:
                # Fallback to plain print if Rich not available
                # Strip markup for plain output
                message = event.format_console(verbose=self.verbose)
                # Simple markup stripping (remove [style]...[/style])
                import re

                message = re.sub(r"\[/?[^\]]+\]", "", message)
                if needs_separation:
                    print()  # Blank line before warning/error
                print(message)
                if needs_separation:
                    print()  # Blank line after warning/error

        # Output to file (JSON format)
        if self._file_handle:
            self._file_handle.write(json.dumps(event.to_dict()) + "\n")
            self._file_handle.flush()

    def debug(self, message: str, **context: Any) -> None:
        """Log debug event."""
        self._emit(LogLevel.DEBUG, message, **context)

    def info(self, message: str, **context: Any) -> None:
        """Log info event."""
        self._emit(LogLevel.INFO, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        """Log warning event."""
        self._emit(LogLevel.WARNING, message, **context)

    def error(self, message: str, **context: Any) -> None:
        """Log error event."""
        self._emit(LogLevel.ERROR, message, **context)

    def critical(self, message: str, **context: Any) -> None:
        """Log critical event."""
        self._emit(LogLevel.CRITICAL, message, **context)

    def get_events(self) -> list[LogEvent]:
        """Get all logged events."""
        return self._events.copy()

    def get_phase_timings(self) -> dict[str, float]:
        """
        Extract phase timings from events.

        Returns:
            Dict mapping phase names to duration in milliseconds
        """
        timings = {}
        for event in self._events:
            if event.message == "phase_complete" and event.duration_ms is not None:
                phase = event.context.get("phase_name", event.phase)
                if phase:
                    timings[phase] = event.duration_ms
        return timings

    def print_summary(self) -> None:
        """Print timing summary of all phases."""
        timings = self.get_phase_timings()
        if not timings:
            return

        try:
            from bengal.utils.observability.rich_console import get_console

            console = get_console()

            console.print("\n" + "=" * 60)
            console.print("Build Phase Timings:")
            console.print("=" * 60)

            total = sum(timings.values())
            for phase, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
                percentage = (duration / total * 100) if total > 0 else 0
                console.print(f"  {phase:30s} {duration:8.1f}ms ({percentage:5.1f}%)")

            console.print("-" * 60)
            console.print(f"  {'TOTAL':30s} {total:8.1f}ms (100.0%)")
            console.print("=" * 60)
        except ImportError:
            # Fallback to plain print
            print("\n" + "=" * 60)
            print("Build Phase Timings:")
            print("=" * 60)

            total = sum(timings.values())
            for phase, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
                percentage = (duration / total * 100) if total > 0 else 0
                print(f"  {phase:30s} {duration:8.1f}ms ({percentage:5.1f}%)")

            print("-" * 60)
            console.print(f"  {'TOTAL':30s} {total:8.1f}ms (100.0%)")
            print("=" * 60)

    def close(self) -> None:
        """Close log file handle."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def __enter__(self) -> BengalLogger:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *args: Any) -> None:
        """Context manager exit."""
        self.close()


def truncate_str(s: str, max_len: int = 500, suffix: str = " ... (truncated)") -> str:
    """Truncate a string if it exceeds max_len characters."""
    if len(s) > max_len:
        return s[:max_len] + suffix
    return s


def truncate_error(e: Exception, max_len: int = 500) -> str:
    """Safely truncate an exception string representation."""
    return truncate_str(str(e), max_len, f"\n... (truncated {len(str(e)) - max_len} chars)")


# Global logger registry
_loggers: dict[str, BengalLogger] = {}
_lazy_loggers: dict[str, LazyLogger] = {}  # Cache of proxy objects
_registry_version: int = 0  # Incremented on reset_loggers()


class _GlobalConfig(TypedDict):
    level: LogLevel
    log_file: Path | None
    verbose: bool
    quiet_console: bool


_global_config: _GlobalConfig = {
    "level": LogLevel.INFO,
    "log_file": None,
    "verbose": False,
    "quiet_console": False,
}


def _get_actual_logger(name: str) -> BengalLogger:
    """Internal helper to fetch or create the real logger instance."""
    if name not in _loggers:
        _loggers[name] = BengalLogger(
            name=name,
            level=_global_config["level"],
            log_file=_global_config["log_file"],
            verbose=_global_config["verbose"],
            quiet_console=_global_config["quiet_console"],
        )
    return _loggers[name]


class LazyLogger:
    """
    Transparent proxy for BengalLogger that tracks registry resets.
    
    Module-level `logger = get_logger(__name__)` references hold this proxy.
    When `reset_loggers()` is called, the registry version increments and
    the proxy will fetch a fresh logger on next access.
    
    Attributes:
        _name: The logger name to fetch.
        _real_logger: Cached reference to the actual logger.
        _version: The registry version when the logger was cached.
        
    """

    __slots__ = ("_name", "_real_logger", "_version")

    def __init__(self, name: str):
        self._name = name
        self._real_logger: BengalLogger | None = None
        self._version: int = -1

    @property
    def _logger(self) -> BengalLogger:
        """Fetch the real logger, refreshing if the registry was reset."""
        global _registry_version
        if self._real_logger is None or self._version != _registry_version:
            self._real_logger = _get_actual_logger(self._name)
            self._version = _registry_version
        return self._real_logger

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._logger, attr)

    def __dir__(self) -> list[str]:
        """Support autocomplete by merging proxy and logger attributes."""
        return list(set(super().__dir__()) | set(dir(BengalLogger)))


def configure_logging(
    level: LogLevel = LogLevel.INFO,
    log_file: Path | None = None,
    verbose: bool = False,
    track_memory: bool = False,
) -> None:
    """
    Configure global logging settings.
    
    Args:
        level: Minimum log level to emit
        log_file: Path to log file
        verbose: Show verbose output
        track_memory: Enable memory profiling (adds overhead)
        
    """
    _global_config["level"] = level
    _global_config["log_file"] = log_file
    _global_config["verbose"] = verbose

    # Clear log file if specified (truncate once at start)
    if log_file:
        try:
            # Ensure parent directory exists before truncating
            log_file.parent.mkdir(parents=True, exist_ok=True)
            # Truncate the file to ensure we start fresh
            with open(log_file, "w", encoding="utf-8"):
                pass
        except Exception:
            # Ignore errors (file might not be writable, etc.)
            pass

    # Enable memory tracking if requested
    if track_memory and not tracemalloc.is_tracing():
        tracemalloc.start()

    # Update existing loggers
    for logger in _loggers.values():
        logger.level = level
        logger.verbose = verbose

        # Update log_file for existing loggers if changed
        # This is needed when reusing loggers across test runs with different log files
        if logger.log_file != log_file:
            # Close old file handle if exists
            if logger._file_handle:
                logger._file_handle.close()
                logger._file_handle = None
            logger.log_file = log_file
            # Open new file handle if log_file specified
            if log_file:
                from contextlib import suppress

                with suppress(Exception):
                    log_file.parent.mkdir(parents=True, exist_ok=True)
                logger._file_handle = open(log_file, "a", encoding="utf-8")  # noqa: SIM115


def get_logger(name: str) -> BengalLogger:
    """
    Get a logger proxy for the given name.
    
    Returns a LazyLogger proxy that automatically refreshes when
    reset_loggers() is called. This ensures module-level logger
    references never become stale.
    
    The proxy is cached, so calling get_logger() with the same name
    returns the same proxy instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        LazyLogger proxy (type-compatible with BengalLogger)
        
    """
    if name not in _lazy_loggers:
        _lazy_loggers[name] = LazyLogger(name)
    return _lazy_loggers[name]  # type: ignore[return-value]


def set_console_quiet(quiet: bool = True) -> None:
    """
    Enable or disable console output for all loggers.
    
    Used by live progress manager to suppress structured log events
    while preserving file logging for debugging.
    
    Args:
        quiet: If True, suppress console output; if False, enable it
        
    """
    _global_config["quiet_console"] = quiet

    # Update existing loggers
    for logger in _loggers.values():
        logger.quiet_console = quiet


def close_all_loggers() -> None:
    """Close all logger file handles."""
    for logger in _loggers.values():
        logger.close()


def reset_loggers() -> None:
    """Close all loggers, clear registry, and increment version counter."""
    global _registry_version
    close_all_loggers()
    _loggers.clear()
    _lazy_loggers.clear()  # Also clear proxy cache
    _registry_version += 1
    _global_config["level"] = LogLevel.INFO
    _global_config["log_file"] = None
    _global_config["verbose"] = False
    _global_config["quiet_console"] = False


def print_all_summaries() -> None:
    """Print timing and memory summaries from all loggers."""
    # Merge all events
    all_events = []
    for logger in _loggers.values():
        all_events.extend(logger.get_events())

    # Extract phase timings and memory
    timings = {}
    memory_deltas = {}
    peak_memories = {}

    for event in all_events:
        if event.message == "phase_complete":
            phase = event.context.get("phase_name", event.phase)
            if phase:
                if event.duration_ms is not None:
                    timings[phase] = event.duration_ms
                if event.memory_mb is not None:
                    memory_deltas[phase] = event.memory_mb
                if event.peak_memory_mb is not None:
                    peak_memories[phase] = event.peak_memory_mb

    if not timings:
        return

    try:
        from bengal.utils.observability.rich_console import get_console

        console = get_console()

        console.print("\n" + "=" * 70)
        console.print("[bold cyan]Build Phase Performance:[/bold cyan]")
        console.print("=" * 70)

        # Show timing + memory
        total_time = sum(timings.values())
        for phase in sorted(timings.keys(), key=lambda x: timings[x], reverse=True):
            duration = timings[phase]
            percentage = (duration / total_time * 100) if total_time > 0 else 0

            line = f"  {phase:25s} {duration:8.1f}ms ({percentage:5.1f}%)"

            # Add memory if available
            if phase in memory_deltas:
                mem_delta = memory_deltas[phase]
                line += f"  Δ{mem_delta:+7.1f}MB"
            if phase in peak_memories:
                peak = peak_memories[phase]
                line += f"  peak:{peak:7.1f}MB"

            console.print(line)

        console.print("-" * 70)
        total_line = f"  {'TOTAL':25s} {total_time:8.1f}ms (100.0%)"
        if memory_deltas:
            total_mem = sum(memory_deltas.values())
            total_line += f"  Δ{total_mem:+7.1f}MB"
        console.print(total_line)
        console.print("=" * 70)
    except ImportError:
        # Fallback to plain print
        print("\n" + "=" * 70)
        print("Build Phase Performance:")
        print("=" * 70)

        # Show timing + memory
        total_time = sum(timings.values())
        for phase in sorted(timings.keys(), key=lambda x: timings[x], reverse=True):
            duration = timings[phase]
            percentage = (duration / total_time * 100) if total_time > 0 else 0

            line = f"  {phase:25s} {duration:8.1f}ms ({percentage:5.1f}%)"

            # Add memory if available
            if phase in memory_deltas:
                mem_delta = memory_deltas[phase]
                line += f"  Δ{mem_delta:+7.1f}MB"
            if phase in peak_memories:
                peak = peak_memories[phase]
                line += f"  peak:{peak:7.1f}MB"

            print(line)

        print("-" * 70)
        total_line = f"  {'TOTAL':25s} {total_time:8.1f}ms (100.0%)"
        if memory_deltas:
            total_mem = sum(memory_deltas.values())
            total_line += f"  Δ{total_mem:+7.1f}MB"
        print(total_line)
        print("=" * 70)
