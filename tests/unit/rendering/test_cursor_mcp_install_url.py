"""Unit tests for cursor_mcp_install_url template helper."""

from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs, unquote, urlparse

from bengal.rendering.template_functions.urls import cursor_mcp_install_url


class TestCursorMcpInstallUrl:
    def test_empty_mcp_url_returns_empty(self) -> None:
        assert cursor_mcp_install_url("") == ""
        assert cursor_mcp_install_url("   ") == ""

    def test_returns_cursor_scheme(self) -> None:
        url = cursor_mcp_install_url("https://docs.example.com/mcp")
        assert url.startswith("cursor://anysphere.cursor-deeplink/mcp/install")

    def test_config_is_base64_json_with_url(self) -> None:
        url = cursor_mcp_install_url("https://docs.example.com/mcp")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        config_b64 = params.get("config", [""])[0]
        config_json = base64.standard_b64decode(config_b64).decode("utf-8")
        config = json.loads(config_json)
        assert config["url"] == "https://docs.example.com/mcp"
        assert config["headers"] == {}

    def test_strips_trailing_slash_from_mcp_url(self) -> None:
        url = cursor_mcp_install_url("https://docs.example.com/mcp/")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        config_b64 = params.get("config", [""])[0]
        config = json.loads(base64.standard_b64decode(config_b64).decode("utf-8"))
        assert config["url"] == "https://docs.example.com/mcp"

    def test_server_name_in_query(self) -> None:
        url = cursor_mcp_install_url("https://x.com/mcp", server_name="My Docs")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        name = params.get("name", [""])[0]
        assert unquote(name) == "My Docs"

    def test_default_server_name_is_docs(self) -> None:
        url = cursor_mcp_install_url("https://x.com/mcp")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        name = params.get("name", [""])[0]
        assert unquote(name) == "Docs"
