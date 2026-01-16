"""Unit tests for QueryIndex and built-in indexes."""

from pathlib import Path

import pytest

from bengal.cache.build_cache import BuildCache
from bengal.cache.indexes.author_index import AuthorIndex
from bengal.cache.indexes.category_index import CategoryIndex
from bengal.cache.indexes.date_range_index import DateRangeIndex
from bengal.cache.indexes.section_index import SectionIndex
from bengal.cache.query_index import IndexEntry
from bengal.core.page import Page
from bengal.core.section import Section


@pytest.fixture
def temp_cache_path(tmp_path):
    """Create a temporary cache path."""
    return tmp_path / "test_index.json"


@pytest.fixture
def build_cache(tmp_path):
    """Create a test build cache."""
    return BuildCache()


@pytest.fixture
def sample_page():
    """Create a sample page for testing."""
    from bengal.core.site import Site

    page = Page(
        source_path=Path("content/blog/test-post.md"),
        _raw_content="Test content",
        metadata={
            "title": "Test Post",
            "author": "Jane Smith",
            "category": "tutorial",
            "date": "2024-01-15",
        },
    )

    # Create a mock site with section registry
    site = Site(root_path=Path("."), config={})
    blog_section = Section(name="blog", path=Path("content/blog"))
    site.sections = [blog_section]
    site.register_sections()

    page._site = site
    page._section = blog_section
    return page


class TestIndexEntry:
    """Test IndexEntry dataclass."""

    def test_create_entry(self):
        """Test creating an index entry."""
        entry = IndexEntry(
            key="blog",
            page_paths={"content/post1.md", "content/post2.md"},
            metadata={"title": "Blog"},
        )

        assert entry.key == "blog"
        assert len(entry.page_paths) == 2
        assert "content/post1.md" in entry.page_paths
        assert entry.metadata["title"] == "Blog"
        assert entry.content_hash  # Auto-computed

    def test_entry_serialization(self):
        """Test entry to/from dict."""
        entry = IndexEntry(
            key="tutorial",
            page_paths={"page1.md", "page2.md"},
            metadata={"count": 2},
        )

        data = entry.to_cache_dict()
        assert data["key"] == "tutorial"
        assert set(data["page_paths"]) == {"page1.md", "page2.md"}

        restored = IndexEntry.from_cache_dict(data)
        assert restored.key == entry.key
        assert restored.page_paths == entry.page_paths


class TestSectionIndex:
    """Test SectionIndex."""

    def test_extract_keys_with_section(self, sample_page):
        """Test extracting section key from page."""
        index = SectionIndex(Path("test.json"))
        keys = index.extract_keys(sample_page)

        assert len(keys) == 1
        assert keys[0][0] == "blog"  # section name
        assert "title" in keys[0][1]  # metadata

    def test_extract_keys_no_section(self):
        """Test page without section."""
        page = Page(source_path=Path("test.md"), _raw_content="Test")
        index = SectionIndex(Path("test.json"))
        keys = index.extract_keys(page)

        assert keys == []

    def test_update_page(self, sample_page, build_cache, temp_cache_path):
        """Test updating index with page."""
        index = SectionIndex(temp_cache_path)
        affected = index.update_page(sample_page, build_cache)

        assert "blog" in affected
        assert "blog" in index.entries
        assert str(sample_page.source_path) in index.entries["blog"].page_paths

    def test_persistence(self, sample_page, build_cache, temp_cache_path):
        """Test saving and loading index."""
        # Build and save
        index1 = SectionIndex(temp_cache_path)
        index1.update_page(sample_page, build_cache)
        index1.save_to_disk()

        # Load in new index
        index2 = SectionIndex(temp_cache_path)
        assert "blog" in index2.entries
        assert str(sample_page.source_path) in index2.get("blog")


class TestAuthorIndex:
    """Test AuthorIndex."""

    def test_extract_single_author_string(self, sample_page):
        """Test extracting author as string."""
        index = AuthorIndex(Path("test.json"))
        keys = index.extract_keys(sample_page)

        assert len(keys) == 1
        assert keys[0][0] == "Jane Smith"

    def test_extract_author_dict(self):
        """Test extracting author as dict."""
        page = Page(
            source_path=Path("test.md"),
            _raw_content="Test",
            metadata={
                "author": {
                    "name": "Bob Jones",
                    "email": "bob@example.com",
                    "bio": "Developer",
                }
            },
        )

        index = AuthorIndex(Path("test.json"))
        keys = index.extract_keys(page)

        assert len(keys) == 1
        assert keys[0][0] == "Bob Jones"
        assert keys[0][1]["email"] == "bob@example.com"

    def test_extract_multiple_authors(self):
        """Test multi-author support."""
        page = Page(
            source_path=Path("test.md"),
            _raw_content="Test",
            metadata={"authors": ["Alice Chen", "Bob Jones"]},
        )

        index = AuthorIndex(Path("test.json"))
        keys = index.extract_keys(page)

        assert len(keys) == 2
        assert keys[0][0] == "Alice Chen"
        assert keys[1][0] == "Bob Jones"


