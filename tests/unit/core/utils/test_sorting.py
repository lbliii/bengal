"""
Tests for bengal.core.utils.sorting module.

Tests weight-based sorting utilities with consistent defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from bengal.core.utils.sorting import (
    DEFAULT_WEIGHT,
    sorted_by_weight,
    weight_sort_key,
)


@dataclass
class MockItem:
    """Mock item for testing sorting."""

    title: str
    metadata: dict[str, Any]

    @property
    def name(self) -> str:
        return self.title


class TestDefaultWeight:
    """Tests for DEFAULT_WEIGHT constant."""

    def test_is_infinity(self) -> None:
        """DEFAULT_WEIGHT is positive infinity."""
        assert DEFAULT_WEIGHT == float("inf")

    def test_always_greater_than_explicit_weights(self) -> None:
        """DEFAULT_WEIGHT is greater than any reasonable explicit weight."""
        assert DEFAULT_WEIGHT > 999999
        assert DEFAULT_WEIGHT > 0
        assert DEFAULT_WEIGHT > -1000

    def test_unweighted_sorts_after_weighted(self) -> None:
        """Items with DEFAULT_WEIGHT sort after items with explicit weights."""
        weighted = [(10, "a"), (DEFAULT_WEIGHT, "b"), (5, "c")]
        sorted_items = sorted(weighted, key=lambda x: x[0])
        assert sorted_items == [(5, "c"), (10, "a"), (DEFAULT_WEIGHT, "b")]


class TestWeightSortKey:
    """Tests for weight_sort_key function."""

    def test_extracts_weight_from_metadata(self) -> None:
        """Weight is extracted from item.metadata["weight"]."""
        item = MockItem(title="Test", metadata={"weight": 10})
        key = weight_sort_key(item)
        assert key == (10.0, "test")

    def test_extracts_title_lowercase(self) -> None:
        """Title is extracted and lowercased."""
        item = MockItem(title="Hello World", metadata={})
        key = weight_sort_key(item)
        assert key[1] == "hello world"

    def test_default_weight_when_missing(self) -> None:
        """DEFAULT_WEIGHT is used when weight is not set."""
        item = MockItem(title="Test", metadata={})
        key = weight_sort_key(item)
        assert key[0] == DEFAULT_WEIGHT

    def test_custom_weight_getter(self) -> None:
        """Custom weight getter is used when provided."""
        item = {"custom_weight": 42, "label": "Test"}
        key = weight_sort_key(
            item,
            weight_getter=lambda x: x.get("custom_weight"),
            title_getter=lambda x: x.get("label", ""),
        )
        assert key == (42.0, "test")

    def test_handles_none_weight(self) -> None:
        """None weight is converted to DEFAULT_WEIGHT."""
        item = MockItem(title="Test", metadata={"weight": None})
        key = weight_sort_key(item)
        assert key[0] == DEFAULT_WEIGHT

    def test_handles_invalid_weight(self) -> None:
        """Invalid weight (non-numeric) is converted to DEFAULT_WEIGHT."""
        item = MockItem(title="Test", metadata={"weight": "invalid"})
        key = weight_sort_key(item)
        assert key[0] == DEFAULT_WEIGHT

    def test_converts_int_weight_to_float(self) -> None:
        """Integer weights are converted to float."""
        item = MockItem(title="Test", metadata={"weight": 5})
        key = weight_sort_key(item)
        assert key[0] == 5.0
        assert isinstance(key[0], float)

    def test_object_without_metadata(self) -> None:
        """Objects without metadata attribute use DEFAULT_WEIGHT."""

        class SimpleObj:
            title = "Test"

        key = weight_sort_key(SimpleObj())
        assert key[0] == DEFAULT_WEIGHT
        assert key[1] == "test"

    def test_falls_back_to_name_attribute(self) -> None:
        """Falls back to name attribute if title not present."""

        class NameOnly:
            name = "Test Name"

        key = weight_sort_key(NameOnly())
        assert key[1] == "test name"


class TestSortedByWeight:
    """Tests for sorted_by_weight function."""

    def test_sorts_by_weight_ascending(self) -> None:
        """Items are sorted by weight in ascending order."""
        items = [
            MockItem(title="C", metadata={"weight": 30}),
            MockItem(title="A", metadata={"weight": 10}),
            MockItem(title="B", metadata={"weight": 20}),
        ]
        result = sorted_by_weight(items)
        assert [i.title for i in result] == ["A", "B", "C"]

    def test_sorts_by_title_when_weight_equal(self) -> None:
        """Items with equal weight are sorted by title."""
        items = [
            MockItem(title="Charlie", metadata={"weight": 10}),
            MockItem(title="Alpha", metadata={"weight": 10}),
            MockItem(title="Bravo", metadata={"weight": 10}),
        ]
        result = sorted_by_weight(items)
        assert [i.title for i in result] == ["Alpha", "Bravo", "Charlie"]

    def test_unweighted_items_sort_last(self) -> None:
        """Items without weight sort after weighted items."""
        items = [
            MockItem(title="Unweighted", metadata={}),
            MockItem(title="Weighted", metadata={"weight": 10}),
        ]
        result = sorted_by_weight(items)
        assert [i.title for i in result] == ["Weighted", "Unweighted"]

    def test_case_insensitive_title_sort(self) -> None:
        """Title sorting is case-insensitive."""
        items = [
            MockItem(title="zebra", metadata={"weight": 10}),
            MockItem(title="Alpha", metadata={"weight": 10}),
            MockItem(title="BETA", metadata={"weight": 10}),
        ]
        result = sorted_by_weight(items)
        assert [i.title for i in result] == ["Alpha", "BETA", "zebra"]

    def test_reverse_sorting(self) -> None:
        """Reverse=True sorts in descending order."""
        items = [
            MockItem(title="A", metadata={"weight": 10}),
            MockItem(title="B", metadata={"weight": 20}),
        ]
        result = sorted_by_weight(items, reverse=True)
        assert [i.title for i in result] == ["B", "A"]

    def test_empty_list(self) -> None:
        """Empty list returns empty list."""
        assert sorted_by_weight([]) == []

    def test_single_item(self) -> None:
        """Single item list returns single item."""
        items = [MockItem(title="Only", metadata={"weight": 5})]
        result = sorted_by_weight(items)
        assert len(result) == 1
        assert result[0].title == "Only"

    def test_with_custom_getters(self) -> None:
        """Custom getters can be used for sorting."""
        items = [
            {"order": 20, "label": "Second"},
            {"order": 10, "label": "First"},
        ]
        result = sorted_by_weight(
            items,
            weight_getter=lambda x: x.get("order"),
            title_getter=lambda x: x.get("label", ""),
        )
        assert [i["label"] for i in result] == ["First", "Second"]


class TestWeightSortingIntegration:
    """Integration tests for weight sorting behavior."""

    def test_mixed_weighted_and_unweighted(self) -> None:
        """Mixed weighted/unweighted items sort correctly."""
        items = [
            MockItem(title="Z-Unweighted", metadata={}),
            MockItem(title="A-Weighted", metadata={"weight": 5}),
            MockItem(title="B-Unweighted", metadata={}),
            MockItem(title="C-Weighted", metadata={"weight": 3}),
        ]
        result = sorted_by_weight(items)
        titles = [i.title for i in result]
        # Weighted first (by weight), then unweighted (by title)
        assert titles == ["C-Weighted", "A-Weighted", "B-Unweighted", "Z-Unweighted"]

    def test_negative_weights(self) -> None:
        """Negative weights sort before positive weights."""
        items = [
            MockItem(title="B", metadata={"weight": 10}),
            MockItem(title="A", metadata={"weight": -5}),
        ]
        result = sorted_by_weight(items)
        assert [i.title for i in result] == ["A", "B"]

    def test_zero_weight(self) -> None:
        """Zero weight sorts before positive weights."""
        items = [
            MockItem(title="B", metadata={"weight": 10}),
            MockItem(title="A", metadata={"weight": 0}),
        ]
        result = sorted_by_weight(items)
        assert [i.title for i in result] == ["A", "B"]
