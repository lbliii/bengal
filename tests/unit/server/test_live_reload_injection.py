from __future__ import annotations

import pytest

pytest.skip(
    "HTML injection path removed in Phase 3; live reload via template include",
    allow_module_level=True,
)
"""Tests for HTML live reload injection and SSE notify flow."""

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
        self.requestline = "GET /index.html HTTP/1.1"

    # Bypass filesystem translation and return our test file path
    def translate_path(self, path: str) -> str:  # type: ignore[override]
        return self._file_path

    # Stub HTTP response methods for testing
    def send_response(self, code: int) -> None:
        """Stub - we're testing content, not HTTP mechanics."""
        pass

    def send_header(self, keyword: str, value: str) -> None:
        """Stub - we're testing content, not HTTP mechanics."""
        pass

    def end_headers(self) -> None:
        """Stub - we're testing content, not HTTP mechanics."""
        pass


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