class TestCategoryIndex:
    """Test CategoryIndex."""

    def test_extract_category(self, sample_page):
        """Test extracting category."""
        index = CategoryIndex(Path("test.json"))
        keys = index.extract_keys(sample_page)

        assert len(keys) == 1
        assert keys[0][0] == "tutorial"  # normalized to lowercase

    def test_category_normalization(self):
        """Test category is normalized."""
        page = Page(
            source_path=Path("test.md"),
            _raw_content="Test",
            metadata={"category": "  API Reference  "},  # with whitespace
        )

        index = CategoryIndex(Path("test.json"))
        keys = index.extract_keys(page)

        assert keys[0][0] == "api reference"  # lowercase, trimmed


class TestDateRangeIndex:
    """Test DateRangeIndex."""

    def test_extract_year_and_month(self, sample_page):
        """Test extracting year and month keys."""
        index = DateRangeIndex(Path("test.json"))
        keys = index.extract_keys(sample_page)

        assert len(keys) == 2
        assert keys[0][0] == "2024"  # year
        assert keys[1][0] == "2024-01"  # year-month

    def test_no_date(self):
        """Test page without date."""
        page = Page(source_path=Path("test.md"), _raw_content="Test")
        index = DateRangeIndex(Path("test.json"))
        keys = index.extract_keys(page)

        assert keys == []


class TestQueryIndexOperations:
    """Test QueryIndex base operations."""

    def test_get_empty(self, temp_cache_path):
        """Test getting non-existent key."""
        index = SectionIndex(temp_cache_path)
        result = index.get("nonexistent")

        assert result == set()

    def test_keys_list(self, sample_page, build_cache, temp_cache_path):
        """Test getting all keys."""
        index = SectionIndex(temp_cache_path)
        index.update_page(sample_page, build_cache)

        keys = index.keys()
        assert "blog" in keys

    def test_has_changed(self, sample_page, build_cache, temp_cache_path):
        """Test change detection."""
        index = SectionIndex(temp_cache_path)
        index.update_page(sample_page, build_cache)

        # Same pages - no change
        assert not index.has_changed("blog", {str(sample_page.source_path)})

        # Different pages - has changed
        assert index.has_changed("blog", {"other.md"})

    def test_remove_page(self, sample_page, build_cache, temp_cache_path):
        """Test removing page from index."""
        index = SectionIndex(temp_cache_path)
        index.update_page(sample_page, build_cache)

        affected = index.remove_page(str(sample_page.source_path))
        assert "blog" in affected
        assert str(sample_page.source_path) not in index.get("blog")

    def test_clear(self, sample_page, build_cache, temp_cache_path):
        """Test clearing index."""
        index = SectionIndex(temp_cache_path)
        index.update_page(sample_page, build_cache)

        index.clear()
        assert len(index.entries) == 0
        assert len(index.keys()) == 0

    def test_stats(self, sample_page, build_cache, temp_cache_path):
        """Test index statistics."""
        index = SectionIndex(temp_cache_path)
        index.update_page(sample_page, build_cache)

        stats = index.stats()
        assert stats["name"] == "section"
        assert stats["total_keys"] == 1
        assert stats["unique_pages"] == 1


