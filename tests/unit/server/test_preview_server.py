"""Tests for the production-like preview server wrapper."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bengal.errors import BengalServerError
from bengal.server.preview_server import PreviewServer


class FakeBackend:
    def __init__(self) -> None:
        self.started = False
        self.shutdown_called = False

    def start(self) -> None:
        self.started = True

    def shutdown(self) -> None:
        self.shutdown_called = True


def test_preview_server_starts_pounce_backend(monkeypatch, tmp_path) -> None:
    """PreviewServer starts a Pounce preview backend for the output directory."""
    (tmp_path / "index.html").write_text("ok")
    site = SimpleNamespace(output_dir=tmp_path)
    backend = FakeBackend()
    calls = []

    def fake_backend(**kwargs):
        calls.append(kwargs)
        return backend

    monkeypatch.setattr("bengal.server.preview_server.create_pounce_preview_backend", fake_backend)

    server = PreviewServer(site, host="127.0.0.1", port=0, open_browser=False)
    server.start()

    assert backend.started is True
    assert calls == [{"host": "127.0.0.1", "port": 0, "output_dir": tmp_path}]


def test_preview_server_requires_existing_output(tmp_path) -> None:
    """PreviewServer fails clearly when the output directory is missing."""
    site = SimpleNamespace(output_dir=tmp_path / "public")
    server = PreviewServer(site, host="127.0.0.1", port=0, open_browser=False)

    with pytest.raises(BengalServerError) as exc:
        server.start()

    assert "Preview output directory does not exist" in str(exc.value)
    assert "bengal preview" in exc.value.suggestion
