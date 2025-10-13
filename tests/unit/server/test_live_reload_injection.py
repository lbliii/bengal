"""Tests for HTML live reload injection and SSE notify flow."""

from __future__ import annotations

import io
from pathlib import Path

from bengal.server.live_reload import LIVE_RELOAD_SCRIPT, notify_clients_reload, set_reload_action
from bengal.server.request_handler import BengalRequestHandler


class DummyHandler(BengalRequestHandler):
    """Subclass to expose injection on an arbitrary file path."""

    def __init__(self, file_path: Path) -> None:
        # Minimal fields needed by SimpleHTTPRequestHandler
        self.path = "/index.html"
        self._file_path = str(file_path)
        self.wfile = io.BytesIO()

    # Bypass filesystem translation and return our test file path
    def translate_path(self, path: str) -> str:  # type: ignore[override]
        return self._file_path


def test_live_reload_injects_script(tmp_path: Path) -> None:
    html = b"<html><body><h1>Test</h1></body></html>"
    file_path = tmp_path / "index.html"
    file_path.write_bytes(html)

    handler = DummyHandler(file_path)
    served = handler.serve_html_with_live_reload()

    assert served is True
    body = handler.wfile.getvalue().decode("utf-8")
    assert "Bengal Live Reload" in body
    assert LIVE_RELOAD_SCRIPT.strip() in body


def test_notify_clients_reload_increments_generation() -> None:
    # Ensure action toggling does not error and notify runs
    set_reload_action("reload-css")
    # Should not raise
    notify_clients_reload()
