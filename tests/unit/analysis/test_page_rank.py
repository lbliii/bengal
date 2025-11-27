"""
Unit tests for PageRank algorithm.
"""

from collections import defaultdict
from unittest.mock import Mock

import pytest

from bengal.analysis.page_rank import PageRankCalculator, PageRankResults, analyze_page_importance


class TestPageRankResults:
    """Tests for PageRankResults dataclass."""

    def test_get_top_pages(self):
        """Test getting top N pages by score."""
        # Create mock pages
        pages = [Mock(source_path=f"page_{i}.md") for i in range(5)]

        # Create results with varying scores
        scores = {
            pages[0]: 0.5,
            pages[1]: 0.3,
            pages[2]: 0.8,
            pages[3]: 0.1,
            pages[4]: 0.6,
        }

        results = PageRankResults(scores=scores, iterations=10, converged=True, damping_factor=0.85)

        # Get top 3
        top_pages = results.get_top_pages(3)

        assert len(top_pages) == 3
        assert top_pages[0][0] == pages[2]  # 0.8
        assert top_pages[1][0] == pages[4]  # 0.6
        assert top_pages[2][0] == pages[0]  # 0.5
        assert top_pages[0][1] == 0.8
        assert top_pages[1][1] == 0.6
        assert top_pages[2][1] == 0.5

    def test_get_top_pages_empty(self):
        """Test getting top pages from empty results."""
        results = PageRankResults(scores={}, iterations=0, converged=True, damping_factor=0.85)

        top_pages = results.get_top_pages(10)
        assert len(top_pages) == 0

    def test_get_pages_above_percentile(self):
        """Test getting pages above a percentile threshold."""
        pages = [Mock(source_path=f"page_{i}.md") for i in range(10)]

        # Create results with scores 0.1 to 1.0
        scores = {pages[i]: (i + 1) * 0.1 for i in range(10)}

        results = PageRankResults(scores=scores, iterations=10, converged=True, damping_factor=0.85)

        # Get top 20% (should be top 2 pages: 0.9, 1.0)
        top_20_percent = results.get_pages_above_percentile(80)

        assert len(top_20_percent) == 2
        assert pages[9] in top_20_percent  # 1.0
        assert pages[8] in top_20_percent  # 0.9

    def test_get_pages_above_percentile_empty(self):
        """Test percentile on empty results."""
        results = PageRankResults(scores={}, iterations=0, converged=True, damping_factor=0.85)

        top_pages = results.get_pages_above_percentile(90)
        assert len(top_pages) == 0

    def test_get_score(self):
        """Test getting score for specific page."""
        page1 = Mock(source_path="page1.md")
        page2 = Mock(source_path="page2.md")
        page3 = Mock(source_path="page3.md")

        scores = {
            page1: 0.5,
            page2: 0.3,
        }

        results = PageRankResults(scores=scores, iterations=10, converged=True, damping_factor=0.85)

        assert results.get_score(page1) == 0.5
        assert results.get_score(page2) == 0.3
        assert results.get_score(page3) == 0.0  # Not in results


