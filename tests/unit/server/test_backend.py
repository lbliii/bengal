"""
Tests for the server backend abstraction (PounceBackend).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.server.backend import PounceBackend, create_pounce_backend


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


def test_pounce_backend_start_calls_server_run() -> None:
    """PounceBackend.start() delegates to server.run()."""
    mock_server = MagicMock()
    backend = PounceBackend(mock_server, 8080)
    backend.start()
    mock_server.run.assert_called_once()
