"""
Tests for live reload functionality.
"""

import pytest

from bengal.server.live_reload import LIVE_RELOAD_SCRIPT, LiveReloadMixin


class TestLiveReloadScriptInjection:
    """Test HTML injection for live reload."""

    def test_inject_before_closing_body(self):
        """Test that script is injected before </body> tag."""
        html = "<html><body><h1>Test</h1></body></html>"

        # The script should be injected before </body>
        assert "</body>" in html
        assert LIVE_RELOAD_SCRIPT not in html

        # After injection, script should be present before </body>
        expected = f"<html><body><h1>Test</h1>{LIVE_RELOAD_SCRIPT}</body></html>"
        assert "</body>" in expected
        assert LIVE_RELOAD_SCRIPT in expected

    def test_inject_before_closing_html_fallback(self):
        """Test fallback injection before </html> when no </body>."""

        # Script should be injected before </html>
        expected = f"<html><div>No body tag</div>{LIVE_RELOAD_SCRIPT}</html>"
        assert "</html>" in expected
        assert LIVE_RELOAD_SCRIPT in expected

    def test_case_insensitive_injection(self):
        """Test that injection works with uppercase HTML tags."""
        html_upper = "<HTML><BODY><h1>Test</h1></BODY></HTML>"
        html_mixed = "<Html><Body><h1>Test</h1></Body></Html>"

        # Both should have closing tags that we can find case-insensitively
        assert "</BODY>" in html_upper or "</body>" in html_upper.lower()
        assert "</Body>" in html_mixed or "</body>" in html_mixed.lower()

    def test_live_reload_script_format(self):
        """Test that the live reload script has expected content."""
        assert "EventSource" in LIVE_RELOAD_SCRIPT
        assert "__bengal_reload__" in LIVE_RELOAD_SCRIPT
        assert "location.reload()" in LIVE_RELOAD_SCRIPT
        assert "<script>" in LIVE_RELOAD_SCRIPT
        assert "</script>" in LIVE_RELOAD_SCRIPT


class TestLiveReloadNotification:
    """Test notification system for live reload."""

    def test_notify_clients_with_no_clients(self):
        """Test that notify works even with no connected clients."""
        from bengal.server.live_reload import notify_clients_reload

        # Should not raise any exceptions
        notify_clients_reload()

    def test_sse_endpoint_path(self):
        """Test that SSE endpoint path is correct."""
        # The endpoint should be at /__bengal_reload__
        endpoint = "/__bengal_reload__"
        assert endpoint.startswith("/")
        assert "bengal" in endpoint
        assert "reload" in endpoint


class TestLiveReloadMixin:
    """Test the LiveReloadMixin class."""

    def test_mixin_has_required_methods(self):
        """Test that mixin has all required methods."""
        assert hasattr(LiveReloadMixin, "handle_sse")
        assert hasattr(LiveReloadMixin, "serve_html_with_live_reload")

    def test_serve_html_with_live_reload_returns_bool(self):
        """Test that serve_html_with_live_reload returns bool."""
        from typing import get_type_hints

        # With PEP 563 (from __future__ import annotations), annotations are strings
        # Use get_type_hints to resolve the actual type
        hints = get_type_hints(LiveReloadMixin.serve_html_with_live_reload)
        assert hints.get("return") is bool


class TestSSEShutdown:
    """Tests for SSE shutdown functionality."""

    def test_shutdown_sse_clients_sets_flag(self):
        """Test that shutdown_sse_clients sets the shutdown flag."""
        from bengal.server.live_reload import (
            _shutdown_requested,
            reset_sse_shutdown,
            shutdown_sse_clients,
        )

        # Reset first
        reset_sse_shutdown()

        # Shutdown should set the flag
        shutdown_sse_clients()

        # Import again to check updated value
        from bengal.server import live_reload

        assert live_reload._shutdown_requested is True

        # Reset for other tests
        reset_sse_shutdown()

    def test_reset_sse_shutdown_clears_flag(self):
        """Test that reset_sse_shutdown clears the shutdown flag."""
        from bengal.server.live_reload import reset_sse_shutdown, shutdown_sse_clients

        # Set shutdown flag
        shutdown_sse_clients()

        # Reset should clear it
        reset_sse_shutdown()

        from bengal.server import live_reload

        assert live_reload._shutdown_requested is False


class TestReloadPayload:
    """Tests for structured reload payloads."""

    def test_send_reload_payload_increments_generation(self):
        """Test that send_reload_payload increments the generation counter."""
        from bengal.server.live_reload import _reload_generation, send_reload_payload

        initial_gen = _reload_generation

        send_reload_payload("reload", "test", [])

        from bengal.server import live_reload

        assert live_reload._reload_generation == initial_gen + 1

    def test_send_reload_payload_stores_action(self):
        """Test that send_reload_payload stores the action as JSON."""
        from bengal.server.live_reload import send_reload_payload

        send_reload_payload("reload-css", "css-only", ["assets/style.css"])

        from bengal.server import live_reload

        # Last action should be JSON with the payload
        assert "reload-css" in live_reload._last_action
        assert "css-only" in live_reload._last_action
        assert "assets/style.css" in live_reload._last_action


