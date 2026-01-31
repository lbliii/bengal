"""
Tests for bengal.analysis.utils package.

Tests the centralized utility functions extracted from the analysis modules.
"""

from unittest.mock import Mock

import pytest

from bengal.analysis.utils.constants import DEFAULT_HUB_THRESHOLD, DEFAULT_LEAF_THRESHOLD
from bengal.analysis.utils.indexing import (
    build_category_index,
    build_inverted_index,
    build_tag_index,
)
from bengal.analysis.utils.scoring import (
    items_above_percentile,
    normalize_scores,
    top_n_by_score,
)
from bengal.analysis.utils.traversal import bfs_distances, bfs_path, bfs_predecessors
from bengal.analysis.utils.validation import ensure_built, require_built
from bengal.errors import BengalGraphError


class TestConstants:
    """Tests for analysis constants."""

    def test_default_hub_threshold(self):
        """Test default hub threshold value."""
        assert DEFAULT_HUB_THRESHOLD == 10

    def test_default_leaf_threshold(self):
        """Test default leaf threshold value."""
        assert DEFAULT_LEAF_THRESHOLD == 2


class TestTopNByScore:
    """Tests for top_n_by_score utility."""

    def test_returns_top_n_descending(self):
        """Test that top N items are returned in descending order."""
        scores = {"a": 0.3, "b": 0.8, "c": 0.5, "d": 0.1}
        result = top_n_by_score(scores, limit=2)
        assert result == [("b", 0.8), ("c", 0.5)]

    def test_returns_all_if_limit_exceeds_size(self):
        """Test that all items are returned if limit > size."""
        scores = {"a": 0.3, "b": 0.8}
        result = top_n_by_score(scores, limit=10)
        assert len(result) == 2
        assert result[0] == ("b", 0.8)

    def test_empty_dict(self):
        """Test empty input."""
        result = top_n_by_score({}, limit=5)
        assert result == []

    def test_reverse_false_returns_lowest(self):
        """Test reverse=False returns lowest scores first."""
        scores = {"a": 0.3, "b": 0.8, "c": 0.1}
        result = top_n_by_score(scores, limit=2, reverse=False)
        assert result == [("c", 0.1), ("a", 0.3)]


class TestItemsAbovePercentile:
    """Tests for items_above_percentile utility."""

    def test_80th_percentile(self):
        """Test 80th percentile (top 20%)."""
        scores = {f"item{i}": float(i) for i in range(10)}
        result = items_above_percentile(scores, 80)
        # Top 20% of 10 items = 2 items (items 8 and 9)
        assert len(result) == 2
        assert "item9" in result
        assert "item8" in result

    def test_empty_scores(self):
        """Test empty input."""
        result = items_above_percentile({}, 80)
        assert result == set()

    def test_0_percentile_returns_all(self):
        """Test 0th percentile returns all items."""
        scores = {"a": 1.0, "b": 2.0, "c": 3.0}
        result = items_above_percentile(scores, 0)
        assert result == {"a", "b", "c"}


class TestNormalizeScores:
    """Tests for normalize_scores utility."""

    def test_normalizes_to_0_1(self):
        """Test normalization to [0, 1] range."""
        scores = {"a": 10.0, "b": 50.0, "c": 30.0}
        result = normalize_scores(scores)
        assert result["a"] == 0.0
        assert result["b"] == 1.0
        assert result["c"] == 0.5

    def test_custom_range(self):
        """Test normalization to custom range."""
        scores = {"a": 0.0, "b": 100.0}
        result = normalize_scores(scores, min_val=0.0, max_val=10.0)
        assert result["a"] == 0.0
        assert result["b"] == 10.0

    def test_equal_scores_return_min(self):
        """Test that equal scores all return min_val."""
        scores = {"a": 5.0, "b": 5.0, "c": 5.0}
        result = normalize_scores(scores)
        assert all(v == 0.0 for v in result.values())

    def test_empty_dict(self):
        """Test empty input."""
        result = normalize_scores({})
        assert result == {}


class TestBfsPath:
    """Tests for bfs_path utility."""

    def test_finds_shortest_path(self):
        """Test BFS finds shortest path."""
        graph = {"A": {"B", "C"}, "B": {"D"}, "C": {"D"}, "D": set()}
        path = bfs_path(graph, "A", "D")
        # Should be length 2 (A->B->D or A->C->D)
        assert path is not None
        assert len(path) == 3
        assert path[0] == "A"
        assert path[-1] == "D"

    def test_same_node(self):
        """Test path to same node."""
        graph = {"A": {"B"}, "B": set()}
        path = bfs_path(graph, "A", "A")
        assert path == ["A"]

    def test_no_path(self):
        """Test when no path exists."""
        graph = {"A": {"B"}, "B": set(), "C": set()}
        path = bfs_path(graph, "A", "C")
        assert path is None

    def test_direct_connection(self):
        """Test direct connection path."""
        graph = {"A": {"B"}, "B": set()}
        path = bfs_path(graph, "A", "B")
        assert path == ["A", "B"]