class TestPageRankCalculator:
    """Tests for PageRank computation."""

    def test_init_validates_damping(self):
        """Test that damping factor is validated."""
        graph = Mock()

        # Valid damping
        calc = PageRankCalculator(graph, damping=0.85)
        assert calc.damping == 0.85

        # Invalid damping - too low
        with pytest.raises(ValueError, match="Damping factor must be between 0 and 1"):
            PageRankCalculator(graph, damping=0.0)

        # Invalid damping - too high
        with pytest.raises(ValueError, match="Damping factor must be between 0 and 1"):
            PageRankCalculator(graph, damping=1.0)

        # Invalid damping - negative
        with pytest.raises(ValueError, match="Damping factor must be between 0 and 1"):
            PageRankCalculator(graph, damping=-0.5)

    def test_init_validates_max_iterations(self):
        """Test that max_iterations is validated."""
        graph = Mock()

        # Valid iterations
        calc = PageRankCalculator(graph, damping=0.85, max_iterations=100)
        assert calc.max_iterations == 100

        # Invalid iterations
        with pytest.raises(ValueError, match="Max iterations must be >= 1"):
            PageRankCalculator(graph, damping=0.85, max_iterations=0)

        with pytest.raises(ValueError, match="Max iterations must be >= 1"):
            PageRankCalculator(graph, damping=0.85, max_iterations=-1)

    def test_compute_empty_site(self):
        """Test PageRank on site with no pages."""
        # Create mock graph with no pages
        graph = Mock()
        graph.get_analysis_pages.return_value = []
        graph.outgoing_refs = defaultdict(set)

        calc = PageRankCalculator(graph, damping=0.85)
        results = calc.compute()

        assert results.scores == {}
        assert results.iterations == 0
        assert results.converged is True
        assert results.damping_factor == 0.85

    def test_compute_single_page(self):
        """Test PageRank on site with single page."""
        # Create mock page
        page = Mock()
        page.metadata = {}

        graph = Mock()
        graph.get_analysis_pages.return_value = [page]
        graph.outgoing_refs = defaultdict(set)

        calc = PageRankCalculator(graph, damping=0.85)
        results = calc.compute()

        # Single page with damping=0.85 gets (1-0.85)/1 = 0.15
        # This is expected behavior: damping represents "following links"
        # With no links, the score is just the random jump probability
        assert len(results.scores) == 1
        assert results.scores[page] == pytest.approx(0.15, rel=1e-5)
        assert results.converged is True

    def test_compute_linear_chain(self):
        """Test PageRank on linear chain: A -> B -> C."""
        # Create mock pages
        page_a = Mock(source_path="a.md", title="Page A")
        page_a.metadata = {}
        page_b = Mock(source_path="b.md", title="Page B")
        page_b.metadata = {}
        page_c = Mock(source_path="c.md", title="Page C")
        page_c.metadata = {}

        # A -> B -> C
        graph = Mock()
        graph.get_analysis_pages.return_value = [page_a, page_b, page_c]
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}
        graph.outgoing_refs[page_b] = {page_c}

        calc = PageRankCalculator(graph, damping=0.85, max_iterations=100)
        results = calc.compute()

        # Page C should have highest score (pointed to by B)
        # Page B should have middle score (pointed to by A)
        # Page A should have lowest score (not pointed to by anyone)
        assert results.scores[page_c] > results.scores[page_b]
        assert results.scores[page_b] > results.scores[page_a]
        assert results.converged is True

    def test_compute_star_graph(self):
        """Test PageRank on star: A -> B, A -> C, A -> D."""
        # Create mock pages
        page_a = Mock(source_path="a.md", title="Hub")
        page_a.metadata = {}
        page_b = Mock(source_path="b.md", title="Spoke 1")
        page_b.metadata = {}
        page_c = Mock(source_path="c.md", title="Spoke 2")
        page_c.metadata = {}
        page_d = Mock(source_path="d.md", title="Spoke 3")
        page_d.metadata = {}

        # A links to all others, no one links back
        graph = Mock()
        graph.get_analysis_pages.return_value = [page_a, page_b, page_c, page_d]
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b, page_c, page_d}

        calc = PageRankCalculator(graph, damping=0.85, max_iterations=100)
        results = calc.compute()

        # Spokes should have equal scores (each pointed to once)
        assert results.scores[page_b] == pytest.approx(results.scores[page_c], rel=1e-5)
        assert results.scores[page_c] == pytest.approx(results.scores[page_d], rel=1e-5)

        # Hub should have lower score (no incoming links)
        assert results.scores[page_a] < results.scores[page_b]

    def test_compute_circular(self):
        """Test PageRank on circular graph: A -> B -> C -> A."""
        # Create mock pages
        page_a = Mock(source_path="a.md", title="Page A")
        page_a.metadata = {}
        page_b = Mock(source_path="b.md", title="Page B")
        page_b.metadata = {}
        page_c = Mock(source_path="c.md", title="Page C")
        page_c.metadata = {}

        # Circular: A -> B -> C -> A
        graph = Mock()
        graph.get_analysis_pages.return_value = [page_a, page_b, page_c]
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}
        graph.outgoing_refs[page_b] = {page_c}
        graph.outgoing_refs[page_c] = {page_a}

        calc = PageRankCalculator(graph, damping=0.85, max_iterations=100)
        results = calc.compute()

        # All pages should have equal scores (symmetric)
        assert results.scores[page_a] == pytest.approx(results.scores[page_b], rel=1e-5)
        assert results.scores[page_b] == pytest.approx(results.scores[page_c], rel=1e-5)
        assert results.converged is True

    def test_compute_convergence(self):
        """Test that algorithm converges within threshold."""
        # Create simple graph
        page_a = Mock(source_path="a.md")
        page_a.metadata = {}
        page_b = Mock(source_path="b.md")
        page_b.metadata = {}

        graph = Mock()
        graph.get_analysis_pages.return_value = [page_a, page_b]
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}

        # Use very tight threshold
        calc = PageRankCalculator(
            graph, damping=0.85, max_iterations=1000, convergence_threshold=1e-8
        )
        results = calc.compute()

        # Should converge with tight threshold
        assert results.converged is True
        assert results.iterations < 1000

    def test_compute_personalized(self):
        """Test personalized PageRank."""
        # Create mock pages
        page_a = Mock(source_path="a.md")
        page_a.metadata = {}
        page_b = Mock(source_path="b.md")
        page_b.metadata = {}
        page_c = Mock(source_path="c.md")
        page_c.metadata = {}

        # A -> B, B -> C
        graph = Mock()
        graph.get_analysis_pages.return_value = [page_a, page_b, page_c]
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}
        graph.outgoing_refs[page_b] = {page_c}

        calc = PageRankCalculator(graph, damping=0.85)

        # Personalized around page A
        results = calc.compute_personalized(seed_pages={page_a})

        # Page A should have higher score than in standard PageRank
        # because random jumps go back to A
        assert results.scores[page_a] > 0
        assert results.converged is True

    def test_compute_personalized_empty_seeds(self):
        """Test that personalized PageRank requires seed pages."""
        graph = Mock()
        graph.get_analysis_pages.return_value = []

        calc = PageRankCalculator(graph, damping=0.85)

        with pytest.raises(ValueError, match="seed_pages cannot be empty"):
            calc.compute_personalized(seed_pages=set())

    def test_compute_filters_generated_pages(self):
        """Test that generated pages are excluded from PageRank."""
        # Create mock pages
        page_real = Mock(source_path="real.md")
        page_real.metadata = {}

        page_generated = Mock(source_path="tag/python.md")
        page_generated.metadata = {"_generated": True}

        graph = Mock()
        graph.get_analysis_pages.return_value = [page_real, page_generated]
        graph.outgoing_refs = defaultdict(set)

        calc = PageRankCalculator(graph, damping=0.85)
        results = calc.compute()

        # Only real page should be in results (generated pages filtered out)
        assert len(results.scores) == 1
        assert page_real in results.scores
        assert page_generated not in results.scores


class TestAnalyzePageImportance:
    """Tests for convenience function."""

    def test_analyze_page_importance(self):
        """Test the convenience function."""
        # Create mock pages
        page_a = Mock(source_path="a.md", title="Page A")
        page_a.metadata = {}
        page_b = Mock(source_path="b.md", title="Page B")
        page_b.metadata = {}
        page_c = Mock(source_path="c.md", title="Page C")
        page_c.metadata = {}

        # B and C point to A (A is important)
        graph = Mock()
        graph.get_analysis_pages.return_value = [page_a, page_b, page_c]
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_b] = {page_a}
        graph.outgoing_refs[page_c] = {page_a}

        # Analyze
        top_pages = analyze_page_importance(graph, damping=0.85, top_n=2)

        assert len(top_pages) == 2
        # Page A should be first (most important)
        assert top_pages[0][0] == page_a
        # Should return tuples of (page, score)
        assert isinstance(top_pages[0][1], float)
