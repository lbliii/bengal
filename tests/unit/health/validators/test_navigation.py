"""
Unit tests for navigation health validator.

Tests the NavigationValidator which checks:
- next/prev link chains
- Breadcrumb validity
- Section navigation consistency
- Navigation coverage
- Weight-based navigation
- Output path completeness
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site
from bengal.health.report import CheckResult, CheckStatus
from bengal.health.validators.navigation import NavigationValidator


class TestNavigationValidator:
    """Tests for NavigationValidator."""

    @pytest.fixture
    def validator(self):
        """Create a NavigationValidator instance."""
        return NavigationValidator()

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site with pages and sections."""
        site = Mock(spec=Site)
        site.root_dir = tmp_path
        site.sections = []
        
        # Create some test pages
        pages = []
        for i in range(5):
            page = Mock(spec=Page)
            page.source_path = tmp_path / f"page{i}.md"
            page.source_path.touch()
            page.output_path = tmp_path / "public" / f"page{i}.html"
            page.output_path.parent.mkdir(parents=True, exist_ok=True)
            page.output_path.touch()
            page.url = f"/page{i}/"
            page.metadata = {"weight": i}
            page.parent = None
            page.ancestors = []
            page.next = None
            page.prev = None
            pages.append(page)
        
        # Set up next/prev chain
        for i in range(len(pages) - 1):
            pages[i].next = pages[i + 1]
            pages[i + 1].prev = pages[i]
        
        site.pages = pages
        return site

    def test_validator_properties(self, validator):
        """Test validator basic properties."""
        assert validator.name == "Navigation"
        assert validator.enabled_by_default is True
        assert "navigation" in validator.description.lower()

    def test_valid_next_prev_chains(self, validator, mock_site):
        """Test validation with valid next/prev chains."""
        results = validator.validate(mock_site)
        
        # Should have at least one success result for next/prev
        assert any(r.status == CheckStatus.SUCCESS for r in results)
        assert not any(r.status == CheckStatus.ERROR for r in results)

    def test_broken_next_link(self, validator, mock_site):
        """Test detection of broken next link."""
        # Make next point to a page not in site.pages
        broken_page = Mock(spec=Page)
        broken_page.source_path = Path("/tmp/broken.md")
        mock_site.pages[0].next = broken_page
        
        results = validator.validate(mock_site)
        
        # Should detect the broken link
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(errors) > 0
        assert any("next" in r.message.lower() for r in errors)

    def test_next_without_output(self, validator, mock_site):
        """Test detection of next link pointing to page without output."""
        # Make next.output_path not exist
        mock_site.pages[0].next.output_path = Path("/nonexistent/path.html")
        
        results = validator.validate(mock_site)
        
        # Should detect the missing output
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(errors) > 0

    def test_broken_prev_link(self, validator, mock_site):
        """Test detection of broken prev link."""
        # Make prev point to a page not in site.pages
        broken_page = Mock(spec=Page)
        broken_page.source_path = Path("/tmp/broken.md")
        mock_site.pages[2].prev = broken_page
        
        results = validator.validate(mock_site)
        
        # Should detect the broken link
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(errors) > 0
        assert any("prev" in r.message.lower() for r in errors)

    def test_valid_breadcrumbs(self, validator, mock_site):
        """Test validation with valid breadcrumbs."""
        # Set up valid ancestor chain
        section = Mock(spec=Section)
        section.source_path = Path("/tmp/section")
        section.url = "/section/"
        section.output_path = Path("/tmp/public/section/index.html")
        section.output_path.parent.mkdir(parents=True, exist_ok=True)
        section.output_path.touch()
        
        mock_site.pages[0].parent = section
        mock_site.pages[0].ancestors = [section]
        mock_site.sections = [section]
        
        results = validator.validate(mock_site)
        
        # Should have success result for breadcrumbs
        assert any(r.status == CheckStatus.SUCCESS and "breadcrumb" in r.message.lower() 
                  for r in results)

    def test_broken_ancestor(self, validator, mock_site):
        """Test detection of invalid ancestor in breadcrumbs."""
        # Create ancestor not in site.sections
        broken_section = Mock(spec=Section)
        broken_section.source_path = Path("/tmp/broken_section")
        broken_section.url = "/broken/"
        
        mock_site.pages[0].ancestors = [broken_section]
        
        results = validator.validate(mock_site)
        
        # Should detect the broken ancestor
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(errors) > 0

    def test_section_navigation_consistency(self, validator, mock_site):
        """Test section navigation consistency checks."""
        # Create a section with pages
        section = Mock(spec=Section)
        section.source_path = Path("/tmp/section")
        section.url = "/section/"
        section.output_path = Path("/tmp/public/section/index.html")
        section.output_path.parent.mkdir(parents=True, exist_ok=True)
        section.output_path.touch()
        section.children = mock_site.pages[:3]
        
        for page in section.children:
            page.parent = section
        
        mock_site.sections = [section]
        
        results = validator.validate(mock_site)
        
        # Should validate section navigation
        assert any("section" in r.message.lower() for r in results)

    def test_navigation_coverage(self, validator, mock_site):
        """Test navigation coverage checking."""
        # Some pages with navigation, some without
        mock_site.pages[0].next = None
        mock_site.pages[0].prev = None
        
        results = validator.validate(mock_site)
        
        # Should report on coverage
        assert len(results) > 0

    def test_weight_based_navigation(self, validator, mock_site):
        """Test weight-based navigation ordering."""
        # Set up pages with weights
        for i, page in enumerate(mock_site.pages):
            page.metadata = {"weight": i * 10}
        
        results = validator.validate(mock_site)
        
        # Should check weight-based navigation
        assert len(results) > 0

    def test_output_path_completeness(self, validator, mock_site):
        """Test that all pages have valid output paths."""
        # All pages should have output paths
        results = validator.validate(mock_site)
        
        # Should check output paths
        assert any("output" in r.message.lower() for r in results)

    def test_missing_output_paths(self, validator, mock_site):
        """Test detection of missing output paths."""
        # Make a page missing output_path
        mock_site.pages[0].output_path = None
        
        results = validator.validate(mock_site)
        
        # Should detect missing output
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(errors) > 0

    def test_generated_pages_skipped(self, validator, mock_site):
        """Test that generated pages are skipped in navigation checks."""
        # Mark a page as generated
        mock_site.pages[0].metadata = {"_generated": True}
        
        results = validator.validate(mock_site)
        
        # Should still complete validation
        assert len(results) > 0

    def test_empty_site(self, validator):
        """Test validation of site with no pages."""
        site = Mock(spec=Site)
        site.pages = []
        site.sections = []
        
        results = validator.validate(site)
        
        # Should complete without errors
        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
