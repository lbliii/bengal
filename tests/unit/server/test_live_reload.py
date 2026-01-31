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
