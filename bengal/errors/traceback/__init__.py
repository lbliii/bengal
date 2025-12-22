"""
Traceback rendering and configuration.

This subpackage provides configurable traceback formatting for different
verbosity levels, integrating with Rich for enhanced display and Bengal's
context-aware error handlers.

Verbosity Styles
================

**full**
    Complete traceback with local variables. Best for deep debugging.
    Uses Rich's full exception rendering when available.

**compact** (default)
    Focused traceback showing last 3 frames with context-aware help.
    Shows error type, message, and actionable suggestions.

**minimal**
    One-line error with location and hint. Best for CI/CD output
    or when errors are expected and just need quick identification.

**off**
    Standard Python traceback. Uses default ``traceback.print_exc()``.
    Useful when Rich is not desired or for compatibility.

Configuration
=============

Traceback style can be configured via:

1. **Environment Variable**: ``BENGAL_TRACEBACK=compact|full|minimal|off``
2. **CLI Flag**: ``--traceback=full``
3. **Site Config**: ``dev.traceback.style`` in config YAML

Additional environment variables:

- ``BENGAL_TRACEBACK_SHOW_LOCALS``: Show local variables (1/true/yes)
- ``BENGAL_TRACEBACK_MAX_FRAMES``: Maximum frames to show
- ``BENGAL_TRACEBACK_SUPPRESS``: Comma-separated modules to suppress

Components
==========

**TracebackConfig**
    Configuration dataclass with style, show_locals, max_frames, suppress.
    Use ``TracebackConfig.from_environment()`` to load from env vars.

**TracebackStyle**
    Enum of available styles: FULL, COMPACT, MINIMAL, OFF.

**TracebackRenderer**
    Base class for style-specific renderers. Subclasses: FullTracebackRenderer,
    CompactTracebackRenderer, MinimalTracebackRenderer, OffTracebackRenderer.

Usage
=====

Install Rich traceback handler::

    from bengal.errors.traceback import TracebackConfig

    config = TracebackConfig.from_environment()
    config.install()  # Install Rich global handler

Display an exception manually::

    from bengal.errors.traceback import TracebackConfig

    config = TracebackConfig.from_environment()
    renderer = config.get_renderer()
    renderer.display_exception(error)

See Also
========

- ``bengal/errors/handlers.py`` - Context-aware help used by renderers
- ``bengal/cli/`` - CLI integration
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
