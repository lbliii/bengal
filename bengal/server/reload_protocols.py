"""
Protocols for live reload notification.

Defines ReloadNotifier for dependency injection, enabling tests to use
no-op or mock implementations.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class ReloadNotifier(Protocol):
    """Protocol for notifying clients of reload events."""

    def send(
        self,
        action: str,
        reason: str,
        changed_paths: Sequence[str],
    ) -> None:
        """Send a reload event to connected clients.

        Args:
            action: Reload type ('reload', 'reload-css', 'reload-page', 'none')
            reason: Machine-readable reason (e.g., 'css-only', 'content-changed')
            changed_paths: Changed output paths relative to output directory.
        """
        ...
