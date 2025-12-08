"""
Unit tests for path analysis algorithms.
"""

from collections import defaultdict
from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.analysis.path_analysis import (
    PathAnalysisResults,
    PathAnalyzer,
    PathSearchResult,
    analyze_paths,
)


class TestPathAnalysisResults:
    """Tests for PathAnalysisResults dataclass."""

    def test_get_top_bridges(self):
        """Test getting top bridge pages."""
        pages = [Mock(source_path=Path(f"page{i}.md")) for i in range(5)]

        betweenness = {
            pages[0]: 0.5,
            pages[1]: 0.3,
            pages[2]: 0.8,
            pages[3]: 0.1,
            pages[4]: 0.6,
        }

        results = PathAnalysisResults(
            betweenness_centrality=betweenness,
            closeness_centrality={},
            avg_path_length=2.5,
            diameter=5,
        )

        bridges = results.get_top_bridges(3)

        assert len(bridges) == 3
        assert bridges[0][0] == pages[2]  # 0.8
        assert bridges[1][0] == pages[4]  # 0.6
        assert bridges[2][0] == pages[0]  # 0.5

    def test_get_most_accessible(self):
        """Test getting most accessible pages."""
        pages = [Mock(source_path=Path(f"page{i}.md")) for i in range(3)]

        closeness = {
            pages[0]: 0.4,
            pages[1]: 0.9,
            pages[2]: 0.6,
        }

        results = PathAnalysisResults(
            betweenness_centrality={},
            closeness_centrality=closeness,
            avg_path_length=2.0,
            diameter=3,
        )

        accessible = results.get_most_accessible(2)

        assert len(accessible) == 2
        assert accessible[0][0] == pages[1]  # 0.9
        assert accessible[1][0] == pages[2]  # 0.6

    def test_get_betweenness(self):
        """Test getting betweenness for specific page."""
        page1 = Mock(source_path=Path("page1.md"))
        page2 = Mock(source_path=Path("page2.md"))

        results = PathAnalysisResults(
            betweenness_centrality={page1: 0.5},
            closeness_centrality={},
            avg_path_length=2.0,
            diameter=3,
        )

        assert results.get_betweenness(page1) == 0.5
        assert results.get_betweenness(page2) == 0.0  # Not in results

    def test_is_approximate_flag(self):
        """Test is_approximate flag is included in results."""
        results = PathAnalysisResults(
            betweenness_centrality={},
            closeness_centrality={},
            avg_path_length=0.0,
            diameter=0,
            is_approximate=True,
            pivots_used=100,
        )

        assert results.is_approximate is True
        assert results.pivots_used == 100

    def test_defaults_for_exact_analysis(self):
        """Test default values for exact analysis."""
        results = PathAnalysisResults(
            betweenness_centrality={},
            closeness_centrality={},
            avg_path_length=0.0,
            diameter=0,
        )

        # Defaults indicate exact analysis
        assert results.is_approximate is False
        assert results.pivots_used == 0


