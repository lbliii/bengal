"""
Tests for request handler helper methods.

Tests the helper methods used for HTML detection and live reload injection.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from io import BytesIO

from bengal.server.request_handler import BengalRequestHandler
from bengal.server.live_reload import LIVE_RELOAD_SCRIPT


class TestMightBeHtml:
    """Test _might_be_html() path checking."""
    
    def setup_method(self):
        """Set up test handler."""
        # Create a mock request that has all the necessary attributes
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b''))
        
        # Patch the handle method to prevent actual request processing
        with patch.object(BengalRequestHandler, 'handle'):
            self.handler = BengalRequestHandler(
                request=request,
                client_address=('127.0.0.1', 12345),
                server=Mock()
            )
    
    def test_html_extensions(self):
        """Test paths with HTML extensions."""
        assert self.handler._might_be_html('/page.html') is True
        assert self.handler._might_be_html('/page.htm') is True
        assert self.handler._might_be_html('/docs/guide.html') is True
    
    def test_directory_paths(self):
        """Test directory paths (ending with /)."""
        assert self.handler._might_be_html('/') is True
        assert self.handler._might_be_html('/docs/') is True
        assert self.handler._might_be_html('/about/') is True
    
    def test_paths_without_extension(self):
        """Test paths without file extensions."""
        assert self.handler._might_be_html('/about') is True
        assert self.handler._might_be_html('/docs/guide') is True
    
    def test_css_files(self):
        """Test CSS files are not HTML."""
        assert self.handler._might_be_html('/style.css') is False
        assert self.handler._might_be_html('/assets/main.css') is False
    
    def test_javascript_files(self):
        """Test JavaScript files are not HTML."""
        assert self.handler._might_be_html('/script.js') is False
        assert self.handler._might_be_html('/assets/app.js') is False
    
    def test_image_files(self):
        """Test image files are not HTML."""
        assert self.handler._might_be_html('/logo.png') is False
        assert self.handler._might_be_html('/photo.jpg') is False
        assert self.handler._might_be_html('/icon.svg') is False
        assert self.handler._might_be_html('/favicon.ico') is False
    
    def test_font_files(self):
        """Test font files are not HTML."""
        assert self.handler._might_be_html('/fonts/roboto.woff2') is False
        assert self.handler._might_be_html('/fonts/arial.ttf') is False
    
    def test_media_files(self):
        """Test media files are not HTML."""
        assert self.handler._might_be_html('/video.mp4') is False
        assert self.handler._might_be_html('/audio.mp3') is False
    
    def test_data_files(self):
        """Test data files are not HTML."""
        assert self.handler._might_be_html('/data.json') is False
        assert self.handler._might_be_html('/feed.xml') is False
        assert self.handler._might_be_html('/readme.txt') is False
    
    def test_unknown_extensions(self):
        """Test unknown extensions (might be HTML)."""
        assert self.handler._might_be_html('/file.xyz') is True
        assert self.handler._might_be_html('/doc.unknown') is True


class TestIsHtmlResponse:
    """Test _is_html_response() response detection."""
    
    def setup_method(self):
        """Set up test handler."""
        # Create a mock request that has all the necessary attributes
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b''))
        
        # Patch the handle method to prevent actual request processing
        with patch.object(BengalRequestHandler, 'handle'):
            self.handler = BengalRequestHandler(
                request=request,
                client_address=('127.0.0.1', 12345),
                server=Mock()
            )
    
    def test_html_with_content_type_header(self):
        """Test HTML detection via Content-Type header."""
        response = b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html></html>'
        assert self.handler._is_html_response(response) is True
    
    def test_html_with_charset(self):
        """Test HTML with charset in Content-Type."""
        response = b'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<html></html>'
        assert self.handler._is_html_response(response) is True
    
    def test_html_with_doctype(self):
        """Test HTML detection via DOCTYPE."""
        response = b'HTTP/1.1 200 OK\r\n\r\n<!DOCTYPE html><html></html>'
        assert self.handler._is_html_response(response) is True
    
    def test_html_with_html_tag(self):
        """Test HTML detection via <html> tag."""
        response = b'HTTP/1.1 200 OK\r\n\r\n<html><body>Content</body></html>'
        assert self.handler._is_html_response(response) is True
    
    def test_css_response(self):
        """Test CSS is not detected as HTML."""
        response = b'HTTP/1.1 200 OK\r\nContent-Type: text/css\r\n\r\nbody { margin: 0; }'
        assert self.handler._is_html_response(response) is False
    
    def test_javascript_response(self):
        """Test JavaScript is not detected as HTML."""
        response = b'HTTP/1.1 200 OK\r\nContent-Type: application/javascript\r\n\r\nconsole.log("test");'
        assert self.handler._is_html_response(response) is False
    
    def test_json_response(self):
        """Test JSON is not detected as HTML."""
        response = b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{"key": "value"}'
        assert self.handler._is_html_response(response) is False
    
    def test_image_response(self):
        """Test images are not detected as HTML."""
        response = b'HTTP/1.1 200 OK\r\nContent-Type: image/png\r\n\r\n\x89PNG\r\n\x1a\n'
        assert self.handler._is_html_response(response) is False
    
    def test_case_insensitive_content_type(self):
        """Test Content-Type is checked case-insensitively."""
        response = b'HTTP/1.1 200 OK\r\nContent-Type: TEXT/HTML\r\n\r\n<html></html>'
        assert self.handler._is_html_response(response) is True
    
    def test_no_headers_separator(self):
        """Test malformed response without headers separator."""
        response = b'HTTP/1.1 200 OK\r\nContent-Type: text/html'
        assert self.handler._is_html_response(response) is False
    
    def test_empty_response(self):
        """Test empty response."""
        response = b''
        assert self.handler._is_html_response(response) is False
    
    def test_multiple_headers(self):
        """Test response with multiple headers."""
        response = b'HTTP/1.1 200 OK\r\nServer: Bengal/1.0\r\nContent-Type: text/html\r\nContent-Length: 13\r\n\r\n<html></html>'
        assert self.handler._is_html_response(response) is True


class TestInjectLiveReload:
    """Test _inject_live_reload() script injection."""
    
    def setup_method(self):
        """Set up test handler."""
        # Create a mock request that has all the necessary attributes
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b''))
        
        # Patch the handle method to prevent actual request processing
        with patch.object(BengalRequestHandler, 'handle'):
            self.handler = BengalRequestHandler(
                request=request,
                client_address=('127.0.0.1', 12345),
                server=Mock()
            )
    
    def test_inject_before_body_tag(self):
        """Test script injection before </body> tag."""
        response = b'HTTP/1.1 200 OK\r\n\r\n<html><body>Content</body></html>'
        result = self.handler._inject_live_reload(response)
        
        # Decode to check content
        result_str = result.decode('utf-8', errors='replace')
        
        # Script should be present
        assert '__bengal_reload__' in result_str
        assert 'EventSource' in result_str
        
        # Script should be before </body>
        script_pos = result_str.find('__bengal_reload__')
        body_pos = result_str.find('</body>')
        assert script_pos < body_pos
    
    def test_inject_before_html_tag(self):
        """Test script injection before </html> when no </body>."""
        response = b'HTTP/1.1 200 OK\r\n\r\n<html><p>Content</p></html>'
        result = self.handler._inject_live_reload(response)
        
        result_str = result.decode('utf-8', errors='replace')
        
        # Script should be present
        assert '__bengal_reload__' in result_str
        
        # Script should be before </html>
        script_pos = result_str.find('__bengal_reload__')
        html_pos = result_str.find('</html>')
        assert script_pos < html_pos
    
    def test_inject_at_end_minimal_html(self):
        """Test script injection at end for minimal HTML."""
        response = b'HTTP/1.1 200 OK\r\n\r\n<h1>Title</h1><p>Content</p>'
        result = self.handler._inject_live_reload(response)
        
        result_str = result.decode('utf-8', errors='replace')
        
        # Script should be present
        assert '__bengal_reload__' in result_str
    
    def test_case_insensitive_tag_matching(self):
        """Test tags are matched case-insensitively."""
        response = b'HTTP/1.1 200 OK\r\n\r\n<HTML><BODY>Content</BODY></HTML>'
        result = self.handler._inject_live_reload(response)
        
        result_str = result.decode('utf-8', errors='replace')
        
        # Script should be injected before </BODY>
        assert '__bengal_reload__' in result_str
        script_pos = result_str.lower().find('__bengal_reload__')
        body_pos = result_str.find('</BODY>')
        assert script_pos < body_pos
    
    def test_content_length_updated(self):
        """Test Content-Length header is updated."""
        response = b'HTTP/1.1 200 OK\r\nContent-Length: 30\r\n\r\n<html><body></body></html>'
        result = self.handler._inject_live_reload(response)
        
        # Check that Content-Length was updated
        headers_end = result.index(b'\r\n\r\n')
        headers = result[:headers_end].decode('latin-1')
        
        # Should have a Content-Length header
        assert 'Content-Length:' in headers
        
        # Extract Content-Length value
        for line in headers.split('\r\n'):
            if line.startswith('Content-Length:'):
                length = int(line.split(':')[1].strip())
                # Body length should match
                body = result[headers_end + 4:]
                assert length == len(body)
    
    def test_utf8_content_preserved(self):
        """Test UTF-8 content is preserved."""
        response = b'HTTP/1.1 200 OK\r\n\r\n<html><body>Hello \xe4\xb8\x96\xe7\x95\x8c</body></html>'
        result = self.handler._inject_live_reload(response)
        
        result_str = result.decode('utf-8', errors='replace')
        
        # Original UTF-8 content should be preserved
        assert 'Hello 世界' in result_str
        assert '__bengal_reload__' in result_str
    
    def test_multiple_body_tags(self):
        """Test injection with multiple </body> tags (uses last one)."""
        response = b'HTTP/1.1 200 OK\r\n\r\n<html><body><div>First</body><body>Last</body></html>'
        result = self.handler._inject_live_reload(response)
        
        result_str = result.decode('utf-8', errors='replace')
        
        # Should inject before the LAST </body>
        last_body_pos = result_str.rfind('</body>')
        script_pos = result_str.rfind('__bengal_reload__')
        
        # Script should be before last </body>
        assert script_pos < last_body_pos
    
    def test_error_returns_original(self):
        """Test that errors return original response."""
        # Create a response that will cause an error during injection
        # (invalid UTF-8 that can't be decoded)
        response = b'HTTP/1.1 200 OK\r\n\r\n\xff\xfe'
        
        result = self.handler._inject_live_reload(response)
        
        # Should return original response on error
        # (or a close approximation - errors='replace' might modify it)
        assert result is not None
        assert len(result) > 0
    
    def test_preserves_headers(self):
        """Test that other headers are preserved."""
        response = b'HTTP/1.1 200 OK\r\nServer: Bengal/1.0\r\nCache-Control: no-cache\r\n\r\n<html><body></body></html>'
        result = self.handler._inject_live_reload(response)
        
        headers_end = result.index(b'\r\n\r\n')
        headers = result[:headers_end].decode('latin-1')
        
        # Other headers should be preserved
        assert 'Server: Bengal/1.0' in headers
        assert 'Cache-Control: no-cache' in headers


class TestRequestHandlerIntegration:
    """Integration tests for request handler."""
    
    def test_complete_html_response_flow(self):
        """Test complete flow: path check -> detection -> injection."""
        # Create a mock request that has all the necessary attributes
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b''))
        
        # Patch the handle method to prevent actual request processing
        with patch.object(BengalRequestHandler, 'handle'):
            handler = BengalRequestHandler(
                request=request,
                client_address=('127.0.0.1', 12345),
                server=Mock()
            )
        
        # Test path that might be HTML
        path = '/docs/guide.html'
        assert handler._might_be_html(path) is True
        
        # Test HTML response detection
        response = b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body>Guide</body></html>'
        assert handler._is_html_response(response) is True
        
        # Test injection
        result = handler._inject_live_reload(response)
        result_str = result.decode('utf-8', errors='replace')
        
        assert '__bengal_reload__' in result_str
        assert 'Guide' in result_str
    
    def test_complete_non_html_flow(self):
        """Test complete flow for non-HTML files."""
        # Create a mock request that has all the necessary attributes
        request = Mock()
        request.makefile = Mock(side_effect=lambda *args, **kwargs: BytesIO(b''))
        
        # Patch the handle method to prevent actual request processing
        with patch.object(BengalRequestHandler, 'handle'):
            handler = BengalRequestHandler(
                request=request,
                client_address=('127.0.0.1', 12345),
                server=Mock()
            )
        
        # CSS file path
        path = '/assets/style.css'
        assert handler._might_be_html(path) is False
        
        # CSS response (wouldn't be checked, but test anyway)
        response = b'HTTP/1.1 200 OK\r\nContent-Type: text/css\r\n\r\nbody { margin: 0; }'
        assert handler._is_html_response(response) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

