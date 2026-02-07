"""
Tests for bengal.core.utils.url module.

Tests URL building and baseurl application utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bengal.core.utils.url import apply_baseurl, get_baseurl


class TestApplyBaseurl:
    """Tests for apply_baseurl function."""

    def test_no_baseurl(self) -> None:
        """Path is unchanged when baseurl is empty."""
        assert apply_baseurl("/docs/guide/", "") == "/docs/guide/"
        assert apply_baseurl("/docs/guide/", None) == "/docs/guide/"

    def test_slash_only_baseurl(self) -> None:
        """Path is unchanged when baseurl is just '/'."""
        assert apply_baseurl("/docs/guide/", "/") == "/docs/guide/"

    def test_path_baseurl(self) -> None:
        """Baseurl is prepended to path."""
        assert apply_baseurl("/docs/guide/", "/bengal") == "/bengal/docs/guide/"

    def test_baseurl_trailing_slash_normalized(self) -> None:
        """Trailing slash on baseurl is removed."""
        assert apply_baseurl("/docs/", "/bengal/") == "/bengal/docs/"

    def test_path_without_leading_slash(self) -> None:
        """Path without leading slash gets one added."""
        assert apply_baseurl("docs/guide/", "/bengal") == "/bengal/docs/guide/"

    def test_double_slash_prevention(self) -> None:
        """No double slashes in result."""
        result = apply_baseurl("/docs/", "/bengal")
        assert "//" not in result

    def test_absolute_baseurl(self) -> None:
        """Absolute baseurl is prepended."""
        result = apply_baseurl("/docs/", "https://example.com")
        assert result == "https://example.com/docs/"

    def test_root_path(self) -> None:
        """Root path works correctly."""
        assert apply_baseurl("/", "/bengal") == "/bengal/"

    def test_complex_path(self) -> None:
        """Complex paths are handled correctly."""
        result = apply_baseurl("/api/v1/users/", "/app/docs")
        assert result == "/app/docs/api/v1/users/"


class TestGetBaseurl:
    """Tests for get_baseurl function."""

    def test_from_nested_site_section(self) -> None:
        """Baseurl is extracted from nested site section."""
        config = {"site": {"baseurl": "/docs"}}
        assert get_baseurl(config) == "/docs"

    def test_from_flat_config(self) -> None:
        """Baseurl is extracted from flat config."""
        config = {"baseurl": "/docs"}
        assert get_baseurl(config) == "/docs"

    def test_flat_takes_precedence(self) -> None:
        """Flat baseurl takes precedence (for runtime overrides)."""
        config = {"baseurl": "/flat", "site": {"baseurl": "/nested"}}
        assert get_baseurl(config) == "/flat"

    def test_missing_baseurl(self) -> None:
        """Empty string when baseurl is not configured."""
        config: dict[str, Any] = {}
        assert get_baseurl(config) == ""

    def test_none_baseurl(self) -> None:
        """Empty string when baseurl is None."""
        config = {"baseurl": None}
        assert get_baseurl(config) == ""

    def test_site_object_with_config(self) -> None:
        """Works with site object that has config attribute."""

        @dataclass
        class MockSite:
            baseurl: str = "/site-attr"

        @dataclass
        class MockConfig:
            site: MockSite = None  # type: ignore

            def get(self, key: str, default: Any = None) -> Any:
                return default

        class MockSiteObject:
            config = MockConfig(site=MockSite())

        assert get_baseurl(MockSiteObject()) == "/site-attr"

    def test_empty_string_baseurl(self) -> None:
        """Empty string baseurl is returned as empty string."""
        config = {"site": {"baseurl": ""}}
        assert get_baseurl(config) == ""


class TestUrlIntegration:
    """Integration tests for URL utilities."""

    def test_typical_github_pages_workflow(self) -> None:
        """Typical GitHub Pages setup works correctly."""
        config = {"site": {"baseurl": "/my-project"}}
        baseurl = get_baseurl(config)
        assert apply_baseurl("/docs/guide/", baseurl) == "/my-project/docs/guide/"

    def test_typical_root_deployment(self) -> None:
        """Root deployment (no baseurl) works correctly."""
        config = {"site": {"baseurl": ""}}
        baseurl = get_baseurl(config)
        assert apply_baseurl("/docs/guide/", baseurl) == "/docs/guide/"

    def test_dev_server_clears_baseurl(self) -> None:
        """Dev server can clear baseurl with flat override."""
        # Production config
        config = {"site": {"baseurl": "/project"}, "baseurl": ""}
        baseurl = get_baseurl(config)
        # Flat empty string takes precedence
        assert baseurl == ""
        assert apply_baseurl("/docs/", baseurl) == "/docs/"
