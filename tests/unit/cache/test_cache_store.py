"""
Unit tests for CacheStore.

Tests the generic cache storage mechanism that works with Cacheable types.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from bengal.cache.cache_store import CacheStore
from bengal.protocols import Cacheable

# Test Cacheable implementations


@dataclass
class SimpleEntry(Cacheable):
    """Simple test entry."""

    key: str
    value: int

    def to_cache_dict(self) -> dict[str, Any]:
        return {"key": self.key, "value": self.value}

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> SimpleEntry:
        return cls(key=data["key"], value=data["value"])


@dataclass
class ComplexEntry(Cacheable):
    """Complex test entry with various types."""

    name: str
    timestamp: datetime
    tags: list[str]
    optional: str | None = None

    def to_cache_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "optional": self.optional,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> ComplexEntry:
        return cls(
            name=data["name"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tags=data["tags"],
            optional=data.get("optional"),
        )


# Tests


class TestCacheStoreSave:
    """Test CacheStore.save() functionality."""

    def test_save_empty_list(self, tmp_path):
        """Save empty list should create valid cache file."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path, compress=False)

        store.save([], version=1)

        assert cache_path.exists()
        with open(cache_path) as f:
            data = json.load(f)
        assert data == {"version": 1, "entries": []}

    def test_save_single_entry(self, tmp_path):
        """Save single entry should serialize correctly."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path, compress=False)

        entries = [SimpleEntry(key="test", value=42)]
        store.save(entries, version=1)

        assert cache_path.exists()
        with open(cache_path) as f:
            data = json.load(f)
        assert data == {
            "version": 1,
            "entries": [{"key": "test", "value": 42}],
        }

    def test_save_multiple_entries(self, tmp_path):
        """Save multiple entries should serialize all entries."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path, compress=False)

        entries = [
            SimpleEntry(key="first", value=1),
            SimpleEntry(key="second", value=2),
            SimpleEntry(key="third", value=3),
        ]
        store.save(entries, version=1)

        with open(cache_path) as f:
            data = json.load(f)
        assert len(data["entries"]) == 3
        assert data["entries"][0]["key"] == "first"
        assert data["entries"][1]["key"] == "second"
        assert data["entries"][2]["key"] == "third"

    def test_save_creates_parent_directory(self, tmp_path):
        """Save should create parent directory if missing."""
        cache_path = tmp_path / "nested" / "dir" / "test.json"
        store = CacheStore(cache_path, compress=False)

        entries = [SimpleEntry(key="test", value=1)]
        store.save(entries, version=1)

        assert cache_path.exists()
        assert cache_path.parent.exists()

    def test_save_with_version(self, tmp_path):
        """Save should store specified version."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path, compress=False)

        store.save([], version=5)

        with open(cache_path) as f:
            data = json.load(f)
        assert data["version"] == 5

    def test_save_complex_entry(self, tmp_path):
        """Save should handle complex entries with datetime, lists, etc."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path, compress=False)

        entries = [
            ComplexEntry(
                name="test",
                timestamp=datetime(2025, 10, 26, 12, 30, 45),
                tags=["python", "web"],
                optional="value",
            )
        ]
        store.save(entries, version=1)

        with open(cache_path) as f:
            data = json.load(f)
        assert data["entries"][0]["timestamp"] == "2025-10-26T12:30:45"
        assert data["entries"][0]["tags"] == ["python", "web"]


class TestCacheStoreLoad:
    """Test CacheStore.load() functionality."""

    def test_load_missing_file(self, tmp_path):
        """Load missing file should return empty list (no error)."""
        cache_path = tmp_path / "missing.json"
        store = CacheStore(cache_path)

        entries = store.load(SimpleEntry, expected_version=1)

        assert entries == []

    def test_load_empty_list(self, tmp_path):
        """Load empty cache should return empty list."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path)

        store.save([], version=1)
        entries = store.load(SimpleEntry, expected_version=1)

        assert entries == []

    def test_load_single_entry(self, tmp_path):
        """Load single entry should deserialize correctly."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path)

        original = [SimpleEntry(key="test", value=42)]
        store.save(original, version=1)

        loaded = store.load(SimpleEntry, expected_version=1)

        assert len(loaded) == 1
        assert loaded[0].key == "test"
        assert loaded[0].value == 42

    def test_load_multiple_entries(self, tmp_path):
        """Load multiple entries should preserve order."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path)

        original = [
            SimpleEntry(key="first", value=1),
            SimpleEntry(key="second", value=2),
            SimpleEntry(key="third", value=3),
        ]
        store.save(original, version=1)

        loaded = store.load(SimpleEntry, expected_version=1)

        assert len(loaded) == 3
        assert loaded[0].key == "first"
        assert loaded[1].key == "second"
        assert loaded[2].key == "third"

    def test_load_complex_entry(self, tmp_path):
        """Load should handle complex entries with datetime, lists, etc."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path)

        original = [
            ComplexEntry(
                name="test",
                timestamp=datetime(2025, 10, 26, 12, 30, 45),
                tags=["python", "web"],
                optional="value",
            )
        ]
        store.save(original, version=1)

        loaded = store.load(ComplexEntry, expected_version=1)

        assert len(loaded) == 1
        assert loaded[0].name == "test"
        assert loaded[0].timestamp == datetime(2025, 10, 26, 12, 30, 45)
        assert loaded[0].tags == ["python", "web"]
        assert loaded[0].optional == "value"


