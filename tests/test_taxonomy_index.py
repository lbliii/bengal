"""
Unit tests for TaxonomyIndex.

Tests cover:
- Creating and updating tag entries
- Bi-directional queries (tag->pages, page->tags)
- Cache persistence
- Invalidation and clearing
- Error handling
"""

import json
from pathlib import Path

import pytest

from bengal.cache.taxonomy_index import TagEntry, TaxonomyIndex


@pytest.fixture
def cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache_path = tmp_path / ".bengal"
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


@pytest.fixture
def index(cache_dir):
    """Create TaxonomyIndex with temporary path."""
    return TaxonomyIndex(cache_dir / "taxonomy.json")


class TestTagEntry:
    """Tests for TagEntry dataclass."""

    def test_create_entry(self):
        """Test creating a tag entry."""
        entry = TagEntry(
            tag_slug="python",
            tag_name="Python",
            page_paths=["post1.md", "post2.md"],
            updated_at="2025-10-16T12:00:00",
            is_valid=True,
        )
        assert entry.tag_slug == "python"
        assert entry.tag_name == "Python"
        assert len(entry.page_paths) == 2

    def test_entry_to_dict(self):
        """Test converting entry to dict."""
        entry = TagEntry(
            tag_slug="python",
            tag_name="Python",
            page_paths=["post1.md"],
            updated_at="2025-10-16T12:00:00",
        )
        data = entry.to_dict()
        assert data["tag_slug"] == "python"
        assert data["tag_name"] == "Python"
        assert data["page_paths"] == ["post1.md"]

    def test_entry_from_dict(self):
        """Test creating entry from dict."""
        data = {
            "tag_slug": "python",
            "tag_name": "Python",
            "page_paths": ["post1.md", "post2.md"],
            "updated_at": "2025-10-16T12:00:00",
            "is_valid": True,
        }
        entry = TagEntry.from_dict(data)
        assert entry.tag_slug == "python"
        assert len(entry.page_paths) == 2


