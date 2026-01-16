"""
Unit tests for Cacheable protocol.

Tests that the Cacheable protocol correctly validates types that implement
the required methods (to_cache_dict and from_cache_dict) and rejects types
that don't.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytest

from bengal.protocols import Cacheable

# Test implementations


@dataclass
class MinimalCacheable(Cacheable):
    """Minimal conforming implementation for testing."""

    value: str

    def to_cache_dict(self) -> dict[str, Any]:
        return {"value": self.value}

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> MinimalCacheable:
        return cls(value=data["value"])


@dataclass
class ComplexCacheable(Cacheable):
    """Complex implementation with various types."""

    name: str
    count: int
    timestamp: datetime
    tags: list[str]
    optional: str | None = None

    def to_cache_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "count": self.count,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "optional": self.optional,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> ComplexCacheable:
        return cls(
            name=data["name"],
            count=data["count"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tags=data["tags"],
            optional=data.get("optional"),
        )


@dataclass
class NonConformingType:
    """Type that doesn't implement Cacheable protocol."""

    value: str


@dataclass
class PartialImplementation(Cacheable):
    """Implements to_cache_dict but not from_cache_dict."""

    value: str

    def to_cache_dict(self) -> dict[str, Any]:
        return {"value": self.value}

    # Missing: from_cache_dict


# Tests


class TestCacheableProtocol:
    """Test Cacheable protocol validation."""

    def test_minimal_conforming_type(self):
        """Minimal conforming type should pass isinstance check."""
        obj = MinimalCacheable(value="test")
        assert isinstance(obj, Cacheable)

    def test_complex_conforming_type(self):
        """Complex conforming type should pass isinstance check."""
        obj = ComplexCacheable(
            name="test",
            count=42,
            timestamp=datetime(2025, 10, 26, 12, 0, 0),
            tags=["python", "web"],
            optional="value",
        )
        assert isinstance(obj, Cacheable)

    def test_non_conforming_type(self):
        """Non-conforming type should fail isinstance check."""
        obj = NonConformingType(value="test")
        assert not isinstance(obj, Cacheable)

    def test_partial_implementation(self):
        """
        Type with only to_cache_dict still passes isinstance check.

        Note: @runtime_checkable checks for method existence, not implementation.
        When PartialImplementation inherits from Cacheable Protocol, it inherits
        the abstract from_cache_dict method (as `...`), so it passes isinstance.

        Real validation comes from mypy, not runtime checks.
        """
        obj = PartialImplementation(value="test")
        # Runtime check passes (method exists, even if abstract)
        assert isinstance(obj, Cacheable)
        # But calling from_cache_dict would fail (not implemented)


class TestCacheableRoundtrip:
    """Test that Cacheable implementations maintain roundtrip invariant."""

    def test_minimal_roundtrip(self):
        """Minimal type should roundtrip correctly."""
        obj = MinimalCacheable(value="test")
        data = obj.to_cache_dict()
        loaded = MinimalCacheable.from_cache_dict(data)
        assert obj == loaded

    def test_complex_roundtrip(self):
        """Complex type should roundtrip correctly."""
        obj = ComplexCacheable(
            name="test",
            count=42,
            timestamp=datetime(2025, 10, 26, 12, 0, 0),
            tags=["python", "web"],
            optional="value",
        )
        data = obj.to_cache_dict()
        loaded = ComplexCacheable.from_cache_dict(data)
        assert obj == loaded

    def test_complex_roundtrip_with_none(self):
        """Complex type with None optional field should roundtrip correctly."""
        obj = ComplexCacheable(
            name="test",
            count=42,
            timestamp=datetime(2025, 10, 26, 12, 0, 0),
            tags=["python", "web"],
            optional=None,
        )
        data = obj.to_cache_dict()
        loaded = ComplexCacheable.from_cache_dict(data)
        assert obj == loaded

    def test_empty_list_roundtrip(self):
        """Type with empty list should roundtrip correctly."""
        obj = ComplexCacheable(
            name="test",
            count=0,
            timestamp=datetime(2025, 10, 26),
            tags=[],
            optional=None,
        )
        data = obj.to_cache_dict()
        loaded = ComplexCacheable.from_cache_dict(data)
        assert obj == loaded


class TestCacheableSerialization:
    """Test that to_cache_dict returns JSON-serializable data."""

    def test_returns_dict(self):
        """to_cache_dict must return a dict."""
        obj = MinimalCacheable(value="test")
        data = obj.to_cache_dict()
        assert isinstance(data, dict)

    def test_contains_expected_keys(self):
        """to_cache_dict should contain expected field keys."""
        obj = MinimalCacheable(value="test")
        data = obj.to_cache_dict()
        assert "value" in data
        assert data["value"] == "test"

    def test_datetime_serialized_as_string(self):
        """datetime should be serialized as ISO-8601 string."""
        obj = ComplexCacheable(
            name="test",
            count=42,
            timestamp=datetime(2025, 10, 26, 12, 30, 45),
            tags=["python"],
        )
        data = obj.to_cache_dict()
        assert isinstance(data["timestamp"], str)
        assert data["timestamp"] == "2025-10-26T12:30:45"

    def test_list_preserved(self):
        """Lists should be preserved as lists."""
        obj = ComplexCacheable(
            name="test",
            count=1,
            timestamp=datetime(2025, 10, 26),
            tags=["python", "web", "django"],
        )
        data = obj.to_cache_dict()
        assert isinstance(data["tags"], list)
        assert data["tags"] == ["python", "web", "django"]

    def test_none_preserved(self):
        """None values should be preserved (not omitted)."""
        obj = ComplexCacheable(
            name="test",
            count=1,
            timestamp=datetime(2025, 10, 26),
            tags=[],
            optional=None,
        )
        data = obj.to_cache_dict()
        assert "optional" in data
        assert data["optional"] is None


class TestCacheableDeserialization:
    """Test that from_cache_dict correctly reconstructs objects."""

    def test_from_dict_classmethod(self):
        """from_cache_dict should be a classmethod that returns instance."""
        data = {"value": "test"}
        obj = MinimalCacheable.from_cache_dict(data)
        assert isinstance(obj, MinimalCacheable)
        assert obj.value == "test"

    def test_datetime_deserialization(self):
        """ISO-8601 string should be deserialized to datetime."""
        data = {
            "name": "test",
            "count": 1,
            "timestamp": "2025-10-26T12:30:45",
            "tags": [],
            "optional": None,
        }
        obj = ComplexCacheable.from_cache_dict(data)
        assert isinstance(obj.timestamp, datetime)
        assert obj.timestamp == datetime(2025, 10, 26, 12, 30, 45)

    def test_missing_optional_field(self):
        """Missing optional field should default to None."""
        data = {
            "name": "test",
            "count": 1,
            "timestamp": "2025-10-26T12:30:45",
            "tags": [],
            # 'optional' key missing
        }
        obj = ComplexCacheable.from_cache_dict(data)
        assert obj.optional is None

    def test_missing_required_field_raises(self):
        """Missing required field should raise KeyError."""
        data = {
            # 'name' key missing
            "count": 1,
            "timestamp": "2025-10-26T12:30:45",
            "tags": [],
        }
        with pytest.raises(KeyError):
            ComplexCacheable.from_cache_dict(data)
