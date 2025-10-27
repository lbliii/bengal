"""
Tests for request handler helper methods.

Tests the helper methods used for HTML detection and live reload injection.
"""

import http
import http.server
from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from bengal.server.request_handler import BengalRequestHandler


class TestMightBeHtml:
    """Test _might_be_html() path checking."""

    def setup_method(self):
        """Set up test handler."""
        # Create a mock request that has all the necessary attributes
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b""))

        # Patch the handle method to prevent actual request processing
        with patch.object(BengalRequestHandler, "handle"):
            self.handler = BengalRequestHandler(
                request=request, client_address=("127.0.0.1", 12345), server=Mock()
            )

    def test_html_extensions(self):
        """Test paths with HTML extensions."""
        assert self.handler._might_be_html("/page.html") is True
        assert self.handler._might_be_html("/page.htm") is True
        assert self.handler._might_be_html("/docs/guide.html") is True

    def test_directory_paths(self):
        """Test directory paths (ending with /)."""
        assert self.handler._might_be_html("/") is True
        assert self.handler._might_be_html("/docs/") is True
        assert self.handler._might_be_html("/about/") is True

    def test_paths_without_extension(self):
        """Test paths without file extensions."""
        assert self.handler._might_be_html("/about") is True
        assert self.handler._might_be_html("/docs/guide") is True

    def test_css_files(self):
        """Test CSS files are not HTML."""
        assert self.handler._might_be_html("/style.css") is False
        assert self.handler._might_be_html("/assets/main.css") is False

    def test_javascript_files(self):
        """Test JavaScript files are not HTML."""
        assert self.handler._might_be_html("/script.js") is False
        assert self.handler._might_be_html("/assets/app.js") is False

    def test_image_files(self):
        """Test image files are not HTML."""
        assert self.handler._might_be_html("/logo.png") is False
        assert self.handler._might_be_html("/photo.jpg") is False
        assert self.handler._might_be_html("/icon.svg") is False
        assert self.handler._might_be_html("/favicon.ico") is False

    def test_font_files(self):
        """Test font files are not HTML."""
        assert self.handler._might_be_html("/fonts/roboto.woff2") is False
        assert self.handler._might_be_html("/fonts/arial.ttf") is False

    def test_media_files(self):
        """Test media files are not HTML."""
        assert self.handler._might_be_html("/video.mp4") is False
        assert self.handler._might_be_html("/audio.mp3") is False

    def test_data_files(self):
        """Test data files are not HTML."""
        assert self.handler._might_be_html("/data.json") is False
        assert self.handler._might_be_html("/feed.xml") is False
        assert self.handler._might_be_html("/readme.txt") is False

    def test_unknown_extensions(self):
        """Test unknown extensions (might be HTML)."""
        assert self.handler._might_be_html("/file.xyz") is True
        assert self.handler._might_be_html("/doc.unknown") is True


