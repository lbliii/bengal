"""
Property tests for Cacheable serialization contract.

Tests edge cases and invariants that should hold for all Cacheable implementations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Self

import pytest

from bengal.cache.cacheable import Cacheable

# Test implementation for property testing


@dataclass
class PropertyTestEntry(Cacheable):
    """Entry for testing serialization properties."""

    string_field: str
    int_field: int
    list_field: list[str]
    optional_field: str | None = None

    def to_cache_dict(self) -> dict[str, Any]:
        return {
            "string_field": self.string_field,
            "int_field": self.int_field,
            "list_field": self.list_field,
            "optional_field": self.optional_field,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> PropertyTestEntry:
        return cls(
            string_field=data["string_field"],
            int_field=data["int_field"],
            list_field=data["list_field"],
            optional_field=data.get("optional_field"),
        )


class TestSerializationProperties:
    """Test properties that should hold for all Cacheable implementations."""

    def test_roundtrip_invariant(self):
        """Property: obj == T.from_cache_dict(obj.to_cache_dict()) for all obj."""
        test_cases = [
            PropertyTestEntry("test", 42, ["a", "b"], "optional"),
            PropertyTestEntry("", 0, [], None),
            PropertyTestEntry("special chars: 日本語", -1, ["x"], "y"),
            PropertyTestEntry("unicode: 🎉", 999999, ["python"], None),
        ]

        for obj in test_cases:
            data = obj.to_cache_dict()
            loaded = PropertyTestEntry.from_cache_dict(data)
            assert obj == loaded, f"Roundtrip failed for {obj}"

    def test_json_serializable(self):
        """Property: to_cache_dict() output must be JSON-serializable."""
        test_cases = [
            PropertyTestEntry("test", 42, ["a"], "b"),
            PropertyTestEntry("", 0, [], None),
            PropertyTestEntry("🎉", -1, ["x", "y", "z"], "value"),
        ]

        for obj in test_cases:
            data = obj.to_cache_dict()
            try:
                json_str = json.dumps(data)
                loaded_data = json.loads(json_str)
                assert data == loaded_data
            except (TypeError, ValueError) as e:
                pytest.fail(f"JSON serialization failed for {obj}: {e}")

    def test_empty_values_preserved(self):
        """Property: Empty strings, empty lists, and None should be preserved."""
        obj = PropertyTestEntry("", 0, [], None)
        data = obj.to_cache_dict()
        loaded = PropertyTestEntry.from_cache_dict(data)

        assert loaded.string_field == ""
        assert loaded.int_field == 0
        assert loaded.list_field == []
        assert loaded.optional_field is None

    def test_special_characters_preserved(self):
        """Property: Special characters in strings should be preserved."""
        special_strings = [
            "newlines\n\ntabs\t\tspaces",
            "quotes: \"single\" and 'double'",
            "backslash: \\ and forward: /",
            "unicode: 日本語 中文 한글",
            "emoji: 🎉 🚀 ✨",
            "html: <div>test</div>",
            'json: {"key": "value"}',
        ]

        for special_str in special_strings:
            obj = PropertyTestEntry(special_str, 1, [], None)
            data = obj.to_cache_dict()
            loaded = PropertyTestEntry.from_cache_dict(data)
            assert loaded.string_field == special_str

    def test_boundary_values_integers(self):
        """Property: Boundary integer values should roundtrip correctly."""
        boundary_values = [
            0,
            1,
            -1,
            999999,
            -999999,
            2**31 - 1,  # Max 32-bit signed int
            -(2**31),  # Min 32-bit signed int
        ]

        for value in boundary_values:
            obj = PropertyTestEntry("test", value, [], None)
            data = obj.to_cache_dict()
            loaded = PropertyTestEntry.from_cache_dict(data)
            assert loaded.int_field == value

    def test_list_order_preserved(self):
        """Property: List order should be preserved."""
        lists_to_test = [
            ["a", "b", "c"],
            ["c", "b", "a"],
            ["same", "same", "same"],
            ["1", "10", "2", "20"],  # Strings, not numbers
        ]

        for test_list in lists_to_test:
            obj = PropertyTestEntry("test", 1, test_list, None)
            data = obj.to_cache_dict()
            loaded = PropertyTestEntry.from_cache_dict(data)
            assert loaded.list_field == test_list

    def test_none_vs_missing_field(self):
        """Property: None should be preserved (not same as missing field)."""
        obj = PropertyTestEntry("test", 1, [], optional_field=None)
        data = obj.to_cache_dict()

        # None should be explicitly present in serialized data
        assert "optional_field" in data
        assert data["optional_field"] is None

        # And should deserialize back to None
        loaded = PropertyTestEntry.from_cache_dict(data)
        assert loaded.optional_field is None


class TestDatetimeSerializationProperties:
    """Test datetime serialization properties."""

    @dataclass
    class DateTimeEntry(Cacheable):
        """Entry with datetime for testing."""

        timestamp: datetime

        def to_cache_dict(self) -> dict[str, Any]:
            return {"timestamp": self.timestamp.isoformat()}

        @classmethod
        def from_cache_dict(cls, data: dict[str, Any]) -> Self:
            return cls(timestamp=datetime.fromisoformat(data["timestamp"]))

    def test_datetime_roundtrip(self):
        """Property: datetime should roundtrip via ISO-8601."""
        test_dates = [
            datetime(2025, 1, 1),
            datetime(2025, 10, 26, 12, 30, 45),
            datetime(1970, 1, 1, 0, 0, 0),  # Unix epoch
            datetime(9999, 12, 31, 23, 59, 59),  # Far future
        ]

        for dt in test_dates:
            obj = self.DateTimeEntry(timestamp=dt)
            data = obj.to_cache_dict()
            loaded = self.DateTimeEntry.from_cache_dict(data)
            assert loaded.timestamp == dt

    def test_datetime_serialized_as_string(self):
        """Property: datetime must be serialized as ISO-8601 string."""
        obj = self.DateTimeEntry(timestamp=datetime(2025, 10, 26, 12, 30, 45))
        data = obj.to_cache_dict()

        assert isinstance(data["timestamp"], str)
        assert data["timestamp"] == "2025-10-26T12:30:45"


class TestPathSerializationProperties:
    """Test Path serialization properties."""

    @dataclass
    class PathEntry(Cacheable):
        """Entry with Path for testing."""

        path: Path

        def to_cache_dict(self) -> dict[str, Any]:
            return {"path": str(self.path)}

        @classmethod
        def from_cache_dict(cls, data: dict[str, Any]) -> Self:
            return cls(path=Path(data["path"]))

    def test_path_roundtrip(self):
        """Property: Path should roundtrip via string."""
        test_paths = [
            Path("content/posts/my-post.md"),
            Path("simple.txt"),
            Path("nested/deep/path/file.md"),
            Path(".bengal/cache.json"),
        ]

        for path in test_paths:
            obj = self.PathEntry(path=path)
            data = obj.to_cache_dict()
            loaded = self.PathEntry.from_cache_dict(data)
            assert loaded.path == path

    def test_path_serialized_as_string(self):
        """Property: Path must be serialized as string."""
        obj = self.PathEntry(path=Path("content/post.md"))
        data = obj.to_cache_dict()

        assert isinstance(data["path"], str)
        assert data["path"] == "content/post.md"


class TestSetSerializationProperties:
    """Test set serialization properties (converted to sorted list)."""

    @dataclass
    class SetEntry(Cacheable):
        """Entry with set for testing (serialized as sorted list)."""

        tags: set[str]

        def to_cache_dict(self) -> dict[str, Any]:
            return {"tags": sorted(list(self.tags))}

        @classmethod
        def from_cache_dict(cls, data: dict[str, Any]) -> Self:
            return cls(tags=set(data["tags"]))

    def test_set_roundtrip(self):
        """Property: set should roundtrip via sorted list."""
        test_sets = [
            {"a", "b", "c"},
            {"python", "web", "django"},
            set(),  # Empty set
            {"single"},
        ]

        for tag_set in test_sets:
            obj = self.SetEntry(tags=tag_set)
            data = obj.to_cache_dict()
            loaded = self.SetEntry.from_cache_dict(data)
            assert loaded.tags == tag_set

    def test_set_serialized_as_sorted_list(self):
        """Property: set must be serialized as sorted list (for stability)."""
        obj = self.SetEntry(tags={"python", "web", "django", "api"})
        data = obj.to_cache_dict()

        assert isinstance(data["tags"], list)
        assert data["tags"] == sorted(["python", "web", "django", "api"])
        assert data["tags"] == ["api", "django", "python", "web"]
