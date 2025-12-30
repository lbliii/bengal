"""
Tests for TaxonomyOrchestrator including conditional generation.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bengal.core.page import Page
from bengal.orchestration.taxonomy import TaxonomyOrchestrator


@pytest.fixture
def mock_site():
    """Create a mock site with pages."""
    from bengal.cache.paths import BengalPaths

    site = Mock()
    site.root_path = Path("/fake/site")
    site.output_dir = Path("/fake/site/public")
    site.paths = BengalPaths(site.root_path)
    site.config = {"pagination": {"per_page": 10}}
    site.taxonomies = {}
    site.pages = []
    site.sections = []

    # Create some mock pages with tags
    pages = [
        Page(
            source_path=Path("/fake/site/content/post1.md"),
            _raw_content="Post 1",
            metadata={
                "title": "Post 1",
                "tags": ["python", "testing"],
                "date": datetime(2024, 1, 1),
            },
        ),
        Page(
            source_path=Path("/fake/site/content/post2.md"),
            _raw_content="Post 2",
            metadata={
                "title": "Post 2",
                "tags": ["python", "django"],
                "date": datetime(2024, 1, 2),
            },
        ),
        Page(
            source_path=Path("/fake/site/content/post3.md"),
            _raw_content="Post 3",
            metadata={"title": "Post 3", "tags": ["testing"], "date": datetime(2024, 1, 3)},
        ),
    ]

    # Set tags property (Page.__post_init__ does this)
    for page in pages:
        page.tags = page.metadata.get("tags", [])

    site.pages = pages
    return site


@pytest.fixture
def orchestrator(mock_site):
    """Create a TaxonomyOrchestrator instance."""
    return TaxonomyOrchestrator(mock_site)


class TestTaxonomyCollection:
    """Test suite for taxonomy collection."""

    def test_collect_taxonomies_empty_site(self, mock_site):
        """Test collecting taxonomies from empty site."""
        mock_site.pages = []
        orchestrator = TaxonomyOrchestrator(mock_site)

        with patch("builtins.print"):  # Suppress print output
            orchestrator.collect_taxonomies()

        assert "tags" in mock_site.taxonomies
        assert "categories" in mock_site.taxonomies
        assert len(mock_site.taxonomies["tags"]) == 0

    def test_collect_taxonomies_with_tags(self, orchestrator, mock_site):
        """Test collecting tags from pages."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

        # Should have 3 unique tags: python, testing, django
        assert len(mock_site.taxonomies["tags"]) == 3
        assert "python" in mock_site.taxonomies["tags"]
        assert "testing" in mock_site.taxonomies["tags"]
        assert "django" in mock_site.taxonomies["tags"]

    def test_taxonomy_structure(self, orchestrator, mock_site):
        """Test structure of collected taxonomies."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

        python_tag = mock_site.taxonomies["tags"]["python"]
        assert python_tag["name"] == "python"
        assert python_tag["slug"] == "python"
        assert len(python_tag["pages"]) == 2  # post1.md and post2.md

    def test_taxonomy_pages_sorted_by_date(self, orchestrator, mock_site):
        """Test that pages within taxonomy are sorted by date (newest first)."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

        python_tag = mock_site.taxonomies["tags"]["python"]
        pages = python_tag["pages"]

        # Should be sorted newest first
        assert pages[0].title == "Post 2"  # 2024-01-02
        assert pages[1].title == "Post 1"  # 2024-01-01


class TestDynamicPageGeneration:
    """Test suite for dynamic page generation."""

    def test_generate_dynamic_pages_full(self, orchestrator, mock_site):
        """Test generating all tag pages (full build)."""
        # Collect taxonomies first
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

            initial_page_count = len(mock_site.pages)
            orchestrator.generate_dynamic_pages()

        # Should have added: 1 tag index + 3 tag pages (python, testing, django)
        assert len(mock_site.pages) > initial_page_count

        # Check generated pages
        generated = [p for p in mock_site.pages if p.metadata.get("_generated")]
        assert len(generated) == 4  # 1 index + 3 tags

    def test_generate_tag_index_page(self, orchestrator, mock_site):
        """Test generating tag index page."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

        tag_index = orchestrator._create_tag_index_page()

        assert tag_index is not None
        assert tag_index.metadata.get("_generated") is True
        assert tag_index.metadata.get("type") == "tag-index"
        assert tag_index.metadata.get("template") == "tags.html"

    def test_create_tag_pages(self, orchestrator, mock_site):
        """Test creating pages for a specific tag."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

        python_tag = mock_site.taxonomies["tags"]["python"]
        tag_pages = orchestrator._create_tag_pages("python", python_tag)

        # Should create 1 page (2 posts fit on 1 page with per_page=10)
        assert len(tag_pages) == 1
        assert tag_pages[0].metadata.get("type") == "tag"
        assert tag_pages[0].metadata.get("_tag") == "python"


