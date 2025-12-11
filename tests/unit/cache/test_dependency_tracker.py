"""
Unit tests for DependencyTracker.
"""

from bengal.cache.build_cache import BuildCache
from bengal.cache.dependency_tracker import DependencyTracker


class TestDependencyTracker:
    """Test suite for DependencyTracker."""

    def test_init(self):
        """Test creating a dependency tracker."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        assert tracker.cache is cache
        # current_page is now a threading.local object, not a simple attribute
        assert not hasattr(tracker.current_page, "value")

    def test_start_page(self, tmp_path):
        """Test starting page tracking."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        page = tmp_path / "page.md"
        page.write_text("# Page")

        tracker.start_page(page)

        # current_page is now thread-local, access via .value
        assert tracker.current_page.value == page
        # Note: File hashes are NOT updated in start_page - they are updated
        # in IncrementalOrchestrator.save_cache() AFTER successful rendering.
        # This prevents cache invalidation during the cache check phase.

    def test_end_page(self, tmp_path):
        """Test ending page tracking."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        page = tmp_path / "page.md"
        page.write_text("# Page")

        tracker.start_page(page)
        tracker.end_page()

        # After end_page(), the thread-local value should be deleted
        assert not hasattr(tracker.current_page, "value")

    def test_track_template(self, tmp_path):
        """Test tracking template dependency."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        page = tmp_path / "page.md"
        template = tmp_path / "template.html"

        page.write_text("# Page")
        template.write_text("<html></html>")

        tracker.start_page(page)
        tracker.track_template(template)
        tracker.end_page()

        # Check dependency was recorded
        assert str(page) in cache.dependencies
        assert str(template) in cache.dependencies[str(page)]
        # Check template hash was recorded
        assert str(template) in cache.file_hashes

    def test_track_partial(self, tmp_path):
        """Test tracking partial dependency."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        page = tmp_path / "page.md"
        partial = tmp_path / "partial.html"

        page.write_text("# Page")
        partial.write_text("<div>Partial</div>")

        tracker.start_page(page)
        tracker.track_partial(partial)
        tracker.end_page()

        # Check dependency was recorded
        assert str(page) in cache.dependencies
        assert str(partial) in cache.dependencies[str(page)]

    def test_track_config(self, tmp_path):
        """Test tracking config dependency."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        page = tmp_path / "page.md"
        config = tmp_path / "bengal.toml"

        page.write_text("# Page")
        config.write_text("[site]\ntitle = 'Test'")

        tracker.start_page(page)
        tracker.track_config(config)
        tracker.end_page()

        # Check dependency was recorded
        assert str(page) in cache.dependencies
        assert str(config) in cache.dependencies[str(page)]

    def test_track_asset(self, tmp_path):
        """Test tracking asset file."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        asset = tmp_path / "style.css"
        asset.write_text("body { color: red; }")

        tracker.track_asset(asset)

        # Check asset hash was recorded
        assert str(asset) in cache.file_hashes

    def test_track_taxonomy(self, tmp_path):
        """Test tracking taxonomy dependencies."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        page = tmp_path / "post.md"
        page.write_text("# Post")

        tracker.track_taxonomy(page, {"Python", "Tutorial"})

        # Check taxonomy dependencies
        assert "tag:python" in cache.taxonomy_deps
        assert "tag:tutorial" in cache.taxonomy_deps
        assert str(page) in cache.taxonomy_deps["tag:python"]
        assert str(page) in cache.taxonomy_deps["tag:tutorial"]

    def test_track_multiple_dependencies(self, tmp_path):
        """Test tracking multiple dependencies for a page."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        page = tmp_path / "page.md"
        template = tmp_path / "template.html"
        partial1 = tmp_path / "header.html"
        partial2 = tmp_path / "footer.html"

        page.write_text("# Page")
        template.write_text("<html></html>")
        partial1.write_text("<header></header>")
        partial2.write_text("<footer></footer>")

        tracker.start_page(page)
        tracker.track_template(template)
        tracker.track_partial(partial1)
        tracker.track_partial(partial2)
        tracker.end_page()

        # Check all dependencies recorded
        deps = cache.dependencies[str(page)]
        assert len(deps) == 3
        assert str(template) in deps
        assert str(partial1) in deps
        assert str(partial2) in deps

    def test_track_without_current_page(self, tmp_path):
        """Test that tracking without a current page doesn't crash."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        template = tmp_path / "template.html"
        template.write_text("<html></html>")

        # Should not crash
        tracker.track_template(template)
        tracker.track_partial(template)

        # No dependencies should be recorded
        assert len(cache.dependencies) == 0

    def test_get_changed_files(self, tmp_path):
        """Test getting changed files."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"

        file1.write_text("Content 1")
        file2.write_text("Content 2")

        # Track files
        cache.update_file(file1)
        cache.update_file(file2)

        # Modify file1
        file1.write_text("Modified content 1")

        # Get changed files
        changed = tracker.get_changed_files(tmp_path)

        assert file1 in changed
        assert file2 not in changed

    def test_find_new_files(self, tmp_path):
        """Test finding new files."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        existing = tmp_path / "existing.md"
        new_file = tmp_path / "new.md"

        existing.write_text("Existing")
        new_file.write_text("New")

        # Track only existing file
        cache.update_file(existing)

        # Find new files
        current_files = {existing, new_file}
        new_files = tracker.find_new_files(current_files)

        assert new_file in new_files
        assert existing not in new_files

    def test_find_deleted_files(self, tmp_path):
        """Test finding deleted files."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"

        file1.write_text("Content 1")
        file2.write_text("Content 2")

        # Track both files
        cache.update_file(file1)
        cache.update_file(file2)

        # Delete file2
        file2.unlink()

        # Find deleted files
        current_files = {file1}
        deleted = tracker.find_deleted_files(current_files)

        assert file2 in deleted
        assert file1 not in deleted
