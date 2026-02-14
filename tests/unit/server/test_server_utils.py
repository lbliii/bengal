from types import SimpleNamespace

from bengal.server.utils import (
    apply_dev_no_cache_headers,
    find_html_injection_point,
    get_content_type,
    get_dev_config,
    get_dev_server_config,
    get_icons,
    get_timestamp,
    safe_int,
)


def test_apply_dev_no_cache_headers_adds_headers():
    collected = {}

    def sender(key, value):
        collected[key] = value

    apply_dev_no_cache_headers(SimpleNamespace(send_header=sender))
    assert "Cache-Control" in collected
    assert "no-store" in collected["Cache-Control"]
    assert collected["Pragma"] == "no-cache"


def test_get_dev_config_nested():
    cfg = {"dev": {"watch": {"backend": "polling", "debounce_ms": 250}}}
    assert get_dev_config(cfg, "watch", "backend", default="auto") == "polling"
    assert get_dev_config(cfg, "watch", "debounce_ms", default=0) == 250
    assert get_dev_config(cfg, "watch", "missing", default=1) == 1


def test_safe_int_variants():
    assert safe_int("300", 0) == 300
    assert safe_int(150, 0) == 150
    assert safe_int("bad", 42) == 42
    assert safe_int(None, 7) == 7


# --- Tests for new utility functions ---


def test_get_icons_returns_icon_set():
    """Test that get_icons returns an IconSet with expected attributes."""
    icons = get_icons()
    # Should have standard icon attributes
    assert hasattr(icons, "success")
    assert hasattr(icons, "warning")
    assert hasattr(icons, "error")
    # Success should be a non-empty string
    assert icons.success


def test_get_timestamp_format():
    """Test that get_timestamp returns HH:MM:SS format."""
    timestamp = get_timestamp()
    # Should be in format HH:MM:SS (8 characters)
    assert len(timestamp) == 8
    parts = timestamp.split(":")
    assert len(parts) == 3
    # Hours, minutes, seconds should all be numeric
    for part in parts:
        assert part.isdigit()


def test_get_content_type_known_extensions():
    """Test content type detection for known extensions."""
    assert get_content_type("/assets/style.css") == "text/css; charset=utf-8"
    assert get_content_type("script.js") == "application/javascript; charset=utf-8"
    assert get_content_type("/page.html") == "text/html; charset=utf-8"
    assert get_content_type("data.json") == "application/json; charset=utf-8"
    assert get_content_type("icon.svg") == "image/svg+xml"
    assert get_content_type("image.png") == "image/png"
    assert get_content_type("font.woff2") == "font/woff2"


def test_get_content_type_unknown_extension():
    """Test content type detection for unknown extensions."""
    assert get_content_type("file.xyz") == "application/octet-stream"
    assert get_content_type("noextension") == "application/octet-stream"


def test_find_html_injection_point_body_tag():
    """Test finding injection point before </body>."""
    html = b"<html><body>Hello</body></html>"
    idx = find_html_injection_point(html)
    assert idx == 17  # Points to '<' in '</body>'
    assert html[idx : idx + 7] == b"</body>"


def test_find_html_injection_point_uppercase_body():
    """Test finding injection point with uppercase </BODY>."""
    html = b"<html><body>Hello</BODY></html>"
    idx = find_html_injection_point(html)
    assert html[idx : idx + 7] == b"</BODY>"


def test_find_html_injection_point_html_fallback():
    """Test fallback to </html> when no </body>."""
    html = b"<html>No body tag here</html>"
    idx = find_html_injection_point(html)
    assert html[idx : idx + 7] == b"</html>"


def test_find_html_injection_point_no_closing_tag():
    """Test returning -1 when no suitable closing tag."""
    html = b"<html><body>Incomplete HTML"
    idx = find_html_injection_point(html)
    assert idx == -1


def test_find_html_injection_point_prefers_body_over_html():
    """Test that </body> is preferred over </html>."""
    html = b"<html><body>Content</body></html>"
    idx = find_html_injection_point(html)
    # Should point to </body>, not </html>
    assert html[idx : idx + 7] == b"</body>"


def test_get_dev_server_config_nested():
    """Test accessing nested dev_server configuration."""
    cfg = {"dev_server": {"exclude_patterns": ["*.pyc"], "debounce": 300}}
    assert get_dev_server_config(cfg, "exclude_patterns") == ["*.pyc"]
    assert get_dev_server_config(cfg, "debounce", default=500) == 300
    assert get_dev_server_config(cfg, "missing", default="auto") == "auto"


def test_get_dev_server_config_missing_dev_server_key():
    """Test when dev_server key is missing."""
    cfg = {"other_key": "value"}
    assert get_dev_server_config(cfg, "exclude_patterns", default=[]) == []


def test_get_dev_server_config_empty_config():
    """Test with empty config."""
    assert get_dev_server_config({}, "anything", default="fallback") == "fallback"


def test_get_dev_server_config_none_value_returns_default():
    """Test that None values return the default."""
    cfg = {"dev_server": {"explicit_none": None}}
    assert get_dev_server_config(cfg, "explicit_none", default="default") == "default"
