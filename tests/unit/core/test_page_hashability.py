"""
Test Page hashability and set operations.

Tests that Page objects are properly hashable based on source_path,
enabling set storage, dictionary keys, and O(1) membership tests.
"""

from pathlib import Path

from bengal.core.page import Page


class TestPageHashability:
    """Test that Page objects are properly hashable."""

    def test_page_is_hashable(self, tmp_path):
        """Pages can be hashed."""
        page = Page(source_path=tmp_path / "content/post.md")
        assert isinstance(hash(page), int)

    def test_page_equality_by_source_path(self, tmp_path):
        """Pages with same source_path are equal."""
        path = tmp_path / "content/post.md"
        page1 = Page(source_path=path)
        page2 = Page(source_path=path)

        assert page1 == page2
        assert hash(page1) == hash(page2)

    def test_page_inequality_different_paths(self, tmp_path):
        """Pages with different source_paths are not equal."""
        page1 = Page(source_path=tmp_path / "content/post1.md")
        page2 = Page(source_path=tmp_path / "content/post2.md")

        assert page1 != page2
        # Hashes are likely different (not guaranteed but highly probable)
        # We don't assert hash inequality because hash collisions are theoretically possible

    def test_page_hash_stable_across_mutations(self, tmp_path):
        """Hash remains stable when mutable fields change."""
        page = Page(source_path=tmp_path / "content/post.md")
        initial_hash = hash(page)

        # Mutate various fields
        page._raw_content = "New content"
        page.rendered_html = "<p>Rendered</p>"
        page.metadata = {"title": "New Title", "tags": ["python"]}
        page.tags = ["python", "tutorial"]
        page.toc = "<nav>TOC</nav>"
        page.output_path = tmp_path / "public/post/index.html"

        # Hash should remain unchanged
        assert hash(page) == initial_hash

    def test_page_in_set(self, tmp_path):
        """Pages can be stored in sets."""
        page1 = Page(source_path=tmp_path / "content/post1.md")
        page2 = Page(source_path=tmp_path / "content/post2.md")
        page3 = Page(source_path=tmp_path / "content/post1.md")  # Duplicate

        pages = {page1, page2, page3}

        # Should deduplicate page1 and page3
        assert len(pages) == 2
        assert page1 in pages
        assert page2 in pages
        assert page3 in pages  # Same as page1

    def test_page_as_dict_key(self, tmp_path):
        """Pages can be used as dictionary keys."""
        page1 = Page(source_path=tmp_path / "content/post1.md")
        page2 = Page(source_path=tmp_path / "content/post2.md")

        data = {page1: "data for page 1", page2: "data for page 2"}

        assert data[page1] == "data for page 1"
        assert data[page2] == "data for page 2"

        # Lookup with equivalent page works
        page1_copy = Page(source_path=tmp_path / "content/post1.md")
        assert data[page1_copy] == "data for page 1"

    def test_page_findable_in_set_after_mutation(self, tmp_path):
        """Page remains findable in set after mutation."""
        page = Page(source_path=tmp_path / "content/post.md")
        pages = {page}

        # Mutate the page
        page._raw_content = "Changed"
        page.tags = ["new-tag"]
        page.metadata = {"updated": True}

        # Should still be findable
        assert page in pages

    def test_page_equality_ignores_content(self, tmp_path):
        """Pages are equal based on path, not content."""
        path = tmp_path / "content/post.md"
        page1 = Page(source_path=path, _raw_content="Content A")
        page2 = Page(source_path=path, _raw_content="Content B")

        # Equal despite different content
        assert page1 == page2
        assert hash(page1) == hash(page2)

    def test_page_equality_ignores_metadata(self, tmp_path):
        """Pages are equal based on path, not metadata."""
        path = tmp_path / "content/post.md"
        page1 = Page(source_path=path, metadata={"title": "First Title", "tags": ["a"]})
        page2 = Page(source_path=path, metadata={"title": "Second Title", "tags": ["b", "c"]})

        # Equal despite different metadata
        assert page1 == page2
        assert hash(page1) == hash(page2)

    def test_page_not_equal_to_other_types(self, tmp_path):
        """Pages are not equal to non-Page objects."""
        page = Page(source_path=tmp_path / "content/post.md")

        assert page != str(tmp_path / "content/post.md")
        assert page != tmp_path / "content/post.md"
        assert page is not None
        assert page != 42
        assert page != {"source_path": tmp_path / "content/post.md"}


