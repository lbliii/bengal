"""
Test cache migration from old location to new location.
"""

import json

from bengal.core.site import Site
from bengal.orchestration.incremental import IncrementalOrchestrator


class TestCacheMigration:
    """Test automatic cache migration from public/ to .bengal/"""

    def test_old_cache_migrated_to_new_location(self, tmp_path):
        """Test that cache at old location is migrated automatically."""
        # Create site structure
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        # Create old cache
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        old_cache = public_dir / ".bengal-cache.json"
        old_cache_data = {
            "file_hashes": {"content/index.md": "abc123"},
            "dependencies": {},
            "last_build": "2025-10-13T10:00:00",
        }
        old_cache.write_text(json.dumps(old_cache_data))

        # Create site and initialize incremental
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir

        incremental = IncrementalOrchestrator(site)
        cache, tracker = incremental.initialize(enabled=True)

        # Verify migration occurred
        new_cache_path = tmp_path / ".bengal" / "cache.json"
        assert new_cache_path.exists(), "New cache should be created"
        assert len(cache.file_hashes) == 1, "Cache data should be migrated"
        assert cache.file_hashes["content/index.md"] == "abc123"

    def test_migration_preserves_cache_data(self, tmp_path):
        """Test that all cache fields are preserved during migration."""
        # Setup
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        public_dir = tmp_path / "public"
        public_dir.mkdir()

        # Create comprehensive old cache
        old_cache = public_dir / ".bengal-cache.json"
        old_cache_data = {
            "file_hashes": {"content/index.md": "hash1", "content/about.md": "hash2"},
            "dependencies": {"content/index.md": ["templates/base.html"]},
            "page_tags": {"content/index.md": ["tag1", "tag2"]},
            "tag_to_pages": {"tag1": ["content/index.md"]},
            "known_tags": ["tag1", "tag2"],
            "parsed_content": {
                "content/index.md": {"html": "<p>Content</p>", "toc": "<ul>...</ul>"}
            },
            "last_build": "2025-10-13T10:00:00",
        }
        old_cache.write_text(json.dumps(old_cache_data))

        # Migrate
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir
        incremental = IncrementalOrchestrator(site)
        cache, tracker = incremental.initialize(enabled=True)

        # Verify all fields preserved
        assert len(cache.file_hashes) == 2
        assert "content/index.md" in cache.dependencies
        assert cache.page_tags["content/index.md"] == {"tag1", "tag2"}
        assert "tag1" in cache.known_tags
        assert "content/index.md" in cache.parsed_content

    def test_new_cache_not_overwritten_by_old(self, tmp_path):
        """Test that existing new cache is not overwritten by old cache."""
        # Create both caches
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        public_dir = tmp_path / "public"
        public_dir.mkdir()

        # Old cache (stale data)
        old_cache = public_dir / ".bengal-cache.json"
        old_cache.write_text(
            json.dumps({"file_hashes": {"old": "data"}, "last_build": "2025-10-01T10:00:00"})
        )

        # New cache (current data)
        new_cache_dir = tmp_path / ".bengal"
        new_cache_dir.mkdir()
        new_cache = new_cache_dir / "cache.json"
        new_cache.write_text(
            json.dumps({"file_hashes": {"new": "data"}, "last_build": "2025-10-13T10:00:00"})
        )

        # Initialize
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir
        incremental = IncrementalOrchestrator(site)
        cache, tracker = incremental.initialize(enabled=True)

        # Verify new cache is used
        assert "new" in cache.file_hashes
        assert "old" not in cache.file_hashes

    def test_migration_failure_falls_back_to_fresh_cache(self, tmp_path):
        """Test graceful fallback if migration fails."""
        # Create corrupted old cache
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        public_dir = tmp_path / "public"
        public_dir.mkdir()

        old_cache = public_dir / ".bengal-cache.json"
        old_cache.write_text("invalid json{{{")

        # Should not crash
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir
        incremental = IncrementalOrchestrator(site)
        cache, tracker = incremental.initialize(enabled=True)

        # Should have fresh cache
        assert len(cache.file_hashes) == 0

    def test_cache_survives_clean_operation(self, tmp_path):
        """Test that cache persists after site.clean()."""
        # Create site with cache
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        public_dir = tmp_path / "public"
        public_dir.mkdir()
        (public_dir / "index.html").write_text("<html>test</html>")

        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text(json.dumps({"file_hashes": {"test": "data"}}))

        # Create site and clean
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir
        site.clean()

        # Verify cache still exists
        assert cache_file.exists(), "Cache should survive clean"
        assert not (public_dir / "index.html").exists(), "Output file should be removed"

    def test_no_migration_on_fresh_install(self, tmp_path):
        """Test that fresh install creates cache at new location directly."""
        # Create site structure (no old cache)
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        public_dir = tmp_path / "public"
        public_dir.mkdir()

        # Initialize
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir
        incremental = IncrementalOrchestrator(site)
        cache, tracker = incremental.initialize(enabled=True)

        # Verify new cache location used
        new_cache_path = tmp_path / ".bengal" / "cache.json"
        assert not new_cache_path.exists(), "Cache not created until save"

        # Cache directory should exist
        assert (tmp_path / ".bengal").exists(), "Cache directory should be created"

    def test_migration_actually_occurs(self, tmp_path):
        """Test that migration actually occurs (functional test)."""
        # Create old cache with data
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        public_dir = tmp_path / "public"
        public_dir.mkdir()

        old_cache = public_dir / ".bengal-cache.json"
        cache_data = {"file_hashes": {"test": "abc123"}}
        old_cache.write_text(json.dumps(cache_data))

        # Verify old cache exists
        assert old_cache.exists()

        # Migrate
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir
        incremental = IncrementalOrchestrator(site)
        cache, tracker = incremental.initialize(enabled=True)

        # Verify new cache was created with migrated data
        new_cache_path = tmp_path / ".bengal" / "cache.json"
        assert new_cache_path.exists(), "New cache should exist after migration"
        assert cache.file_hashes["test"] == "abc123", "Cache data should be migrated"
