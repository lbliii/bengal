"""
Server backend abstraction for Bengal dev server.

Allows swapping HTTP implementations (current: ThreadingTCPServer,
future: Pounce ASGI) without changing DevServer orchestration.
"""

from __future__ import annotations

import socketserver
from functools import partial
from typing import Protocol

from bengal.server.request_handler import BengalRequestHandler


class ServerBackend(Protocol):
    """Protocol for dev server HTTP backends (current: TCPServer, future: Pounce)."""

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


class ThreadingTCPServerBackend:
    """Backend wrapping socketserver.ThreadingTCPServer with BengalRequestHandler."""

    def __init__(self, httpd: socketserver.ThreadingTCPServer, port: int) -> None:
        self._httpd = httpd
        self._port = port

    def start(self) -> None:
        """Run serve_forever (blocks until shutdown)."""
        self._httpd.serve_forever()

    def shutdown(self) -> None:
        """Stop the server and close the socket."""
        self._httpd.shutdown()
        self._httpd.server_close()

    @property
    def port(self) -> int:
        """Port the server is bound to."""
        return self._port


def create_threading_tcp_backend(
    host: str,
    port: int,
    output_dir: str,
) -> ThreadingTCPServerBackend:
    """
    Create a ThreadingTCPServerBackend bound to the given host and port.

    Args:
        host: Bind address
        port: Port to bind to
        output_dir: Directory for static file serving

    Returns:
        Configured backend (not started)
    """
    socketserver.TCPServer.allow_reuse_address = True

    class BengalThreadingTCPServer(socketserver.ThreadingTCPServer):
        request_queue_size = 128

    handler = partial(BengalRequestHandler, directory=output_dir)
    httpd = BengalThreadingTCPServer((host, port), handler)
    httpd.daemon_threads = True

    return ThreadingTCPServerBackend(httpd, port)