class TestCacheStoreVersioning:
    """Test version handling (tolerant loading)."""

    def test_version_mismatch_returns_empty(self, tmp_path):
        """Load with version mismatch should return empty list."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path)

        entries = [SimpleEntry(key="test", value=1)]
        store.save(entries, version=2)

        # Try to load with version 1 (mismatch)
        loaded = store.load(SimpleEntry, expected_version=1)

        assert loaded == []

    def test_version_match_loads_correctly(self, tmp_path):
        """Load with matching version should load entries."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path)

        entries = [SimpleEntry(key="test", value=1)]
        store.save(entries, version=2)

        # Load with version 2 (match)
        loaded = store.load(SimpleEntry, expected_version=2)

        assert len(loaded) == 1
        assert loaded[0].key == "test"

    def test_missing_version_field_returns_empty(self, tmp_path):
        """Cache file missing version field should return empty."""
        cache_path = tmp_path / "test.json"
        with open(cache_path, "w") as f:
            json.dump({"entries": []}, f)  # Missing 'version'

        store = CacheStore(cache_path)
        loaded = store.load(SimpleEntry, expected_version=1)

        assert loaded == []


class TestCacheStoreRoundtrip:
    """Test save/load roundtrip integrity."""

    def test_roundtrip_simple(self, tmp_path):
        """Simple entries should roundtrip correctly."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path)

        original = [
            SimpleEntry(key="a", value=1),
            SimpleEntry(key="b", value=2),
        ]
        store.save(original, version=1)
        loaded = store.load(SimpleEntry, expected_version=1)

        assert original == loaded

    def test_roundtrip_complex(self, tmp_path):
        """Complex entries should roundtrip correctly."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path)

        original = [
            ComplexEntry(
                name="first",
                timestamp=datetime(2025, 10, 26, 10, 0, 0),
                tags=["tag1", "tag2"],
                optional="value",
            ),
            ComplexEntry(
                name="second",
                timestamp=datetime(2025, 10, 27, 15, 30, 0),
                tags=[],
                optional=None,
            ),
        ]
        store.save(original, version=1)
        loaded = store.load(ComplexEntry, expected_version=1)

        assert original == loaded


class TestCacheStoreMalformedData:
    """Test handling of malformed cache files (tolerant loading)."""

    def test_invalid_json(self, tmp_path):
        """Invalid JSON should return empty list and log error."""
        cache_path = tmp_path / "test.json"
        with open(cache_path, "w") as f:
            f.write("{invalid json")

        store = CacheStore(cache_path)
        loaded = store.load(SimpleEntry, expected_version=1)

        assert loaded == []

    def test_non_dict_root(self, tmp_path):
        """Root element not a dict should return empty list."""
        cache_path = tmp_path / "test.json"
        with open(cache_path, "w") as f:
            json.dump([], f)  # List instead of dict

        store = CacheStore(cache_path)
        loaded = store.load(SimpleEntry, expected_version=1)

        assert loaded == []

    def test_entries_not_list(self, tmp_path):
        """'entries' field not a list should return empty list."""
        cache_path = tmp_path / "test.json"
        with open(cache_path, "w") as f:
            json.dump({"version": 1, "entries": "not a list"}, f)

        store = CacheStore(cache_path)
        loaded = store.load(SimpleEntry, expected_version=1)

        assert loaded == []

    def test_partial_deserialization_failure(self, tmp_path):
        """Failed deserialization of some entries should continue loading others."""
        cache_path = tmp_path / "test.json"
        with open(cache_path, "w") as f:
            json.dump(
                {
                    "version": 1,
                    "entries": [
                        {"key": "valid1", "value": 1},
                        {"key": "invalid"},  # Missing 'value' field
                        {"key": "valid2", "value": 2},
                    ],
                },
                f,
            )

        store = CacheStore(cache_path)
        loaded = store.load(SimpleEntry, expected_version=1)

        # Should load 2 valid entries, skip the invalid one
        assert len(loaded) == 2
        assert loaded[0].key == "valid1"
        assert loaded[1].key == "valid2"


class TestCacheStoreUtilities:
    """Test utility methods."""

    def test_exists_returns_false_for_missing_file(self, tmp_path):
        """exists() should return False for missing file."""
        cache_path = tmp_path / "missing.json"
        store = CacheStore(cache_path)

        assert not store.exists()

    def test_exists_returns_true_after_save(self, tmp_path):
        """exists() should return True after save."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path)

        store.save([], version=1)

        assert store.exists()

    def test_clear_deletes_file(self, tmp_path):
        """clear() should delete cache file."""
        cache_path = tmp_path / "test.json"
        store = CacheStore(cache_path, compress=False)

        store.save([], version=1)
        assert cache_path.exists()

        store.clear()
        assert not cache_path.exists()

    def test_clear_on_missing_file_no_error(self, tmp_path):
        """clear() on missing file should not raise error."""
        cache_path = tmp_path / "missing.json"
        store = CacheStore(cache_path)

        store.clear()  # Should not raise

        assert not cache_path.exists()