class TestIsHtmlResponse:
    """Test _is_html_response() response detection."""

    def setup_method(self):
        """Set up test handler."""
        # Create a mock request that has all the necessary attributes
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b""))

        # Patch the handle method to prevent actual request processing
        with patch.object(BengalRequestHandler, "handle"):
            self.handler = BengalRequestHandler(
                request=request, client_address=("127.0.0.1", 12345), server=Mock()
            )

    def test_html_with_content_type_header(self):
        """Test HTML detection via Content-Type header."""
        response = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html></html>"
        assert self.handler._is_html_response(response) is True

    def test_html_with_charset(self):
        """Test HTML with charset in Content-Type."""
        response = b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<html></html>"
        assert self.handler._is_html_response(response) is True

    def test_html_with_doctype(self):
        """Test HTML detection via DOCTYPE."""
        response = b"HTTP/1.1 200 OK\r\n\r\n<!DOCTYPE html><html></html>"
        assert self.handler._is_html_response(response) is True

    def test_html_with_html_tag(self):
        """Test HTML detection via <html> tag."""
        response = b"HTTP/1.1 200 OK\r\n\r\n<html><body>Content</body></html>"
        assert self.handler._is_html_response(response) is True

    def test_css_response(self):
        """Test CSS is not detected as HTML."""
        response = b"HTTP/1.1 200 OK\r\nContent-Type: text/css\r\n\r\nbody { margin: 0; }"
        assert self.handler._is_html_response(response) is False

    def test_javascript_response(self):
        """Test JavaScript is not detected as HTML."""
        response = (
            b'HTTP/1.1 200 OK\r\nContent-Type: application/javascript\r\n\r\nconsole.log("test");'
        )
        assert self.handler._is_html_response(response) is False

    def test_json_response(self):
        """Test JSON is not detected as HTML."""
        response = b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{"key": "value"}'
        assert self.handler._is_html_response(response) is False

    def test_image_response(self):
        """Test images are not detected as HTML."""
        response = b"HTTP/1.1 200 OK\r\nContent-Type: image/png\r\n\r\n\x89PNG\r\n\x1a\n"
        assert self.handler._is_html_response(response) is False

    def test_case_insensitive_content_type(self):
        """Test Content-Type is checked case-insensitively."""
        response = b"HTTP/1.1 200 OK\r\nContent-Type: TEXT/HTML\r\n\r\n<html></html>"
        assert self.handler._is_html_response(response) is True

    def test_no_headers_separator(self):
        """Test malformed response without headers separator."""
        response = b"HTTP/1.1 200 OK\r\nContent-Type: text/html"
        assert self.handler._is_html_response(response) is False

    def test_empty_response(self):
        """Test empty response."""
        response = b""
        assert self.handler._is_html_response(response) is False

    def test_multiple_headers(self):
        """Test response with multiple headers."""
        response = b"HTTP/1.1 200 OK\r\nServer: Bengal/1.0\r\nContent-Type: text/html\r\nContent-Length: 13\r\n\r\n<html></html>"
        assert self.handler._is_html_response(response) is True


