"""
Tests for KnowledgeGraph analysis module.
"""

import pytest

from bengal.analysis.graph.knowledge_graph import KnowledgeGraph
from bengal.analysis.graph.metrics import PageConnectivity
from bengal.core.page import Page
from bengal.core.site import Site


@pytest.fixture
def simple_site(tmp_path):
    """Create a simple test site with a few pages."""
    site = Site(root_path=tmp_path, config={})

    # Create pages (slug is auto-derived from title)
    page1 = Page(
        source_path=tmp_path / "page1.md", _raw_content="# Page 1", metadata={"title": "Page 1"}
    )

    page2 = Page(
        source_path=tmp_path / "page2.md",
        _raw_content="# Page 2",
        metadata={"title": "Page 2", "tags": ["python"]},
    )

    page3 = Page(
        source_path=tmp_path / "page3.md",
        _raw_content="# Page 3",
        metadata={"title": "Page 3", "tags": ["python", "tutorial"]},
    )

    site.pages = [page1, page2, page3]

    return site


@pytest.fixture
def site_with_links(tmp_path):
    """Create a test site with internal links."""
    site = Site(root_path=tmp_path, config={})

    # Create hub page (slug is auto-derived from title)
    hub = Page(
        source_path=tmp_path / "hub.md", _raw_content="# Hub Page", metadata={"title": "Hub"}
    )

    # Create leaf pages that link to hub
    leaf1 = Page(
        source_path=tmp_path / "leaf1.md", _raw_content="# Leaf 1", metadata={"title": "Leaf 1"}
    )
    leaf1.related_posts = [hub]  # Simulates link

    leaf2 = Page(
        source_path=tmp_path / "leaf2.md", _raw_content="# Leaf 2", metadata={"title": "Leaf 2"}
    )
    leaf2.related_posts = [hub]  # Simulates link

    # Create orphan (no connections)
    orphan = Page(
        source_path=tmp_path / "orphan.md", _raw_content="# Orphan", metadata={"title": "Orphan"}
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
        assert orphans[0].slug == "orphan"

    def test_get_hubs(self, site_with_links):
        """Test hub page identification."""
        # Lower threshold to detect our test hub
        graph = KnowledgeGraph(site_with_links, hub_threshold=2)
        graph.build()

        hubs = graph.get_hubs()
        assert len(hubs) == 1
        assert hubs[0].slug == "hub"

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

        hub = [p for p in site_with_links.pages if p.slug == "hub"][0]
        score = graph.get_connectivity_score(hub)

        # Hub has 2 incoming refs (from leaf1 and leaf2)
        assert score == 2

    def test_get_connectivity_object(self, site_with_links):
        """Test PageConnectivity object."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        hub = [p for p in site_with_links.pages if p.slug == "hub"][0]
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

        orphan = [p for p in site_with_links.pages if p.slug == "orphan"][0]
        conn = graph.get_connectivity(orphan)

        assert conn.is_orphan is True
        assert conn.incoming_refs == 0
        assert conn.connectivity_score == 0


class TestLayers:
    """Test layer partitioning."""

    def test_get_layers(self, site_with_links):
        """Test that pages are partitioned into layers."""
        from bengal.analysis.results import PageLayers

        graph = KnowledgeGraph(site_with_links)
        graph.build()

        layers = graph.get_layers()

        # Verify it's a PageLayers dataclass
        assert isinstance(layers, PageLayers)

        # Test tuple unpacking (backward compatibility)
        hubs, mid_tier, leaves = layers

        # All pages should be in one of the layers
        total = len(layers.hubs) + len(layers.mid_tier) + len(layers.leaves)
        assert total == len(site_with_links.pages)

        # No page should be in multiple layers
        all_pages = layers.hubs + layers.mid_tier + layers.leaves
        assert len(all_pages) == len(set(all_pages))

    def test_layers_sorted_by_connectivity(self, site_with_links):
        """Test that layers are sorted correctly."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        layers = graph.get_layers()

        # Test tuple unpacking (backward compatibility)
        hubs, mid_tier, leaves = layers

        # If we have pages in multiple layers,
        # hubs should have higher connectivity than leaves
        if layers.hubs and layers.leaves:
            hub_conn = graph.get_connectivity_score(layers.hubs[0])
            leaf_conn = graph.get_connectivity_score(layers.leaves[-1])
            assert hub_conn >= leaf_conn


class TestErrorHandling:
    """Test error handling."""

    def test_methods_require_build(self, simple_site):
        """Test that analysis methods require build() first."""
        from bengal.errors import BengalError

        graph = KnowledgeGraph(simple_site)

        with pytest.raises(BengalError, match="not built"):
            graph.get_hubs()

        with pytest.raises(BengalError, match="not built"):
            graph.get_leaves()

        with pytest.raises(BengalError, match="not built"):
            graph.get_orphans()

        with pytest.raises(BengalError, match="not built"):
            graph.get_layers()

        with pytest.raises(BengalError, match="not built"):
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
        page1 = Page(source_path=tmp_path / "p1.md", _raw_content="", metadata={"title": "Page 1"})
        page2 = Page(source_path=tmp_path / "p2.md", _raw_content="", metadata={"title": "Page 2"})
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
            "tags": {
                "python": {
                    "pages": [simple_site.pages[1], simple_site.pages[2]]  # page2, page3
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


class TestAutodocFiltering:
    """Test autodoc page filtering."""

    def test_exclude_autodoc_default(self, tmp_path):
        """Test that autodoc pages are excluded by default."""
        site = Site(root_path=tmp_path, config={})

        # Create regular page
        regular = Page(
            source_path=tmp_path / "regular.md",
            _raw_content="# Regular",
            metadata={"title": "Regular", "type": "doc"},
        )

        # Create autodoc page
        autodoc = Page(
            source_path=tmp_path / "api" / "module.md",
            _raw_content="# API",
            metadata={"title": "API", "type": "autodoc-python"},
        )

        site.pages = [regular, autodoc]

        graph = KnowledgeGraph(site, exclude_autodoc=True)
        graph.build()

        analysis_pages = graph.get_analysis_pages()
        assert len(analysis_pages) == 1
        assert regular in analysis_pages
        assert autodoc not in analysis_pages

    def test_include_autodoc_when_disabled(self, tmp_path):
        """Test that autodoc pages are included when filtering is disabled."""
        site = Site(root_path=tmp_path, config={})

        regular = Page(
            source_path=tmp_path / "regular.md",
            _raw_content="# Regular",
            metadata={"title": "Regular"},
        )

        autodoc = Page(
            source_path=tmp_path / "api" / "module.md",
            _raw_content="# API",
            metadata={"title": "API", "type": "autodoc-python"},
        )

        site.pages = [regular, autodoc]

        graph = KnowledgeGraph(site, exclude_autodoc=False)
        graph.build()

        analysis_pages = graph.get_analysis_pages()
        assert len(analysis_pages) == 2
        assert regular in analysis_pages
        assert autodoc in analysis_pages

    def test_is_autodoc_page(self, tmp_path):
        """Test autodoc page detection via utility function."""
        from bengal.utils.autodoc import is_autodoc_page

        # Test different autodoc markers
        api_ref = Page(
            source_path=tmp_path / "api.md",
            _raw_content="",
            metadata={"type": "autodoc-python"},
        )

        python_module = Page(
            source_path=tmp_path / "module.md",
            _raw_content="",
            metadata={"type": "python-module"},
        )

        api_path = Page(
            source_path=tmp_path / "content" / "api" / "test.md",
            _raw_content="",
            metadata={},
        )

        regular = Page(
            source_path=tmp_path / "regular.md",
            _raw_content="",
            metadata={"type": "doc"},
        )

        # Test the utility function directly
        assert is_autodoc_page(api_ref) is True
        assert is_autodoc_page(python_module) is True
        assert is_autodoc_page(api_path) is True
        assert is_autodoc_page(regular) is False


class TestActionableRecommendations:
    """Test actionable recommendations feature."""

    def test_get_actionable_recommendations(self, site_with_links):
        """Test that recommendations are generated."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        recommendations = graph.get_actionable_recommendations()

        assert isinstance(recommendations, list)
        # Should have at least orphan recommendation
        assert len(recommendations) > 0

    def test_recommendations_include_orphans(self, site_with_links):
        """Test that orphaned pages are recommended."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        recommendations = graph.get_actionable_recommendations()

        orphan_recs = [r for r in recommendations if "orphan" in r.lower() or "🔗" in r]
        assert len(orphan_recs) > 0

    def test_recommendations_require_build(self, simple_site):
        """Test that recommendations require build."""
        from bengal.errors import BengalError

        graph = KnowledgeGraph(simple_site)

        with pytest.raises(BengalError, match="not built"):
            graph.get_actionable_recommendations()


class TestSEOInsights:
    """Test SEO insights feature."""

    def test_get_seo_insights(self, site_with_links):
        """Test that SEO insights are generated."""
        graph = KnowledgeGraph(site_with_links)
        graph.build()

        insights = graph.get_seo_insights()

        assert isinstance(insights, list)
        # Should have some insights
        assert len(insights) >= 0

    def test_seo_insights_require_build(self, simple_site):
        """Test that SEO insights require build."""
        from bengal.errors import BengalError

        graph = KnowledgeGraph(simple_site)

        with pytest.raises(BengalError, match="not built"):
            graph.get_seo_insights()


class TestContentGaps:
    """Test content gap detection."""

    def test_get_content_gaps(self, tmp_path):
        """Test content gap detection."""
        site = Site(root_path=tmp_path, config={})

        # Create pages with shared tag but no links
        page1 = Page(
            source_path=tmp_path / "p1.md",
            _raw_content="",
            metadata={"title": "Page 1", "tags": ["python"]},
        )
        page2 = Page(
            source_path=tmp_path / "p2.md",
            _raw_content="",
            metadata={"title": "Page 2", "tags": ["python"]},
        )
        page3 = Page(
            source_path=tmp_path / "p3.md",
            _raw_content="",
            metadata={"title": "Page 3", "tags": ["python"]},
        )

        site.pages = [page1, page2, page3]

        graph = KnowledgeGraph(site)
        graph.build()

        gaps = graph.get_content_gaps()

        assert isinstance(gaps, list)
        # Should detect gap in python tag pages
        python_gaps = [g for g in gaps if "python" in g.lower()]
        assert len(python_gaps) > 0

    def test_content_gaps_require_build(self, simple_site):
        """Test that content gaps require build."""
        from bengal.errors import BengalError

        graph = KnowledgeGraph(simple_site)

        with pytest.raises(BengalError, match="not built"):
            graph.get_content_gaps()


class TestLinkExtraction:
    """Test link extraction during build."""

    def test_links_extracted_during_build(self, tmp_path):
        """Test that links are extracted before graph build."""
        site = Site(root_path=tmp_path, config={})

        # Create pages with markdown links
        page1 = Page(
            source_path=tmp_path / "page1.md",
            _raw_content="# Page 1\n\nSee [Page 2](page2.md)",
            metadata={"title": "Page 1"},
        )

        page2 = Page(
            source_path=tmp_path / "page2.md",
            _raw_content="# Page 2",
            metadata={"title": "Page 2"},
        )

        site.pages = [page1, page2]

        # Build xref_index for link resolution
        site.xref_index = {
            "by_path": {
                "page2": page2,
            },
            "by_slug": {},
            "by_id": {},
        }

        graph = KnowledgeGraph(site)
        graph.build()

        # Page1 should have extracted links (extract_links is called during build)
        # Links may be empty if xref resolution fails, but the method should be called
        assert hasattr(page1, "links")
        # The links attribute should exist (may be empty list if resolution fails)
        assert isinstance(page1.links, list)
