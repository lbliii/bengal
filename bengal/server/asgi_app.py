"""
Chirp ASGI application for Bengal dev server.

Replaces the legacy ThreadingTCPServer + BengalRequestHandler stack with
a Chirp web app served by Pounce. Provides the same feature set:

- Static file serving (via Chirp StaticFiles middleware)
- SSE live reload endpoint (via Chirp EventStream)
- HTML live reload script injection (via HtmlInjectionMiddleware)
- Build-in-progress gate page (via BuildGateMiddleware)
- Custom 404 pages

Architecture:
    build_trigger.py
         |
    DevState (thread-safe shared state)
         |
    Chirp ASGI App
         |--- BuildGateMiddleware (outermost: returns rebuilding page during builds)
         |--- HtmlInjectionMiddleware (injects live reload <script> into HTML)
         |--- StaticFiles (serves output directory)
         |--- SSE route (/__bengal_reload__: pushes reload events to browser)

Threading Model:
    DevState bridges the sync build pipeline (build_trigger runs in a thread)
    to the async ASGI world (Chirp handlers run in the Pounce event loop).
    Uses asyncio.Queue per SSE client with loop.call_soon_threadsafe for
    thread-safe event delivery.

Related:
    - bengal/server/dev_server.py: Creates and runs the ASGI app via Pounce
    - bengal/server/build_trigger.py: Signals build state via DevState
    - bengal/server/live_reload.py: LIVE_RELOAD_SCRIPT, send_reload_payload
    - bengal/server/request_handler.py: get_rebuilding_page_html (reused)

"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chirp import App, EventStream, SSEEvent
from chirp.http.request import Request
from chirp.http.response import Response
from chirp.middleware.protocol import AnyResponse, Next
from chirp.middleware.static import StaticFiles

from bengal.server.constants import LIVE_RELOAD_PATH
from bengal.server.live_reload import LIVE_RELOAD_SCRIPT
from bengal.server.request_handler import get_rebuilding_page_html
from bengal.server.utils import find_html_injection_point
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# DevState: thread-safe shared state between build pipeline and ASGI app
# ---------------------------------------------------------------------------

_SENTINEL = object()


@dataclass
class DevState:
    """Shared mutable state for the Bengal dev server.

    Bridges the synchronous build pipeline (BuildTrigger runs in a thread)
    to the asynchronous ASGI world (Chirp SSE handlers run in the event loop).

    Thread Safety:
        All public methods are thread-safe. The build pipeline calls
        ``set_build_in_progress`` and ``broadcast_reload`` from worker threads;
        SSE handlers call ``subscribe``/``unsubscribe`` from the async loop.
    """

    # Build state
    _build_in_progress: bool = field(default=False, repr=False)
    _build_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    active_palette: str | None = field(default=None)

    # SSE broadcast
    _clients: set[asyncio.Queue[str]] = field(default_factory=set, repr=False)
    _clients_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _loop: asyncio.AbstractEventLoop | None = field(default=None, repr=False)

    @property
    def build_in_progress(self) -> bool:
        with self._build_lock:
            return self._build_in_progress

    def set_build_in_progress(self, value: bool) -> None:
        """Update build state. Called from build trigger thread."""
        with self._build_lock:
            self._build_in_progress = value
        logger.debug("build_state_changed", in_progress=value)

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the event loop for thread-safe SSE delivery."""
        self._loop = loop

    def broadcast_reload(self, payload: str) -> None:
        """Push a reload event to all connected SSE clients.

        Thread-safe: called from the build trigger thread, delivers
        to async queues via ``loop.call_soon_threadsafe``.
        """
        with self._clients_lock:
            clients = set(self._clients)

        loop = self._loop
        if loop is None or not clients:
            return

        import contextlib

        for queue in clients:
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(queue.put_nowait, payload)

        logger.debug("sse_broadcast_sent", client_count=len(clients), payload_len=len(payload))

    def subscribe(self) -> asyncio.Queue[str]:
        """Create a new SSE client subscription queue."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        with self._clients_lock:
            self._clients.add(queue)
        logger.info("sse_client_subscribed", total_clients=len(self._clients))
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        """Remove an SSE client subscription."""
        with self._clients_lock:
            self._clients.discard(queue)
        logger.info("sse_client_unsubscribed", total_clients=len(self._clients))


# Module-level singleton — set by create_dev_app(), read by build_trigger
_dev_state: DevState | None = None


def get_dev_state() -> DevState | None:
    """Get the active DevState singleton (None if dev server not running)."""
    return _dev_state


# ---------------------------------------------------------------------------
# HtmlInjectionMiddleware
# ---------------------------------------------------------------------------


class HtmlInjectionMiddleware:
    """Injects the live reload ``<script>`` into HTML responses.

    Inspects the response from downstream middleware (typically StaticFiles).
    If the response body is HTML, injects ``LIVE_RELOAD_SCRIPT`` before
    ``</body>`` or ``</html>``.

    Skips injection for:
    - Non-HTML content types
    - The SSE endpoint itself
    - Non-200 responses (error pages have their own scripts)
    """

    __slots__ = ("_script_bytes",)

    def __init__(self, script: str = LIVE_RELOAD_SCRIPT) -> None:
        self._script_bytes = script.encode("utf-8")

    async def __call__(self, request: Request, next: Next) -> AnyResponse:
        # Never inject into the SSE stream
        if request.path == LIVE_RELOAD_PATH:
            return await next(request)

        response = await next(request)

        # Only inject into successful HTML responses
        if not isinstance(response, Response):
            return response
        if response.status != 200:
            return response
        if "text/html" not in (response.content_type or ""):
            return response

        body = response.body
        if isinstance(body, str):
            body = body.encode("utf-8")

        injection_idx = find_html_injection_point(body)
        if injection_idx == -1:
            # No closing tag — append at end
            modified = body + self._script_bytes
        else:
            modified = body[:injection_idx] + self._script_bytes + body[injection_idx:]

        return (
            Response(
                body=modified,
                content_type=response.content_type,
                status=response.status,
                headers=response.headers,
                cookies=response.cookies,
            )
            .with_header("Content-Length", str(len(modified)))
            .with_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        )


# ---------------------------------------------------------------------------
# BuildGateMiddleware
# ---------------------------------------------------------------------------


class BuildGateMiddleware:
    """Returns a themed "rebuilding" page when a build is in progress.

    Intercepts HTML requests during active builds and returns the Bengal
    rebuilding placeholder page (animated loading with live reload).

    Passes through:
    - The SSE endpoint (must stay connected during builds)
    - Non-GET requests
    - Asset requests (CSS/JS — served from Pounce's compression cache)
    """

    __slots__ = ("_state",)

    def __init__(self, state: DevState) -> None:
        self._state = state

    async def __call__(self, request: Request, next: Next) -> AnyResponse:
        # Always let SSE through — browser needs it to detect build completion
        if request.path == LIVE_RELOAD_PATH:
            return await next(request)

        # Only gate GET requests for pages (not assets)
        if request.method != "GET":
            return await next(request)

        # Don't gate asset requests — CSS/JS should still be served
        if self._is_asset_path(request.path):
            return await next(request)

        if not self._state.build_in_progress:
            return await next(request)

        # Build in progress — return the rebuilding page
        html = get_rebuilding_page_html(request.path, self._state.active_palette)

        return (
            Response(body=html, content_type="text/html; charset=utf-8", status=200)
            .with_header("Content-Length", str(len(html)))
            .with_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        )

    @staticmethod
    def _is_asset_path(path: str) -> bool:
        """Check if a path is a static asset (CSS/JS/images/fonts)."""
        path_lower = path.lower()
        asset_prefixes = ("/assets/", "/static/")
        asset_extensions = (
            ".css", ".js", ".map", ".json",
            ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
            ".woff", ".woff2", ".ttf", ".otf", ".eot",
        )
        if any(path_lower.startswith(p) for p in asset_prefixes):
            return True
        return any(path_lower.endswith(ext) for ext in asset_extensions)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_dev_app(
    output_dir: Path,
    state: DevState,
) -> App:
    """Create the Chirp ASGI app for Bengal's dev server.

    Args:
        output_dir: Path to the built site output directory (``public/``).
        state: Shared DevState for build state and SSE broadcast.

    Returns:
        A Chirp ``App`` instance ready to be served by Pounce.

    Middleware stack (outermost → innermost):
        BuildGateMiddleware → HtmlInjectionMiddleware → StaticFiles → Router

    Routes:
        GET /__bengal_reload__ → SSE live reload endpoint
    """
    app = App()

    # -- Lifespan: register the event loop so sync→async bridging works --

    @app.on_worker_startup
    async def _register_loop() -> None:
        state.set_loop(asyncio.get_running_loop())

    # -- SSE live reload endpoint --

    @app.route(LIVE_RELOAD_PATH)
    def sse_reload() -> EventStream:
        async def stream() -> Any:
            queue = state.subscribe()
            try:
                while True:
                    payload = await queue.get()
                    yield SSEEvent(data=payload)
            finally:
                state.unsubscribe(queue)

        return EventStream(stream(), heartbeat_interval=15.0)

    # -- Middleware stack (added order = outermost first) --

    # 1. Build gate: returns rebuilding page during builds
    app.add_middleware(BuildGateMiddleware(state))

    # 2. HTML injection: injects live reload script into HTML responses
    app.add_middleware(HtmlInjectionMiddleware())

    # 3. Static files: serves the built site from output_dir
    app.add_middleware(StaticFiles(
        directory=output_dir,
        prefix="/",
        not_found_page="404.html",
        cache_control="no-store, no-cache, must-revalidate, max-age=0",
    ))

    return app


def init_dev_state() -> DevState:
    """Create and register the global DevState singleton.

    Called once by DevServer.start() to set up the shared state.
    The state is used by:
    - create_dev_app() for the ASGI app
    - build_trigger.py for signaling build state
    - live_reload.py for broadcasting reload events
    """
    global _dev_state
    _dev_state = DevState()

    # Register the broadcast hook in live_reload so existing callers
    # (send_reload_payload, notify_clients_reload) push to SSE clients
    from bengal.server.live_reload import register_broadcast_hook

    register_broadcast_hook(_dev_state.broadcast_reload)

    return _dev_state


def cleanup_dev_state() -> None:
    """Clear the global DevState singleton on shutdown."""
    global _dev_state

    from bengal.server.live_reload import register_broadcast_hook

    register_broadcast_hook(None)
    _dev_state = None
