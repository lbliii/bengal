"""
Integration tests for link checker with mock HTTP server.
"""

from __future__ import annotations

import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from time import sleep

import pytest

from bengal.health.linkcheck.async_checker import AsyncLinkChecker
from bengal.health.linkcheck.models import LinkStatus


class MockHTTPHandler(BaseHTTPRequestHandler):
    """Mock HTTP handler for testing."""

    def log_message(self, format, *args):
        """Suppress log messages."""
        pass

    def do_HEAD(self):
        """Handle HEAD requests."""
        if "/200" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
        elif "/404" in self.path:
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
        elif "/500" in self.path:
            self.send_response(500)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
        elif "/no-head" in self.path:
            # Simulate server that doesn't support HEAD
            self.send_response(405)
            self.send_header("Allow", "GET")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if "/200" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>OK</body></html>")
        elif "/no-head" in self.path:
            # This path only supports GET
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>OK via GET</body></html>")
        elif "/404" in self.path:
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Not Found</body></html>")
        elif "/500" in self.path:
            self.send_response(500)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Server Error</body></html>")
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture(scope="module")
def http_server():
    """Start a mock HTTP server for testing."""
    server = HTTPServer(("127.0.0.1", 0), MockHTTPHandler)
    port = server.server_address[1]

    # Run server in background thread
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Give server time to start
    sleep(0.1)

    yield f"http://127.0.0.1:{port}"

    # Shutdown server
    server.shutdown()


@pytest.mark.asyncio
async def test_check_successful_link(http_server):
    """Test checking a successful link."""
    checker = AsyncLinkChecker(timeout=5.0, retries=0)

    urls = [(f"{http_server}/200", "/test.md")]
    results = await checker.check_links(urls)

    assert len(results) == 1
    result = results[f"{http_server}/200"]

    assert result.status == LinkStatus.OK
    assert result.status_code == 200
    assert result.first_ref == "/test.md"


@pytest.mark.asyncio
async def test_check_404_link(http_server):
    """Test checking a 404 link."""
    checker = AsyncLinkChecker(timeout=5.0, retries=0)

    urls = [(f"{http_server}/404", "/test.md")]
    results = await checker.check_links(urls)

    assert len(results) == 1
    result = results[f"{http_server}/404"]

    assert result.status == LinkStatus.BROKEN
    assert result.status_code == 404


@pytest.mark.asyncio
async def test_check_500_link(http_server):
    """Test checking a 500 server error link."""
    checker = AsyncLinkChecker(timeout=5.0, retries=0)

    urls = [(f"{http_server}/500", "/test.md")]
    results = await checker.check_links(urls)

    assert len(results) == 1
    result = results[f"{http_server}/500"]

    assert result.status == LinkStatus.BROKEN
    assert result.status_code == 500


@pytest.mark.asyncio
async def test_check_500_with_ignore(http_server):
    """Test ignoring 5xx errors."""
    from bengal.health.linkcheck.ignore_policy import IgnorePolicy

    ignore_policy = IgnorePolicy(status_ranges=["500-599"])
    checker = AsyncLinkChecker(timeout=5.0, retries=0, ignore_policy=ignore_policy)

    urls = [(f"{http_server}/500", "/test.md")]
    results = await checker.check_links(urls)

    assert len(results) == 1
    result = results[f"{http_server}/500"]

    assert result.status == LinkStatus.IGNORED
    assert result.ignored is True
    assert result.ignore_reason is not None


@pytest.mark.asyncio
async def test_head_fallback_to_get(http_server):
    """Test fallback from HEAD to GET when HEAD not supported."""
    checker = AsyncLinkChecker(timeout=5.0, retries=0)

    urls = [(f"{http_server}/no-head", "/test.md")]
    results = await checker.check_links(urls)

    assert len(results) == 1
    result = results[f"{http_server}/no-head"]

    # Should succeed via GET fallback
    assert result.status == LinkStatus.OK
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_multiple_references_to_same_url(http_server):
    """Test that multiple references to same URL are counted."""
    checker = AsyncLinkChecker(timeout=5.0, retries=0)

    # Same URL referenced from 3 different pages
    urls = [
        (f"{http_server}/200", "/page1.md"),
        (f"{http_server}/200", "/page2.md"),
        (f"{http_server}/200", "/page3.md"),
    ]
    results = await checker.check_links(urls)

    assert len(results) == 1  # Only one unique URL
    result = results[f"{http_server}/200"]

    assert result.ref_count == 3
    assert result.first_ref == "/page1.md"


@pytest.mark.asyncio
async def test_concurrent_checking(http_server):
    """Test concurrent checking of multiple URLs."""
    checker = AsyncLinkChecker(timeout=5.0, retries=0, max_concurrency=10)

    # Check multiple URLs concurrently
    urls = [
        (f"{http_server}/200", "/test.md"),
        (f"{http_server}/404", "/test.md"),
        (f"{http_server}/500", "/test.md"),
    ]
    results = await checker.check_links(urls)

    assert len(results) == 3

    # Each should have correct status
    assert results[f"{http_server}/200"].status == LinkStatus.OK
    assert results[f"{http_server}/404"].status == LinkStatus.BROKEN
    assert results[f"{http_server}/500"].status == LinkStatus.BROKEN


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test timeout handling for slow servers."""
    # Use a URL that will timeout (non-routable IP)
    checker = AsyncLinkChecker(timeout=0.5, retries=0)

    urls = [("http://10.255.255.1/page", "/test.md")]
    results = await checker.check_links(urls)

    assert len(results) == 1
    result = results["http://10.255.255.1/page"]

    # Should be marked as error due to timeout
    assert result.status == LinkStatus.ERROR
    assert result.error_message is not None


def test_sync_wrapper_for_async_check():
    """Test that async check can be run from sync context."""
    # This is how the orchestrator uses it
    checker = AsyncLinkChecker(timeout=5.0, retries=0)

    urls = [("https://httpbin.org/status/200", "/test.md")]

    # Run in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(checker.check_links(urls))
        assert len(results) == 1
    finally:
        loop.close()
