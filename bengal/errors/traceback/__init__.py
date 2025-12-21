"""
Traceback rendering and configuration.

Provides configurable traceback formatting for different verbosity styles:
- full: Complete traceback with locals
- compact: Focused traceback with context-aware help
- minimal: One-line error with hint
- off: Standard Python traceback

Usage:
    from bengal.errors.traceback import TracebackConfig, TracebackStyle

    config = TracebackConfig.from_environment()
    config.install()  # Install Rich traceback handler
    renderer = config.get_renderer()
    renderer.display_exception(error)
"""

from __future__ import annotations

from bengal.errors.traceback.config import (
    DEFAULT_SUPPRESS,
    TracebackConfig,
    TracebackStyle,
    apply_file_traceback_to_env,
    map_debug_flag_to_traceback,
    set_effective_style_from_cli,
)
from bengal.errors.traceback.renderer import (
    CompactTracebackRenderer,
    FullTracebackRenderer,
    MinimalTracebackRenderer,
    OffTracebackRenderer,
    TracebackRenderer,
)

__all__ = [
    # Config
    "TracebackConfig",
    "TracebackStyle",
    "DEFAULT_SUPPRESS",
    "set_effective_style_from_cli",
    "map_debug_flag_to_traceback",
    "apply_file_traceback_to_env",
    # Renderers
    "TracebackRenderer",
    "FullTracebackRenderer",
    "CompactTracebackRenderer",
    "MinimalTracebackRenderer",
    "OffTracebackRenderer",
]
