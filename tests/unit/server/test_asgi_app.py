"""
Tests for the ASGI app (create_bengal_dev_app).

SSE endpoint streams live reload events; static files served with HTML injection.
"""

from __future__ import annotations

import gzip
from typing import TYPE_CHECKING

import pytest

from bengal.server.asgi_app import (
    _prefers_markdown,
    create_bengal_dev_app,
    create_bengal_preview_app,
)

if TYPE_CHECKING:
    from pathlib import Path


async def _noop_receive() -> dict:
    """ASGI receive stub (app never reads body for GET)."""
    return {}


def _make_send_capture() -> tuple[list[dict], object]:
    """Return (list to capture send calls, async send callable)."""
    sent: list[dict] = []

    async def send(message: dict) -> None:
        sent.append(message)

    return sent, send


def _headers(message: dict) -> dict[bytes, bytes]:
    return {name.lower(): value for name, value in message["headers"]}


def _body(sent: list[dict]) -> bytes:
    return b"".join(
        message.get("body", b"") for message in sent if message.get("type") == "http.response.body"
    )


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
    assert any(h[0] == b"content-type" and b"event-stream" in h[1] for h in sent[0]["headers"])
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
    assert any(h[0] == b"content-type" and b"text/css" in h[1] for h in sent[0]["headers"])
    assert _body(sent) == b"body { color: red; }"


@pytest.mark.asyncio
async def test_static_asset_uses_pounce_etag_and_304(tmp_path: Path) -> None:
    """Static assets use Pounce conditional request handling."""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "style.css").write_text("body { color: red; }")
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )

    first, first_send = _make_send_capture()
    await app(
        scope={"type": "http", "method": "GET", "path": "/assets/style.css"},
        receive=_noop_receive,
        send=first_send,
    )

    first_headers = _headers(first[0])
    etag = first_headers[b"etag"]
    assert first[0]["status"] == 200
    assert first_headers[b"accept-ranges"] == b"bytes"
    assert first_headers[b"cache-control"] == b"no-cache, must-revalidate"

    second, second_send = _make_send_capture()
    await app(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/assets/style.css",
            "headers": [(b"if-none-match", etag)],
        },
        receive=_noop_receive,
        send=second_send,
    )

    assert second[0]["status"] == 304
    assert _body(second) == b""


@pytest.mark.asyncio
async def test_static_asset_range_request_returns_partial_content(tmp_path: Path) -> None:
    """Static assets use Pounce range request handling."""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("0123456789")
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/assets/app.js",
            "headers": [(b"range", b"bytes=2-5")],
        },
        receive=_noop_receive,
        send=send,
    )

    headers = _headers(sent[0])
    assert sent[0]["status"] == 206
    assert headers[b"content-range"] == b"bytes 2-5/10"
    assert _body(sent) == b"2345"


@pytest.mark.asyncio
async def test_static_asset_serves_precompressed_gzip_variant(tmp_path: Path) -> None:
    """Static assets use Pounce precompressed variant negotiation."""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "style.css").write_text("body { color: red; }")
    gz_body = gzip.compress(b"body { color: red; }")
    (assets / "style.css.gz").write_bytes(gz_body)
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/assets/style.css",
            "headers": [(b"accept-encoding", b"gzip")],
        },
        receive=_noop_receive,
        send=send,
    )

    headers = _headers(sent[0])
    assert sent[0]["status"] == 200
    assert headers[b"content-encoding"] == b"gzip"
    assert headers[b"vary"].lower() == b"accept-encoding"
    assert _body(sent) == gz_body


@pytest.mark.asyncio
async def test_head_index_html_serves_headers_without_body(tmp_path: Path) -> None:
    """HEAD / mirrors the document response headers without a body."""
    (tmp_path / "index.html").write_text("<html><body>Hello</body></html>")
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "HEAD", "path": "/"},
        receive=_noop_receive,
        send=send,
    )

    headers = _headers(sent[0])
    assert sent[0]["status"] == 200
    assert int(headers[b"content-length"]) > len("<html><body>Hello</body></html>")
    assert _body(sent) == b""


