"""
Server backend abstraction for Bengal dev server.

Uses Pounce ASGI as the HTTP backend.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

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
    output_dir: Path | Callable[[], Path],
    build_in_progress: Callable[[], bool],
    active_palette: Callable[[], str | None] | None = None,
    request_callback: Callable[[], Callable[[str, str, int, float], None] | None] | None = None,
) -> PounceBackend:
    """
    Create a PounceBackend serving the Bengal dev ASGI app.

    Args:
        host: Bind address
        port: Port to bind to
        output_dir: Directory for static file serving, or callable returning
            the current active directory (for double-buffered output)
        build_in_progress: Callable returning True when a build is active
        active_palette: Callable returning current palette (or None)
        request_callback: Optional getter returning request log callback. When set,
            Pounce access logs are disabled and Bengal logs document requests.

    Returns:
        Configured backend (not started)
    """
    from pounce import ServerConfig
    from pounce.server import Server

    from bengal.server.asgi_app import create_bengal_dev_app

    app = create_bengal_dev_app(
        output_dir=output_dir,
        build_in_progress=build_in_progress,
        active_palette=active_palette,
        request_callback=request_callback,
    )
    # Disable compression for dev server: SSE live reload must stream immediately.
    # Compression can buffer chunks and delay EventSource delivery; Pounce skips
    # text/event-stream but we avoid it entirely for dev to ensure reliable reload.
    config = ServerConfig(
        host=host,
        port=port,
        access_log=request_callback is None,
        compression=False,
        debug=True,
        shutdown_timeout=5.0,
    )
    server = Server(config, app)
    return PounceBackend(server, port)


def create_pounce_preview_backend(
    host: str,
    port: int,
    output_dir: Path,
) -> PounceBackend:
    """
    Create a PounceBackend for production-like static preview serving.

    Preview serving has no live reload or build-aware routing: the completed
    output directory is mounted as a Pounce static root and Bengal only handles
    fallback responses such as custom 404 pages.
    """
    from pounce import ServerConfig
    from pounce.server import Server

    from bengal.server.asgi_app import create_bengal_preview_app

    app = create_bengal_preview_app(output_dir=output_dir)
    config = ServerConfig(
        host=host,
        port=port,
        access_log=True,
        compression=True,
        debug=False,
        health_check_path="/__bengal_pounce_health__",
        shutdown_timeout=5.0,
    )
    server = Server(config, app)
    return PounceBackend(server, port)