class TestPageSetOperations:
    """Test set operations with pages."""

    def test_set_union(self, tmp_path):
        """Set union works with pages."""
        page1 = Page(source_path=tmp_path / "content/a.md")
        page2 = Page(source_path=tmp_path / "content/b.md")
        page3 = Page(source_path=tmp_path / "content/c.md")

        set1 = {page1, page2}
        set2 = {page2, page3}

        union = set1 | set2
        assert len(union) == 3
        assert page1 in union
        assert page2 in union
        assert page3 in union

    def test_set_intersection(self, tmp_path):
        """Set intersection works with pages."""
        page1 = Page(source_path=tmp_path / "content/a.md")
        page2 = Page(source_path=tmp_path / "content/b.md")
        page3 = Page(source_path=tmp_path / "content/c.md")

        set1 = {page1, page2}
        set2 = {page2, page3}

        intersection = set1 & set2
        assert len(intersection) == 1
        assert page2 in intersection
        assert page1 not in intersection
        assert page3 not in intersection

    def test_set_difference(self, tmp_path):
        """Set difference works with pages."""
        page1 = Page(source_path=tmp_path / "content/a.md")
        page2 = Page(source_path=tmp_path / "content/b.md")
        page3 = Page(source_path=tmp_path / "content/c.md")

        set1 = {page1, page2, page3}
        set2 = {page2}

        difference = set1 - set2
        assert len(difference) == 2
        assert page1 in difference
        assert page3 in difference
        assert page2 not in difference

    def test_set_symmetric_difference(self, tmp_path):
        """Set symmetric difference works with pages."""
        page1 = Page(source_path=tmp_path / "content/a.md")
        page2 = Page(source_path=tmp_path / "content/b.md")
        page3 = Page(source_path=tmp_path / "content/c.md")

        set1 = {page1, page2}
        set2 = {page2, page3}

        sym_diff = set1 ^ set2
        assert len(sym_diff) == 2
        assert page1 in sym_diff
        assert page3 in sym_diff
        assert page2 not in sym_diff

    def test_set_issubset(self, tmp_path):
        """Set subset operations work with pages."""
        page1 = Page(source_path=tmp_path / "content/a.md")
        page2 = Page(source_path=tmp_path / "content/b.md")
        page3 = Page(source_path=tmp_path / "content/c.md")

        small_set = {page1, page2}
        large_set = {page1, page2, page3}

        assert small_set.issubset(large_set)
        assert small_set <= large_set
        assert not large_set.issubset(small_set)

    def test_set_issuperset(self, tmp_path):
        """Set superset operations work with pages."""
        page1 = Page(source_path=tmp_path / "content/a.md")
        page2 = Page(source_path=tmp_path / "content/b.md")
        page3 = Page(source_path=tmp_path / "content/c.md")

        small_set = {page1, page2}
        large_set = {page1, page2, page3}

        assert large_set.issuperset(small_set)
        assert large_set >= small_set
        assert not small_set.issuperset(large_set)


class TestPageDictionaryOperations:
    """Test dictionary operations with pages as keys."""

    def test_dict_get_and_set(self, tmp_path):
        """Basic dict operations with page keys."""
        page = Page(source_path=tmp_path / "content/post.md")

        data = {}
        data[page] = "some value"

        assert data[page] == "some value"
        assert page in data

    def test_dict_update(self, tmp_path):
        """Dict update with equivalent page."""
        page1 = Page(source_path=tmp_path / "content/post.md")
        page2 = Page(source_path=tmp_path / "content/post.md")  # Same path

        data = {page1: "first value"}
        data[page2] = "second value"  # Should update, not add

        assert len(data) == 1
        assert data[page1] == "second value"
        assert data[page2] == "second value"

    def test_dict_keys_contains_check(self, tmp_path):
        """Check if page is in dict keys."""
        page1 = Page(source_path=tmp_path / "content/a.md")
        page2 = Page(source_path=tmp_path / "content/b.md")
        page3 = Page(source_path=tmp_path / "content/c.md")

        data = {page1: 1, page2: 2}

        assert page1 in data
        assert page2 in data
        assert page3 not in data

    def test_dict_with_mutated_page(self, tmp_path):
        """Dict lookup works after page mutation."""
        page = Page(source_path=tmp_path / "content/post.md")
        data = {page: "original"}

        # Mutate the page
        page._raw_content = "New content"
        page.tags = ["new"]

        # Should still be findable
        assert page in data
        assert data[page] == "original"


class TestPageHashStability:
    """Test hash stability in various scenarios."""

    def test_hash_consistent_across_calls(self, tmp_path):
        """Hash value is consistent across multiple calls."""
        page = Page(source_path=tmp_path / "content/post.md")

        hash1 = hash(page)
        hash2 = hash(page)
        hash3 = hash(page)

        assert hash1 == hash2 == hash3

    def test_hash_stable_with_all_fields_set(self, tmp_path):
        """Hash stable even when all fields are populated."""
        page = Page(
            source_path=tmp_path / "content/post.md",
            _raw_content="# Title\n\nContent here",
            metadata={"title": "Test", "tags": ["a", "b"]},
            rendered_html="<h1>Title</h1><p>Content</p>",
            output_path=tmp_path / "public/post/index.html",
            tags=["a", "b"],
            toc="<nav>TOC</nav>",
        )

        hash1 = hash(page)

        # Modify everything except source_path
        page._raw_content = "Different"
        page.metadata = {}
        page.rendered_html = "Different"
        page.tags = []

        hash2 = hash(page)

        assert hash1 == hash2

    def test_generated_pages_have_unique_hashes(self, tmp_path):
        """Generated pages with different paths have different hashes."""
        tag_page1 = Page(source_path=Path("_generated/tags/python.md"))
        tag_page2 = Page(source_path=Path("_generated/tags/javascript.md"))

        assert hash(tag_page1) != hash(tag_page2)
        assert tag_page1 != tag_page2
