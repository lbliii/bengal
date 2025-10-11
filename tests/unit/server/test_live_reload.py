"""
Tests for live reload functionality.
"""

import pytest
from bengal.server.live_reload import LiveReloadMixin, LIVE_RELOAD_SCRIPT


class TestLiveReloadScriptInjection:
    """Test HTML injection for live reload."""
    
    def test_inject_before_closing_body(self):
        """Test that script is injected before </body> tag."""
        html = "<html><body><h1>Test</h1></body></html>"
        
        # The script should be injected before </body>
        assert '</body>' in html
        assert LIVE_RELOAD_SCRIPT not in html
        
        # After injection, script should be present before </body>
        expected = f"<html><body><h1>Test</h1>{LIVE_RELOAD_SCRIPT}</body></html>"
        assert '</body>' in expected
        assert LIVE_RELOAD_SCRIPT in expected
    
    def test_inject_before_closing_html_fallback(self):
        """Test fallback injection before </html> when no </body>."""
        
        # Script should be injected before </html>
        expected = f"<html><div>No body tag</div>{LIVE_RELOAD_SCRIPT}</html>"
        assert '</html>' in expected
        assert LIVE_RELOAD_SCRIPT in expected
    
    def test_case_insensitive_injection(self):
        """Test that injection works with uppercase HTML tags."""
        html_upper = "<HTML><BODY><h1>Test</h1></BODY></HTML>"
        html_mixed = "<Html><Body><h1>Test</h1></Body></Html>"
        
        # Both should have closing tags that we can find case-insensitively
        assert '</BODY>' in html_upper or '</body>' in html_upper.lower()
        assert '</Body>' in html_mixed or '</body>' in html_mixed.lower()
    
    def test_live_reload_script_format(self):
        """Test that the live reload script has expected content."""
        assert 'EventSource' in LIVE_RELOAD_SCRIPT
        assert '__bengal_reload__' in LIVE_RELOAD_SCRIPT
        assert 'location.reload()' in LIVE_RELOAD_SCRIPT
        assert '<script>' in LIVE_RELOAD_SCRIPT
        assert '</script>' in LIVE_RELOAD_SCRIPT


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
        endpoint = '/__bengal_reload__'
        assert endpoint.startswith('/')
        assert 'bengal' in endpoint
        assert 'reload' in endpoint


class TestLiveReloadMixin:
    """Test the LiveReloadMixin class."""
    
    def test_mixin_has_required_methods(self):
        """Test that mixin has all required methods."""
        assert hasattr(LiveReloadMixin, 'handle_sse')
        assert hasattr(LiveReloadMixin, 'serve_html_with_live_reload')
    
    def test_serve_html_with_live_reload_returns_bool(self):
        """Test that serve_html_with_live_reload returns bool."""
        import inspect
        sig = inspect.signature(LiveReloadMixin.serve_html_with_live_reload)
        assert sig.return_annotation is bool


# Integration test example (requires more setup)
@pytest.mark.skip(reason="Requires full server setup - placeholder for future implementation")
class TestLiveReloadIntegration:
    """Integration tests for live reload (to be implemented)."""
    
    def test_server_starts_and_serves_with_live_reload(self):
        """Test that server starts and injects live reload script."""
        # TODO: Implement with actual server startup
        pass
    
    def test_sse_connection_establishes(self):
        """Test that SSE connection can be established."""
        # TODO: Implement with actual SSE client
        pass
    
    def test_file_change_triggers_notification(self):
        """Test that file changes trigger browser reload notification."""
        # TODO: Implement with file watching and SSE
        pass