class TestTaxonomyIndex:
    """Tests for TaxonomyIndex."""

    def test_create_empty_index(self, cache_dir):
        """Test creating new empty index."""
        idx = TaxonomyIndex(cache_dir / "taxonomy.json")
        assert len(idx.tags) == 0

    def test_update_and_get_tag(self, index):
        """Test updating and retrieving a tag."""
        index.update_tag("python", "Python", ["post1.md", "post2.md"])

        entry = index.get_tag("python")
        assert entry is not None
        assert entry.tag_name == "Python"
        assert entry.page_paths == ["post1.md", "post2.md"]

    def test_get_pages_for_tag(self, index):
        """Test getting pages for a tag."""
        index.update_tag("python", "Python", ["post1.md", "post2.md"])

        pages = index.get_pages_for_tag("python")
        assert pages == ["post1.md", "post2.md"]

    def test_has_tag(self, index):
        """Test checking if tag exists."""
        index.update_tag("python", "Python", ["post1.md"])

        assert index.has_tag("python") is True
        assert index.has_tag("missing") is False

    def test_get_tags_for_page(self, index):
        """Test reverse lookup - get tags for a page."""
        index.update_tag("python", "Python", ["post1.md", "post2.md"])
        index.update_tag("tutorial", "Tutorial", ["post1.md", "post3.md"])
        index.update_tag("advanced", "Advanced", ["post2.md"])

        tags = index.get_tags_for_page(Path("post1.md"))
        assert tags == {"python", "tutorial"}

    def test_invalidate_tag(self, index):
        """Test invalidating a tag."""
        index.update_tag("python", "Python", ["post1.md"])

        assert index.has_tag("python") is True

        index.invalidate_tag("python")

        assert index.has_tag("python") is False

    def test_invalidate_all(self, index):
        """Test invalidating all tags."""
        index.update_tag("python", "Python", ["post1.md"])
        index.update_tag("tutorial", "Tutorial", ["post2.md"])

        index.invalidate_all()

        assert index.has_tag("python") is False
        assert index.has_tag("tutorial") is False

    def test_clear_index(self, index):
        """Test clearing all tags."""
        index.update_tag("python", "Python", ["post1.md"])
        index.update_tag("tutorial", "Tutorial", ["post2.md"])

        index.clear()

        assert len(index.tags) == 0

    def test_remove_page_from_all_tags(self, index):
        """Test removing a page from all its tags."""
        index.update_tag("python", "Python", ["post1.md", "post2.md"])
        index.update_tag("tutorial", "Tutorial", ["post1.md", "post3.md"])

        affected = index.remove_page_from_all_tags(Path("post1.md"))

        assert affected == {"python", "tutorial"}
        assert index.get_pages_for_tag("python") == ["post2.md"]
        assert index.get_pages_for_tag("tutorial") == ["post3.md"]

    def test_save_and_load(self, cache_dir):
        """Test saving and loading from disk."""
        # Create and populate
        idx1 = TaxonomyIndex(cache_dir / "taxonomy.json")
        idx1.update_tag("python", "Python", ["post1.md", "post2.md"])
        idx1.update_tag("tutorial", "Tutorial", ["post1.md"])
        idx1.save_to_disk()

        # Load in new instance
        idx2 = TaxonomyIndex(cache_dir / "taxonomy.json")
        assert idx2.has_tag("python") is True
        assert idx2.get_pages_for_tag("python") == ["post1.md", "post2.md"]
        assert idx2.get_pages_for_tag("tutorial") == ["post1.md"]

    def test_load_nonexistent_file(self, cache_dir):
        """Test loading when file doesn't exist."""
        idx = TaxonomyIndex(cache_dir / "nonexistent.json")
        assert len(idx.tags) == 0

    def test_load_corrupted_file(self, cache_dir):
        """Test loading corrupted JSON file."""
        cache_file = cache_dir / "taxonomy.json"
        with open(cache_file, "w") as f:
            f.write("{ invalid json }")

        idx = TaxonomyIndex(cache_file)
        assert len(idx.tags) == 0

    def test_load_version_mismatch(self, cache_dir):
        """Test loading file with wrong version."""
        cache_file = cache_dir / "taxonomy.json"
        data = {"version": 999, "tags": {}}
        with open(cache_file, "w") as f:
            json.dump(data, f)

        idx = TaxonomyIndex(cache_file)
        assert len(idx.tags) == 0

    def test_get_all_tags(self, index):
        """Test getting all valid tags."""
        index.update_tag("python", "Python", ["post1.md"])
        index.update_tag("tutorial", "Tutorial", ["post2.md"])
        index.update_tag("advanced", "Advanced", ["post3.md"])

        index.invalidate_tag("advanced")

        tags = index.get_all_tags()
        assert len(tags) == 2
        assert "python" in tags
        assert "tutorial" in tags

    def test_get_valid_entries(self, index):
        """Test getting valid entries."""
        index.update_tag("python", "Python", ["post1.md"])
        index.update_tag("tutorial", "Tutorial", ["post2.md"])
        index.update_tag("advanced", "Advanced", ["post3.md"])

        index.invalidate_tag("tutorial")

        valid = index.get_valid_entries()
        assert len(valid) == 2
        assert "python" in valid
        assert "advanced" in valid

    def test_get_invalid_entries(self, index):
        """Test getting invalid entries."""
        index.update_tag("python", "Python", ["post1.md"])
        index.update_tag("tutorial", "Tutorial", ["post2.md"])

        index.invalidate_tag("python")

        invalid = index.get_invalid_entries()
        assert len(invalid) == 1
        assert "python" in invalid

    def test_stats(self, index):
        """Test getting statistics."""
        index.update_tag("python", "Python", ["post1.md", "post2.md"])
        index.update_tag("tutorial", "Tutorial", ["post1.md", "post3.md"])
        index.update_tag("advanced", "Advanced", ["post2.md"])

        index.invalidate_tag("advanced")

        stats = index.stats()
        assert stats["total_tags"] == 3
        assert stats["valid_tags"] == 2
        assert stats["invalid_tags"] == 1
        assert stats["total_unique_pages"] == 3
        assert stats["total_page_tag_pairs"] == 4
        assert stats["avg_tags_per_page"] > 0

    def test_update_existing_tag(self, index):
        """Test updating an existing tag."""
        index.update_tag("python", "Python", ["post1.md"])

        # Update with new pages
        index.update_tag("python", "Python", ["post2.md", "post3.md"])

        pages = index.get_pages_for_tag("python")
        assert pages == ["post2.md", "post3.md"]

    def test_empty_page_list(self, index):
        """Test tag with no pages."""
        index.update_tag("unused", "Unused", [])

        assert index.has_tag("unused") is True
        assert index.get_pages_for_tag("unused") == []

    def test_special_characters_in_tags(self, index):
        """Test handling special characters in tag names."""
        index.update_tag("c-plus-plus", "C++", ["post1.md"])
        index.update_tag("dot-net", ".NET", ["post2.md"])

        assert index.get_pages_for_tag("c-plus-plus") == ["post1.md"]
        assert index.get_pages_for_tag("dot-net") == ["post2.md"]

    def test_multiple_pages_per_tag(self, index):
        """Test tag with many pages."""
        pages = [f"post{i}.md" for i in range(1, 11)]
        index.update_tag("tutorial", "Tutorial", pages)

        retrieved = index.get_pages_for_tag("tutorial")
        assert len(retrieved) == 10
        assert retrieved == pages
