"""
Tests for KnowledgeGraph analysis module.
"""

import pytest

from bengal.analysis.knowledge_graph import KnowledgeGraph, PageConnectivity
from bengal.core.page import Page
from bengal.core.site import Site


@pytest.fixture
def simple_site(tmp_path):
    """Create a simple test site with a few pages."""
    site = Site(root_path=tmp_path, config={})

    # Create pages (slug is auto-derived from title)
    page1 = Page(
        source_path=tmp_path / "page1.md",
        content="# Page 1",
        metadata={'title': 'Page 1'}
    )

    page2 = Page(
        source_path=tmp_path / "page2.md",
        content="# Page 2",
        metadata={'title': 'Page 2', 'tags': ['python']}
    )

    page3 = Page(
        source_path=tmp_path / "page3.md",
        content="# Page 3",
        metadata={'title': 'Page 3', 'tags': ['python', 'tutorial']}
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
        metadata={'title': 'Hub'}
    )

    # Create leaf pages that link to hub
    leaf1 = Page(
        source_path=tmp_path / "leaf1.md",
        content="# Leaf 1",
        metadata={'title': 'Leaf 1'}
    )
    leaf1.related_posts = [hub]  # Simulates link

    leaf2 = Page(
        source_path=tmp_path / "leaf2.md",
        content="# Leaf 2",
        metadata={'title': 'Leaf 2'}
    )
    leaf2.related_posts = [hub]  # Simulates link

    # Create orphan (no connections)
    orphan = Page(
        source_path=tmp_path / "orphan.md",
        content="# Orphan",
        metadata={'title': 'Orphan'}
    )

    site.pages = [hub, leaf1, leaf2, orphan]

    return site


class TestKnowledgeGraphBasics:
    """Test basic Knowledge Graph functionality."""

    def test_graph_initialization(self, simple_site):
        """Test that graph can be initialized."""
        graph = KnowledgeGraph(simple_site)
        assert graph.site == simple_site
        assert graph.hub_threshold == 10
        assert graph.leaf_threshold == 2
        assert graph._built is False

    def test_graph_build(self, simple_site):
        """Test that graph can be built."""
        graph = KnowledgeGraph(simple_site)
        graph.build()

        assert graph._built is True
        assert graph.metrics is not None
        assert graph.metrics.total_pages == 3

    def test_graph_build_idempotent(self, simple_site):
        """Test that calling build() multiple times is safe."""
        graph = KnowledgeGraph(simple_site)
        graph.build()
        first_metrics = graph.metrics

        graph.build()  # Build again

        assert graph.metrics == first_metrics  # Should be same


class TestGraphMetrics:
    """Test graph metrics computation."""

    def test_simple_metrics(self, simple_site):
        """Test metrics for simple site with no links."""
        graph = KnowledgeGraph(simple_site)
        graph.build()

        m = graph.metrics
        assert m.total_pages == 3
        assert m.total_links == 0  # No explicit links
        assert m.hub_count == 0
        assert m.orphan_count == 3  # All orphans (no incoming refs)

    def test_metrics_with_links(self, site_with_links):
        """Test metrics for site with internal links."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        m = graph.metrics
        assert m.total_pages == 4
        assert m.total_links == 2  # leaf1->hub, leaf2->hub
        assert m.orphan_count == 1  # Only the orphan page


class TestHubsAndLeaves:
    """Test hub and leaf identification."""

    def test_get_orphans(self, site_with_links):
        """Test orphan page detection."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        orphans = graph.get_orphans()
        assert len(orphans) == 1
        assert orphans[0].slug == 'orphan'

    def test_get_hubs(self, site_with_links):
        """Test hub page identification."""
        # Lower threshold to detect our test hub
        graph = KnowledgeGraph(site_with_links, hub_threshold=2)
        graph.build()

        hubs = graph.get_hubs()
        assert len(hubs) == 1
        assert hubs[0].slug == 'hub'

    def test_get_leaves(self, site_with_links):
        """Test leaf page identification."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        leaves = graph.get_leaves()
        # Orphan and leaves should all be low connectivity
        assert len(leaves) >= 1


class TestConnectivity:
    """Test connectivity analysis."""

    def test_get_connectivity_score(self, site_with_links):
        """Test connectivity score calculation."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        hub = [p for p in site_with_links.pages if p.slug == 'hub'][0]
        score = graph.get_connectivity_score(hub)

        # Hub has 2 incoming refs (from leaf1 and leaf2)
        assert score == 2

    def test_get_connectivity_object(self, site_with_links):
        """Test PageConnectivity object."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        hub = [p for p in site_with_links.pages if p.slug == 'hub'][0]
        conn = graph.get_connectivity(hub)

        assert isinstance(conn, PageConnectivity)
        assert conn.page == hub
        assert conn.incoming_refs == 2
        assert conn.outgoing_refs == 0
        assert conn.connectivity_score == 2

    def test_orphan_connectivity(self, site_with_links):
        """Test that orphans have zero connectivity."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        orphan = [p for p in site_with_links.pages if p.slug == 'orphan'][0]
        conn = graph.get_connectivity(orphan)

        assert conn.is_orphan is True
        assert conn.incoming_refs == 0
        assert conn.connectivity_score == 0