class TestServeHtmlWithLiveReload:
    """Test serve_html_with_live_reload() script injection via mixin path."""

    def setup_method(self):
        """Set up test handler."""
        # Create a mock request that has all the necessary attributes
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b""))

        # Patch the handle method to prevent actual request processing
        with patch.object(BengalRequestHandler, "handle"):
            self.handler = BengalRequestHandler(
                request=request, client_address=("127.0.0.1", 12345), server=Mock()
            )

    def _serve_temp_html(self, tmp_path, html: str) -> str:
        # Create a temporary HTML file
        tmp_path.mkdir(parents=True, exist_ok=True)
        p = tmp_path / "index.html"
        p.write_text(html)

        # Point handler to directory serving
        mock_server = Mock()
        mock_server.directory = str(tmp_path)
        self.handler.server = mock_server
        self.handler.path = "/index.html"

        # Stub translate_path to map to tmp file
        def fake_translate_path(_self, path):
            from pathlib import Path as _P

            return str(_P(str(tmp_path)) / path.lstrip("/"))

        with patch.object(BengalRequestHandler, "translate_path", fake_translate_path):
            # Capture output
            buf = BytesIO()
            self.handler.wfile = buf
            served = self.handler.serve_html_with_live_reload()
            assert served is True
            return buf.getvalue().decode("utf-8", errors="replace")

    def test_inject_before_body_tag(self, tmp_path):
        """Script should be injected before </body> when present."""
        result_str = self._serve_temp_html(tmp_path, "<html><body>Content</body></html>")
        assert "__bengal_reload__" in result_str
        assert "EventSource" in result_str
        assert result_str.find("__bengal_reload__") < result_str.find("</body>")

    def test_inject_before_html_tag(self, tmp_path):
        """Script should be injected before </html> when no </body>."""
        result_str = self._serve_temp_html(tmp_path, "<html><p>Content</p></html>")
        assert "__bengal_reload__" in result_str
        assert result_str.find("__bengal_reload__") < result_str.find("</html>")

    def test_inject_at_end_minimal_html(self, tmp_path):
        """Script should be appended when no closing tags are found."""
        result_str = self._serve_temp_html(tmp_path, "<h1>Title</h1><p>Content</p>")
        assert "__bengal_reload__" in result_str

    def test_case_insensitive_tag_matching(self, tmp_path):
        """Tags are matched case-insensitively for injection location."""
        result_str = self._serve_temp_html(tmp_path, "<HTML><BODY>Content</BODY></HTML>")
        assert "__bengal_reload__" in result_str
        assert result_str.lower().find("__bengal_reload__") < result_str.find("</BODY>")

    def test_content_length_header_set(self, tmp_path):
        """Serve path should set Content-Length matching body size."""
        # Serve simple HTML and capture raw bytes
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "index.html").write_text("<html><body></body></html>")

        mock_server = Mock()
        mock_server.directory = str(tmp_path)
        self.handler.server = mock_server
        self.handler.path = "/index.html"

        buf = BytesIO()
        self.handler.wfile = buf

        def fake_translate_path(_self, path):
            return str((tmp_path / path.lstrip("/")).resolve())

        with patch.object(BengalRequestHandler, "translate_path", fake_translate_path):
            served = self.handler.serve_html_with_live_reload()
            assert served is True
            raw = buf.getvalue()
            headers_end = raw.index(b"\r\n\r\n")
            headers = raw[:headers_end].decode("latin-1")
            body = raw[headers_end + 4 :]
            # Should include Content-Length of modified content
            assert "Content-Length:" in headers
            length = None
            for line in headers.split("\r\n"):
                if line.lower().startswith("content-length:"):
                    length = int(line.split(":", 1)[1].strip())
                    break
            assert length == len(body)

    def test_utf8_content_preserved(self, tmp_path):
        """UTF-8 content is preserved during injection."""
        result_str = self._serve_temp_html(tmp_path, "<html><body>Hello 世界</body></html>")
        assert "Hello 世界" in result_str
        assert "__bengal_reload__" in result_str

    def test_multiple_body_tags(self, tmp_path):
        """Injection should target the last </body> occurrence."""
        html = "<html><body><div>First</body><body>Last</body></html>"
        result_str = self._serve_temp_html(tmp_path, html)
        last_body_pos = result_str.rfind("</body>")
        script_pos = result_str.rfind("__bengal_reload__")
        assert script_pos < last_body_pos

    def test_error_returns_404_on_missing_file(self, tmp_path):
        """Missing files should return 404 and not crash."""
        mock_server = Mock()
        mock_server.directory = str(tmp_path)
        self.handler.server = mock_server
        self.handler.path = "/does-not-exist.html"
        buf = BytesIO()
        self.handler.wfile = buf
        served = self.handler.serve_html_with_live_reload()
        assert served is True  # handler wrote an error response

    def test_no_cache_headers_set(self, tmp_path):
        """Dev no-cache headers should be present on served HTML."""
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "index.html").write_text("<html><body></body></html>")

        mock_server = Mock()
        mock_server.directory = str(tmp_path)
        self.handler.server = mock_server
        self.handler.path = "/index.html"

        buf = BytesIO()
        self.handler.wfile = buf

        def fake_translate_path(_self, path):
            return str((tmp_path / path.lstrip("/")).resolve())

        with patch.object(BengalRequestHandler, "translate_path", fake_translate_path):
            served = self.handler.serve_html_with_live_reload()
            assert served is True
            raw = buf.getvalue()
            headers_end = raw.index(b"\r\n\r\n")
            headers = raw[:headers_end].decode("latin-1").lower()
            assert "cache-control:" in headers


