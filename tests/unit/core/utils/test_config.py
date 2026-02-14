"""
Tests for bengal.core.utils.config module.

Tests config access utilities for nested configuration structures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.core.utils.config import get_config_section, get_site_value


class TestGetSiteValue:
    """Tests for get_site_value function."""

    def test_nested_site_section(self) -> None:
        """Value is found in nested site section."""
        config = {"site": {"title": "My Site"}}
        assert get_site_value(config, "title") == "My Site"

    def test_flat_config(self) -> None:
        """Value is found at root level."""
        config = {"title": "My Site"}
        assert get_site_value(config, "title") == "My Site"

    def test_nested_takes_precedence(self) -> None:
        """Nested site section takes precedence over flat."""
        config = {"site": {"title": "Nested"}, "title": "Flat"}
        assert get_site_value(config, "title") == "Nested"

    def test_default_when_missing(self) -> None:
        """Default is returned when key is missing."""
        config: dict[str, Any] = {}
        assert get_site_value(config, "title", "Default") == "Default"

    def test_none_value_returns_none(self) -> None:
        """None value is returned as-is (not treated as missing)."""
        config = {"site": {"title": None}}
        # None in config returns None, not the default
        assert get_site_value(config, "title", "Default") is None

    def test_empty_string_value(self) -> None:
        """Empty string is returned as-is."""
        config = {"site": {"baseurl": ""}}
        assert get_site_value(config, "baseurl", "/default") == ""

    def test_config_object_with_site_attribute(self) -> None:
        """Works with Config-like objects with site attribute."""

        @dataclass
        class MockSite:
            title: str = "From Attr"

        @dataclass
        class MockConfig:
            site: MockSite = None  # type: ignore

            def get(self, key: str, default: Any = None) -> Any:
                return default

        config = MockConfig(site=MockSite())
        assert get_site_value(config, "title") == "From Attr"

    def test_all_values_for_site(self) -> None:
        """Common site values are accessible."""
        config = {
            "site": {
                "title": "My Blog",
                "description": "A great blog",
                "author": "Jane Doe",
                "baseurl": "/blog",
                "language": "en",
            }
        }
        assert get_site_value(config, "title") == "My Blog"
        assert get_site_value(config, "description") == "A great blog"
        assert get_site_value(config, "author") == "Jane Doe"
        assert get_site_value(config, "baseurl") == "/blog"
        assert get_site_value(config, "language") == "en"


class TestGetConfigSection:
    """Tests for get_config_section function."""

    def test_existing_section(self) -> None:
        """Existing section is returned as dict."""
        config = {"build": {"parallel": True, "strict": False}}
        section = get_config_section(config, "build")
        assert section == {"parallel": True, "strict": False}

    def test_missing_section(self) -> None:
        """Missing section returns empty dict."""
        config: dict[str, Any] = {}
        section = get_config_section(config, "build")
        assert section == {}

    def test_non_dict_section(self) -> None:
        """Non-dict section returns empty dict."""
        config = {"theme": "dark"}  # string, not dict
        section = get_config_section(config, "theme")
        # Non-dict returns empty dict
        assert section == {}

    def test_returns_copy(self) -> None:
        """Returned dict is a copy, not the original."""
        config = {"build": {"key": "value"}}
        section = get_config_section(config, "build")
        section["key"] = "modified"
        # Original should be unchanged
        assert config["build"]["key"] == "value"

    def test_config_object_with_section_attribute(self) -> None:
        """Works with Config-like objects with section attributes."""

        class MockSection:
            _data: ClassVar[dict] = {"parallel": True}

        class MockConfig:
            build = MockSection()

            def get(self, key: str, default: Any = None) -> Any:
                return default

        config = MockConfig()
        section = get_config_section(config, "build")
        assert section == {"parallel": True}

    def test_common_sections(self) -> None:
        """Common config sections are accessible."""
        config = {
            "build": {"parallel": True},
            "assets": {"pipeline": False},
            "i18n": {"default_language": "en"},
            "menu": {"main": []},
            "content": {"dir": "content"},
            "output": {"dir": "public"},
        }
        assert get_config_section(config, "build") == {"parallel": True}
        assert get_config_section(config, "assets") == {"pipeline": False}
        assert get_config_section(config, "i18n") == {"default_language": "en"}
        assert get_config_section(config, "menu") == {"main": []}
        assert get_config_section(config, "content") == {"dir": "content"}
        assert get_config_section(config, "output") == {"dir": "public"}
