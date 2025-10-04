"""
Structured logging system for Bengal SSG.

Provides phase-aware logging with context propagation, timing,
and structured event emission. Designed for observability into
the 22-phase build pipeline.

Example:
    from bengal.utils.logger import get_logger
    
    logger = get_logger(__name__)
    
    with logger.phase("discovery", page_count=100):
        logger.info("discovered_content", files=len(files))
        logger.debug("parsed_frontmatter", page=page.path, keys=list(metadata.keys()))
"""

import json
import time
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO
from dataclasses import dataclass, field, asdict
from enum import Enum


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
    phase: Optional[str] = None
    phase_depth: int = 0
    duration_ms: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def format_console(self, verbose: bool = False) -> str:
        """Format for console output."""
        indent = "  " * self.phase_depth
        
        # Color codes
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m',
            'BOLD': '\033[1m',
            'DIM': '\033[2m',
        }
        
        # Phase markers
        if self.phase:
            phase_marker = f" {colors['BOLD']}[{self.phase}]{colors['RESET']}"
        else:
            phase_marker = ""
        
        # Timing
        if self.duration_ms is not None:
            timing = f" {colors['DIM']}({self.duration_ms:.1f}ms){colors['RESET']}"
        else:
            timing = ""
        
        # Level color
        level_color = colors.get(self.level, colors['RESET'])
        
        # Basic format
        base = f"{indent}{level_color}●{colors['RESET']}{phase_marker} {self.message}{timing}"
        
        if verbose:
            # Add context in verbose mode
            if self.context:
                context_str = " " + " ".join(f"{k}={v}" for k, v in self.context.items())
                base += f"{colors['DIM']}{context_str}{colors['RESET']}"
            
            # Add timestamp in verbose mode
            time_str = self.timestamp.split('T')[1].split('.')[0]  # HH:MM:SS
            base = f"{colors['DIM']}{time_str}{colors['RESET']} {base}"
        
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
        log_file: Optional[Path] = None,
        verbose: bool = False
    ):
        """
        Initialize logger.
        
        Args:
            name: Logger name (typically __name__)
            level: Minimum log level to emit
            log_file: Path to log file (optional)
            verbose: Whether to show verbose output
        """
        self.name = name
        self.level = level
        self.log_file = log_file
        self.verbose = verbose
        
        # Phase tracking
        self._phase_stack: List[tuple[str, float, Dict[str, Any]]] = []
        self._events: List[LogEvent] = []
        
        # File handle
        self._file_handle: Optional[TextIO] = None
        if log_file:
            self._file_handle = open(log_file, 'w', encoding='utf-8')
    
    @contextmanager
    def phase(self, name: str, **context):
        """
        Context manager for tracking build phases.
        
        Example:
            with logger.phase("discovery", page_count=100):
                # ... work ...
                pass
        
        Args:
            name: Phase name
            **context: Additional context to attach to all events in phase
        """
        start_time = time.time()
        self._phase_stack.append((name, start_time, context))
        
        # Emit phase start
        self.info(f"phase_start", phase_name=name, **context)
        
        try:
            yield
        except Exception as e:
            # Emit phase error
            self.error(f"phase_error", phase_name=name, error=str(e), **context)
            raise
        finally:
            # Pop phase and emit completion
            phase_name, phase_start, phase_context = self._phase_stack.pop()
            duration_ms = (time.time() - phase_start) * 1000
            
            self.info(
                f"phase_complete",
                phase_name=phase_name,
                duration_ms=duration_ms,
                **phase_context
            )
    
    def _emit(self, level: LogLevel, event_type: str, message: str, **context):
        """
        Emit a log event.
        
        Args:
            level: Log level
            event_type: Event type identifier
            message: Human-readable message
            **context: Additional context data
        """
        # Check if we should emit based on level
        if level.value < self.level.value:
            return
        
        # Get current phase context
        phase_name = None
        phase_depth = len(self._phase_stack)
        phase_context = {}
        
        if self._phase_stack:
            phase_name, _, phase_context = self._phase_stack[-1]
        
        # Merge contexts (explicit context overrides phase context)
        merged_context = {**phase_context, **context}
        
        # Create event
        event = LogEvent(
            timestamp=datetime.now().isoformat(),
            level=level.name,
            logger_name=self.name,
            event_type=message,  # Use message as event_type (e.g., "phase_start", "discovery_complete")
            message=message,
            phase=phase_name,
            phase_depth=phase_depth,
            context=merged_context
        )
        
        # Store event
        self._events.append(event)
        
        # Output to console
        print(event.format_console(verbose=self.verbose))
        
        # Output to file (JSON format)
        if self._file_handle:
            self._file_handle.write(json.dumps(event.to_dict()) + '\n')
            self._file_handle.flush()
    
    def debug(self, message: str, **context):
        """Log debug event."""
        self._emit(LogLevel.DEBUG, "debug", message, **context)
    
    def info(self, message: str, **context):
        """Log info event."""
        self._emit(LogLevel.INFO, "info", message, **context)
    
    def warning(self, message: str, **context):
        """Log warning event."""
        self._emit(LogLevel.WARNING, "warning", message, **context)
    
    def error(self, message: str, **context):
        """Log error event."""
        self._emit(LogLevel.ERROR, "error", message, **context)
    
    def critical(self, message: str, **context):
        """Log critical event."""
        self._emit(LogLevel.CRITICAL, "critical", message, **context)
    
    def get_events(self) -> List[LogEvent]:
        """Get all logged events."""
        return self._events.copy()
    
    def get_phase_timings(self) -> Dict[str, float]:
        """
        Extract phase timings from events.
        
        Returns:
            Dict mapping phase names to duration in milliseconds
        """
        timings = {}
        for event in self._events:
            if event.message == "phase_complete" and "duration_ms" in event.context:
                phase = event.context.get("phase_name", event.phase)
                if phase:
                    timings[phase] = event.context["duration_ms"]
        return timings
    
    def print_summary(self):
        """Print timing summary of all phases."""
        timings = self.get_phase_timings()
        if not timings:
            return
        
        print("\n" + "="*60)
        print("Build Phase Timings:")
        print("="*60)
        
        total = sum(timings.values())
        for phase, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
            percentage = (duration / total * 100) if total > 0 else 0
            print(f"  {phase:30s} {duration:8.1f}ms ({percentage:5.1f}%)")
        
        print("-"*60)
        print(f"  {'TOTAL':30s} {total:8.1f}ms (100.0%)")
        print("="*60)
    
    def close(self):
        """Close log file handle."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


# Global logger registry
_loggers: Dict[str, BengalLogger] = {}
_global_config = {
    'level': LogLevel.INFO,
    'log_file': None,
    'verbose': False,
}


def configure_logging(
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[Path] = None,
    verbose: bool = False
):
    """
    Configure global logging settings.
    
    Args:
        level: Minimum log level to emit
        log_file: Path to log file
        verbose: Show verbose output
    """
    _global_config['level'] = level
    _global_config['log_file'] = log_file
    _global_config['verbose'] = verbose
    
    # Update existing loggers
    for logger in _loggers.values():
        logger.level = level
        logger.verbose = verbose
        
        # Note: We don't update log_file for existing loggers
        # to avoid closing/reopening files mid-build


def get_logger(name: str) -> BengalLogger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        BengalLogger instance
    """
    if name not in _loggers:
        _loggers[name] = BengalLogger(
            name=name,
            level=_global_config['level'],
            log_file=_global_config['log_file'],
            verbose=_global_config['verbose']
        )
    
    return _loggers[name]


def close_all_loggers():
    """Close all logger file handles."""
    for logger in _loggers.values():
        logger.close()


def print_all_summaries():
    """Print timing summaries from all loggers."""
    # Merge all events
    all_events = []
    for logger in _loggers.values():
        all_events.extend(logger.get_events())
    
    # Extract phase timings
    timings = {}
    for event in all_events:
        if event.message == "phase_complete" and "duration_ms" in event.context:
            phase = event.context.get("phase_name", event.phase)
            if phase:
                timings[phase] = event.context["duration_ms"]
    
    if not timings:
        return
    
    print("\n" + "="*60)
    print("Build Phase Timings:")
    print("="*60)
    
    total = sum(timings.values())
    for phase, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
        percentage = (duration / total * 100) if total > 0 else 0
        print(f"  {phase:30s} {duration:8.1f}ms ({percentage:5.1f}%)")
    
    print("-"*60)
    print(f"  {'TOTAL':30s} {total:8.1f}ms (100.0%)")
    print("="*60)