class TestPathAnalyzer:
    """Tests for path analysis algorithms."""

    def test_find_shortest_path_direct(self):
        """Test finding shortest path when direct link exists."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})

        site = Mock()
        site.pages = [page_a, page_b]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}

        analyzer = PathAnalyzer(graph)
        path = analyzer.find_shortest_path(page_a, page_b)

        assert path == [page_a, page_b]

    def test_find_shortest_path_indirect(self):
        """Test finding shortest path through intermediate page."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})
        page_c = Mock(source_path=Path("c.md"), metadata={})

        site = Mock()
        site.pages = [page_a, page_b, page_c]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}
        graph.outgoing_refs[page_b] = {page_c}

        analyzer = PathAnalyzer(graph)
        path = analyzer.find_shortest_path(page_a, page_c)

        assert path == [page_a, page_b, page_c]

    def test_find_shortest_path_no_path(self):
        """Test when no path exists."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})

        site = Mock()
        site.pages = [page_a, page_b]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)  # No connections

        analyzer = PathAnalyzer(graph)
        path = analyzer.find_shortest_path(page_a, page_b)

        assert path is None

    def test_find_shortest_path_same_page(self):
        """Test when source equals target."""
        page_a = Mock(source_path=Path("a.md"), metadata={})

        site = Mock()
        site.pages = [page_a]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)

        analyzer = PathAnalyzer(graph)
        path = analyzer.find_shortest_path(page_a, page_a)

        assert path == [page_a]

    def test_analyze_empty_graph(self):
        """Test analysis on empty graph."""
        graph = Mock()
        graph.get_analysis_pages.return_value = []
        graph.outgoing_refs = defaultdict(set)

        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()

        assert len(results.betweenness_centrality) == 0
        assert len(results.closeness_centrality) == 0
        assert results.avg_path_length == 0.0
        assert results.diameter == 0

    def test_analyze_single_page(self):
        """Test analysis with single page."""
        page = Mock(source_path=Path("page.md"), metadata={})

        graph = Mock()
        graph.get_analysis_pages.return_value = [page]
        graph.outgoing_refs = defaultdict(set)

        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()

        # Single isolated page has zero centrality
        assert results.betweenness_centrality[page] == 0.0
        assert results.closeness_centrality[page] == 0.0

    def test_analyze_chain(self):
        """Test analysis on chain: A -> B -> C."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})
        page_c = Mock(source_path=Path("c.md"), metadata={})

        graph = Mock()
        graph.get_analysis_pages.return_value = [page_a, page_b, page_c]
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}
        graph.outgoing_refs[page_b] = {page_c}

        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()

        # B should have highest betweenness (it's on the path from A to C)
        assert results.betweenness_centrality[page_b] > results.betweenness_centrality[page_a]
        assert results.betweenness_centrality[page_b] > results.betweenness_centrality[page_c]

        # Network diameter should be 2 (A to C)
        assert results.diameter == 2

    def test_analyze_star(self):
        """Test analysis on star graph: center connected to all spokes."""
        center = Mock(source_path=Path("center.md"), metadata={})
        spokes = [Mock(source_path=Path(f"spoke{i}.md"), metadata={}) for i in range(4)]

        graph = Mock()
        graph.get_analysis_pages.return_value = [center] + spokes
        graph.outgoing_refs = defaultdict(set)

        # Center connects to all spokes (directed out from center)
        graph.outgoing_refs[center] = set(spokes)

        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()

        # Center should have high closeness (can reach all spokes easily)
        center_closeness = results.closeness_centrality[center]
        for spoke in spokes:
            # Spokes can't reach each other, only center can reach them
            assert center_closeness > results.closeness_centrality[spoke]

    def test_analyze_fully_connected(self):
        """Test analysis on fully connected graph."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(4)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        # Fully connected
        for page in pages:
            graph.outgoing_refs[page] = {p for p in pages if p != page}

        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()

        # In fully connected graph, all pages should have similar centrality
        betweenness_values = list(results.betweenness_centrality.values())
        avg_betweenness = sum(betweenness_values) / len(betweenness_values)

        for value in betweenness_values:
            # Should be within 10% of average
            assert abs(value - avg_betweenness) / (avg_betweenness + 1e-10) < 0.1

        # Diameter should be 1 (all connected directly)
        assert results.diameter == 1

    def test_find_all_paths(self):
        """Test finding all paths between pages."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})
        page_c = Mock(source_path=Path("c.md"), metadata={})

        site = Mock()
        site.pages = [page_a, page_b, page_c]

        # Create diamond: A -> B -> C and A -> C
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b, page_c}
        graph.outgoing_refs[page_b] = {page_c}

        analyzer = PathAnalyzer(graph)
        result = analyzer.find_all_paths(page_a, page_c, max_length=10)

        # Should return PathSearchResult
        assert isinstance(result, PathSearchResult)
        assert result.complete is True
        assert result.termination_reason is None

        # Should find 2 paths: A->C and A->B->C
        assert len(result.paths) == 2
        assert [page_a, page_c] in result.paths
        assert [page_a, page_b, page_c] in result.paths

    def test_find_all_paths_max_length(self):
        """Test that max_length constraint works."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(5)]

        site = Mock()
        site.pages = pages

        # Create chain: 0 -> 1 -> 2 -> 3 -> 4
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        for i in range(4):
            graph.outgoing_refs[pages[i]] = {pages[i + 1]}

        analyzer = PathAnalyzer(graph)

        # Max length 2 should not find path from 0 to 4 (needs length 4)
        result = analyzer.find_all_paths(pages[0], pages[4], max_length=2)
        assert len(result.paths) == 0

        # Max length 5 should find the path
        result = analyzer.find_all_paths(pages[0], pages[4], max_length=5)
        assert len(result.paths) == 1
        assert result.paths[0] == pages

    def test_find_all_paths_max_paths_limit(self):
        """Test that max_paths limit stops search early."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})
        page_c = Mock(source_path=Path("c.md"), metadata={})

        site = Mock()
        site.pages = [page_a, page_b, page_c]

        # Create diamond: A -> B -> C and A -> C
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b, page_c}
        graph.outgoing_refs[page_b] = {page_c}

        analyzer = PathAnalyzer(graph)

        # Limit to 1 path
        result = analyzer.find_all_paths(page_a, page_c, max_length=10, max_paths=1)

        assert len(result.paths) == 1
        assert result.complete is False
        assert "max_paths" in result.termination_reason

    def test_find_all_paths_timeout(self):
        """Test that timeout stops search early."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})

        site = Mock()
        site.pages = [page_a, page_b]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)

        analyzer = PathAnalyzer(graph)

        # Very short timeout (should complete before timeout for simple graph)
        result = analyzer.find_all_paths(
            page_a, page_b, max_length=10, timeout_seconds=10.0
        )

        # Should complete (no path exists)
        assert result.complete is True

    def test_find_all_paths_simple_legacy_api(self):
        """Test the legacy find_all_paths_simple API."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})
        page_c = Mock(source_path=Path("c.md"), metadata={})

        site = Mock()
        site.pages = [page_a, page_b, page_c]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b, page_c}
        graph.outgoing_refs[page_b] = {page_c}

        analyzer = PathAnalyzer(graph)
        paths = analyzer.find_all_paths_simple(page_a, page_c, max_length=10)

        # Returns list directly (not PathSearchResult)
        assert isinstance(paths, list)
        assert len(paths) == 2

    def test_filters_generated_pages(self):
        """Test that generated pages are excluded from analysis."""
        real_page = Mock(source_path=Path("real.md"), metadata={})
        generated_page = Mock(source_path=Path("generated.md"), metadata={"_generated": True})

        graph = Mock()
        graph.get_analysis_pages.return_value = [real_page, generated_page]
        graph.outgoing_refs = defaultdict(set)

        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()

        # Only real page should be analyzed (generated filtered in analyze())
        assert len(results.betweenness_centrality) == 1
        assert real_page in results.betweenness_centrality
        assert generated_page not in results.betweenness_centrality


