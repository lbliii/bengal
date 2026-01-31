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

    def test_entry_to_cache_dict(self):
        """Test converting entry to dict."""
        entry = TagEntry(
            tag_slug="python",
            tag_name="Python",
            page_paths=["post1.md"],
            updated_at="2025-10-16T12:00:00",
        )
        data = entry.to_cache_dict()
        assert data["tag_slug"] == "python"
        assert data["tag_name"] == "Python"
        assert data["page_paths"] == ["post1.md"]

    def test_entry_from_cache_dict(self):
        """Test creating entry from dict."""
        data = {
            "tag_slug": "python",
            "tag_name": "Python",
            "page_paths": ["post1.md", "post2.md"],
            "updated_at": "2025-10-16T12:00:00",
            "is_valid": True,
        }
        entry = TagEntry.from_cache_dict(data)
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

    def test_round_trip_compressed_format(self, cache_dir):
        """Test save/load cycle with compressed format."""
        # Create and populate
        idx1 = TaxonomyIndex(cache_dir / "taxonomy.json")
        idx1.update_tag("python", "Python", ["post1.md", "post2.md"])
        idx1.update_tag("tutorial", "Tutorial", ["post1.md"])
        idx1.save_to_disk()

        # Verify compressed file exists
        compressed_path = cache_dir / "taxonomy.json.zst"
        assert compressed_path.exists(), "Compressed cache file should exist"

        # Verify original JSON file doesn't exist (or is old)
        json_path = cache_dir / "taxonomy.json"
        # If old JSON exists, compressed should be newer
        if json_path.exists():
            assert compressed_path.stat().st_mtime >= json_path.stat().st_mtime

        # Load in new instance (should use compressed format)
        idx2 = TaxonomyIndex(cache_dir / "taxonomy.json")
        assert idx2.has_tag("python") is True
        assert idx2.get_pages_for_tag("python") == ["post1.md", "post2.md"]
        assert idx2.get_pages_for_tag("tutorial") == ["post1.md"]

        # Verify file was written (compression ratio check skipped for small test data)
        # Real-world caches achieve 92-93% reduction, but tiny test payloads
        # don't compress well due to header overhead
        compressed_size = compressed_path.stat().st_size
        assert compressed_size > 0, "Compressed cache file should not be empty"

    def test_migration_from_uncompressed(self, cache_dir):
        """Test backward compatibility: load old .json format, save new .json.zst format."""
        # Create old uncompressed JSON format
        json_path = cache_dir / "taxonomy.json"
        old_data = {
            "version": 2,
            "tags": {
                "python": {
                    "tag_slug": "python",
                    "tag_name": "Python",
                    "page_paths": ["post1.md", "post2.md"],
                    "updated_at": "2025-10-16T12:00:00",
                    "is_valid": True,
                }
            },
            "page_to_tags": {
                "post1.md": ["python"],
                "post2.md": ["python"],
            },
        }
        with open(json_path, "w") as f:
            json.dump(old_data, f, indent=2)

        # Load old format (should work via load_auto fallback)
        idx = TaxonomyIndex(cache_dir / "taxonomy.json")
        assert idx.has_tag("python") is True
        assert idx.get_pages_for_tag("python") == ["post1.md", "post2.md"]

        # Save should create new compressed format
        idx.save_to_disk()
        compressed_path = cache_dir / "taxonomy.json.zst"
        assert compressed_path.exists(), "Save should create compressed format"

        # Subsequent load should use compressed format
        idx2 = TaxonomyIndex(cache_dir / "taxonomy.json")
        assert idx2.has_tag("python") is True


class TestTaxonomyIndexThreadSafety:
    """Thread safety tests for TaxonomyIndex."""

    def test_concurrent_tag_updates(self, cache_dir):
        """Multiple threads can safely update tags concurrently."""
        import threading

        idx = TaxonomyIndex(cache_dir / "taxonomy.json")
        errors: list[str] = []

        def update_tags(thread_id: int):
            """Update tags from a specific thread."""
            try:
                for i in range(50):
                    tag_slug = f"tag-{thread_id}-{i}"
                    pages = [f"page-{thread_id}-{i}-{j}.md" for j in range(3)]
                    idx.update_tag(tag_slug, f"Tag {thread_id}-{i}", pages)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Spawn multiple threads
        threads = [threading.Thread(target=update_tags, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety violations: {errors}"

        # Verify all tags were created
        for thread_id in range(4):
            for i in range(50):
                tag_slug = f"tag-{thread_id}-{i}"
                assert idx.has_tag(tag_slug), f"Missing tag: {tag_slug}"

    def test_concurrent_read_write(self, cache_dir):
        """Readers and writers can operate concurrently."""
        import threading

        idx = TaxonomyIndex(cache_dir / "taxonomy.json")
        # Pre-populate some tags
        for i in range(10):
            idx.update_tag(f"tag-{i}", f"Tag {i}", [f"page-{i}.md"])

        errors: list[str] = []
        read_count = [0]

        def reader():
            """Read tags repeatedly."""
            try:
                for _ in range(100):
                    for i in range(10):
                        _ = idx.get_tag(f"tag-{i}")
                        _ = idx.get_pages_for_tag(f"tag-{i}")
                        read_count[0] += 1
            except Exception as e:
                errors.append(f"Reader: {e}")

        def writer():
            """Update tags repeatedly."""
            try:
                for i in range(100):
                    idx.update_tag(f"tag-{i % 10}", f"Tag {i}", [f"new-page-{i}.md"])
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


class TestTaxonomyIndexInvariantViolation:
    """Tests for handling invariant violations in TaxonomyIndex."""

    def test_save_clears_index_on_invariant_violation(self, cache_dir):
        """save_to_disk clears index if invariants are violated instead of saving corrupted data."""
        idx = TaxonomyIndex(cache_dir / "taxonomy.json")

        # Add valid data
        idx.update_tag("python", "Python", ["post1.md", "post2.md"])

        # Manually corrupt the internal state (simulate invariant violation)
        # Add an entry to tags that references pages not in _page_to_tags
        idx.tags["orphan-tag"] = TagEntry(
            tag_slug="orphan-tag",
            tag_name="Orphan",
            page_paths=["nonexistent-page.md"],  # Not in _page_to_tags
            updated_at="2025-10-16T12:00:00",
            is_valid=True,
        )

        # save_to_disk should detect corruption and clear the index
        idx.save_to_disk()

        # Index should be cleared
        assert len(idx.tags) == 0
        assert len(idx._page_to_tags) == 0

        # On next load, it should be empty (no corrupted data saved)
        idx2 = TaxonomyIndex(cache_dir / "taxonomy.json")
        assert len(idx2.tags) == 0