@pytest.mark.asyncio
async def test_head_custom_404_serves_headers_without_body(tmp_path: Path) -> None:
    """HEAD missing documents preserve custom 404 headers without a body."""
    (tmp_path / "404.html").write_text("<html><body>Missing</body></html>")
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "HEAD", "path": "/missing"},
        receive=_noop_receive,
        send=send,
    )

    headers = _headers(sent[0])
    assert sent[0]["status"] == 404
    assert headers[b"content-type"] == b"text/html; charset=utf-8"
    assert int(headers[b"content-length"]) > len("<html><body>Missing</body></html>")
    assert _body(sent) == b""


@pytest.mark.asyncio
async def test_head_missing_deferred_artifact_returns_503_without_body(tmp_path: Path) -> None:
    """HEAD generated artifacts preserve the serve-ready pending status."""
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: True,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "HEAD", "path": "/search-index.json"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 503
    assert _headers(sent[0])[b"retry-after"] == b"1"
    assert _body(sent) == b""


@pytest.mark.asyncio
async def test_preview_app_serves_root_without_live_reload(tmp_path: Path) -> None:
    """Preview serves completed output through Pounce without dev injection."""
    (tmp_path / "index.html").write_text("<html><body>Preview</body></html>")
    app = create_bengal_preview_app(output_dir=tmp_path)
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/"},
        receive=_noop_receive,
        send=send,
    )

    headers = _headers(sent[0])
    assert sent[0]["status"] == 200
    assert headers[b"accept-ranges"] == b"bytes"
    assert b"Preview" in _body(sent)
    assert b"__bengal_reload__" not in _body(sent)


@pytest.mark.asyncio
async def test_preview_app_serves_nested_index(tmp_path: Path) -> None:
    """Preview static root resolves directory indexes."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text("<html><body>Docs</body></html>")
    app = create_bengal_preview_app(output_dir=tmp_path)
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/docs/"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 200
    assert b"Docs" in _body(sent)


@pytest.mark.asyncio
async def test_preview_app_serves_custom_404_without_live_reload(tmp_path: Path) -> None:
    """Preview keeps generated custom 404 content unchanged."""
    (tmp_path / "404.html").write_text("<html><body>Custom 404</body></html>")
    app = create_bengal_preview_app(output_dir=tmp_path)
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/missing"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 404
    assert b"Custom 404" in _body(sent)
    assert b"__bengal_reload__" not in _body(sent)


@pytest.mark.asyncio
async def test_preview_app_health_path(tmp_path: Path) -> None:
    """Preview exposes a Bengal-namespaced health response."""
    (tmp_path / "index.html").write_text("ok")
    app = create_bengal_preview_app(output_dir=tmp_path)
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/__bengal_pounce_health__"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 200
    assert _body(sent) == b"ok\n"


@pytest.mark.asyncio
async def test_preview_app_serves_generated_artifact_as_static_file(tmp_path: Path) -> None:
    """Preview serves generated artifacts as completed static output."""
    (tmp_path / "search-index.json").write_text('{"pages":[]}')
    app = create_bengal_preview_app(output_dir=tmp_path)
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/search-index.json"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 200
    assert _body(sent) == b'{"pages":[]}'


@pytest.mark.asyncio
async def test_preview_app_serves_precompressed_zstd_variant(tmp_path: Path) -> None:
    """Preview uses Pounce zstd precompressed sidecar negotiation."""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "style.css").write_text("body { color: red; }")
    zstd_body = b"fake-zstd-body"
    (assets / "style.css.zst").write_bytes(zstd_body)
    app = create_bengal_preview_app(output_dir=tmp_path)
    sent, send = _make_send_capture()

    await app(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/assets/style.css",
            "headers": [(b"accept-encoding", b"zstd")],
        },
        receive=_noop_receive,
        send=send,
    )

    headers = _headers(sent[0])
    assert sent[0]["status"] == 200
    assert headers[b"content-encoding"] == b"zstd"
    assert _body(sent) == zstd_body


@pytest.mark.asyncio
async def test_preview_app_rejects_symlinked_files(tmp_path: Path) -> None:
    """Preview inherits Pounce's refusal for symlinks escaping the output root."""
    output_root = tmp_path / "public"
    output_root.mkdir()
    target = tmp_path / "target.txt"
    target.write_text("secret")
    link = output_root / "link.txt"
    link.symlink_to(target)
    app = create_bengal_preview_app(output_dir=output_root)
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/link.txt"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 404
    assert _body(sent) == b"Not Found"


