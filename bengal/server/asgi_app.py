"""
ASGI application skeleton for Bengal dev server.

Provides create_bengal_dev_app() for Pounce/ASGI backends. Full implementation
(static files, HTML injection, SSE) will be added during Pounce wiring phase.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

# ASGI app type: async (scope, receive, send) -> None
ASGIApp = Callable[..., Any]


def create_bengal_dev_app(
    *,
    output_dir: Path,
    build_in_progress: Callable[[], bool],
    active_palette: str | None = None,
) -> ASGIApp:
    """
    Create an ASGI app for Bengal dev server.

    Skeleton implementation: handles GET /__bengal_reload__ with a placeholder,
    returns 404 for all other paths. Static serving and full SSE will be added
    when wiring Pounce.

    Args:
        output_dir: Directory for static file serving (used when wired)
        build_in_progress: Callable returning True when a build is active
        active_palette: Theme for rebuilding page styling (used when wired)

    Returns:
        ASGI application callable
    """

    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            return

        method = scope.get("method", "")
        path = scope.get("path", "")

        if method == "GET" and path == "/__bengal_reload__":
            # Placeholder: return 501 until SSE is wired
            await send(
                {
                    "type": "http.response.start",
                    "status": 501,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"SSE not yet implemented (Pounce wiring pending)",
                }
            )
            return

        # All other paths: 404 until static serving is wired
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"Not Found",
            }
        )

    return app
