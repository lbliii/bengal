"""
Tests for weight-based next/previous navigation within sections.

Regression tests for the navigation fix ensuring:
- next_in_section and prev_in_section respect weight order
- Index pages are skipped in navigation
- Navigation stays within section boundaries
- Pages without weight appear last
- Equal weights are sorted alphabetically
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from bengal.core.page import Page
from bengal.core.site import Site
from bengal.orchestration.content import ContentOrchestrator


class TestWeightBasedNavigation:
    """Test that next/prev navigation respects weight metadata."""

    @pytest.fixture
    def weighted_section_site(self):
        """Create site with weighted pages in a section."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "content" / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            # Section index
            (docs_dir / "_index.md").write_text("---\ntitle: Docs\ntype: doc\n---")

            # Pages with explicit weights (out of order)
            (docs_dir / "zebra.md").write_text("---\ntitle: Zebra\nweight: 30\n---\n# Zebra")
            (docs_dir / "alpha.md").write_text("---\ntitle: Alpha\nweight: 10\n---\n# Alpha")
            (docs_dir / "beta.md").write_text("---\ntitle: Beta\nweight: 20\n---\n# Beta")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_next_in_section_follows_weight_order(self, weighted_section_site):
        """Next navigation should follow weight order, not filename order."""
        # Find pages (filesystem order would be: alpha, beta, zebra)
        # Weight order should be: alpha(10), beta(20), zebra(30)

        alpha = [p for p in weighted_section_site.pages if "alpha" in str(p.source_path)][0]
        beta = [p for p in weighted_section_site.pages if "beta" in str(p.source_path)][0]
        zebra = [p for p in weighted_section_site.pages if "zebra" in str(p.source_path)][0]

        # Verify weight-based order
        assert alpha.next_in_section == beta, "Alpha (weight 10) should go to Beta (weight 20)"
        assert beta.next_in_section == zebra, "Beta (weight 20) should go to Zebra (weight 30)"
        assert zebra.next_in_section is None, "Zebra (weight 30) is last"

    def test_prev_in_section_follows_weight_order(self, weighted_section_site):
        """Previous navigation should follow weight order."""
        alpha = [p for p in weighted_section_site.pages if "alpha" in str(p.source_path)][0]
        beta = [p for p in weighted_section_site.pages if "beta" in str(p.source_path)][0]
        zebra = [p for p in weighted_section_site.pages if "zebra" in str(p.source_path)][0]

        # Verify reverse weight-based order
        assert zebra.prev_in_section == beta, "Zebra (30) prev should be Beta (20)"
        assert beta.prev_in_section == alpha, "Beta (20) prev should be Alpha (10)"
        assert alpha.prev_in_section is None, "Alpha (10) is first"


class TestIndexPageSkipping:
    """Test that index pages are skipped in navigation."""

    @pytest.fixture
    def section_with_index(self):
        """Create section with index page and regular pages."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "content" / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            # Section index (should be skipped)
            (docs_dir / "_index.md").write_text("---\ntitle: Docs Index\nweight: 1\n---")

            # Regular pages
            (docs_dir / "page-1.md").write_text("---\ntitle: Page 1\nweight: 10\n---")
            (docs_dir / "page-2.md").write_text("---\ntitle: Page 2\nweight: 20\n---")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_first_page_skips_index_in_prev(self, section_with_index):
        """First regular page should have no previous (index is skipped)."""
        page_1 = [p for p in section_with_index.pages if "page-1" in str(p.source_path)][0]

        # Page 1 is first regular page, prev should be None (skips _index.md)
        assert page_1.prev_in_section is None, "First page should skip index in prev"

    def test_navigation_skips_over_index(self, section_with_index):
        """Navigation should skip index pages entirely."""
        page_1 = [p for p in section_with_index.pages if "page-1" in str(p.source_path)][0]
        page_2 = [p for p in section_with_index.pages if "page-2" in str(p.source_path)][0]

        # Direct navigation between regular pages
        assert page_1.next_in_section == page_2
        assert page_2.prev_in_section == page_1


class TestMixedWeightScenarios:
    """Test pages with and without weight metadata."""

    @pytest.fixture
    def mixed_weight_site(self):
        """Create site with some weighted, some unweighted pages."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "content" / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            (docs_dir / "_index.md").write_text("---\ntitle: Docs\n---")

            # Weighted pages
            (docs_dir / "intro.md").write_text("---\ntitle: Introduction\nweight: 10\n---")
            (docs_dir / "basics.md").write_text("---\ntitle: Basics\nweight: 20\n---")

            # Unweighted pages (should appear last)
            (docs_dir / "zebra.md").write_text("---\ntitle: Zebra\n---")
            (docs_dir / "alpha.md").write_text("---\ntitle: Alpha\n---")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_unweighted_pages_appear_after_weighted(self, mixed_weight_site):
        """Pages without weight should appear after all weighted pages."""
        intro = [p for p in mixed_weight_site.pages if "intro" in str(p.source_path)][0]
        basics = [p for p in mixed_weight_site.pages if "basics" in str(p.source_path)][0]

        # Weighted pages navigate to each other
        assert intro.next_in_section == basics

        # Last weighted page should go to first unweighted (alphabetically)
        next_page = basics.next_in_section
        assert next_page is not None, "Should have next page (unweighted)"
        # Unweighted pages are sorted alphabetically: Alpha, Zebra
        assert "alpha" in str(next_page.source_path).lower()

    def test_unweighted_pages_sorted_alphabetically(self, mixed_weight_site):
        """Unweighted pages should be sorted alphabetically by title."""
        alpha = [p for p in mixed_weight_site.pages if p.source_path.stem == "alpha"][0]
        zebra = [p for p in mixed_weight_site.pages if p.source_path.stem == "zebra"][0]

        # Alpha comes before Zebra alphabetically
        assert alpha.next_in_section == zebra


