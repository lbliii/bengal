"""Unit tests for QueryIndexRegistry."""

from datetime import datetime
from pathlib import Path

import pytest

from bengal.cache.build_cache import BuildCache
from bengal.cache.query_index_registry import QueryIndexRegistry
from bengal.core.section import Section
from bengal.core.site import Site
from tests._testing.mocks import MockPage


def _page(
    *,
    source_path: Path,
    raw_content: str = "",
    metadata: dict[str, object] | None = None,
    **attrs: object,
) -> MockPage:
    """Create a page-like cache fixture without constructing legacy Page."""
    page_metadata = dict(metadata or {})
    date_value = page_metadata.get("date")
    date = datetime.fromisoformat(date_value) if isinstance(date_value, str) else None
    page = MockPage(
        title=str(page_metadata.get("title", "")),
        source_path=source_path,
        metadata=page_metadata,
        tags=list(page_metadata.get("tags", []))
        if isinstance(page_metadata.get("tags"), list)
        else [],
        date=date,
    )
    page.raw_content = raw_content
    page._raw_content = raw_content
    for attr, value in attrs.items():
        setattr(page, attr, value)
    return page


@pytest.fixture
def temp_site(tmp_path):
    """Create a temporary site for testing."""
    site = Site(root_path=tmp_path, config={})
    return site


@pytest.fixture
def sample_pages(temp_site):
    """Create sample pages for testing."""
    from unittest.mock import Mock

    pages = []

    # Create sections
    blog_section = Section(name="blog", path=Path("content/blog"))
    docs_section = Section(name="docs", path=Path("content/docs"))

    # Set up site registry
    temp_site._mock_sections = {
        blog_section.path: blog_section,
        docs_section.path: docs_section,
    }
    temp_site.registry.register_section(blog_section)
    temp_site.registry.register_section(docs_section)
    temp_site.get_section_by_path = Mock(
        side_effect=lambda path: temp_site._mock_sections.get(path)
    )

    # Blog posts
    for i in range(3):
        page = _page(
            source_path=Path(f"content/blog/post{i}.md"),
            raw_content=f"Post {i}",
            metadata={
                "title": f"Post {i}",
                "author": "Jane Smith",
                "category": "tutorial",
                "date": f"2024-01-{i + 10}",
            },
        )
        page._site = temp_site
        page._section = blog_section  # This stores the path
        pages.append(page)

    # Docs pages
    for i in range(2):
        page = _page(
            source_path=Path(f"content/docs/doc{i}.md"),
            raw_content=f"Doc {i}",
            metadata={
                "title": f"Doc {i}",
                "author": "Bob Jones",
                "category": "guide",
                "date": f"2024-02-{i + 10}",
            },
        )
        page._site = temp_site
        page._section = docs_section  # This stores the path
        pages.append(page)

    return pages


