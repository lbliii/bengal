"""
Tests for cache invalidation fixes (RFC: rfc-cache-invalidation-fixes).

These tests verify the fixes for false cache invalidations that were causing
incremental builds to trigger unnecessary full rebuilds.

Fixes covered:
- Fix 1: Config hash stability (excludes internal keys)
- Fix 3: Deferred fingerprint updates (queued until post-build)
- Fix 4: Don't update unchanged template fingerprints
- Fix 5: Content hash for dependency validation

See: plan/drafted/rfc-cache-invalidation-fixes.md
"""

from __future__ import annotations

import time
from pathlib import Path

from bengal.cache.build_cache import BuildCache
from bengal.cache.dependency_tracker import DependencyTracker
from bengal.config.hash import compute_config_hash


class TestDeferredFingerprintUpdates:
    """Tests for Fix 3: Deferred fingerprint updates."""

    def test_updates_not_applied_during_build(self, tmp_path: Path) -> None:
        """Fingerprint updates are queued, not applied immediately."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        test_file = tmp_path / "test.html"
        test_file.write_text("content")

        # Queue update via internal method
        tracker._update_dependency_file_once(test_file)

        # Fingerprint NOT updated yet (queued for post-build)
        assert str(test_file) not in cache.file_fingerprints

        # Verify it's in the pending queue
        assert test_file in tracker._pending_fingerprint_updates

    def test_updates_applied_on_flush(self, tmp_path: Path) -> None:
        """Fingerprint updates applied after flush."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        test_file = tmp_path / "test.html"
        test_file.write_text("content")

        # Queue update
        tracker._update_dependency_file_once(test_file)

        # Flush pending updates
        tracker.flush_pending_updates()

        # Fingerprint NOW updated
        assert str(test_file) in cache.file_fingerprints

    def test_flush_clears_pending_queue(self, tmp_path: Path) -> None:
        """Flush clears the pending queue."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        test_file = tmp_path / "test.html"
        test_file.write_text("content")

        tracker._update_dependency_file_once(test_file)
        assert len(tracker._pending_fingerprint_updates) == 1

        tracker.flush_pending_updates()
        assert len(tracker._pending_fingerprint_updates) == 0

    def test_reset_clears_pending_without_applying(self, tmp_path: Path) -> None:
        """Reset clears pending updates without applying them."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        test_file = tmp_path / "test.html"
        test_file.write_text("content")

        tracker._update_dependency_file_once(test_file)
        tracker.reset_pending_updates()

        # Pending queue cleared
        assert len(tracker._pending_fingerprint_updates) == 0
        # Fingerprint NOT updated (was reset, not flushed)
        assert str(test_file) not in cache.file_fingerprints

    def test_duplicate_updates_only_queued_once(self, tmp_path: Path) -> None:
        """Same file queued multiple times only appears once."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        test_file = tmp_path / "test.html"
        test_file.write_text("content")

        # Queue same file multiple times
        tracker._update_dependency_file_once(test_file)
        tracker._update_dependency_file_once(test_file)
        tracker._update_dependency_file_once(test_file)

        # Only one entry in pending queue
        assert len(tracker._pending_fingerprint_updates) == 1

    def test_missing_files_skipped_on_flush(self, tmp_path: Path) -> None:
        """Missing files are skipped during flush (no error)."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        test_file = tmp_path / "test.html"
        test_file.write_text("content")

        # Queue update then delete file
        tracker._update_dependency_file_once(test_file)
        test_file.unlink()

        # Flush should not raise
        tracker.flush_pending_updates()

        # File not in fingerprints (was deleted)
        assert str(test_file) not in cache.file_fingerprints


class TestUnchangedTemplateFingerprintBehavior:
    """Tests for Fix 4: Don't update unchanged templates."""

    def test_unchanged_template_fingerprint_preserved(self, tmp_path: Path) -> None:
        """Unchanged templates keep original fingerprint."""
        template = tmp_path / "base.html"
        template.write_text("original content")

        cache = BuildCache()
        cache.update_file(template)
        original_fp = cache.file_fingerprints[str(template)].copy()

        # Touch file (mtime changes) but don't modify content
        time.sleep(0.01)
        template.touch()

        # Check template - should report "unchanged" by content hash
        # (is_changed does hash comparison when mtime differs)
        assert not cache.is_changed(template)

        # Fingerprint mtime updated in-place during is_changed() for fast path next time
        # But the hash should remain the same
        current_fp = cache.file_fingerprints[str(template)]
        assert current_fp.get("hash") == original_fp.get("hash")

    def test_changed_template_detected(self, tmp_path: Path) -> None:
        """Changed templates are properly detected."""
        template = tmp_path / "base.html"
        template.write_text("original content")

        cache = BuildCache()
        cache.update_file(template)

        # Actually modify the file
        time.sleep(0.01)
        template.write_text("modified content")

        # Should be detected as changed
        assert cache.is_changed(template)


