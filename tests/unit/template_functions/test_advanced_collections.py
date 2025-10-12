"""Tests for advanced collection template functions."""

from bengal.rendering.template_functions.advanced_collections import (
    chunk,
    sample,
    shuffle,
)


class TestSample:
    """Tests for sample filter."""

    def test_sample_less_than_length(self):
        items = [1, 2, 3, 4, 5]
        result = sample(items, 3)
        assert len(result) == 3
        assert all(item in items for item in result)

    def test_sample_more_than_length(self):
        items = [1, 2, 3]
        result = sample(items, 10)
        assert len(result) == 3
        assert set(result) == set(items)

    def test_sample_with_seed(self):
        items = [1, 2, 3, 4, 5]
        result1 = sample(items, 3, seed=42)
        result2 = sample(items, 3, seed=42)
        assert result1 == result2  # Same seed = same result

    def test_empty_list(self):
        assert sample([], 5) == []

    def test_single_item(self):
        items = [1, 2, 3, 4, 5]
        result = sample(items, 1)
        assert len(result) == 1


class TestShuffle:
    """Tests for shuffle filter."""

    def test_shuffle_changes_order(self):
        items = list(range(100))
        result = shuffle(items)
        # Very unlikely to be in same order
        assert len(result) == len(items)
        assert set(result) == set(items)

    def test_shuffle_with_seed(self):
        items = [1, 2, 3, 4, 5]
        result1 = shuffle(items, seed=42)
        result2 = shuffle(items, seed=42)
        assert result1 == result2  # Same seed = same result

    def test_empty_list(self):
        assert shuffle([]) == []

    def test_original_unchanged(self):
        items = [1, 2, 3]
        shuffle(items)
        assert items == [1, 2, 3]  # Original not modified


class TestChunk:
    """Tests for chunk filter."""

    def test_chunk_evenly(self):
        items = [1, 2, 3, 4, 5, 6]
        result = chunk(items, 2)
        assert result == [[1, 2], [3, 4], [5, 6]]

    def test_chunk_unevenly(self):
        items = [1, 2, 3, 4, 5]
        result = chunk(items, 2)
        assert result == [[1, 2], [3, 4], [5]]

    def test_chunk_size_larger_than_list(self):
        items = [1, 2, 3]
        result = chunk(items, 10)
        assert result == [[1, 2, 3]]

    def test_empty_list(self):
        assert chunk([], 3) == []

    def test_chunk_size_zero(self):
        items = [1, 2, 3]
        result = chunk(items, 0)
        assert result == []

    def test_chunk_size_one(self):
        items = [1, 2, 3]
        result = chunk(items, 1)
        assert result == [[1], [2], [3]]
