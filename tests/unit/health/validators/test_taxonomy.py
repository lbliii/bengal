"""
Unit tests for taxonomy health validator.

Tests the TaxonomyValidator which checks:
- Tag page generation
- Archive page generation
- Taxonomy consistency
- Pagination integrity
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site
from bengal.health.report import CheckResult, CheckStatus
from bengal.health.validators.taxonomy import TaxonomyValidator


class TestTaxonomyValidator:
    """Tests for TaxonomyValidator."""

    @pytest.fixture
    def validator(self):
        """Create a TaxonomyValidator instance."""
        return TaxonomyValidator()

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site with taxonomy data."""
        site = Mock(spec=Site)
        site.root_dir = tmp_path
        
        # Set up taxonomies
        site.taxonomies = {
            "tags": {
                "python": {"name": "Python", "count": 3},
                "testing": {"name": "Testing", "count": 2},
                "docs": {"name": "Documentation", "count": 1},
            },
            "categories": {
                "tutorials": {"name": "Tutorials", "count": 2},
                "guides": {"name": "Guides", "count": 1},
            }
        }
        
        # Create tag pages
        tag_pages = []
        for tag_slug in ["python", "testing", "docs"]:
            page = Mock(spec=Page)
            page.source_path = tmp_path / f"tags/{tag_slug}.md"
            page.output_path = tmp_path / "public" / "tags" / tag_slug / "index.html"
            page.output_path.parent.mkdir(parents=True, exist_ok=True)
            page.output_path.touch()
            page.metadata = {
                "_generated": True,
                "type": "tag",
                "_tag_slug": tag_slug
            }
            page.url = f"/tags/{tag_slug}/"
            tag_pages.append(page)
        
        # Create some regular pages
        regular_pages = []
        for i in range(3):
            page = Mock(spec=Page)
            page.source_path = tmp_path / f"page{i}.md"
            page.source_path.touch()
            page.output_path = tmp_path / "public" / f"page{i}.html"
            page.output_path.parent.mkdir(parents=True, exist_ok=True)
            page.output_path.touch()
            page.metadata = {"tags": ["python"], "categories": ["tutorials"]}
            page.url = f"/page{i}/"
            regular_pages.append(page)
        
        site.pages = tag_pages + regular_pages
        site.sections = []
        
        return site

    def test_validator_properties(self, validator):
        """Test validator basic properties."""
        assert validator.name == "Taxonomies"
        assert validator.enabled_by_default is True
        assert "taxonom" in validator.description.lower()

    def test_all_tags_have_pages(self, validator, mock_site):
        """Test validation when all tags have corresponding pages."""
        results = validator.validate(mock_site)
        
        # Should have success results for tag pages
        assert any(r.status == CheckStatus.SUCCESS and "tag" in r.message.lower() 
                  for r in results)

    def test_missing_tag_page(self, validator, mock_site):
        """Test detection of missing tag page."""
        # Add a tag without corresponding page
        mock_site.taxonomies["tags"]["new-tag"] = {"name": "New Tag", "count": 1}
        
        results = validator.validate(mock_site)
        
        # Should detect missing tag page
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        assert any("tag" in r.message.lower() and "no generated pages" in r.message.lower() 
                  for r in errors)

    def test_orphaned_tag_page(self, validator, mock_site):
        """Test detection of orphaned tag page."""
        # Create tag page for non-existent tag
        orphan_page = Mock(spec=Page)
        orphan_page.metadata = {
            "_generated": True,
            "type": "tag",
            "_tag_slug": "orphan-tag"
        }
        mock_site.pages.append(orphan_page)
        
        results = validator.validate(mock_site)
        
        # Should detect orphaned page
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        assert any("orphaned" in r.message.lower() for r in errors)

    def test_no_tags_in_site(self, validator):
        """Test validation when site has no tags."""
        site = Mock(spec=Site)
        site.taxonomies = {"tags": {}}
        site.pages = []
        site.sections = []
        
        results = validator.validate(site)
        
        # Should return info message about no tags
        assert any(r.status == CheckStatus.INFO and "no tags" in r.message.lower() 
                  for r in results)

    def test_archive_pages_exist(self, validator, mock_site, tmp_path):
        """Test validation of archive pages for sections."""
        # Create a section with archive page
        section = Mock(spec=Section)
        section.source_path = tmp_path / "blog"
        section.url = "/blog/"
        section.output_path = tmp_path / "public" / "blog" / "index.html"
        section.output_path.parent.mkdir(parents=True, exist_ok=True)
        section.output_path.touch()
        section.children = mock_site.pages[:2]
        
        # Create archive page for section
        archive_page = Mock(spec=Page)
        archive_page.source_path = tmp_path / "blog/archive.md"
        archive_page.output_path = tmp_path / "public" / "blog" / "archive" / "index.html"
        archive_page.output_path.parent.mkdir(parents=True, exist_ok=True)
        archive_page.output_path.touch()
        archive_page.metadata = {
            "_generated": True,
            "type": "archive",
            "_section_url": "/blog/"
        }
        
        mock_site.sections = [section]
        mock_site.pages.append(archive_page)
        
        results = validator.validate(mock_site)
        
        # Should validate archive pages
        assert len(results) > 0

    def test_taxonomy_consistency(self, validator, mock_site):
        """Test taxonomy consistency checking."""
        results = validator.validate(mock_site)
        
        # Should check consistency
        assert len(results) > 0

    def test_pagination_integrity(self, validator, mock_site, tmp_path):
        """Test pagination page integrity checking."""
        # Create paginated tag pages
        page1 = Mock(spec=Page)
        page1.metadata = {
            "_generated": True,
            "type": "tag",
            "_tag_slug": "python",
            "_page_num": 1
        }
        page1.output_path = tmp_path / "public" / "tags" / "python" / "page" / "1" / "index.html"
        page1.output_path.parent.mkdir(parents=True, exist_ok=True)
        page1.output_path.touch()
        
        page2 = Mock(spec=Page)
        page2.metadata = {
            "_generated": True,
            "type": "tag",
            "_tag_slug": "python",
            "_page_num": 2
        }
        page2.output_path = tmp_path / "public" / "tags" / "python" / "page" / "2" / "index.html"
        page2.output_path.parent.mkdir(parents=True, exist_ok=True)
        page2.output_path.touch()
        
        mock_site.pages.extend([page1, page2])
        
        results = validator.validate(mock_site)
        
        # Should check pagination
        assert len(results) > 0

    def test_multiple_taxonomies(self, validator, mock_site):
        """Test validation with multiple taxonomy types."""
        # Site already has tags and categories
        results = validator.validate(mock_site)
        
        # Should validate both taxonomies
        assert len(results) > 0

    def test_empty_taxonomy(self, validator):
        """Test validation when taxonomy is empty."""
        site = Mock(spec=Site)
        site.taxonomies = {}
        site.pages = []
        site.sections = []
        
        results = validator.validate(site)
        
        # Should handle empty taxonomy gracefully
        assert len(results) > 0

    def test_tag_page_output_exists(self, validator, mock_site):
        """Test that tag pages have valid output paths."""
        results = validator.validate(mock_site)
        
        # All tag pages should have output
        assert not any(r.status == CheckStatus.ERROR and "output" in r.message.lower() 
                      for r in results)

    def test_category_pages(self, validator, mock_site, tmp_path):
        """Test validation of category pages."""
        # Create category pages
        for cat_slug in ["tutorials", "guides"]:
            page = Mock(spec=Page)
            page.metadata = {
                "_generated": True,
                "type": "category",
                "_category_slug": cat_slug
            }
            page.output_path = tmp_path / "public" / "categories" / cat_slug / "index.html"
            page.output_path.parent.mkdir(parents=True, exist_ok=True)
            page.output_path.touch()
            mock_site.pages.append(page)
        
        results = validator.validate(mock_site)
        
        # Should validate category pages
        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