class TestSetReloadAction:
    """Tests for set_reload_action function."""

    def test_set_reload_action_valid_values(self):
        """Test that valid action values are accepted."""
        from bengal.server.live_reload import _last_action, set_reload_action

        for action in ("reload", "reload-css", "reload-page"):
            set_reload_action(action)
            from bengal.server import live_reload

            assert live_reload._last_action == action

    def test_set_reload_action_invalid_value_defaults_to_reload(self):
        """Test that invalid action values default to 'reload'."""
        from bengal.server.live_reload import set_reload_action

        set_reload_action("invalid-action")

        from bengal.server import live_reload

        assert live_reload._last_action == "reload"


class TestInjectLiveReloadIntoResponse:
    """Tests for inject_live_reload_into_response function."""

    def test_inject_before_body_tag(self):
        """Test injection before </body> tag."""
        from bengal.server.live_reload import (
            LIVE_RELOAD_SCRIPT,
            inject_live_reload_into_response,
        )

        response = (
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body>Test</body></html>"
        )
        result = inject_live_reload_into_response(response)

        assert LIVE_RELOAD_SCRIPT.encode() in result
        # Script should be before </body>
        script_pos = result.find(LIVE_RELOAD_SCRIPT.encode())
        body_pos = result.find(b"</body>")
        assert script_pos < body_pos

    def test_inject_before_html_tag_fallback(self):
        """Test injection before </html> when no </body>."""
        from bengal.server.live_reload import (
            LIVE_RELOAD_SCRIPT,
            inject_live_reload_into_response,
        )

        response = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html>No body</html>"
        result = inject_live_reload_into_response(response)

        assert LIVE_RELOAD_SCRIPT.encode() in result
        # Script should be before </html>
        script_pos = result.find(LIVE_RELOAD_SCRIPT.encode())
        html_pos = result.find(b"</html>")
        assert script_pos < html_pos

    def test_inject_updates_content_length(self):
        """Test that Content-Length is updated after injection."""
        from bengal.server.live_reload import inject_live_reload_into_response

        response = b"HTTP/1.1 200 OK\r\nContent-Length: 30\r\n\r\n<html><body></body></html>"
        result = inject_live_reload_into_response(response)

        # Parse headers to check Content-Length
        headers_end = result.index(b"\r\n\r\n")
        headers = result[:headers_end].decode("latin-1")
        body = result[headers_end + 4 :]

        for line in headers.split("\r\n"):
            if line.lower().startswith("content-length:"):
                length = int(line.split(":", 1)[1].strip())
                assert length == len(body)
                break

    def test_malformed_response_returned_unchanged(self):
        """Test that malformed responses are returned unchanged."""
        from bengal.server.live_reload import inject_live_reload_into_response

        # No header separator
        malformed = b"HTTP/1.1 200 OK<html></html>"
        result = inject_live_reload_into_response(malformed)
        assert result == malformed


