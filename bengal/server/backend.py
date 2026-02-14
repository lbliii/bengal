"""
Server backend abstraction for Bengal dev server.

Uses Pounce ASGI as the HTTP backend.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pounce.server import Server


class ServerBackend(Protocol):
    """Protocol for dev server HTTP backends (Pounce ASGI, legacy: TCPServer)."""

    def start(self) -> None:
        """Start the server (blocks until shutdown)."""
        ...

    def shutdown(self) -> None:
        """Stop the server and release resources."""
        ...

    @property
    def port(self) -> int:
        """Port the server is bound to."""
        ...


class PounceBackend:
    """Backend that runs the Bengal dev ASGI app via Pounce."""

    def __init__(self, server: Server, port: int) -> None:
        self._server = server
        self._port = port

    def start(self) -> None:
        """Run Pounce (blocks until shutdown)."""
        self._server.run()

    def shutdown(self) -> None:
        """Trigger graceful shutdown with connection draining."""
        self._server.shutdown()

    @property
    def port(self) -> int:
        return self._port


def create_pounce_backend(
    host: str,
    port: int,
    output_dir: Path,
    build_in_progress: Callable[[], bool],
    active_palette: Callable[[], str | None] | None = None,
) -> PounceBackend:
    """
    Create a PounceBackend serving the Bengal dev ASGI app.

    Args:
        host: Bind address
        port: Port to bind to
        output_dir: Directory for static file serving
        build_in_progress: Callable returning True when a build is active
        active_palette: Callable returning current palette (or None)

    Returns:
        Configured backend (not started)
    """
    from pounce import ServerConfig
    from pounce.server import Server

    from bengal.server.asgi_app import create_bengal_dev_app

    def _skip_sse_in_access_log(_method: str, path: str, _status: int) -> bool:
        return path != "/__bengal_reload__"

    app = create_bengal_dev_app(
        output_dir=output_dir,
        build_in_progress=build_in_progress,
        active_palette=active_palette,
    )
    config = ServerConfig(
        host=host,
        port=port,
        access_log=True,
        access_log_filter=_skip_sse_in_access_log,
        compression=True,
        debug=True,
        shutdown_timeout=5.0,
    )
    server = Server(config, app)
    return PounceBackend(server, port)
