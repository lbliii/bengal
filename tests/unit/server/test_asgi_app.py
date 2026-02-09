"""
Tests for the Chirp ASGI app, DevState, and middleware.

Validates the Pounce/Chirp dev server stack:
- DevState: Thread-safe shared state + SSE broadcast
- HtmlInjectionMiddleware: Live reload script injection
- BuildGateMiddleware: Rebuilding page during builds
- create_dev_app: App factory wires everything correctly
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

import pytest

from bengal.server.asgi_app import (
    BuildGateMiddleware,
    DevState,
    HtmlInjectionMiddleware,
    cleanup_dev_state,
    create_dev_app,
    get_dev_state,
    init_dev_state,
)
from bengal.server.constants import LIVE_RELOAD_PATH


def _make_request(method: str = "GET", path: str = "/") -> Any:
    """Create a minimal Chirp Request for testing."""
    from chirp.http.request import Request

    async def _noop_receive() -> dict[str, Any]:
        return {"type": "http.disconnect"}

    return Request(
        method=method,
        path=path,
        headers=(),
        query={},
        path_params={},
        http_version="1.1",
        server=("127.0.0.1", 5173),
        client=("127.0.0.1", 9999),
        cookies={},
        _receive=_noop_receive,
    )


# ---------------------------------------------------------------------------
# DevState
# ---------------------------------------------------------------------------


class TestDevState:
    """Test DevState shared state management."""

    def test_build_in_progress_default_false(self) -> None:
        state = DevState()
        assert state.build_in_progress is False

    def test_set_build_in_progress(self) -> None:
        state = DevState()
        state.set_build_in_progress(True)
        assert state.build_in_progress is True
        state.set_build_in_progress(False)
        assert state.build_in_progress is False

    def test_build_state_thread_safe(self) -> None:
        """Toggle build state from multiple threads without errors."""
        state = DevState()
        errors: list[Exception] = []

        def toggle() -> None:
            try:
                for _ in range(100):
                    state.set_build_in_progress(True)
                    state.set_build_in_progress(False)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=toggle) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []

    def test_subscribe_unsubscribe(self) -> None:
        state = DevState()
        q = state.subscribe()
        assert q in state._clients
        state.unsubscribe(q)
        assert q not in state._clients

    def test_broadcast_no_loop_is_noop(self) -> None:
        """Broadcast without a registered event loop should not raise."""
        state = DevState()
        state.subscribe()
        state.broadcast_reload("reload")  # Should not raise

    @pytest.mark.asyncio
    async def test_broadcast_delivers_to_subscribers(self) -> None:
        """Broadcast should push payload to all subscriber queues."""
        state = DevState()
        loop = asyncio.get_running_loop()
        state.set_loop(loop)

        q1 = state.subscribe()
        q2 = state.subscribe()

        state.broadcast_reload("reload")

        # Allow the event loop to process the call_soon_threadsafe
        await asyncio.sleep(0.01)

        assert not q1.empty()
        assert not q2.empty()
        assert await q1.get() == "reload"
        assert await q2.get() == "reload"

    @pytest.mark.asyncio
    async def test_broadcast_skips_unsubscribed(self) -> None:
        """Unsubscribed queues should not receive broadcasts."""
        state = DevState()
        loop = asyncio.get_running_loop()
        state.set_loop(loop)

        q = state.subscribe()
        state.unsubscribe(q)

        state.broadcast_reload("reload")
        await asyncio.sleep(0.01)

        assert q.empty()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


class TestDevStateSingleton:
    """Test init/cleanup of the module-level DevState."""

    def test_init_and_cleanup(self) -> None:
        state = init_dev_state()
        assert get_dev_state() is state

        cleanup_dev_state()
        assert get_dev_state() is None


# ---------------------------------------------------------------------------
# HtmlInjectionMiddleware
# ---------------------------------------------------------------------------


class TestHtmlInjectionMiddleware:
    """Test HTML live reload script injection."""

    @pytest.mark.asyncio
    async def test_injects_script_into_html(self) -> None:
        from chirp.http.response import Response

        middleware = HtmlInjectionMiddleware()
        request = _make_request(path="/index.html")

        html_body = b"<html><body><h1>Test</h1></body></html>"
        downstream_response = Response(
            body=html_body,
            content_type="text/html; charset=utf-8",
            status=200,
        )

        async def next_handler(req: Any) -> Response:
            return downstream_response

        result = await middleware(request, next_handler)
        assert isinstance(result, Response)
        body = result.body if isinstance(result.body, bytes) else result.body.encode()
        assert b"Bengal Live Reload" in body
        assert b"</body>" in body

    @pytest.mark.asyncio
    async def test_skips_non_html(self) -> None:
        from chirp.http.response import Response

        middleware = HtmlInjectionMiddleware()
        request = _make_request(path="/style.css")

        css_response = Response(
            body=b"body { color: red; }",
            content_type="text/css",
            status=200,
        )

        async def next_handler(req: Any) -> Response:
            return css_response

        result = await middleware(request, next_handler)
        assert isinstance(result, Response)
        assert result.body == b"body { color: red; }"

    @pytest.mark.asyncio
    async def test_skips_sse_endpoint(self) -> None:
        from chirp.http.response import Response

        middleware = HtmlInjectionMiddleware()
        request = _make_request(path=LIVE_RELOAD_PATH)

        original = Response(body=b"data: test", content_type="text/event-stream", status=200)

        async def next_handler(req: Any) -> Response:
            return original

        result = await middleware(request, next_handler)
        assert result is original  # Passthrough, not modified

    @pytest.mark.asyncio
    async def test_skips_error_responses(self) -> None:
        from chirp.http.response import Response

        middleware = HtmlInjectionMiddleware()
        request = _make_request(path="/missing.html")

        error_response = Response(
            body=b"<html><body>Not Found</body></html>",
            content_type="text/html; charset=utf-8",
            status=404,
        )

        async def next_handler(req: Any) -> Response:
            return error_response

        result = await middleware(request, next_handler)
        assert isinstance(result, Response)
        # Should not inject into error responses
        body = result.body if isinstance(result.body, bytes) else result.body.encode()
        assert b"Bengal Live Reload" not in body


# ---------------------------------------------------------------------------
# BuildGateMiddleware
# ---------------------------------------------------------------------------


class TestBuildGateMiddleware:
    """Test build-in-progress gating."""

    @pytest.mark.asyncio
    async def test_passthrough_when_not_building(self) -> None:
        from chirp.http.response import Response

        state = DevState()
        middleware = BuildGateMiddleware(state)
        request = _make_request(path="/index.html")

        original = Response(body=b"<html>Hello</html>", status=200)

        async def next_handler(req: Any) -> Response:
            return original

        result = await middleware(request, next_handler)
        assert result is original

    @pytest.mark.asyncio
    async def test_returns_rebuilding_page_during_build(self) -> None:
        from chirp.http.response import Response

        state = DevState()
        state.set_build_in_progress(True)
        middleware = BuildGateMiddleware(state)
        request = _make_request(path="/blog/post")

        async def next_handler(req: Any) -> Response:
            msg = "Should not be called"
            raise AssertionError(msg)

        result = await middleware(request, next_handler)
        assert isinstance(result, Response)
        assert result.status == 200
        body = result.body if isinstance(result.body, bytes) else result.body.encode()
        assert b"Rebuilding" in body
        assert b"Bengal" in body

    @pytest.mark.asyncio
    async def test_always_passes_sse_through(self) -> None:
        from chirp.http.response import Response

        state = DevState()
        state.set_build_in_progress(True)
        middleware = BuildGateMiddleware(state)
        request = _make_request(path=LIVE_RELOAD_PATH)

        original = Response(body=b"sse-stream", status=200)

        async def next_handler(req: Any) -> Response:
            return original

        result = await middleware(request, next_handler)
        assert result is original

    @pytest.mark.asyncio
    async def test_passes_assets_through_during_build(self) -> None:
        from chirp.http.response import Response

        state = DevState()
        state.set_build_in_progress(True)
        middleware = BuildGateMiddleware(state)
        request = _make_request(path="/assets/css/style.css")

        original = Response(body=b"body{}", content_type="text/css", status=200)

        async def next_handler(req: Any) -> Response:
            return original

        result = await middleware(request, next_handler)
        assert result is original

    def test_is_asset_path(self) -> None:
        assert BuildGateMiddleware._is_asset_path("/assets/css/style.css") is True
        assert BuildGateMiddleware._is_asset_path("/static/img/logo.png") is True
        assert BuildGateMiddleware._is_asset_path("/favicon.ico") is True
        assert BuildGateMiddleware._is_asset_path("/blog/post") is False
        assert BuildGateMiddleware._is_asset_path("/") is False


# ---------------------------------------------------------------------------
# create_dev_app
# ---------------------------------------------------------------------------


class TestCreateDevApp:
    """Test the ASGI app factory."""

    def test_creates_chirp_app(self, tmp_path: Path) -> None:
        from chirp import App

        state = DevState()
        app = create_dev_app(tmp_path, state)
        assert isinstance(app, App)

    def test_app_is_asgi_callable(self, tmp_path: Path) -> None:
        state = DevState()
        app = create_dev_app(tmp_path, state)
        assert callable(app)
