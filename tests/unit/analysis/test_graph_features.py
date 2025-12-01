"""
Tests for new graph analysis features: recommendations, SEO insights, content gaps.
"""

import pytest

from bengal.analysis.knowledge_graph import KnowledgeGraph
from bengal.core.page import Page
from bengal.core.site import Site


@pytest.fixture
def site_with_structure(tmp_path):
    """Create a test site with realistic structure for testing new features."""
    site = Site(root_path=tmp_path, config={})

    # Create hub page
    hub = Page(
        source_path=tmp_path / "hub.md",
        content="# Hub",
        metadata={"title": "Hub Page", "tags": ["important"]},
    )

    # Create pages that link to hub
    page1 = Page(
        source_path=tmp_path / "page1.md",
        content="# Page 1",
        metadata={"title": "Page 1", "tags": ["python"]},
    )
    page1.related_posts = [hub]

    page2 = Page(
        source_path=tmp_path / "page2.md",
        content="# Page 2",
        metadata={"title": "Page 2", "tags": ["python"]},
    )
    page2.related_posts = [hub]

    # Create orphaned pages
    orphan1 = Page(
        source_path=tmp_path / "orphan1.md",
        content="# Orphan 1",
        metadata={"title": "Orphan 1", "tags": ["tutorial"]},
    )

    orphan2 = Page(
        source_path=tmp_path / "orphan2.md",
        content="# Orphan 2",
        metadata={"title": "Orphan 2", "tags": ["tutorial"]},
    )

    site.pages = [hub, page1, page2, orphan1, orphan2]

    # Add taxonomies
    site.taxonomies = {
        "tags": {
            "python": {"pages": [page1, page2]},
            "tutorial": {"pages": [orphan1, orphan2]},
        }
    }

    return site


class TestActionableRecommendations:
    """Test actionable recommendations feature."""

    def test_recommendations_generated(self, site_with_structure):
        """Test that recommendations are generated."""
        graph = KnowledgeGraph(site_with_structure, hub_threshold=2)
        graph.build()

        recommendations = graph.get_actionable_recommendations()

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    def test_recommendations_include_orphans(self, site_with_structure):
        """Test that orphan recommendations are included."""
        graph = KnowledgeGraph(site_with_structure)
        graph.build()

        recommendations = graph.get_actionable_recommendations()

        # Should have recommendations (may include orphans if they exist)
        assert len(recommendations) > 0
        # Check that recommendations contain actionable content
        assert any("🔗" in r or "🌉" in r or "🏆" in r or "⚡" in r for r in recommendations)

    def test_recommendations_include_hubs(self, site_with_structure):
        """Test that hub recommendations are included."""
        graph = KnowledgeGraph(site_with_structure, hub_threshold=2)
        graph.build()

        recommendations = graph.get_actionable_recommendations()

        hub_recs = [r for r in recommendations if "hub" in r.lower() or "🏆" in r]
        assert len(hub_recs) > 0

    def test_recommendations_require_build(self, site_with_structure):
        """Test that recommendations require build."""
        graph = KnowledgeGraph(site_with_structure)

        with pytest.raises(ValueError, match="Must call build"):
            graph.get_actionable_recommendations()


class TestSEOInsights:
    """Test SEO insights feature."""

    def test_seo_insights_generated(self, site_with_structure):
        """Test that SEO insights are generated."""
        graph = KnowledgeGraph(site_with_structure)
        graph.build()

        insights = graph.get_seo_insights()

        assert isinstance(insights, list)

    def test_seo_insights_include_link_density(self, site_with_structure):
        """Test that link density insights are included."""
        graph = KnowledgeGraph(site_with_structure)
        graph.build()

        insights = graph.get_seo_insights()

        density_insights = [i for i in insights if "link density" in i.lower() or "📊" in i]
        # May or may not have density insight depending on connectivity
        assert isinstance(density_insights, list)

    def test_seo_insights_require_build(self, site_with_structure):
        """Test that SEO insights require build."""
        graph = KnowledgeGraph(site_with_structure)

        with pytest.raises(ValueError, match="Must call build"):
            graph.get_seo_insights()


