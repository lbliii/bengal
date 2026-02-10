"""Server composition wiring helpers."""

from __future__ import annotations

from bengal.protocols import ReloadControllerProtocol


def get_reload_controller() -> ReloadControllerProtocol:
    """Return the default reload controller singleton for composition wiring."""
    from bengal.server.reload_controller import controller

    return controller