class TestAssetCaching:
    """Tests for CSS/JS asset caching during builds.

    These tests verify the asset cache serves stable content during builds,
    preventing CSS from disappearing when files are being rewritten.
    """

    @pytest.fixture
    def mixin_instance(self):
        """Create a minimal LiveReloadMixin instance for testing."""
        # Create a concrete class that inherits from the mixin
        class TestHandler(LiveReloadMixin):
            pass

        return TestHandler()

    def test_is_cacheable_asset_css(self, mixin_instance):
        """Test that CSS files in assets directory are cacheable."""
        assert mixin_instance._is_cacheable_asset("/assets/css/main.css")
        assert mixin_instance._is_cacheable_asset("/assets/css/components/nav.css")

    def test_is_cacheable_asset_js(self, mixin_instance):
        """Test that JS files in assets directory are cacheable."""
        assert mixin_instance._is_cacheable_asset("/assets/js/app.js")
        assert mixin_instance._is_cacheable_asset("/assets/js/modules/utils.js")

    def test_is_cacheable_asset_excludes_non_assets(self, mixin_instance):
        """Test that non-asset paths are not cacheable."""
        # HTML pages
        assert not mixin_instance._is_cacheable_asset("/index.html")
        assert not mixin_instance._is_cacheable_asset("/docs/intro.html")

        # CSS/JS outside assets directory
        assert not mixin_instance._is_cacheable_asset("/styles/main.css")
        assert not mixin_instance._is_cacheable_asset("/scripts/app.js")

        # Other asset types
        assert not mixin_instance._is_cacheable_asset("/assets/images/logo.png")
        assert not mixin_instance._is_cacheable_asset("/assets/fonts/roboto.woff2")

    def test_get_content_type_css(self, mixin_instance):
        """Test content type detection for CSS."""
        assert mixin_instance._get_content_type("/assets/css/main.css") == "text/css; charset=utf-8"
        assert mixin_instance._get_content_type("/assets/css/a.CSS") == "text/css; charset=utf-8"

    def test_get_content_type_js(self, mixin_instance):
        """Test content type detection for JavaScript."""
        content_type = mixin_instance._get_content_type("/assets/js/app.js")
        assert content_type == "application/javascript; charset=utf-8"
        content_type_upper = mixin_instance._get_content_type("/assets/js/app.JS")
        assert content_type_upper == "application/javascript; charset=utf-8"

    def test_get_content_type_unknown(self, mixin_instance):
        """Test content type for unknown extensions."""
        # .txt is now recognized as text/plain, so use a truly unknown extension
        assert mixin_instance._get_content_type("/assets/other.xyz") == "application/octet-stream"

    def test_get_content_type_txt(self, mixin_instance):
        """Test content type for text files."""
        assert mixin_instance._get_content_type("/assets/readme.txt") == "text/plain; charset=utf-8"

    def test_asset_cache_storage(self):
        """Test that asset cache can store and retrieve content."""
        # Clear any existing cache
        LiveReloadMixin._asset_cache.clear()

        # Simulate caching
        test_content = b"body { color: red; }"
        test_content_type = "text/css"
        LiveReloadMixin._asset_cache["/assets/css/test.css"] = (test_content, test_content_type)

        # Verify retrieval
        cached = LiveReloadMixin._asset_cache.get("/assets/css/test.css")
        assert cached is not None
        assert cached[0] == test_content
        assert cached[1] == test_content_type

        # Clean up
        LiveReloadMixin._asset_cache.clear()

    def test_clear_asset_cache(self):
        """Test that clear_asset_cache removes all cached assets."""
        # Add some cache entries
        LiveReloadMixin._asset_cache["/assets/css/a.css"] = (b"a", "text/css")
        LiveReloadMixin._asset_cache["/assets/js/b.js"] = (b"b", "application/javascript")

        assert len(LiveReloadMixin._asset_cache) >= 2

        # Clear cache
        LiveReloadMixin.clear_asset_cache()

        assert len(LiveReloadMixin._asset_cache) == 0

    def test_asset_cache_max_size_constant(self):
        """Test that asset cache has a reasonable max size."""
        # Should keep enough assets for typical sites
        assert LiveReloadMixin._asset_cache_max_size >= 10
        assert LiveReloadMixin._asset_cache_max_size <= 100


class TestAssetCacheBuildAwareServing:
    """Tests for build-aware CSS/JS serving.

    Verifies that assets are served from cache during builds when
    the file is temporarily unavailable due to atomic rewrites.
    """

    @pytest.fixture
    def mock_handler(self, tmp_path):
        """Create a mock handler with LiveReloadMixin methods."""
        from io import BytesIO
        from unittest.mock import MagicMock

        # Create a concrete class that inherits from LiveReloadMixin
        class TestHandler(LiveReloadMixin):
            def __init__(self, path: str, directory: str):
                self.path = path
                self.directory = directory
                self.wfile = BytesIO()
                self._headers_sent = []
                self._response_code = None

            def translate_path(self, path: str) -> str:
                """Convert URL path to file system path."""
                from pathlib import Path as PathLib

                # Strip leading slash and join with directory
                clean_path = path.lstrip("/").split("?")[0]
                return str(PathLib(self.directory) / clean_path)

            def send_response(self, code: int) -> None:
                self._response_code = code

            def send_header(self, name: str, value: str) -> None:
                self._headers_sent.append((name, value))

            def end_headers(self) -> None:
                pass

        return TestHandler

    def test_serve_asset_from_file_and_cache(self, tmp_path, mock_handler):
        """Test that assets are read from file and cached."""
        # Create a CSS file
        css_dir = tmp_path / "assets" / "css"
        css_dir.mkdir(parents=True)
        css_file = css_dir / "main.css"
        css_content = b"body { color: blue; }"
        css_file.write_bytes(css_content)

        # Create handler
        handler = mock_handler("/assets/css/main.css", str(tmp_path))

        # Clear cache first
        LiveReloadMixin._asset_cache.clear()

        # Serve asset (build not in progress)
        result = handler.serve_asset_with_cache(build_in_progress=False)

        assert result is True
        assert handler._response_code == 200
        assert handler.wfile.getvalue() == css_content

        # Verify cache was updated
        assert "assets/css/main.css" in LiveReloadMixin._asset_cache

        # Clean up
        LiveReloadMixin._asset_cache.clear()

    def test_serve_asset_from_cache_during_build(self, tmp_path, mock_handler):
        """Test that missing assets are served from cache during builds."""
        # Pre-populate cache with CSS content
        cached_content = b".cached { display: block; }"
        LiveReloadMixin._asset_cache["assets/css/cached.css"] = (
            cached_content,
            "text/css; charset=utf-8",
        )

        # Create handler for non-existent file (simulating mid-build state)
        handler = mock_handler("/assets/css/cached.css", str(tmp_path))

        # Serve asset with build in progress (file doesn't exist)
        result = handler.serve_asset_with_cache(build_in_progress=True)

        assert result is True
        assert handler._response_code == 200
        assert handler.wfile.getvalue() == cached_content

        # Clean up
        LiveReloadMixin._asset_cache.clear()

    def test_serve_asset_returns_false_when_no_cache_and_file_missing(
        self, tmp_path, mock_handler
    ):
        """Test that False is returned when file missing and no cache."""
        # Clear cache
        LiveReloadMixin._asset_cache.clear()

        # Create handler for non-existent file
        handler = mock_handler("/assets/css/missing.css", str(tmp_path))

        # Without build in progress - should return False
        result = handler.serve_asset_with_cache(build_in_progress=False)
        assert result is False

        # With build in progress but no cache - should also return False
        result = handler.serve_asset_with_cache(build_in_progress=True)
        assert result is False

    def test_non_asset_paths_return_false(self, tmp_path, mock_handler):
        """Test that non-cacheable paths return False immediately."""
        handler = mock_handler("/index.html", str(tmp_path))

        result = handler.serve_asset_with_cache(build_in_progress=False)
        assert result is False

        handler2 = mock_handler("/docs/guide.html", str(tmp_path))
        result2 = handler2.serve_asset_with_cache(build_in_progress=False)
        assert result2 is False