class TestLayers:
    """Test layer partitioning."""

    def test_get_layers(self, site_with_links):
        """Test that pages are partitioned into layers."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        hubs, mid_tier, leaves = graph.get_layers()

        # All pages should be in one of the layers
        total = len(hubs) + len(mid_tier) + len(leaves)
        assert total == len(site_with_links.pages)

        # No page should be in multiple layers
        all_pages = hubs + mid_tier + leaves
        assert len(all_pages) == len(set(all_pages))

    def test_layers_sorted_by_connectivity(self, site_with_links):
        """Test that layers are sorted correctly."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        hubs, mid_tier, leaves = graph.get_layers()

        # If we have pages in multiple layers,
        # hubs should have higher connectivity than leaves
        if hubs and leaves:
            hub_conn = graph.get_connectivity_score(hubs[0])
            leaf_conn = graph.get_connectivity_score(leaves[-1])
            assert hub_conn >= leaf_conn


class TestErrorHandling:
    """Test error handling."""

    def test_methods_require_build(self, simple_site):
        """Test that analysis methods require build() first."""
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
            graph.get_metrics()

    def test_empty_site(self, tmp_path):
        """Test graph with no pages."""
        site = Site(root_path=tmp_path, config={})
        site.pages = []

        graph = KnowledgeGraph(site)
        graph.build()

        assert graph.metrics.total_pages == 0
        assert graph.metrics.total_links == 0
        assert graph.get_hubs() == []
        assert graph.get_leaves() == []
        assert graph.get_orphans() == []


class TestFormatStats:
    """Test statistics formatting."""

    def test_format_stats(self, site_with_links):
        """Test that format_stats produces readable output."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        output = graph.format_stats()

        assert "Knowledge Graph Statistics" in output
        assert "Total pages" in output
        assert "Total links" in output
        assert "Connectivity Distribution" in output
        assert "Orphaned Pages" in output

    def test_format_stats_no_orphans(self, tmp_path):
        """Test stats output when there are no orphans."""
        site = Site(root_path=tmp_path, config={})

        # Create pages that all reference each other
        page1 = Page(source_path=tmp_path / "p1.md", content="", metadata={'title': 'Page 1'})
        page2 = Page(source_path=tmp_path / "p2.md", content="", metadata={'title': 'Page 2'})
        page1.related_posts = [page2]
        page2.related_posts = [page1]

        site.pages = [page1, page2]

        graph = KnowledgeGraph(site)
        graph.build()

        output = graph.format_stats()
        assert "Orphaned Pages: None" in output


class TestTaxonomyAnalysis:
    """Test analysis of taxonomies."""

    def test_taxonomy_adds_connectivity(self, simple_site):
        """Test that pages with tags get connectivity boost."""
        # Add taxonomies to site
        simple_site.taxonomies = {
            'tags': {
                'python': {
                    'pages': [simple_site.pages[1], simple_site.pages[2]]  # page2, page3
                }
            }
        }

        graph = KnowledgeGraph(simple_site)
        graph.build()

        # Pages with tags should have some connectivity
        page2_score = graph.get_connectivity_score(simple_site.pages[1])
        page3_score = graph.get_connectivity_score(simple_site.pages[2])

        assert page2_score > 0
        assert page3_score > 0

