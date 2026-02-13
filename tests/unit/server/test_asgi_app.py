"""
Tests for the ASGI app (create_bengal_dev_app).

SSE endpoint streams live reload events; static files served with HTML injection.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.server.asgi_app import create_bengal_dev_app


async def _noop_receive() -> dict:
    """ASGI receive stub (app never reads body for GET)."""
    return {}


def _make_send_capture() -> tuple[list[dict], object]:
    """Return (list to capture send calls, async send callable)."""
    sent: list[dict] = []

    async def send(message: dict) -> None:
        sent.append(message)

    return sent, send


@pytest.mark.asyncio
async def test_reload_endpoint_streams_sse(tmp_path: Path) -> None:
    """GET /__bengal_reload__ returns 200 and streams SSE (retry, connected)."""
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
        sse_keepalive_interval=0.05,
    )
    sent: list[dict] = []
    call_count = 0

    async def send_raise_after_handshake(message: dict) -> None:
        nonlocal call_count
        sent.append(message)
        call_count += 1
        # Disconnect after headers + retry + connected + 2 keepalives (~0.1s)
        if call_count >= 6:
            raise ConnectionResetError("Simulated client disconnect")

    await app(
        scope={"type": "http", "method": "GET", "path": "/__bengal_reload__"},
        receive=_noop_receive,
        send=send_raise_after_handshake,
    )

    assert len(sent) >= 2
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 200
    assert any(
        h[0] == b"content-type" and b"event-stream" in h[1]
        for h in sent[0]["headers"]
    )
    body_parts = b"".join(
        m["body"] for m in sent[1:] if m["type"] == "http.response.body" and m["body"]
    )
    assert b"retry:" in body_parts
    assert b"connected" in body_parts


@pytest.mark.asyncio
async def test_missing_path_returns_404(tmp_path: Path) -> None:
    """GET / returns 404 when index.html does not exist."""
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/"},
        receive=_noop_receive,
        send=send,
    )

    assert len(sent) == 2
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 404
    assert sent[1]["type"] == "http.response.body"
    assert sent[1]["body"] == b"Not Found"


@pytest.mark.asyncio
async def test_get_index_html_serves_file(tmp_path: Path) -> None:
    """GET / serves index.html with injected live reload script."""
    (tmp_path / "index.html").write_text("<html><body>Hello</body></html>")
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 200
    body = sent[1]["body"]
    assert b"Hello" in body
    assert b"EventSource" in body or b"__bengal_reload__" in body


@pytest.mark.asyncio
async def test_get_static_asset_serves_file(tmp_path: Path) -> None:
    """GET /assets/style.css serves file with correct content-type."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "style.css").write_text("body { color: red; }")
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/assets/style.css"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 200
    assert any(
        h[0] == b"content-type" and b"text/css" in h[1]
        for h in sent[0]["headers"]
    )
    assert sent[1]["body"] == b"body { color: red; }"


@pytest.mark.asyncio
async def test_build_in_progress_serves_rebuilding_page(tmp_path: Path) -> None:
    """When build in progress and path is HTML-like, serve rebuilding page."""
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: True,
        active_palette="snow-lynx",
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/blog/post"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 200
    assert b"Rebuilding" in sent[1]["body"]
    assert b"/blog/post" in sent[1]["body"]


@pytest.mark.asyncio
async def test_custom_404_served_when_present(tmp_path: Path) -> None:
    """404 serves custom 404.html with injection when present."""
    (tmp_path / "404.html").write_text("<html><body>Custom 404</body></html>")
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/nonexistent"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 404
    assert b"Custom 404" in sent[1]["body"]
    assert b"__bengal_reload__" in sent[1]["body"]


@pytest.mark.asyncio
async def test_path_traversal_returns_404(tmp_path: Path) -> None:
    """Path traversal (..) returns 404."""
    (tmp_path / "index.html").write_text("ok")
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/../etc/passwd"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 404


@pytest.mark.asyncio
async def test_non_http_scope_ignored(tmp_path: Path) -> None:
    """Non-http scope (lifespan, websocket) is ignored - no response sent."""
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "lifespan"},
        receive=_noop_receive,
        send=send,
    )

    assert len(sent) == 0


@pytest.mark.asyncio
async def test_post_reload_returns_404(tmp_path: Path) -> None:
    """POST /__bengal_reload__ returns 404 (only GET is SSE)."""
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "POST", "path": "/__bengal_reload__"},
        receive=_noop_receive,
        send=send,
    )

    assert len(sent) == 2
    assert sent[0]["status"] == 404