class TestBfsDistances:
    """Tests for bfs_distances utility."""

    def test_computes_distances(self):
        """Test BFS computes correct distances."""
        graph = {"A": {"B"}, "B": {"C"}, "C": set()}
        distances = bfs_distances(graph, "A", {"A", "B", "C"})
        assert distances["A"] == 0
        assert distances["B"] == 1
        assert distances["C"] == 2

    def test_unreachable_node(self):
        """Test unreachable nodes have distance -1."""
        graph = {"A": {"B"}, "B": set(), "C": set()}
        distances = bfs_distances(graph, "A", {"A", "B", "C"})
        assert distances["A"] == 0
        assert distances["B"] == 1
        assert distances["C"] == -1

    def test_no_targets(self):
        """Test with no targets specified (all reachable)."""
        graph = {"A": {"B"}, "B": {"C"}, "C": set()}
        distances = bfs_distances(graph, "A")
        assert distances["A"] == 0
        assert distances["B"] == 1
        assert distances["C"] == 2


class TestBfsPredecessors:
    """Tests for bfs_predecessors utility."""

    def test_computes_predecessors(self):
        """Test BFS computes predecessor information."""
        graph = {"A": {"B", "C"}, "B": {"D"}, "C": {"D"}, "D": set()}
        preds, sigma, dist, stack = bfs_predecessors(graph, "A", {"A", "B", "C", "D"})

        # A is source
        assert dist["A"] == 0
        assert sigma["A"] == 1

        # B and C are one hop from A
        assert dist["B"] == 1
        assert dist["C"] == 1

        # D is two hops, reachable via B or C
        assert dist["D"] == 2
        assert sigma["D"] == 2  # Two shortest paths to D
        assert set(preds["D"]) == {"B", "C"}


class TestBuildInvertedIndex:
    """Tests for build_inverted_index utility."""

    def test_builds_index(self):
        """Test building an inverted index."""
        items = ["page1", "page2", "page3"]
        values = {"page1": {"a", "b"}, "page2": {"b", "c"}, "page3": {"a"}}

        index = build_inverted_index(items, lambda x: values.get(x, set()))

        assert "page1" in index["a"]
        assert "page3" in index["a"]
        assert "page2" not in index["a"]
        assert "page1" in index["b"]
        assert "page2" in index["b"]

    def test_empty_items(self):
        """Test with empty items list."""
        index = build_inverted_index([], lambda x: set())
        assert index == {}


class TestBuildTagIndex:
    """Tests for build_tag_index utility."""

    def test_builds_tag_index(self):
        """Test building a tag index from pages."""
        page1 = Mock()
        page1.tags = ["Python", "Web"]
        page2 = Mock()
        page2.tags = ["python", "Data"]
        page3 = Mock()
        page3.tags = None

        pages = [page1, page2, page3]
        index = build_tag_index(pages)

        # Normalized to lowercase
        assert page1 in index["python"]
        assert page2 in index["python"]
        assert page1 in index["web"]
        assert page2 in index["data"]

    def test_no_normalize(self):
        """Test without normalization."""
        page = Mock()
        page.tags = ["Python"]

        index = build_tag_index([page], normalize=False)
        assert page in index["Python"]
        assert "python" not in index


class TestBuildCategoryIndex:
    """Tests for build_category_index utility."""

    def test_builds_category_index(self):
        """Test building a category index from pages."""
        page1 = Mock()
        page1.category = "Tutorials"
        page1.categories = None

        page2 = Mock()
        page2.category = None
        page2.categories = ["guides", "API"]

        pages = [page1, page2]
        index = build_category_index(pages)

        assert page1 in index["tutorials"]
        assert page2 in index["guides"]
        assert page2 in index["api"]


class TestRequireBuiltDecorator:
    """Tests for @require_built decorator."""

    def test_raises_when_not_built(self):
        """Test that decorator raises BengalGraphError when graph not built."""

        class MyAnalyzer:
            def __init__(self):
                self._graph = Mock()
                self._graph._built = False

            @require_built
            def analyze(self):
                return "analyzed"

        analyzer = MyAnalyzer()
        with pytest.raises(BengalGraphError) as exc_info:
            analyzer.analyze()

        assert "G001" in str(exc_info.value)

    def test_allows_when_built(self):
        """Test that decorator allows execution when graph is built."""

        class MyAnalyzer:
            def __init__(self):
                self._graph = Mock()
                self._graph._built = True

            @require_built
            def analyze(self):
                return "analyzed"

        analyzer = MyAnalyzer()
        result = analyzer.analyze()
        assert result == "analyzed"

    def test_works_on_graph_directly(self):
        """Test decorator works when self is the graph (has _built)."""

        class MyGraph:
            def __init__(self):
                self._built = True

            @require_built
            def get_data(self):
                return "data"

        graph = MyGraph()
        assert graph.get_data() == "data"


class TestEnsureBuilt:
    """Tests for ensure_built function."""

    def test_raises_when_not_built(self):
        """Test that function raises when graph not built."""
        graph = Mock()
        graph._built = False

        with pytest.raises(BengalGraphError):
            ensure_built(graph, "test operation")

    def test_passes_when_built(self):
        """Test that function passes when graph is built."""
        graph = Mock()
        graph._built = True

        # Should not raise
        ensure_built(graph, "test operation")
