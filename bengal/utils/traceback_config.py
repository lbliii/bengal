"""
Backward compatibility shim - import from bengal.errors.traceback instead.

This module re-exports from bengal.errors.traceback.config for backward compatibility.
New code should import directly from bengal.errors.traceback.
"""

from bengal.errors.traceback.config import (
    DEFAULT_SUPPRESS,
    TracebackConfig,
    TracebackStyle,
    apply_file_traceback_to_env,
    map_debug_flag_to_traceback,
    set_effective_style_from_cli,
)

__all__ = [
    "TracebackConfig",
    "TracebackStyle",
    "DEFAULT_SUPPRESS",
    "set_effective_style_from_cli",
    "map_debug_flag_to_traceback",
    "apply_file_traceback_to_env",
]