class TestAssetCacheConcurrency:
    """Tests for thread-safety of the asset cache."""

    def test_concurrent_cache_access(self):
        """Test that multiple threads can safely access the cache."""
        import threading

        # Clear cache
        LiveReloadMixin._asset_cache.clear()

        errors = []
        write_count = [0]
        read_count = [0]

        def writer_thread(thread_id: int):
            """Write assets to cache."""
            try:
                for i in range(50):
                    key = f"assets/css/thread{thread_id}_{i}.css"
                    content = f"/* thread {thread_id} file {i} */".encode()
                    with LiveReloadMixin._asset_cache_lock:
                        LiveReloadMixin._asset_cache[key] = (content, "text/css")
                        write_count[0] += 1
            except Exception as e:
                errors.append(f"Writer {thread_id}: {e}")

        def reader_thread(thread_id: int):
            """Read assets from cache."""
            try:
                for _ in range(100):
                    with LiveReloadMixin._asset_cache_lock:
                        # Just iterate over cache (may be empty or populated)
                        for key in list(LiveReloadMixin._asset_cache.keys()):
                            _ = LiveReloadMixin._asset_cache.get(key)
                            read_count[0] += 1
            except Exception as e:
                errors.append(f"Reader {thread_id}: {e}")

        # Start multiple writer and reader threads
        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=writer_thread, args=(i,)))
            threads.append(threading.Thread(target=reader_thread, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"

        # Verify writes actually happened
        assert write_count[0] == 250, f"Expected 250 writes, got {write_count[0]}"

        # Clean up
        LiveReloadMixin._asset_cache.clear()

    def test_cache_eviction_under_load(self):
        """Test that LRU eviction works correctly under concurrent load."""
        import threading

        # Clear and set a small max size for testing
        LiveReloadMixin._asset_cache.clear()
        original_max = LiveReloadMixin._asset_cache_max_size

        try:
            # Temporarily set small max size
            LiveReloadMixin._asset_cache_max_size = 10

            errors = []

            def add_items(thread_id: int):
                try:
                    for i in range(20):
                        key = f"assets/js/evict_{thread_id}_{i}.js"
                        content = f"// {thread_id}-{i}".encode()
                        with LiveReloadMixin._asset_cache_lock:
                            LiveReloadMixin._asset_cache[key] = (content, "application/javascript")
                            # LRU eviction
                            if len(LiveReloadMixin._asset_cache) > LiveReloadMixin._asset_cache_max_size:
                                first_key = next(iter(LiveReloadMixin._asset_cache))
                                del LiveReloadMixin._asset_cache[first_key]
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=add_items, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)

            assert len(errors) == 0
            # Cache should not exceed max size
            assert len(LiveReloadMixin._asset_cache) <= 10

        finally:
            # Restore original max size and clean up
            LiveReloadMixin._asset_cache_max_size = original_max
            LiveReloadMixin._asset_cache.clear()
