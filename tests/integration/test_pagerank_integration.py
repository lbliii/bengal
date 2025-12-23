"""
Integration tests for PageRank with KnowledgeGraph.
"""

from collections import defaultdict
from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.analysis.knowledge_graph import KnowledgeGraph


@pytest.fixture
def sample_site(tmp_path):
    """Create a mock site with interconnected pages for testing."""
    # Create mock pages
    hub_page = Mock()
    hub_page.source_path = Path("hub.md")
    hub_page.title = "Hub Page"
    hub_page.metadata = {}
    hub_page.links = []

    spoke_pages = []
    for i in range(3):
        spoke = Mock()
        spoke.source_path = Path(f"spoke{i}.md")
        spoke.title = f"Spoke {i}"
        spoke.metadata = {}
        spoke.links = ["/hub/"]
        spoke_pages.append(spoke)

    orphan_page = Mock()
    orphan_page.source_path = Path("orphan.md")
    orphan_page.title = "Orphan Page"
    orphan_page.metadata = {}
    orphan_page.links = []

    # Create mock site
    site = Mock()
    site.pages = [hub_page] + spoke_pages + [orphan_page]
    site.sections = []
    site.menus = {}
    site.config = {"taxonomies": {}}

    # Setup graph manually with connections
    # Spokes link to hub
    graph = KnowledgeGraph(site)
    graph._built = True  # Skip build method
    graph.incoming_refs = defaultdict(int)
    graph.outgoing_refs = defaultdict(set)

    # Set up links: spokes -> hub
    for spoke in spoke_pages:
        graph.incoming_refs[hub_page] += 1
        graph.outgoing_refs[spoke].add(hub_page)

    return site, graph, hub_page, spoke_pages, orphan_page


class TestPageRankIntegration:
    """Integration tests for PageRank with knowledge graph."""

    def test_compute_pagerank(self, sample_site):
        """Test basic PageRank computation."""
        site, graph, hub_page, spoke_pages, orphan_page = sample_site

        # Compute PageRank
        results = graph.compute_pagerank()

        # Verify results structure
        assert results.converged is True
        assert results.iterations > 0
        assert results.damping_factor == 0.85
        assert len(results.scores) == 5  # 1 hub + 3 spokes + 1 orphan

        # Hub should have highest score (3 incoming links)
        hub_score = results.get_score(hub_page)

        for spoke in spoke_pages:
            spoke_score = results.get_score(spoke)
            assert hub_score > spoke_score

        orphan_score = results.get_score(orphan_page)
        assert hub_score > orphan_score

    def test_pagerank_caching(self, sample_site):
        """Test that PageRank results are cached."""
        site, graph, hub_page, spoke_pages, orphan_page = sample_site

        # First computation
        results1 = graph.compute_pagerank()

        # Second computation should return cached results
        results2 = graph.compute_pagerank()

        # Should be the same object
        assert results1 is results2

        # Force recompute
        results3 = graph.compute_pagerank(force_recompute=True)

        # Should be different object but same scores
        assert results3 is not results1
        assert results3.scores == results1.scores

    def test_get_top_pages_by_pagerank(self, sample_site):
        """Test getting top pages by PageRank."""
        site, graph, hub_page, spoke_pages, orphan_page = sample_site

        # Get top 3 pages
        top_pages = graph.get_top_pages_by_pagerank(limit=3)

        assert len(top_pages) == 3

        # First page should be the hub (most links)
        assert top_pages[0][0] == hub_page

        # All should have scores
        for _page, score in top_pages:
            assert score > 0
            assert isinstance(score, float)

    def test_get_pagerank_score(self, sample_site):
        """Test getting PageRank score for specific page."""
        site, graph, hub_page, spoke_pages, orphan_page = sample_site

        # Get score for hub page
        hub_score = graph.get_pagerank_score(hub_page)

        assert hub_score > 0
        assert isinstance(hub_score, float)

        # Spokes should have lower scores
        for spoke in spoke_pages:
            spoke_score = graph.get_pagerank_score(spoke)
            assert hub_score > spoke_score

    def test_personalized_pagerank(self, sample_site):
        """Test personalized PageRank from seed pages."""
        site, graph, hub_page, spoke_pages, orphan_page = sample_site

        # Compute personalized PageRank around spoke 0
        seed_pages = {spoke_pages[0]}
        results = graph.compute_personalized_pagerank(seed_pages)

        # Verify results
        assert results.converged is True
        assert len(results.scores) == 5

        # Spoke 0 should have different score than in standard PageRank
        standard_results = graph.compute_pagerank()

        spoke0_personalized = results.get_score(spoke_pages[0])
        spoke0_standard = standard_results.get_score(spoke_pages[0])

        # Personalized score should be different (likely higher)
        assert spoke0_personalized != spoke0_standard

    def test_personalized_pagerank_empty_seeds(self, sample_site):
        """Test that personalized PageRank requires seed pages."""
        site, graph, hub_page, spoke_pages, orphan_page = sample_site

        with pytest.raises(ValueError, match="requires at least one seed page"):
            graph.compute_personalized_pagerank(seed_pages=set())

    def test_pagerank_without_build(self, sample_site):
        """Test that PageRank requires graph to be built first."""
        from bengal.errors import BengalError

        site, graph, hub_page, spoke_pages, orphan_page = sample_site

        # Create new graph without building
        new_graph = KnowledgeGraph(site)

        with pytest.raises(BengalError, match="not built"):
            new_graph.compute_pagerank()

    def test_pagerank_with_different_damping(self, sample_site):
        """Test PageRank with different damping factors."""
        site, graph, hub_page, spoke_pages, orphan_page = sample_site

        # Compute with different damping factors
        results_low = graph.compute_pagerank(damping=0.5)
        results_high = graph.compute_pagerank(damping=0.95, force_recompute=True)

        # Both should converge
        assert results_low.converged is True
        assert results_high.converged is True

        # Scores should be different
        hub_score_low = results_low.get_score(hub_page)
        hub_score_high = results_high.get_score(hub_page)

        assert hub_score_low != hub_score_high

    def test_pagerank_identifies_important_pages(self, sample_site):
        """Test that PageRank correctly identifies important pages."""
        site, graph, hub_page, spoke_pages, orphan_page = sample_site

        results = graph.compute_pagerank()

        # Hub should be in top 90th percentile
        top_pages = results.get_pages_above_percentile(90)
        assert hub_page in top_pages

        # Orphan should not be in top percentile
        assert orphan_page not in top_pages