class TestRequestHandlerIntegration:
    """Integration tests for request handler."""

    def test_complete_html_response_flow(self):
        """Test complete flow: path check -> detection -> injection."""
        # Create a mock request that has all the necessary attributes
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b""))

        # Patch the handle method to prevent actual request processing
        with patch.object(BengalRequestHandler, "handle"):
            handler = BengalRequestHandler(
                request=request, client_address=("127.0.0.1", 12345), server=Mock()
            )

        # Test path that might be HTML
        path = "/docs/guide.html"
        assert handler._might_be_html(path) is True

        # Test HTML response detection
        response = (
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body>Guide</body></html>"
        )
        assert handler._is_html_response(response) is True

        # Test injection
        result = handler._inject_live_reload(response)
        result_str = result.decode("utf-8", errors="replace")

        assert "__bengal_reload__" in result_str
        assert "Guide" in result_str

    def test_complete_non_html_flow(self):
        """Test complete flow for non-HTML files."""
        # Create a mock request that has all the necessary attributes
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b""))

        # Patch the handle method to prevent actual request processing
        with patch.object(BengalRequestHandler, "handle"):
            handler = BengalRequestHandler(
                request=request, client_address=("127.0.0.1", 12345), server=Mock()
            )

        # CSS file path
        path = "/assets/style.css"
        assert handler._might_be_html(path) is False

        # CSS response (wouldn't be checked, but test anyway)
        response = b"HTTP/1.1 200 OK\r\nContent-Type: text/css\r\n\r\nbody { margin: 0; }"
        assert handler._is_html_response(response) is False


class TestDoGetIntegrationMinimal:
    """Minimal integration around do_GET buffering and injection."""

    def _make_handler(self):
        from io import BytesIO
        from unittest.mock import Mock

        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b""))
        with patch.object(BengalRequestHandler, "handle"):
            handler = BengalRequestHandler(
                request=request, client_address=("127.0.0.1", 12345), server=Mock()
            )
        return handler

    @pytest.mark.skip(
        reason="Phase 3: live reload now handled via template includes, not runtime injection"
    )
    def test_do_get_injects_for_html(self, tmp_path, monkeypatch):
        """HTML responses should be injected with live reload script."""
        # Create test file
        (tmp_path / "index.html").write_text("<html><body>Test</body></html>")

        # Create mock server with directory
        mock_server = Mock()
        mock_server.directory = str(tmp_path)

        # Create handler
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b""))
        handler = BengalRequestHandler(
            request=request, client_address=("127.0.0.1", 12345), server=mock_server
        )
        handler.requestline = "GET /index.html HTTP/1.1"
        handler.path = "/index.html"
        output = BytesIO()
        handler.wfile = output

        # Monkeypatch to avoid actual handle, but since we set directory, it should work
        # But to control, mock translate_path to return the file
        def fake_translate_path(self, path):
            return str(tmp_path / path.lstrip("/"))

        monkeypatch.setattr(BengalRequestHandler, "translate_path", fake_translate_path)

        # Execute
        handler.do_GET()
        result = output.getvalue().decode("utf-8", errors="replace")

        # Verify server-injected live reload script is present
        assert "__bengal_reload__" in result
        assert "Bengal Live Reload" in result  # Comment from injected script
        assert "Test" in result  # Original content preserved

    def test_do_get_bypasses_non_html(self, monkeypatch):
        """Non-HTML responses should not be modified or injected."""
        handler = self._make_handler()
        handler.path = "/assets/app.js"
        output = BytesIO()
        handler.wfile = output

        def fake_do_get(self):
            # Simulate JS asset response
            self.wfile.write(b"HTTP/1.1 200 OK\r\n")
            self.wfile.write(b"Content-Type: application/javascript\r\n")
            self.wfile.write(b"\r\n")
            self.wfile.write(b'console.log("ok");')

        monkeypatch.setattr(
            http.server.SimpleHTTPRequestHandler, "do_GET", fake_do_get, raising=True
        )

        # Execute
        handler.do_GET()
        result = output.getvalue().decode("utf-8", errors="replace")

        assert "__bengal_reload__" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