@pytest.mark.asyncio
async def test_preview_app_head_static_file_has_no_body(tmp_path: Path) -> None:
    """Preview HEAD requests are handled by Pounce's static responder."""
    (tmp_path / "index.html").write_text("<html><body>Preview</body></html>")
    app = create_bengal_preview_app(output_dir=tmp_path)
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "HEAD", "path": "/"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 200
    assert (
        _headers(sent[0])[b"content-length"]
        == str(len("<html><body>Preview</body></html>")).encode()
    )
    assert _body(sent) == b""


@pytest.mark.asyncio
async def test_build_in_progress_missing_file_returns_404(tmp_path: Path) -> None:
    """When build in progress and requested file does not exist, return 404 (no full placeholder)."""
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: True,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/blog/post"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 404
    assert sent[1]["body"] == b"Not Found"


@pytest.mark.asyncio
async def test_build_in_progress_missing_deferred_artifact_returns_503(tmp_path: Path) -> None:
    """Known generated artifacts should say they are still being prepared."""
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: True,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/index.json"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 503
    assert any(h[0] == b"retry-after" and h[1] == b"1" for h in sent[0]["headers"])
    assert b"still being prepared" in sent[1]["body"]


@pytest.mark.asyncio
async def test_missing_deferred_artifact_returns_404_when_not_building(tmp_path: Path) -> None:
    """Deferred artifact handling is only active during a build."""
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/docs/v1/search-index.json"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 404
    assert sent[1]["body"] == b"Not Found"


@pytest.mark.asyncio
async def test_build_in_progress_404_html_gets_badge(tmp_path: Path) -> None:
    """When build in progress and 404.html exists, serve it with rebuilding badge."""
    (tmp_path / "404.html").write_text("<html><body>Custom 404</body></html>")
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: True,
    )
    sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/blog/post"},
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 404
    body = sent[1]["body"]
    assert b"Custom 404" in body
    assert b"bengal-rebuilding-badge" in body


@pytest.mark.asyncio
async def test_build_in_progress_serves_cached_with_badge(tmp_path: Path) -> None:
    """When build in progress and file exists, serve cached content with rebuilding badge."""
    (tmp_path / "index.html").write_text("<html><body>Hello</body></html>")
    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: True,
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
    assert b"bengal-rebuilding-badge" in body
    assert b"Rebuilding" in body


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


@pytest.mark.asyncio
async def test_request_callback_invoked_for_document(tmp_path: Path) -> None:
    """Request callback is invoked for document requests (HTML, no extension)."""
    (tmp_path / "index.html").write_text("<html><body>Hi</body></html>")
    logged: list[tuple[str, str, int, float]] = []
    holder: list = [lambda m, p, s, d: logged.append((m, p, s, d))]

    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
        request_callback=lambda: holder[0],
    )
    _sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/"},
        receive=_noop_receive,
        send=send,
    )

    assert len(logged) == 1
    assert logged[0][0] == "GET"
    assert logged[0][1] == "/"
    assert logged[0][2] == 200
    assert logged[0][3] >= 0


