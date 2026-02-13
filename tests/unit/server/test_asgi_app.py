"""
Tests for the ASGI app skeleton (create_bengal_dev_app).

Skeleton returns 501 for /__bengal_reload__ and 404 for other paths.
Full implementation (SSE, static serving) will be added during Pounce wiring.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.server.asgi_app import create_bengal_dev_app


async def _noop_receive() -> dict:
    """ASGI receive stub (skeleton app never reads body)."""
    return {}


def _make_send_capture() -> tuple[list[dict], object]:
    """Return (list to capture send calls, async send callable)."""
    sent: list[dict] = []

    async def send(message: dict) -> None:
        sent.append(message)

    return sent, send


@pytest.mark.asyncio
async def test_reload_endpoint_returns_501(tmp_path: Path) -> None:
    """GET /__bengal_reload__ returns 501 until SSE is wired."""
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/__bengal_reload__"},
        receive=_noop_receive,
        send=send,
    )

    assert len(sent) == 2
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 501
    assert sent[1]["type"] == "http.response.body"
    assert b"SSE not yet implemented" in sent[1]["body"]
    assert b"Pounce" in sent[1]["body"]


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
