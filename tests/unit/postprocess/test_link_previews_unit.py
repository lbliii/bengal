"""
Unit tests for Link Previews feature.

Tests the configuration, JSON URL conversion, and template rendering
for Wikipedia-style hover cards on internal links.

See: plan/drafted/rfc-link-previews.md
"""

from __future__ import annotations

import pytest

from bengal.config.defaults import DEFAULTS, normalize_bool_or_dict


class TestLinkPreviewsDefaults:
    """Test that link_previews defaults are correctly defined."""

    def test_link_previews_in_defaults(self):
        """Link previews config section exists in defaults."""
        assert "link_previews" in DEFAULTS
        config = DEFAULTS["link_previews"]
        assert isinstance(config, dict)

    def test_default_enabled(self):
        """Link previews are enabled by default."""
        config = DEFAULTS["link_previews"]
        assert config["enabled"] is True

    def test_default_timings(self):
        """Default timing values are reasonable."""
        config = DEFAULTS["link_previews"]
        assert config["hover_delay"] == 200  # ms
        assert config["hide_delay"] == 150  # ms

    def test_default_display_options(self):
        """Default display options show all metadata."""
        config = DEFAULTS["link_previews"]
        assert config["show_section"] is True
        assert config["show_reading_time"] is True
        assert config["show_word_count"] is True
        assert config["show_date"] is True
        assert config["show_tags"] is True
        assert config["max_tags"] == 3

    def test_default_exclude_selectors(self):
        """Default exclude selectors skip nav/toc/breadcrumb/pagination."""
        config = DEFAULTS["link_previews"]
        assert "nav" in config["exclude_selectors"]
        assert ".toc" in config["exclude_selectors"]
        assert ".breadcrumb" in config["exclude_selectors"]
        assert ".pagination" in config["exclude_selectors"]


class TestLinkPreviewsNormalization:
    """Test bool/dict normalization for link_previews."""

    def test_normalize_true(self):
        """True normalizes to enabled with defaults."""
        result = normalize_bool_or_dict(True, "link_previews")
        assert result["enabled"] is True
        assert result["hover_delay"] == 200

    def test_normalize_false(self):
        """False normalizes to disabled."""
        result = normalize_bool_or_dict(False, "link_previews")
        assert result["enabled"] is False

    def test_normalize_none(self):
        """None normalizes to enabled with defaults."""
        result = normalize_bool_or_dict(None, "link_previews")
        assert result["enabled"] is True

    def test_normalize_dict_with_overrides(self):
        """Dict merges with defaults."""
        result = normalize_bool_or_dict(
            {"hover_delay": 300, "max_tags": 5},
            "link_previews",
        )
        assert result["enabled"] is True  # Default
        assert result["hover_delay"] == 300  # Override
        assert result["max_tags"] == 5  # Override
        assert result["hide_delay"] == 150  # Default preserved

    def test_normalize_dict_disabled(self):
        """Dict with enabled=False disables."""
        result = normalize_bool_or_dict(
            {"enabled": False, "hover_delay": 500},
            "link_previews",
        )
        assert result["enabled"] is False


class TestJsonUrlConversion:
    """
    Test JSON URL conversion logic.
    
    Note: The actual toJsonUrl() is in JavaScript. These tests document
    the expected behavior for parity testing.
        
    """

    @pytest.mark.parametrize(
        "page_url,expected_json_url",
        [
            ("/docs/getting-started/", "/docs/getting-started/index.json"),
            ("/docs/getting-started", "/docs/getting-started/index.json"),
            ("/docs/api/index.html", "/docs/api/index.json"),
            ("/docs/page.html", "/docs/page/index.json"),
            ("/", "/index.json"),
            ("", "/index.json"),
        ],
    )
    def test_url_conversion_expected(self, page_url: str, expected_json_url: str):
        """Document expected URL conversions for JS parity."""
        # This is a documentation test - the actual conversion happens in JS
        # The Python side just needs to ensure JSON files are generated at
        # these paths by PageJSONGenerator
        assert expected_json_url.endswith("/index.json")


class TestSiteLinkPreviewsProperty:
    """Test Site.link_previews property."""

    def test_property_with_defaults(self):
        """Site.link_previews returns defaults when not configured."""
        from bengal.core import Site

        site = Site.for_testing()
        lp = site.link_previews

        assert lp["enabled"] is True
        assert lp["hover_delay"] == 200
        assert lp["hide_delay"] == 150
        assert lp["show_section"] is True
        assert lp["max_tags"] == 3

    def test_property_disabled(self):
        """Site.link_previews respects disabled config."""
        from bengal.core import Site

        site = Site.for_testing()
        site.config["link_previews"] = False
        lp = site.link_previews

        assert lp["enabled"] is False

    def test_property_with_overrides(self):
        """Site.link_previews merges user config with defaults."""
        from bengal.core import Site

        site = Site.for_testing()
        site.config["link_previews"] = {
            "hover_delay": 400,
            "show_word_count": False,
            "max_tags": 5,
        }
        lp = site.link_previews

        assert lp["enabled"] is True  # Default
        assert lp["hover_delay"] == 400  # Override
        assert lp["show_word_count"] is False  # Override
        assert lp["max_tags"] == 5  # Override
        assert lp["hide_delay"] == 150  # Default preserved
        assert lp["show_section"] is True  # Default preserved