class TestEqualWeights:
    """Test navigation when multiple pages have the same weight."""

    @pytest.fixture
    def equal_weight_site(self):
        """Create site with pages having equal weights."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "content" / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            (docs_dir / "_index.md").write_text("---\ntitle: Docs\n---")

            # All same weight, different titles
            (docs_dir / "zebra.md").write_text("---\ntitle: Zebra\nweight: 10\n---")
            (docs_dir / "alpha.md").write_text("---\ntitle: Alpha\nweight: 10\n---")
            (docs_dir / "charlie.md").write_text("---\ntitle: Charlie\nweight: 10\n---")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_equal_weights_sorted_alphabetically(self, equal_weight_site):
        """Pages with equal weight should be sorted alphabetically by title."""
        alpha = [p for p in equal_weight_site.pages if "alpha" in str(p.source_path)][0]
        charlie = [p for p in equal_weight_site.pages if "charlie" in str(p.source_path)][0]
        zebra = [p for p in equal_weight_site.pages if "zebra" in str(p.source_path)][0]

        # Alphabetical order: Alpha → Charlie → Zebra
        assert alpha.next_in_section == charlie, "Alpha should go to Charlie"
        assert charlie.next_in_section == zebra, "Charlie should go to Zebra"
        assert zebra.prev_in_section == charlie, "Zebra back to Charlie"
        assert charlie.prev_in_section == alpha, "Charlie back to Alpha"


class TestSectionBoundaries:
    """Test that navigation stays within section boundaries."""

    @pytest.fixture
    def multi_section_site(self):
        """Create site with multiple sections."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content = root / "content"

            # Docs section
            docs = content / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            (docs / "_index.md").write_text("---\ntitle: Docs\ntype: doc\n---")
            (docs / "doc-1.md").write_text("---\ntitle: Doc 1\nweight: 10\n---")
            (docs / "doc-2.md").write_text("---\ntitle: Doc 2\nweight: 20\n---")

            # Guides section
            guides = content / "guides"
            guides.mkdir(parents=True, exist_ok=True)
            (guides / "_index.md").write_text("---\ntitle: Guides\ntype: doc\n---")
            (guides / "guide-1.md").write_text("---\ntitle: Guide 1\nweight: 10\n---")
            (guides / "guide-2.md").write_text("---\ntitle: Guide 2\nweight: 20\n---")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_last_page_in_section_has_no_next(self, multi_section_site):
        """Last page in a section should not navigate to next section."""
        doc_2 = [p for p in multi_section_site.pages if "doc-2" in str(p.source_path)][0]

        # Last doc should not go to first guide
        assert doc_2.next_in_section is None, "Should not cross section boundary"

    def test_first_page_in_section_has_no_prev(self, multi_section_site):
        """First page in a section should not navigate to previous section."""
        guide_1 = [p for p in multi_section_site.pages if "guide-1" in str(p.source_path)][0]

        # First guide should not go to last doc
        assert guide_1.prev_in_section is None, "Should not cross section boundary"

    def test_navigation_within_section_only(self, multi_section_site):
        """Navigation should only move between pages in the same section."""
        doc_1 = [p for p in multi_section_site.pages if "doc-1" in str(p.source_path)][0]
        doc_2 = [p for p in multi_section_site.pages if "doc-2" in str(p.source_path)][0]

        # Docs navigate to each other
        assert doc_1.next_in_section == doc_2
        assert doc_2.prev_in_section == doc_1

        guide_1 = [p for p in multi_section_site.pages if "guide-1" in str(p.source_path)][0]
        guide_2 = [p for p in multi_section_site.pages if "guide-2" in str(p.source_path)][0]

        # Guides navigate to each other
        assert guide_1.next_in_section == guide_2
        assert guide_2.prev_in_section == guide_1


