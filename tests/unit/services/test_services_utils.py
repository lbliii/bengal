"""
Unit tests for services/utils.py.

Tests the shared utilities extracted for the services package:
- get_bengal_dir: Package directory resolution
- get_bundled_themes_dir: Bundled themes directory
- freeze_dict / freeze_value: Immutability helpers
"""

from pathlib import Path
from types import MappingProxyType

import pytest

from bengal.services.utils import (
    freeze_dict,
    freeze_value,
    get_bengal_dir,
    get_bundled_themes_dir,
)


class TestGetBengalDir:
    """Tests for get_bengal_dir function."""

    def test_returns_path(self) -> None:
        """get_bengal_dir returns a Path object."""
        result = get_bengal_dir()
        assert isinstance(result, Path)

    def test_path_exists(self) -> None:
        """get_bengal_dir returns an existing path."""
        result = get_bengal_dir()
        assert result.exists()

    def test_is_bengal_package(self) -> None:
        """get_bengal_dir returns the bengal package directory."""
        result = get_bengal_dir()
        assert result.name == "bengal"
        # Should contain expected subdirectories
        assert (result / "core").exists()
        assert (result / "services").exists()

    def test_is_cached(self) -> None:
        """get_bengal_dir returns the same object on repeated calls."""
        result1 = get_bengal_dir()
        result2 = get_bengal_dir()
        # lru_cache should return the same object
        assert result1 is result2


class TestGetBundledThemesDir:
    """Tests for get_bundled_themes_dir function."""

    def test_returns_path(self) -> None:
        """get_bundled_themes_dir returns a Path object."""
        result = get_bundled_themes_dir()
        assert isinstance(result, Path)

    def test_path_exists(self) -> None:
        """get_bundled_themes_dir returns an existing path."""
        result = get_bundled_themes_dir()
        assert result.exists()

    def test_is_themes_directory(self) -> None:
        """get_bundled_themes_dir returns the themes directory."""
        result = get_bundled_themes_dir()
        assert result.name == "themes"
        # Should contain the default theme
        assert (result / "default").exists()

    def test_is_under_bengal_dir(self) -> None:
        """get_bundled_themes_dir is a subdirectory of get_bengal_dir."""
        bengal_dir = get_bengal_dir()
        themes_dir = get_bundled_themes_dir()
        assert themes_dir.parent == bengal_dir


class TestFreezeDict:
    """Tests for freeze_dict function."""

    def test_returns_mapping_proxy(self) -> None:
        """freeze_dict returns a MappingProxyType."""
        result = freeze_dict({"key": "value"})
        assert isinstance(result, MappingProxyType)

    def test_preserves_values(self) -> None:
        """freeze_dict preserves dictionary values."""
        original = {"name": "test", "count": 42, "enabled": True}
        result = freeze_dict(original)
        assert result["name"] == "test"
        assert result["count"] == 42
        assert result["enabled"] is True

    def test_converts_nested_dict(self) -> None:
        """freeze_dict recursively converts nested dicts to MappingProxyType."""
        original = {"outer": {"inner": "value"}}
        result = freeze_dict(original)
        assert isinstance(result["outer"], MappingProxyType)
        assert result["outer"]["inner"] == "value"

    def test_converts_lists_to_tuples(self) -> None:
        """freeze_dict converts lists to tuples."""
        original = {"items": [1, 2, 3]}
        result = freeze_dict(original)
        assert isinstance(result["items"], tuple)
        assert result["items"] == (1, 2, 3)

    def test_freezes_nested_lists(self) -> None:
        """freeze_dict recursively freezes list contents."""
        original = {"data": [{"a": 1}, {"b": 2}]}
        result = freeze_dict(original)
        assert isinstance(result["data"], tuple)
        assert isinstance(result["data"][0], MappingProxyType)
        assert result["data"][0]["a"] == 1

    def test_handles_deeply_nested(self) -> None:
        """freeze_dict handles deeply nested structures."""
        original = {
            "level1": {
                "level2": {
                    "level3": [
                        {"level4": "deep"},
                    ],
                },
            },
        }
        result = freeze_dict(original)
        assert result["level1"]["level2"]["level3"][0]["level4"] == "deep"

    def test_immutability(self) -> None:
        """frozen dict cannot be modified."""
        result = freeze_dict({"key": "value"})
        with pytest.raises(TypeError):
            result["key"] = "new_value"  # type: ignore[index]

    def test_empty_dict(self) -> None:
        """freeze_dict handles empty dictionary."""
        result = freeze_dict({})
        assert len(result) == 0
        assert isinstance(result, MappingProxyType)


class TestFreezeValue:
    """Tests for freeze_value function."""

    def test_freezes_dict(self) -> None:
        """freeze_value converts dict to MappingProxyType."""
        result = freeze_value({"key": "value"})
        assert isinstance(result, MappingProxyType)

    def test_freezes_list(self) -> None:
        """freeze_value converts list to tuple."""
        result = freeze_value([1, 2, 3])
        assert isinstance(result, tuple)
        assert result == (1, 2, 3)

    def test_preserves_primitives(self) -> None:
        """freeze_value returns primitives unchanged."""
        assert freeze_value("string") == "string"
        assert freeze_value(42) == 42
        assert freeze_value(3.14) == 3.14
        assert freeze_value(True) is True
        assert freeze_value(None) is None

    def test_preserves_tuples(self) -> None:
        """freeze_value returns tuples unchanged (already immutable)."""
        original = (1, 2, 3)
        result = freeze_value(original)
        assert result == original

    def test_freezes_nested_list_items(self) -> None:
        """freeze_value recursively freezes list items."""
        result = freeze_value([{"a": 1}, [1, 2]])
        assert isinstance(result, tuple)
        assert isinstance(result[0], MappingProxyType)
        assert isinstance(result[1], tuple)


class TestFreezeIntegration:
    """Integration tests for freeze functions with real data patterns."""

    def test_data_file_structure(self) -> None:
        """freeze_dict handles typical data file structures."""
        # Simulates what data service loads from data/ files
        config = {
            "site": {
                "name": "My Site",
                "languages": ["en", "es", "fr"],
            },
            "navigation": [
                {"title": "Home", "url": "/"},
                {"title": "About", "url": "/about/"},
            ],
        }
        result = freeze_dict(config)

        # All nested structures should be frozen
        assert isinstance(result["site"], MappingProxyType)
        assert isinstance(result["site"]["languages"], tuple)
        assert isinstance(result["navigation"], tuple)
        assert isinstance(result["navigation"][0], MappingProxyType)

        # Values should be accessible
        assert result["site"]["name"] == "My Site"
        assert result["navigation"][0]["title"] == "Home"