@pytest.mark.asyncio
async def test_request_callback_not_invoked_for_static(tmp_path: Path) -> None:
    """Request callback is not invoked for static assets."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "style.css").write_text("body {}")
    logged: list[tuple[str, str, int, float]] = []
    holder: list = [lambda m, p, s, d: logged.append((m, p, s, d))]

    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
        request_callback=lambda: holder[0],
    )
    _sent, send = _make_send_capture()

    await app(
        scope={"type": "http", "method": "GET", "path": "/assets/style.css"},
        receive=_noop_receive,
        send=send,
    )

    assert len(logged) == 0


@pytest.mark.asyncio
async def test_callable_output_dir_resolves_per_request(tmp_path: Path) -> None:
    """When output_dir is a callable, it is invoked per request (double-buffer)."""
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "index.html").write_text("<html><body>buffer-a</body></html>")
    (dir_b / "index.html").write_text("<html><body>buffer-b</body></html>")

    current = [dir_a]
    app = create_bengal_dev_app(
        output_dir=lambda: current[0],
        build_in_progress=lambda: False,
    )
    scope = {"type": "http", "method": "GET", "path": "/"}

    sent, send = _make_send_capture()
    await app(scope=scope, receive=_noop_receive, send=send)
    body_a = sent[1]["body"]
    assert b"buffer-a" in body_a

    current[0] = dir_b
    sent2, send2 = _make_send_capture()
    await app(scope=scope, receive=_noop_receive, send=send2)
    body_b = sent2[1]["body"]
    assert b"buffer-b" in body_b


@pytest.mark.asyncio
async def test_static_asset_callable_output_dir_resolves_per_request(tmp_path: Path) -> None:
    """Pounce-backed static assets still follow double-buffer swaps."""
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    (dir_a / "assets").mkdir(parents=True)
    (dir_b / "assets").mkdir(parents=True)
    (dir_a / "assets" / "style.css").write_text("body { color: red; }")
    (dir_b / "assets" / "style.css").write_text("body { color: blue; }")

    current = [dir_a]
    app = create_bengal_dev_app(
        output_dir=lambda: current[0],
        build_in_progress=lambda: False,
    )
    scope = {"type": "http", "method": "GET", "path": "/assets/style.css"}

    sent, send = _make_send_capture()
    await app(scope=scope, receive=_noop_receive, send=send)
    assert _body(sent) == b"body { color: red; }"

    current[0] = dir_b
    sent2, send2 = _make_send_capture()
    await app(scope=scope, receive=_noop_receive, send=send2)
    assert _body(sent2) == b"body { color: blue; }"


# ---------------------------------------------------------------------------
# Accept header parsing (_prefers_markdown)
# ---------------------------------------------------------------------------


class TestPrefersMarkdown:
    """Test Accept header q-value parsing for content negotiation."""

    def test_explicit_markdown_only(self):
        assert _prefers_markdown("text/markdown") is True

    def test_markdown_with_html_lower_q(self):
        assert _prefers_markdown("text/markdown, text/html;q=0.5") is True

    def test_html_preferred_over_markdown(self):
        assert _prefers_markdown("text/html, text/markdown;q=0.5") is False

    def test_markdown_with_q_zero(self):
        assert _prefers_markdown("text/markdown;q=0") is False

    def test_equal_q_values(self):
        assert _prefers_markdown("text/html;q=0.9, text/markdown;q=0.9") is True

    def test_no_markdown_in_accept(self):
        assert _prefers_markdown("text/html, application/json") is False

    def test_wildcard_does_not_trigger(self):
        assert _prefers_markdown("*/*") is False

    def test_empty_accept(self):
        assert _prefers_markdown("") is False


# ---------------------------------------------------------------------------
# Content negotiation integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_content_negotiation_serves_markdown(tmp_path: Path) -> None:
    """Accept: text/markdown serves the .md file when available."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text("<html><body>HTML</body></html>")
    (docs / "index.md").write_text("# Docs\n\nMarkdown content.")

    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/docs/",
            "headers": [(b"accept", b"text/markdown")],
        },
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 200
    assert any(h[0] == b"content-type" and b"text/markdown" in h[1] for h in sent[0]["headers"])
    assert b"Markdown content." in sent[1]["body"]


@pytest.mark.asyncio
async def test_content_negotiation_falls_through_when_no_md(tmp_path: Path) -> None:
    """Accept: text/markdown falls through to HTML when no .md file exists."""
    (tmp_path / "index.html").write_text("<html><body>HTML only</body></html>")

    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"accept", b"text/markdown")],
        },
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 200
    assert b"HTML only" in sent[1]["body"]


@pytest.mark.asyncio
async def test_content_negotiation_respects_q_values(tmp_path: Path) -> None:
    """HTML preferred (higher q) — should serve HTML, not markdown."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text("<html><body>HTML</body></html>")
    (docs / "index.md").write_text("# Docs\n\nMarkdown.")

    app = create_bengal_dev_app(
        output_dir=tmp_path,
        build_in_progress=lambda: False,
    )
    sent, send = _make_send_capture()

    await app(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/docs/",
            "headers": [(b"accept", b"text/html, text/markdown;q=0.5")],
        },
        receive=_noop_receive,
        send=send,
    )

    assert sent[0]["status"] == 200
    assert b"HTML" in sent[1]["body"]