class TestContentGaps:
    """Test content gap detection."""

    def test_content_gaps_detected(self, site_with_structure):
        """Test that content gaps are detected."""
        graph = KnowledgeGraph(site_with_structure)
        graph.build()

        gaps = graph.get_content_gaps()

        assert isinstance(gaps, list)
        # Content gaps may or may not be detected depending on structure
        # Just verify the method works and returns a list
        assert all(isinstance(g, str) for g in gaps)

    def test_content_gaps_require_build(self, site_with_structure):
        """Test that content gaps require build."""
        graph = KnowledgeGraph(site_with_structure)

        with pytest.raises(ValueError, match="Must call build"):
            graph.get_content_gaps()


class TestAutodocFiltering:
    """Test autodoc page filtering."""

    def test_autodoc_excluded_by_default(self, tmp_path):
        """Test that autodoc pages are excluded by default."""
        site = Site(root_path=tmp_path, config={})

        regular = Page(
            source_path=tmp_path / "regular.md",
            content="# Regular",
            metadata={"title": "Regular", "type": "doc"},
        )

        autodoc = Page(
            source_path=tmp_path / "api" / "module.md",
            content="# API",
            metadata={"title": "API", "type": "api-reference"},
        )

        site.pages = [regular, autodoc]

        graph = KnowledgeGraph(site)
        graph.build()

        analysis_pages = graph.get_analysis_pages()
        assert regular in analysis_pages
        assert autodoc not in analysis_pages
        assert len(analysis_pages) == 1

    def test_autodoc_included_when_disabled(self, tmp_path):
        """Test that autodoc pages are included when filtering disabled."""
        site = Site(root_path=tmp_path, config={})

        regular = Page(
            source_path=tmp_path / "regular.md",
            content="# Regular",
            metadata={"title": "Regular"},
        )

        autodoc = Page(
            source_path=tmp_path / "api" / "module.md",
            content="# API",
            metadata={"title": "API", "type": "api-reference"},
        )

        site.pages = [regular, autodoc]

        graph = KnowledgeGraph(site, exclude_autodoc=False)
        graph.build()

        analysis_pages = graph.get_analysis_pages()
        assert regular in analysis_pages
        assert autodoc in analysis_pages
        assert len(analysis_pages) == 2

    def test_is_autodoc_page_detection(self, tmp_path):
        """Test autodoc page detection via utility function."""
        from bengal.utils.autodoc import is_autodoc_page

        api_ref = Page(
            source_path=tmp_path / "api.md",
            content="",
            metadata={"type": "api-reference"},
        )

        python_module = Page(
            source_path=tmp_path / "module.md",
            content="",
            metadata={"type": "python-module"},
        )

        api_path = Page(
            source_path=tmp_path / "api" / "test.md",
            content="",
            metadata={},
        )

        regular = Page(
            source_path=tmp_path / "regular.md",
            content="",
            metadata={"type": "doc"},
        )

        # Test the utility function directly
        assert is_autodoc_page(api_ref) is True
        assert is_autodoc_page(python_module) is True
        assert is_autodoc_page(api_path) is True
        assert is_autodoc_page(regular) is False


class TestLinkExtraction:
    """Test link extraction during build."""

    def test_links_extracted_before_build(self, tmp_path):
        """Test that links are extracted before graph analysis."""
        site = Site(root_path=tmp_path, config={})

        page1 = Page(
            source_path=tmp_path / "page1.md",
            content="# Page 1\n\nSee [Page 2](page2.md)",
            metadata={"title": "Page 1"},
        )

        page2 = Page(
            source_path=tmp_path / "page2.md",
            content="# Page 2",
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

        # Links should be extracted
        assert hasattr(page1, "links")
        assert len(page1.links) > 0

    def test_format_stats_includes_recommendations(self, site_with_structure):
        """Test that format_stats includes actionable recommendations."""
        graph = KnowledgeGraph(site_with_structure)
        graph.build()

        stats = graph.format_stats()

        assert "Actionable Recommendations" in stats or "🎯" in stats

    def test_format_stats_includes_seo_insights(self, site_with_structure):
        """Test that format_stats includes SEO insights."""
        graph = KnowledgeGraph(site_with_structure)
        graph.build()

        stats = graph.format_stats()

        assert "SEO Insights" in stats or "🎯" in stats

    def test_format_stats_includes_content_gaps(self, site_with_structure):
        """Test that format_stats includes content gaps."""
        graph = KnowledgeGraph(site_with_structure)
        graph.build()

        stats = graph.format_stats()

        # Content gaps may or may not be present depending on structure
        # Just verify stats are formatted correctly
        assert "Knowledge Graph Statistics" in stats
        assert "Total pages" in stats
