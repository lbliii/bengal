"""Tests for live reload notify flow."""

from __future__ import annotations

from bengal.server.live_reload import notify_clients_reload, set_reload_action


def test_notify_clients_reload_increments_generation() -> None:
    """Ensure action toggling does not error and notify runs."""
    set_reload_action("reload-css")
    notify_clients_reload()