class TestContentHashDependencyValidation:
    """Tests for Fix 5: Content hash validation."""

    def test_touched_but_unchanged_dependency_is_cache_hit(self, tmp_path: Path) -> None:
        """File touch without content change should not invalidate cache."""
        dep = tmp_path / "partial.html"
        dep.write_text("unchanged content")

        cache = BuildCache()
        cache.update_file(dep)

        # Touch file (mtime changes, content same)
        time.sleep(0.01)
        dep.touch()

        # is_changed should return False (content hash matches)
        assert not cache.is_changed(dep)

    def test_content_change_invalidates_cache(self, tmp_path: Path) -> None:
        """Actual content change should invalidate cache."""
        dep = tmp_path / "partial.html"
        dep.write_text("original content")

        cache = BuildCache()
        cache.update_file(dep)

        # Change content
        time.sleep(0.01)
        dep.write_text("modified content")

        # is_changed should return True (content hash differs)
        assert cache.is_changed(dep)


class TestConfigHashStability:
    """Tests for Fix 1: Config hash stability."""

    def test_internal_keys_excluded_from_hash(self) -> None:
        """Internal keys (starting with _) are excluded from hash."""
        config1 = {"title": "My Site", "baseurl": "/"}
        config2 = {"title": "My Site", "baseurl": "/", "_paths": object()}
        config3 = {"title": "My Site", "baseurl": "/", "_config_hash": "abc123"}

        hash1 = compute_config_hash(config1)
        hash2 = compute_config_hash(config2)
        hash3 = compute_config_hash(config3)

        # All hashes should be identical (internal keys excluded)
        assert hash1 == hash2
        assert hash1 == hash3

    def test_nested_internal_keys_excluded(self) -> None:
        """Internal keys in nested dicts are also excluded."""
        config1 = {"site": {"title": "Test"}}
        config2 = {"site": {"title": "Test", "_cache": object()}}

        hash1 = compute_config_hash(config1)
        hash2 = compute_config_hash(config2)

        assert hash1 == hash2

    def test_config_hash_deterministic(self) -> None:
        """Config hash is deterministic regardless of key order."""
        config1 = {"title": "My Site", "baseurl": "/", "theme": "default"}
        config2 = {"theme": "default", "baseurl": "/", "title": "My Site"}

        hash1 = compute_config_hash(config1)
        hash2 = compute_config_hash(config2)

        assert hash1 == hash2

    def test_config_hash_changes_on_value_change(self) -> None:
        """Config hash changes when actual values change."""
        config1 = {"title": "My Site", "baseurl": "/"}
        config2 = {"title": "My Site", "baseurl": "/blog"}

        hash1 = compute_config_hash(config1)
        hash2 = compute_config_hash(config2)

        assert hash1 != hash2


class TestFileTrackingDiagnostics:
    """Tests for Phase 0: Diagnostic instrumentation."""

    def test_is_changed_returns_true_for_new_file(self, tmp_path: Path) -> None:
        """New files (not in cache) return True from is_changed."""
        cache = BuildCache()

        new_file = tmp_path / "new.md"
        new_file.write_text("content")

        assert cache.is_changed(new_file)

    def test_is_changed_returns_true_for_deleted_file(self, tmp_path: Path) -> None:
        """Deleted files return True from is_changed."""
        cache = BuildCache()

        test_file = tmp_path / "test.md"
        test_file.write_text("content")
        cache.update_file(test_file)

        # Delete the file
        test_file.unlink()

        assert cache.is_changed(test_file)

    def test_is_changed_returns_false_for_unchanged_file(self, tmp_path: Path) -> None:
        """Unchanged files return False from is_changed."""
        cache = BuildCache()

        test_file = tmp_path / "test.md"
        test_file.write_text("content")
        cache.update_file(test_file)

        # File not modified
        assert not cache.is_changed(test_file)

    def test_is_changed_returns_true_for_modified_file(self, tmp_path: Path) -> None:
        """Modified files return True from is_changed."""
        cache = BuildCache()

        test_file = tmp_path / "test.md"
        test_file.write_text("original content")
        cache.update_file(test_file)

        # Modify file
        time.sleep(0.01)
        test_file.write_text("modified content")

        assert cache.is_changed(test_file)
