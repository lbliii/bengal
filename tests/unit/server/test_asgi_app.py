"""
Tests for the ASGI app (create_bengal_dev_app).

SSE endpoint streams live reload events; other paths return 404 until static wired.
"""

from __future__ import annotations

import os
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
async def test_other_paths_return_404(tmp_path: Path) -> None:
    """All other paths return 404 until static serving is wired."""
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
