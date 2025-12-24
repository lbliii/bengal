"""
Tests for parallel GraphBuilder functionality.

Tests the free-threading expansion for knowledge graph building,
ensuring parallel mode produces identical results to sequential mode.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from bengal.analysis.graph_builder import MIN_PAGES_FOR_PARALLEL, GraphBuilder
from bengal.core.page import Page
from bengal.core.site import Site


@pytest.fixture
def small_site(tmp_path):
    """Create a small test site (below parallel threshold)."""
    site = Site(root_path=tmp_path, config={})

    pages = []
    for i in range(10):
        page = Page(
            source_path=tmp_path / f"page{i}.md",
            content=f"# Page {i}",
            metadata={"title": f"Page {i}"},
        )
        pages.append(page)

    # Add some related posts to create connections
    pages[0].related_posts = [pages[1], pages[2]]
    pages[1].related_posts = [pages[0]]
    pages[3].related_posts = [pages[4], pages[5], pages[6]]

    site.pages = pages
    return site


@pytest.fixture
def large_site(tmp_path):
    """Create a large test site (above parallel threshold)."""
    site = Site(root_path=tmp_path, config={})

    pages = []
    for i in range(150):  # Above MIN_PAGES_FOR_PARALLEL (100)
        page = Page(
            source_path=tmp_path / f"page{i}.md",
            content=f"# Page {i}",
            metadata={"title": f"Page {i}"},
        )
        pages.append(page)

    # Add various connections
    # Related posts
    for i in range(0, 100, 10):
        pages[i].related_posts = [pages[i + 1], pages[i + 2]]

    # Add some links
    for i in range(50):
        pages[i].links = [f"page{i + 50}.md"]

    site.pages = pages
    return site


class TestParallelModeDetection:
    """Test automatic parallel mode detection."""

    def test_small_site_uses_sequential(self, small_site):
        """Test that small sites use sequential mode by default."""
        builder = GraphBuilder(small_site)
        assert builder.parallel is False

    def test_large_site_uses_parallel(self, large_site):
        """Test that large sites use parallel mode by default."""
        builder = GraphBuilder(large_site)
        assert builder.parallel is True

    def test_explicit_parallel_true(self, small_site):
        """Test forcing parallel mode on small site."""
        builder = GraphBuilder(small_site, parallel=True)
        assert builder.parallel is True

    def test_explicit_parallel_false(self, large_site):
        """Test forcing sequential mode on large site."""
        builder = GraphBuilder(large_site, parallel=False)
        assert builder.parallel is False

    def test_env_var_disables_parallel(self, large_site):
        """Test BENGAL_NO_PARALLEL environment variable."""
        with patch.dict(os.environ, {"BENGAL_NO_PARALLEL": "1"}):
            builder = GraphBuilder(large_site)
            assert builder.parallel is False

    def test_env_var_overrides_explicit(self, large_site):
        """Test that env var overrides explicit parallel=True."""
        with patch.dict(os.environ, {"BENGAL_NO_PARALLEL": "true"}):
            builder = GraphBuilder(large_site, parallel=True)
            assert builder.parallel is False

    def test_config_disables_parallel(self, large_site):
        """Test parallel_graph config option."""
        large_site.config["parallel_graph"] = False
        builder = GraphBuilder(large_site)
        assert builder.parallel is False

    def test_threshold_constant(self):
        """Test that MIN_PAGES_FOR_PARALLEL is 100."""
        assert MIN_PAGES_FOR_PARALLEL == 100


class TestParallelMatchesSequential:
    """Test that parallel mode produces identical results to sequential."""

    def test_results_match_small_site(self, tmp_path):
        """Test that parallel and sequential produce same results on small site."""

        # Create fresh sites for each builder to avoid state sharing
        def make_site():
            site = Site(root_path=tmp_path, config={})
            pages = []
            for i in range(10):
                page = Page(
                    source_path=tmp_path / f"page{i}.md",
                    content=f"# Page {i}",
                    metadata={"title": f"Page {i}"},
                )
                pages.append(page)

            # Add some related posts to create connections
            pages[0].related_posts = [pages[1], pages[2]]
            pages[1].related_posts = [pages[0]]
            pages[3].related_posts = [pages[4], pages[5], pages[6]]

            site.pages = pages
            return site

        # Build with sequential
        site_seq = make_site()
        builder_seq = GraphBuilder(site_seq, parallel=False)
        builder_seq.build()

        # Build with parallel
        site_par = make_site()
        builder_par = GraphBuilder(site_par, parallel=True)
        builder_par.build()

        # Compare incoming ref counts (by page title since pages are different objects)
        seq_incoming = {p.title: v for p, v in builder_seq.incoming_refs.items()}
        par_incoming = {p.title: v for p, v in builder_par.incoming_refs.items()}
        assert seq_incoming == par_incoming

        # Compare link type counts
        assert len(builder_seq.link_types) == len(builder_par.link_types)


class TestParallelLinkTypes:
    """Test that link types are correctly assigned in parallel mode."""

    def test_related_posts_link_type(self, small_site):
        """Test RELATED link type for related posts."""
        from bengal.analysis.link_types import LinkType

        builder = GraphBuilder(small_site, parallel=True)
        builder.build()

        # Check that related posts create RELATED link types
        page0 = small_site.pages[0]
        page1 = small_site.pages[1]

        assert (page0, page1) in builder.link_types
        assert builder.link_types[(page0, page1)] == LinkType.RELATED


class TestParallelErrorHandling:
    """Test error handling in parallel mode."""

    def test_handles_missing_attributes(self, tmp_path):
        """Test that missing page attributes are handled gracefully."""
        site = Site(root_path=tmp_path, config={})

        # Create pages without links or related_posts
        pages = []
        for i in range(5):
            page = Page(
                source_path=tmp_path / f"page{i}.md",
                content=f"# Page {i}",
                metadata={"title": f"Page {i}"},
            )
            # Ensure attributes don't exist
            if hasattr(page, "links"):
                delattr(page, "links")
            if hasattr(page, "related_posts"):
                delattr(page, "related_posts")
            pages.append(page)

        site.pages = pages

        # Should not raise
        builder = GraphBuilder(site, parallel=True)
        builder.build()

        # Should have no links
        assert len(builder.link_types) == 0

    def test_handles_empty_site(self, tmp_path):
        """Test parallel mode with empty site."""
        site = Site(root_path=tmp_path, config={})
        site.pages = []

        builder = GraphBuilder(site, parallel=True)
        builder.build()

        assert len(builder.incoming_refs) == 0
        assert len(builder.outgoing_refs) == 0
        assert len(builder.link_types) == 0


class TestParallelMetrics:
    """Test that link metrics are built correctly after parallel analysis."""

    def test_link_metrics_built(self, small_site):
        """Test that link metrics are computed after parallel build."""
        builder = GraphBuilder(small_site, parallel=True)
        builder.build()

        # Should have link metrics for pages with connections
        assert len(builder.link_metrics) > 0

        # Check that metrics are valid LinkMetrics objects
        for _page, metrics in builder.link_metrics.items():
            assert hasattr(metrics, "explicit")
            assert hasattr(metrics, "related")
            assert hasattr(metrics, "total_links")


class TestParallelTaxonomyAndMenus:
    """Test that taxonomy and menu analysis still runs (sequentially)."""

    def test_taxonomy_analysis_runs(self, small_site):
        """Test that taxonomy analysis runs after parallel page analysis."""
        from bengal.analysis.link_types import LinkType

        # Add taxonomies
        small_site.taxonomies = {
            "tags": {
                "python": {
                    "pages": [small_site.pages[0], small_site.pages[1]],
                }
            }
        }

        builder = GraphBuilder(small_site, parallel=True)
        builder.build()

        # Check that taxonomy links are added
        taxonomy_links = [lt for lt in builder.link_types.values() if lt == LinkType.TAXONOMY]
        assert len(taxonomy_links) > 0

    def test_menu_analysis_runs(self, small_site):
        """Test that menu analysis runs after parallel page analysis."""
        from bengal.analysis.link_types import LinkType

        # Add menus
        class MockMenuItem:
            def __init__(self, page):
                self.page = page

        small_site.menu = {
            "main": [MockMenuItem(small_site.pages[0]), MockMenuItem(small_site.pages[1])],
        }

        builder = GraphBuilder(small_site, parallel=True)
        builder.build()

        # Check that menu links are added
        menu_links = [lt for lt in builder.link_types.values() if lt == LinkType.MENU]
        assert len(menu_links) > 0


class TestParallelWorkerConfig:
    """Test worker configuration for parallel mode."""

    def test_respects_max_workers_config(self, large_site):
        """Test that max_workers config is used."""
        large_site.config["max_workers"] = 2

        # Just verify it doesn't error - actual worker count is internal
        builder = GraphBuilder(large_site, parallel=True)
        builder.build()

        assert len(builder.link_metrics) > 0