class TestQueryIndexRegistry:
    """Test QueryIndexRegistry."""

    def test_initialization(self, temp_site, tmp_path):
        """Test registry initialization."""
        cache_dir = tmp_path / "indexes"
        registry = QueryIndexRegistry(temp_site, cache_dir)

        assert registry.site == temp_site
        assert registry.cache_dir == cache_dir
        assert not registry._initialized

    def test_lazy_initialization(self, temp_site, tmp_path):
        """Test indexes are registered lazily."""
        cache_dir = tmp_path / "indexes"
        registry = QueryIndexRegistry(temp_site, cache_dir)

        # Not initialized yet
        assert not registry._initialized

        # Access triggers initialization
        section_index = registry.get("section")
        assert registry._initialized
        assert section_index is not None

    def test_builtin_indexes_registered(self, temp_site, tmp_path):
        """Test built-in indexes are registered."""
        cache_dir = tmp_path / "indexes"
        registry = QueryIndexRegistry(temp_site, cache_dir)
        registry._ensure_initialized()

        assert "section" in registry.indexes
        assert "author" in registry.indexes
        assert "category" in registry.indexes
        assert "date_range" in registry.indexes

    def test_attribute_access(self, temp_site, tmp_path):
        """Test attribute-style access to indexes."""
        cache_dir = tmp_path / "indexes"
        registry = QueryIndexRegistry(temp_site, cache_dir)

        # Can access via attribute
        section_index = registry.section
        assert section_index.name == "section"

        author_index = registry.author
        assert author_index.name == "author"

    def test_attribute_access_missing(self, temp_site, tmp_path):
        """Test accessing non-existent index."""
        cache_dir = tmp_path / "indexes"
        registry = QueryIndexRegistry(temp_site, cache_dir)

        with pytest.raises(AttributeError):
            _ = registry.nonexistent_index

    def test_build_all(self, temp_site, sample_pages, tmp_path):
        """Test building all indexes."""
        cache_dir = tmp_path / "indexes"
        temp_site.pages = sample_pages
        build_cache = BuildCache()

        registry = QueryIndexRegistry(temp_site, cache_dir)
        registry.build_all(sample_pages, build_cache)

        # Check section index
        blog_pages = registry.section.get("blog")
        docs_pages = registry.section.get("docs")
        assert len(blog_pages) == 3
        assert len(docs_pages) == 2

        # Check author index
        jane_pages = registry.author.get("Jane Smith")
        bob_pages = registry.author.get("Bob Jones")
        assert len(jane_pages) == 3
        assert len(bob_pages) == 2

        # Check category index
        tutorial_pages = registry.category.get("tutorial")
        guide_pages = registry.category.get("guide")
        assert len(tutorial_pages) == 3
        assert len(guide_pages) == 2

    def test_incremental_update(self, temp_site, sample_pages, tmp_path):
        """Test incremental index updates."""
        cache_dir = tmp_path / "indexes"
        temp_site.pages = sample_pages
        build_cache = BuildCache()

        registry = QueryIndexRegistry(temp_site, cache_dir)

        # Initial build
        registry.build_all(sample_pages, build_cache)

        # Modify one page
        changed_page = sample_pages[0]
        changed_page.metadata["author"] = "Alice Chen"  # Change author

        # Incremental update
        affected = registry.update_incremental([changed_page], build_cache)

        # Author index should be affected
        assert "author" in affected
        assert "Jane Smith" in affected["author"]  # Old author
        assert "Alice Chen" in affected["author"]  # New author

        # Verify update
        jane_pages = registry.author.get("Jane Smith")
        alice_pages = registry.author.get("Alice Chen")
        assert len(jane_pages) == 2  # One less
        assert len(alice_pages) == 1  # One more

    def test_has_method(self, temp_site, tmp_path):
        """Test checking if index exists."""
        cache_dir = tmp_path / "indexes"
        registry = QueryIndexRegistry(temp_site, cache_dir)

        assert registry.has("section")
        assert registry.has("author")
        assert not registry.has("nonexistent")

    def test_save_all(self, temp_site, sample_pages, tmp_path):
        """Test saving all indexes."""
        cache_dir = tmp_path / "indexes"
        temp_site.pages = sample_pages
        build_cache = BuildCache()

        registry = QueryIndexRegistry(temp_site, cache_dir)
        registry.build_all(sample_pages, build_cache)
        registry.save_all()

        # Verify files were created
        assert (cache_dir / "section_index.json").exists()
        assert (cache_dir / "author_index.json").exists()

    def test_stats(self, temp_site, sample_pages, tmp_path):
        """Test registry statistics."""
        cache_dir = tmp_path / "indexes"
        temp_site.pages = sample_pages
        build_cache = BuildCache()

        registry = QueryIndexRegistry(temp_site, cache_dir)
        registry.build_all(sample_pages, build_cache)

        stats = registry.stats()
        assert stats["total_indexes"] == 4  # section, author, category, date_range
        assert "section" in stats["indexes"]
        assert stats["indexes"]["section"]["total_keys"] == 2  # blog, docs

    def test_skip_generated_pages(self, temp_site, tmp_path):
        """Test that generated pages are skipped."""
        cache_dir = tmp_path / "indexes"
        build_cache = BuildCache()

        # Create pages including generated
        pages = []
        page1 = _page(
            source_path=Path("content/post.md"),
            raw_content="Test",
            metadata={"title": "Post", "author": "Jane"},
        )
        page1._section = Section(name="blog", path=Path("content/blog"))
        pages.append(page1)

        # Generated page (should be skipped)
        page2 = _page(
            source_path=Path("tags/python.md"),
            raw_content="Tag page",
            metadata={"title": "Python", "_generated": True},
        )
        pages.append(page2)

        temp_site.pages = pages
        registry = QueryIndexRegistry(temp_site, cache_dir)
        registry.build_all(pages, build_cache)

        # Only non-generated page should be indexed
        jane_pages = registry.author.get("Jane")
        assert len(jane_pages) == 1
        assert str(page2.source_path) not in jane_pages