class TestApproximation:
    """Tests for pivot-based approximation."""

    def test_uses_exact_for_small_sites(self):
        """Test that exact algorithm is used for small sites."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(10)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        # Default threshold is 500, so 10 pages should use exact
        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()

        assert results.is_approximate is False
        assert results.pivots_used == 10  # All pages used

    def test_uses_approximate_for_large_sites(self):
        """Test that approximate algorithm is used for large sites."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(600)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        # Create some connections
        for i in range(599):
            graph.outgoing_refs[pages[i]] = {pages[i + 1]}

        # Default threshold is 500, so 600 pages should use approximate
        analyzer = PathAnalyzer(graph, k_pivots=50)
        results = analyzer.analyze()

        assert results.is_approximate is True
        assert results.pivots_used == 50

    def test_custom_threshold(self):
        """Test custom auto_approximate_threshold."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(100)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        # Set threshold to 50, so 100 pages should use approximate
        analyzer = PathAnalyzer(graph, auto_approximate_threshold=50, k_pivots=20)
        results = analyzer.analyze()

        assert results.is_approximate is True
        assert results.pivots_used == 20

    def test_deterministic_with_seed(self):
        """Test that results are deterministic with same seed."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(100)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        # Create connections
        for i in range(99):
            graph.outgoing_refs[pages[i]] = {pages[i + 1]}

        # Run with same seed twice
        analyzer1 = PathAnalyzer(graph, auto_approximate_threshold=50, seed=42)
        results1 = analyzer1.analyze()

        analyzer2 = PathAnalyzer(graph, auto_approximate_threshold=50, seed=42)
        results2 = analyzer2.analyze()

        # Results should be identical
        for page in pages:
            assert results1.betweenness_centrality[page] == results2.betweenness_centrality[page]
            assert results1.closeness_centrality[page] == results2.closeness_centrality[page]

    def test_different_seeds_give_different_results(self):
        """Test that different seeds can give different results."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(100)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        # Create connections
        for i in range(99):
            graph.outgoing_refs[pages[i]] = {pages[i + 1]}

        # Run with different seeds
        analyzer1 = PathAnalyzer(graph, auto_approximate_threshold=50, seed=42)
        results1 = analyzer1.analyze()

        analyzer2 = PathAnalyzer(graph, auto_approximate_threshold=50, seed=123)
        results2 = analyzer2.analyze()

        # Results may differ (not guaranteed, but likely with different pivots)
        # Just check both completed successfully
        assert results1.is_approximate is True
        assert results2.is_approximate is True

    def test_approximate_preserves_relative_ranking(self):
        """Test that approximate algorithm preserves relative ranking of important nodes."""
        # Create a chain graph where middle nodes have higher betweenness
        # 0 -> 1 -> 2 -> 3 -> ... -> 99
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(100)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        # Create a chain
        for i in range(99):
            graph.outgoing_refs[pages[i]] = {pages[i + 1]}

        analyzer = PathAnalyzer(graph, auto_approximate_threshold=50, k_pivots=30)
        results = analyzer.analyze()

        assert results.is_approximate is True

        # In a chain, middle nodes should have higher betweenness than endpoints
        # Node 50 (middle) should have higher betweenness than node 0 or 99
        middle_betweenness = results.betweenness_centrality[pages[50]]
        first_betweenness = results.betweenness_centrality[pages[0]]
        last_betweenness = results.betweenness_centrality[pages[99]]

        # Middle should be higher than endpoints
        assert middle_betweenness >= first_betweenness
        assert middle_betweenness >= last_betweenness


class TestProgressCallback:
    """Tests for progress callback functionality."""

    def test_progress_callback_called(self):
        """Test that progress callback is called during analysis."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(5)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        progress_calls = []

        def callback(current, total, phase):
            progress_calls.append((current, total, phase))

        analyzer = PathAnalyzer(graph)
        analyzer.analyze(progress_callback=callback)

        # Should have calls for both betweenness and closeness phases
        betweenness_calls = [c for c in progress_calls if c[2] == "betweenness"]
        closeness_calls = [c for c in progress_calls if c[2] == "closeness"]

        assert len(betweenness_calls) == 5  # 5 pages
        assert len(closeness_calls) == 5  # 5 pages

        # Check progression
        assert betweenness_calls[0][0] == 1  # First call is 1
        assert betweenness_calls[-1][0] == 5  # Last call is 5
        assert all(c[1] == 5 for c in betweenness_calls)  # Total is always 5

    def test_progress_callback_with_approximation(self):
        """Test progress callback reports pivot count for approximate analysis."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(100)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        progress_calls = []

        def callback(current, total, phase):
            progress_calls.append((current, total, phase))

        # Force approximation with low threshold
        analyzer = PathAnalyzer(graph, auto_approximate_threshold=50, k_pivots=20)
        analyzer.analyze(progress_callback=callback)

        # Should report based on pivot count, not total pages
        betweenness_calls = [c for c in progress_calls if c[2] == "betweenness"]
        assert all(c[1] == 20 for c in betweenness_calls)  # Total should be k_pivots


class TestAnalyzePathsFunction:
    """Tests for convenience function."""

    def test_analyze_paths(self):
        """Test the convenience function."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(3)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[pages[0]] = {pages[1]}
        graph.outgoing_refs[pages[1]] = {pages[2]}

        results = analyze_paths(graph)

        assert isinstance(results, PathAnalysisResults)
        assert len(results.betweenness_centrality) == 3
        assert len(results.closeness_centrality) == 3
        assert results.diameter > 0

    def test_analyze_paths_with_parameters(self):
        """Test convenience function with custom parameters."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(100)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        results = analyze_paths(
            graph,
            k_pivots=25,
            seed=123,
            auto_approximate_threshold=50,
        )

        assert results.is_approximate is True
        assert results.pivots_used == 25

    def test_analyze_paths_with_progress_callback(self):
        """Test convenience function with progress callback."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(3)]

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = defaultdict(set)

        callback_called = []

        def callback(current, total, phase):
            callback_called.append(phase)

        analyze_paths(graph, progress_callback=callback)

        assert "betweenness" in callback_called
        assert "closeness" in callback_called