class TestConditionalGeneration:
    """Test suite for conditional generation (phase ordering optimization)."""

    def test_generate_dynamic_pages_for_tags_empty(self, orchestrator, mock_site):
        """Test generating pages for empty tag set."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

            initial_count = len(mock_site.pages)
            orchestrator.generate_dynamic_pages_for_tags(set())

        # Should only add tag index, no individual tag pages
        assert len(mock_site.pages) == initial_count + 1

    def test_generate_dynamic_pages_for_specific_tags(self, orchestrator, mock_site):
        """Test generating pages only for specific tags."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

            initial_count = len(mock_site.pages)
            # Only generate for 'python' tag
            affected_tags = {"python"}
            orchestrator.generate_dynamic_pages_for_tags(affected_tags)

        # Should add: 1 tag index + 1 tag page (python only)
        assert len(mock_site.pages) == initial_count + 2

        # Check that only python tag page was generated
        generated = [
            p
            for p in mock_site.pages
            if p.metadata.get("_generated") and p.metadata.get("type") == "tag"
        ]
        assert len(generated) == 1
        assert generated[0].metadata.get("_tag") == "python"

    def test_generate_dynamic_pages_for_multiple_tags(self, orchestrator, mock_site):
        """Test generating pages for multiple specific tags."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

            initial_count = len(mock_site.pages)
            # Generate for python and testing tags
            affected_tags = {"python", "testing"}
            orchestrator.generate_dynamic_pages_for_tags(affected_tags)

        # Should add: 1 tag index + 2 tag pages
        assert len(mock_site.pages) == initial_count + 3

        # Verify correct tags were generated
        generated = [
            p
            for p in mock_site.pages
            if p.metadata.get("_generated") and p.metadata.get("type") == "tag"
        ]
        generated_tags = {p.metadata.get("_tag") for p in generated}
        assert generated_tags == {"python", "testing"}

    def test_generate_dynamic_pages_for_nonexistent_tag(self, orchestrator, mock_site):
        """Test generating pages for tag that doesn't exist."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

            initial_count = len(mock_site.pages)
            # Try to generate for non-existent tag
            affected_tags = {"nonexistent"}
            orchestrator.generate_dynamic_pages_for_tags(affected_tags)

        # Should only add tag index (nonexistent tag should be skipped)
        assert len(mock_site.pages) == initial_count + 1

    def test_generate_always_creates_tag_index(self, orchestrator, mock_site):
        """Test that tag index is always created even with selective generation."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

            # Generate for just one tag
            orchestrator.generate_dynamic_pages_for_tags({"python"})

        # Check that tag index exists
        tag_indexes = [p for p in mock_site.pages if p.metadata.get("type") == "tag-index"]
        assert len(tag_indexes) == 1


class TestPerformanceOptimization:
    """Test that conditional generation is more efficient."""

    def test_selective_generation_calls_create_once_per_tag(self, orchestrator, mock_site):
        """Test that selective generation only creates pages for affected tags."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

        with patch.object(
            orchestrator, "_create_tag_pages", wraps=orchestrator._create_tag_pages
        ) as mock_create:
            affected_tags = {"python"}
            orchestrator.generate_dynamic_pages_for_tags(affected_tags)

            # Should only call _create_tag_pages once (for 'python')
            assert mock_create.call_count == 1
            assert mock_create.call_args[0][0] == "python"

    def test_full_generation_calls_create_for_all_tags(self, orchestrator, mock_site):
        """Test that full generation creates pages for all tags."""
        with patch("builtins.print"):
            orchestrator.collect_taxonomies()

        with patch.object(
            orchestrator, "_create_tag_pages", wraps=orchestrator._create_tag_pages
        ) as mock_create:
            orchestrator.generate_dynamic_pages()

            # Should call _create_tag_pages 3 times (python, testing, django)
            assert mock_create.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
