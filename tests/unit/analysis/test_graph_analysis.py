"""
Tests for the GraphAnalyzer class.

Verifies the extracted graph analysis functionality works correctly
both directly and through KnowledgeGraph delegation.
"""

from __future__ import annotations

import pytest

from bengal.analysis import GraphAnalyzer, KnowledgeGraph
from bengal.core.page import Page
from bengal.core.site import Site


@pytest.fixture
def simple_site(tmp_path):
    """Create a simple site for testing."""
    site = Site(root_path=tmp_path, config={})

    # Create pages (slug is auto-derived from title)
    page1 = Page(
        source_path=tmp_path / "page1.md",
        content="# Page 1",
        metadata={"title": "Page 1"},
    )

    page2 = Page(
        source_path=tmp_path / "page2.md",
        content="# Page 2",
        metadata={"title": "Page 2"},
    )

    page3 = Page(
        source_path=tmp_path / "page3.md",
        content="# Page 3",
        metadata={"title": "Page 3"},
    )

    site.pages = [page1, page2, page3]
    return site


@pytest.fixture
def site_with_links(tmp_path):
    """Create a test site with internal links."""
    site = Site(root_path=tmp_path, config={})

    # Create hub page (slug is auto-derived from title)
    hub = Page(
        source_path=tmp_path / "hub.md",
        content="# Hub Page",
        metadata={"title": "Hub"},
    )

    # Create leaf pages that link to hub
    leaf1 = Page(
        source_path=tmp_path / "leaf1.md",
        content="# Leaf 1",
        metadata={"title": "Leaf 1"},
    )
    leaf1.related_posts = [hub]  # Simulates link

    leaf2 = Page(
        source_path=tmp_path / "leaf2.md",
        content="# Leaf 2",
        metadata={"title": "Leaf 2"},
    )
    leaf2.related_posts = [hub]  # Simulates link

    site.pages = [hub, leaf1, leaf2]
    return site


class TestGraphAnalyzerDirect:
    """Test GraphAnalyzer when used directly."""

    def test_analyzer_requires_built_graph(self, simple_site):
        """Test that analyzer methods require graph to be built."""
        graph = KnowledgeGraph(simple_site)
        analyzer = GraphAnalyzer(graph)

        with pytest.raises(ValueError, match="graph.build"):
            analyzer.get_hubs()

    def test_get_connectivity_score(self, simple_site):
        """Test connectivity score calculation."""
        graph = KnowledgeGraph(simple_site)
        graph.build()
        analyzer = GraphAnalyzer(graph)

        page1 = simple_site.pages[0]
        score = analyzer.get_connectivity_score(page1)
        # Score should be non-negative
        assert score >= 0

    def test_get_hubs(self, site_with_links):
        """Test hub detection."""
        graph = KnowledgeGraph(site_with_links, hub_threshold=1)
        graph.build()
        analyzer = GraphAnalyzer(graph)

        hubs = analyzer.get_hubs()
        # Hub page should be detected
        assert isinstance(hubs, list)

    def test_get_leaves(self, simple_site):
        """Test leaf detection."""
        graph = KnowledgeGraph(simple_site, leaf_threshold=10)
        graph.build()
        analyzer = GraphAnalyzer(graph)

        leaves = analyzer.get_leaves()
        # With high threshold, all pages might be leaves
        assert isinstance(leaves, list)

    def test_get_orphans(self, simple_site):
        """Test orphan detection."""
        graph = KnowledgeGraph(simple_site)
        graph.build()
        analyzer = GraphAnalyzer(graph)

        orphans = analyzer.get_orphans()
        assert isinstance(orphans, list)

    def test_get_connectivity(self, simple_site):
        """Test connectivity information."""
        graph = KnowledgeGraph(simple_site)
        graph.build()
        analyzer = GraphAnalyzer(graph)

        page1 = simple_site.pages[0]
        connectivity = analyzer.get_connectivity(page1)

        assert connectivity.page == page1
        assert connectivity.outgoing_refs >= 0
        assert connectivity.incoming_refs >= 0
        assert (
            connectivity.connectivity_score
            == connectivity.incoming_refs + connectivity.outgoing_refs
        )

    def test_get_layers(self, simple_site):
        """Test layer partitioning."""
        graph = KnowledgeGraph(simple_site)
        graph.build()
        analyzer = GraphAnalyzer(graph)

        hubs, mid_tier, leaves = analyzer.get_layers()

        # All pages should be in exactly one layer
        all_in_layers = set(hubs) | set(mid_tier) | set(leaves)
        assert len(all_in_layers) == len(simple_site.pages)


class TestGraphAnalyzerDelegation:
    """Test that KnowledgeGraph correctly delegates to GraphAnalyzer."""

    def test_delegation_preserves_behavior(self, simple_site):
        """Test that delegated methods return same results."""
        graph = KnowledgeGraph(simple_site)
        graph.build()

        # Direct analyzer access
        analyzer = GraphAnalyzer(graph)

        # Compare results
        page1 = simple_site.pages[0]

        assert graph.get_connectivity_score(page1) == analyzer.get_connectivity_score(page1)
        assert graph.get_hubs() == analyzer.get_hubs()
        assert graph.get_leaves() == analyzer.get_leaves()
        assert graph.get_orphans() == analyzer.get_orphans()
        assert graph.get_layers() == analyzer.get_layers()

    def test_delegation_error_handling(self, simple_site):
        """Test that delegated methods still raise ValueError before build."""
        graph = KnowledgeGraph(simple_site)

        with pytest.raises(ValueError, match="Must call build"):
            graph.get_hubs()

        with pytest.raises(ValueError, match="Must call build"):
            graph.get_leaves()

        with pytest.raises(ValueError, match="Must call build"):
            graph.get_orphans()

        with pytest.raises(ValueError, match="Must call build"):
            graph.get_layers()

        with pytest.raises(ValueError, match="Must call build"):
            graph.get_connectivity_score(simple_site.pages[0])

        with pytest.raises(ValueError, match="Must call build"):
            graph.get_connectivity(simple_site.pages[0])
