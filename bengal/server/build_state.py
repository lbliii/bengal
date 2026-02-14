"""
Shared build state for Bengal dev server.

Decouples build_in_progress and active_palette for the ASGI app and build trigger.
"""

from __future__ import annotations

import threading


class BuildState:
    """
    Thread-safe shared state for build progress and palette.

    Used by create_bengal_dev_app (ASGI) and BuildTrigger.
    Written by BuildTrigger and DevServer.
    """

    def __init__(self) -> None:
        self._build_in_progress = False
        self._active_palette: str | None = None
        self._lock = threading.Lock()

    def set_build_in_progress(self, in_progress: bool) -> None:
        """Set build-in-progress flag (True when build starts, False when done)."""
        with self._lock:
            self._build_in_progress = in_progress

    def get_build_in_progress(self) -> bool:
        """Get build-in-progress flag."""
        with self._lock:
            return self._build_in_progress

    def set_active_palette(self, palette: str | None) -> None:
        """Set active palette for rebuilding page styling."""
        with self._lock:
            self._active_palette = palette

    def get_active_palette(self) -> str | None:
        """Get active palette."""
        with self._lock:
            return self._active_palette


# Module-level registry - single source of truth for dev server build state
build_state = BuildState()