class TestIncrementalUpdates:
    """Test incremental index updates."""

    def test_page_moved_between_keys(self, build_cache, temp_cache_path):
        """Test page moving from one key to another."""
        from unittest.mock import Mock

        from bengal.core.site import Site

        index = SectionIndex(temp_cache_path)

        # Create a mock site with section registry
        mock_site = Mock(spec=Site)
        mock_site._mock_sections = {}
        mock_site.registry = Mock()
        mock_site.registry.epoch = 0
        mock_site.get_section_by_path = Mock(
            side_effect=lambda path: mock_site._mock_sections.get(path)
        )

        # First update - page in 'blog'
        blog_section = Section(name="blog", path=Path("content/blog"))
        mock_site._mock_sections[blog_section.path] = blog_section

        page = Page(source_path=Path("content/post.md"), _raw_content="Test")
        page._site = mock_site
        page._section = blog_section  # This stores the path
        index.update_page(page, build_cache)

        assert str(page.source_path) in index.get("blog")

        # Second update - page moved to 'docs'
        docs_section = Section(name="docs", path=Path("content/docs"))
        mock_site._mock_sections[docs_section.path] = docs_section

        page._section = docs_section  # This updates the path
        affected = index.update_page(page, build_cache)

        assert "blog" in affected  # Removed from blog
        assert "docs" in affected  # Added to docs
        assert str(page.source_path) not in index.get("blog")
        assert str(page.source_path) in index.get("docs")

    def test_multiple_pages_same_key(self, build_cache, temp_cache_path):
        """Test multiple pages with same key."""
        index = AuthorIndex(temp_cache_path)

        page1 = Page(
            source_path=Path("post1.md"),
            _raw_content="Test",
            metadata={"author": "Jane Smith"},
        )
        page2 = Page(
            source_path=Path("post2.md"),
            _raw_content="Test",
            metadata={"author": "Jane Smith"},
        )

        index.update_page(page1, build_cache)
        index.update_page(page2, build_cache)

        pages = index.get("Jane Smith")
        assert len(pages) == 2
        assert str(page1.source_path) in pages
        assert str(page2.source_path) in pages


class TestQueryIndexThreadSafety:
    """Thread safety tests for QueryIndex."""

    def test_concurrent_page_updates(self, build_cache, temp_cache_path):
        """Multiple threads can safely update pages concurrently."""
        import threading

        index = AuthorIndex(temp_cache_path)
        errors: list[str] = []

        def update_pages(thread_id: int):
            """Update pages from a specific thread."""
            try:
                for i in range(50):
                    page = Page(
                        source_path=Path(f"post-{thread_id}-{i}.md"),
                        _raw_content="Test",
                        metadata={"author": f"Author {thread_id}"},
                    )
                    index.update_page(page, build_cache)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Spawn multiple threads
        threads = [threading.Thread(target=update_pages, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety violations: {errors}"

        # Verify all authors have pages
        for thread_id in range(4):
            pages = index.get(f"Author {thread_id}")
            assert len(pages) == 50, f"Author {thread_id} should have 50 pages"

    def test_concurrent_read_write(self, build_cache, temp_cache_path):
        """Readers and writers can operate concurrently."""
        import threading

        index = AuthorIndex(temp_cache_path)
        # Pre-populate
        for i in range(10):
            page = Page(
                source_path=Path(f"initial-{i}.md"),
                _raw_content="Test",
                metadata={"author": f"Author {i % 3}"},
            )
            index.update_page(page, build_cache)

        errors: list[str] = []
        read_count = [0]

        def reader():
            """Read index repeatedly."""
            try:
                for _ in range(100):
                    for i in range(3):
                        _ = index.get(f"Author {i}")
                        _ = index.keys()
                        read_count[0] += 1
            except Exception as e:
                errors.append(f"Reader: {e}")

        def writer():
            """Update pages repeatedly."""
            try:
                for i in range(100):
                    page = Page(
                        source_path=Path(f"new-post-{i}.md"),
                        _raw_content="Test",
                        metadata={"author": f"Author {i % 3}"},
                    )
                    index.update_page(page, build_cache)
            except Exception as e:
                errors.append(f"Writer: {e}")

        threads = [threading.Thread(target=reader) for _ in range(3)]
        threads.append(threading.Thread(target=writer))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety violations: {errors}"
        assert read_count[0] > 0, "Reads should have occurred"


class TestQueryIndexInvariantViolation:
    """Tests for handling invariant violations in QueryIndex."""

    def test_save_clears_index_on_invariant_violation(self, build_cache, temp_cache_path):
        """save_to_disk clears index if invariants are violated."""
        from bengal.cache.query_index import IndexEntry

        index = AuthorIndex(temp_cache_path)

        # Add valid data
        page = Page(
            source_path=Path("post1.md"),
            _raw_content="Test",
            metadata={"author": "Jane"},
        )
        index.update_page(page, build_cache)

        # Manually corrupt the internal state (simulate invariant violation)
        # Add an entry that references pages not in _page_to_keys
        index.entries["Orphan Author"] = IndexEntry(
            key="Orphan Author",
            page_paths={"nonexistent-page.md"},  # Not in _page_to_keys
            metadata={},
        )

        # save_to_disk should detect corruption and clear the index
        index.save_to_disk()

        # Index should be cleared
        assert len(index.entries) == 0
        assert len(index._page_to_keys) == 0

        # On next load, it should be empty (no corrupted data saved)
        index2 = AuthorIndex(temp_cache_path)
        assert len(index2.entries) == 0