class TestEdgeCases:
    """Test edge cases in navigation."""

    def test_single_page_section(self):
        """Section with single page should have no navigation."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "content" / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            (docs_dir / "_index.md").write_text("---\ntitle: Docs\n---")
            (docs_dir / "only-page.md").write_text("---\ntitle: Only Page\n---")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()

            only_page = [p for p in site.pages if "only-page" in str(p.source_path)][0]

            assert only_page.next_in_section is None
            assert only_page.prev_in_section is None

    def test_section_with_only_index(self):
        """Section with only index page should have no navigation."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "content" / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            (docs_dir / "_index.md").write_text("---\ntitle: Docs\n---")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()

            # Index pages are skipped, so they shouldn't navigate
            # (This is expected - index pages don't use next/prev navigation)

    def test_page_without_section(self):
        """Page not in a section should have no section navigation."""
        page = Page(source_path=Path("/content/standalone.md"), metadata={"title": "Standalone"})
        # No _section set

        assert page.next_in_section is None
        assert page.prev_in_section is None


class TestRegressionScenarios:
    """Test exact scenarios from the bug report."""

    @pytest.fixture
    def reference_section(self):
        """Create the exact reference section structure from bug report."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ref_dir = root / "content" / "reference"
            ref_dir.mkdir(parents=True, exist_ok=True)

            (ref_dir / "_index.md").write_text("---\ntitle: Reference\ntype: doc\nweight: 30\n---")

            # Pages (with dates that would affect global navigation)
            (ref_dir / "reference-page-1.md").write_text(
                "---\ntitle: Reference Page 1\ndate: 2025-10-13\nweight: 10\n---"
            )
            (ref_dir / "reference-page-2.md").write_text(
                "---\ntitle: Reference Page 2\ndate: 2025-10-12\nweight: 20\n---"
            )
            (ref_dir / "reference-page-3.md").write_text(
                "---\ntitle: Reference Page 3\ndate: 2025-10-11\nweight: 30\n---"
            )

            # Add other sections to test cross-section isolation
            guides_dir = root / "content" / "guides"
            guides_dir.mkdir(parents=True, exist_ok=True)
            (guides_dir / "_index.md").write_text("---\ntitle: Guides\ntype: doc\n---")
            (guides_dir / "quickstart.md").write_text(
                "---\ntitle: Quickstart\ndate: 2025-10-12\n---"
            )

            # Homepage
            (root / "content" / "index.md").write_text("---\ntitle: Welcome to Bengal\n---")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_reference_page_2_navigation(self, reference_section):
        """
        Regression test for the exact bug:
        Reference Page 2 should navigate to Page 1 and Page 3, not homepage or quickstart.
        """
        page_1 = [p for p in reference_section.pages if "reference-page-1" in str(p.source_path)][0]
        page_2 = [p for p in reference_section.pages if "reference-page-2" in str(p.source_path)][0]
        page_3 = [p for p in reference_section.pages if "reference-page-3" in str(p.source_path)][0]

        # THE FIX: Should navigate within section by weight
        assert page_2.prev_in_section == page_1, "Page 2 prev should be Page 1"
        assert page_2.next_in_section == page_3, "Page 2 next should be Page 3"

        # NOT homepage or quickstart (those are in different sections)
        assert page_2.prev_in_section.title != "Welcome to Bengal"
        assert page_2.next_in_section.title != "Quickstart"

    def test_weight_order_ignores_date(self, reference_section):
        """Weight order should be used, not date order."""
        page_1 = [p for p in reference_section.pages if "reference-page-1" in str(p.source_path)][0]
        page_2 = [p for p in reference_section.pages if "reference-page-2" in str(p.source_path)][0]
        page_3 = [p for p in reference_section.pages if "reference-page-3" in str(p.source_path)][0]

        # Dates are: Page 1 (Oct 13), Page 2 (Oct 12), Page 3 (Oct 11)
        # But weights are: 10, 20, 30
        # Navigation should follow weight, not date

        assert page_1.next_in_section == page_2
        assert page_2.next_in_section == page_3


class TestBackwardCompatibility:
    """Ensure global navigation (page.next/prev) still works."""

    def test_global_navigation_still_exists(self):
        """page.next and page.prev should still work for global navigation."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content_dir = root / "content"
            content_dir.mkdir(parents=True, exist_ok=True)

            (content_dir / "page-1.md").write_text("---\ntitle: Page 1\n---")
            (content_dir / "page-2.md").write_text("---\ntitle: Page 2\n---")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()

            # Global navigation should still work
            pages = [p for p in site.pages if "page-" in str(p.source_path)]
            assert len(pages) >= 2

            # At least some pages should have next/prev (global)
            has_next = any(p.next is not None for p in pages)
            has_prev = any(p.prev is not None for p in pages)

            # Global navigation exists (even if order is filesystem-based)
            assert has_next or has_prev, "Global navigation should still work"
