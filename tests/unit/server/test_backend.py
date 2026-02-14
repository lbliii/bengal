"""
Tests for the server backend abstraction (PounceBackend, ThreadingTCPServerBackend).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.backend import (
    PounceBackend,
    ThreadingTCPServerBackend,
    create_pounce_backend,
    create_threading_tcp_backend,
)


def test_backend_port_property() -> None:
    """ThreadingTCPServerBackend.port returns the configured port."""
    mock_httpd = MagicMock()
    backend = ThreadingTCPServerBackend(mock_httpd, 5173)
    assert backend.port == 5173


def test_backend_shutdown_calls_httpd_shutdown_and_close() -> None:
    """ThreadingTCPServerBackend.shutdown() calls httpd.shutdown() and server_close()."""
    mock_httpd = MagicMock()
    backend = ThreadingTCPServerBackend(mock_httpd, 0)
    backend.shutdown()
    mock_httpd.shutdown.assert_called_once()
    mock_httpd.server_close.assert_called_once()


def test_backend_start_calls_serve_forever() -> None:
    """ThreadingTCPServerBackend.start() delegates to httpd.serve_forever()."""
    mock_httpd = MagicMock()
    backend = ThreadingTCPServerBackend(mock_httpd, 0)
    backend.start()
    mock_httpd.serve_forever.assert_called_once()


def test_create_pounce_backend_returns_backend(tmp_path: Path) -> None:
    """create_pounce_backend returns a PounceBackend with expected port."""
    backend = create_pounce_backend(
        host="127.0.0.1",
        port=8080,
        output_dir=tmp_path,
        build_in_progress=lambda: False,
        active_palette=lambda: None,
    )
    assert isinstance(backend, PounceBackend)
    assert backend.port == 8080


def test_pounce_backend_shutdown_calls_server_shutdown() -> None:
    """PounceBackend.shutdown() calls server.shutdown()."""
    mock_server = MagicMock()
    backend = PounceBackend(mock_server, 5173)
    backend.shutdown()
    mock_server.shutdown.assert_called_once()


@patch("bengal.server.backend.socketserver.ThreadingTCPServer", MagicMock())
def test_create_threading_tcp_backend_returns_backend(tmp_path: Path) -> None:
    """create_threading_tcp_backend returns a ThreadingTCPServerBackend with expected port."""
    backend = create_threading_tcp_backend(
        host="127.0.0.1",
        port=8080,
        output_dir=str(tmp_path),
    )
    assert isinstance(backend, ThreadingTCPServerBackend)
    assert backend.port == 8080