class TestPageRankScalability:
    """Test PageRank performance characteristics."""

    def test_pagerank_large_graph(self):
        """Test PageRank on larger graph (50 pages)."""
        # Create 50 mock pages with circular interconnections
        pages = []
        for i in range(50):
            page = Mock()
            page.source_path = Path(f"page{i}.md")
            page.title = f"Page {i}"
            page.metadata = {}
            page.links = [f"/page{(i + 1) % 50}/"]
            pages.append(page)

        # Create mock site
        site = Mock()
        site.pages = pages
        site.sections = []
        site.menus = {}
        site.config = {"taxonomies": {}}

        # Build graph with circular connections
        graph = KnowledgeGraph(site)
        graph._built = True
        graph.incoming_refs = defaultdict(int)
        graph.outgoing_refs = defaultdict(set)

        for i, page in enumerate(pages):
            next_page = pages[(i + 1) % 50]
            graph.outgoing_refs[page].add(next_page)
            graph.incoming_refs[next_page] += 1

        # Compute PageRank
        results = graph.compute_pagerank()

        # Should converge
        assert results.converged is True
        assert len(results.scores) == 50

        # All pages should have similar scores (circular graph)
        scores = list(results.scores.values())
        avg_score = sum(scores) / len(scores)

        for score in scores:
            # Each score should be within 10% of average (approximately equal)
            assert abs(score - avg_score) / avg_score < 0.1

    def test_pagerank_disconnected_components(self):
        """Test PageRank on graph with disconnected components."""
        # Component 1: A -> B
        page_a = Mock()
        page_a.source_path = Path("a.md")
        page_a.title = "Page A"
        page_a.metadata = {}
        page_a.links = ["/b/"]

        page_b = Mock()
        page_b.source_path = Path("b.md")
        page_b.title = "Page B"
        page_b.metadata = {}
        page_b.links = []

        # Component 2: C -> D
        page_c = Mock()
        page_c.source_path = Path("c.md")
        page_c.title = "Page C"
        page_c.metadata = {}
        page_c.links = ["/d/"]

        page_d = Mock()
        page_d.source_path = Path("d.md")
        page_d.title = "Page D"
        page_d.metadata = {}
        page_d.links = []

        # Create mock site
        site = Mock()
        site.pages = [page_a, page_b, page_c, page_d]
        site.sections = []
        site.menus = {}
        site.config = {"taxonomies": {}}

        # Build graph with two disconnected components
        graph = KnowledgeGraph(site)
        graph._built = True
        graph.incoming_refs = defaultdict(int)
        graph.outgoing_refs = defaultdict(set)

        # Component 1: A -> B
        graph.outgoing_refs[page_a].add(page_b)
        graph.incoming_refs[page_b] += 1

        # Component 2: C -> D
        graph.outgoing_refs[page_c].add(page_d)
        graph.incoming_refs[page_d] += 1

        results = graph.compute_pagerank()

        # Should still converge
        assert results.converged is True

        # B and D should have similar scores (both have 1 incoming link)
        score_b = results.get_score(page_b)
        score_d = results.get_score(page_d)

        assert score_b == pytest.approx(score_d, rel=1e-3)
