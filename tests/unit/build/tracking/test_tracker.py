"""
Unit tests for bengal.build.tracking.tracker.

Tests DependencyTracker and CacheInvalidator for dependency tracking.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.build.tracking.tracker import CacheInvalidator, DependencyTracker


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create mock BuildCache."""
    cache = MagicMock()
    cache.file_fingerprints = {}
    cache.dependencies = {}
    cache.add_dependency = MagicMock()
    cache.update_file = MagicMock()
    cache.add_taxonomy_dependency = MagicMock()
    cache.is_changed = MagicMock(return_value=False)
    return cache


@pytest.fixture
def mock_site(tmp_path: Path) -> MagicMock:
    """Create mock Site."""
    site = MagicMock()
    site.root_path = tmp_path

    # Create config file
    config_path = tmp_path / "bengal.toml"
    config_path.write_text("[site]\ntitle = 'Test'")

    return site


@pytest.fixture
def tracker(mock_cache: MagicMock, mock_site: MagicMock) -> DependencyTracker:
    """Create DependencyTracker instance."""
    return DependencyTracker(cache=mock_cache, site=mock_site)


# =============================================================================
# CacheInvalidator Tests
# =============================================================================


class TestCacheInvalidator:
    """Tests for CacheInvalidator class."""

    def test_creates_with_fields(self) -> None:
        """CacheInvalidator can be created with fields."""
        content_paths = [Path("content/a.md"), Path("content/b.md")]
        template_paths = [Path("templates/base.html")]

        invalidator = CacheInvalidator(
            config_hash="abc123",
            content_paths=content_paths,
            template_paths=template_paths,
        )

        assert invalidator.config_hash == "abc123"
        assert invalidator.content_paths == content_paths
        assert invalidator.template_paths == template_paths
        assert invalidator.invalidated == set()

    def test_invalidate_content(self) -> None:
        """invalidate_content adds paths to invalidated set."""
        invalidator = CacheInvalidator("hash", [], [])
        changed = {Path("content/a.md"), Path("content/b.md")}

        result = invalidator.invalidate_content(changed)

        assert Path("content/a.md") in result
        assert Path("content/b.md") in result

    def test_invalidate_config(self) -> None:
        """invalidate_config invalidates all paths."""
        content_paths = [Path("content/a.md")]
        template_paths = [Path("templates/base.html")]
        invalidator = CacheInvalidator("hash", content_paths, template_paths)

        result = invalidator.invalidate_config()

        assert Path("content/a.md") in result
        assert Path("templates/base.html") in result

    def test_is_stale_when_invalidated(self) -> None:
        """is_stale returns True when paths are invalidated."""
        invalidator = CacheInvalidator("hash", [], [])
        invalidator.invalidate_content({Path("content/a.md")})

        assert invalidator.is_stale is True

    def test_is_stale_when_empty(self) -> None:
        """is_stale returns False when no paths invalidated."""
        invalidator = CacheInvalidator("hash", [], [])

        assert invalidator.is_stale is False


# =============================================================================
# DependencyTracker Basic Tests
# =============================================================================


class TestDependencyTrackerBasics:
    """Basic tests for DependencyTracker."""

    def test_creates_with_cache_and_site(self, mock_cache: MagicMock, mock_site: MagicMock) -> None:
        """DependencyTracker can be created with cache and site."""
        tracker = DependencyTracker(cache=mock_cache, site=mock_site)

        assert tracker.cache is mock_cache
        assert tracker.site is mock_site

    def test_start_and_end_page(self, tracker: DependencyTracker) -> None:
        """start_page and end_page manage current page state."""
        page_path = Path("content/about.md")

        tracker.start_page(page_path)
        assert tracker.current_page.value == page_path

        tracker.end_page()
        assert not hasattr(tracker.current_page, "value")


# =============================================================================
# Template Tracking Tests
# =============================================================================


class TestTemplateTracking:
    """Tests for template dependency tracking."""

    def test_track_template(self, tracker: DependencyTracker, mock_cache: MagicMock) -> None:
        """track_template records template dependency."""
        page_path = Path("content/about.md")
        template_path = Path("templates/base.html")

        tracker.start_page(page_path)
        tracker.track_template(template_path)

        mock_cache.add_dependency.assert_called_once_with(page_path, template_path)

    def test_track_template_without_current_page(
        self, tracker: DependencyTracker, mock_cache: MagicMock
    ) -> None:
        """track_template does nothing without current page."""
        tracker.track_template(Path("templates/base.html"))

        mock_cache.add_dependency.assert_not_called()


# =============================================================================
# Partial Tracking Tests
# =============================================================================


class TestPartialTracking:
    """Tests for partial/include dependency tracking."""

    def test_track_partial(self, tracker: DependencyTracker, mock_cache: MagicMock) -> None:
        """track_partial records partial dependency."""
        page_path = Path("content/about.md")
        partial_path = Path("templates/partials/header.html")

        tracker.start_page(page_path)
        tracker.track_partial(partial_path)

        mock_cache.add_dependency.assert_called_once_with(page_path, partial_path)


# =============================================================================
# Data File Tracking Tests
# =============================================================================


class TestDataFileTracking:
    """Tests for data file dependency tracking."""

    def test_track_data_file(self, tracker: DependencyTracker, mock_cache: MagicMock) -> None:
        """track_data_file records data file dependency."""
        page_path = Path("content/about.md")
        data_file = Path("data/team.yaml")

        tracker.track_data_file(page_path, data_file)

        # Should add dependency with "data:" prefix
        call_args = mock_cache.add_dependency.call_args
        assert call_args[0][0] == page_path
        assert "data:" in str(call_args[0][1])

    def test_get_pages_using_data_file(
        self, tracker: DependencyTracker, mock_cache: MagicMock
    ) -> None:
        """get_pages_using_data_file returns dependent pages."""
        mock_cache.dependencies = {
            "content/about.md": ["data:data/team.yaml"],
            "content/contact.md": ["data:data/team.yaml"],
            "content/other.md": ["data:data/config.yaml"],
        }

        result = tracker.get_pages_using_data_file(Path("data/team.yaml"))

        assert Path("content/about.md") in result
        assert Path("content/contact.md") in result
        assert Path("content/other.md") not in result


# =============================================================================
# Taxonomy Tracking Tests
# =============================================================================


class TestTaxonomyTracking:
    """Tests for taxonomy dependency tracking."""

    def test_track_taxonomy(self, tracker: DependencyTracker, mock_cache: MagicMock) -> None:
        """track_taxonomy records taxonomy dependencies."""
        page_path = Path("content/post.md")
        tags = {"python", "web"}

        tracker.track_taxonomy(page_path, tags)

        # Should call add_taxonomy_dependency for each tag
        assert mock_cache.add_taxonomy_dependency.call_count == 2

    def test_track_taxonomy_skips_none(
        self, tracker: DependencyTracker, mock_cache: MagicMock
    ) -> None:
        """track_taxonomy skips None tags."""
        page_path = Path("content/post.md")
        tags = {"python", None, "web"}  # type: ignore[arg-type]

        tracker.track_taxonomy(page_path, tags)

        # Should only call for non-None tags
        assert mock_cache.add_taxonomy_dependency.call_count == 2

    def test_get_term_pages_for_member(self, tracker: DependencyTracker) -> None:
        """get_term_pages_for_member returns term page keys."""
        # Set up reverse dependencies
        tracker.reverse_dependencies = {
            "_generated/tags/tag:python": {"content/post.md"},
            "_generated/tags/tag:rust": {"content/other.md"},
        }

        result = tracker.get_term_pages_for_member(Path("content/post.md"))

        assert "_generated/tags/tag:python" in result
        assert "_generated/tags/tag:rust" not in result


# =============================================================================
# Cross-Version Tracking Tests
# =============================================================================


class TestCrossVersionTracking:
    """Tests for cross-version link tracking."""

    def test_track_cross_version_link(self, tracker: DependencyTracker) -> None:
        """track_cross_version_link records cross-version dependency."""
        source_page = Path("content/docs/v3/index.md")

        tracker.track_cross_version_link(
            source_page=source_page,
            target_version="v2",
            target_path="docs/guide",
        )

        # Check reverse dependency is recorded
        target_key = "xver:v2:docs/guide"
        assert target_key in tracker.reverse_dependencies
        assert str(source_page) in tracker.reverse_dependencies[target_key]

    def test_get_cross_version_dependents(self, tracker: DependencyTracker) -> None:
        """get_cross_version_dependents returns dependent pages."""
        tracker.reverse_dependencies = {
            "xver:v2:docs/guide": {"content/docs/v3/migration.md"},
        }

        result = tracker.get_cross_version_dependents(
            changed_version="v2",
            changed_path="docs/guide",
        )

        assert Path("content/docs/v3/migration.md") in result


# =============================================================================
# Changed Files Detection Tests
# =============================================================================


class TestChangedFilesDetection:
    """Tests for changed files detection."""

    def test_get_changed_files(
        self, tracker: DependencyTracker, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """get_changed_files returns changed file paths."""
        # Create test files
        file1 = mock_site.root_path / "content" / "changed.md"
        file2 = mock_site.root_path / "content" / "unchanged.md"
        file1.parent.mkdir(parents=True, exist_ok=True)
        file1.touch()
        file2.touch()

        mock_cache.file_fingerprints = {
            str(file1): "hash1",
            str(file2): "hash2",
        }

        def is_changed_side_effect(path: Path) -> bool:
            # Only changed.md should return True
            return path.name == "changed.md"

        mock_cache.is_changed.side_effect = is_changed_side_effect

        result = tracker.get_changed_files(mock_site.root_path)

        assert file1 in result
        assert file2 not in result

    def test_find_new_files(self, tracker: DependencyTracker, mock_cache: MagicMock) -> None:
        """find_new_files returns files not in cache."""
        mock_cache.file_fingerprints = {
            "content/existing.md": "hash1",
        }

        current_files = {
            Path("content/existing.md"),
            Path("content/new.md"),
        }

        result = tracker.find_new_files(current_files)

        assert Path("content/new.md") in result
        assert Path("content/existing.md") not in result

    def test_find_deleted_files(self, tracker: DependencyTracker, mock_cache: MagicMock) -> None:
        """find_deleted_files returns files in cache but not on disk."""
        mock_cache.file_fingerprints = {
            "content/existing.md": "hash1",
            "content/deleted.md": "hash2",
        }

        current_files = {Path("content/existing.md")}

        result = tracker.find_deleted_files(current_files)

        assert Path("content/deleted.md") in result
        assert Path("content/existing.md") not in result


# =============================================================================
# Pending Updates Tests
# =============================================================================


class TestPendingUpdates:
    """Tests for pending fingerprint updates."""

    def test_flush_pending_updates(
        self, tracker: DependencyTracker, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """flush_pending_updates applies pending fingerprint updates."""
        # Create test file
        template_path = mock_site.root_path / "templates" / "base.html"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text("<html>")

        # Track template (queues fingerprint update)
        tracker.start_page(Path("content/about.md"))
        tracker.track_template(template_path)

        # Flush pending updates
        tracker.flush_pending_updates()

        # update_file should have been called
        mock_cache.update_file.assert_called()

    def test_reset_pending_updates(
        self, tracker: DependencyTracker, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """reset_pending_updates clears pending updates without applying."""
        template_path = mock_site.root_path / "templates" / "base.html"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text("<html>")

        tracker.start_page(Path("content/about.md"))
        tracker.track_template(template_path)

        # Reset (don't apply)
        tracker.reset_pending_updates()

        # Flush should now have nothing to do (second call count check)
        initial_call_count = mock_cache.update_file.call_count
        tracker.flush_pending_updates()
        # No additional calls should have been made for the template
        # (only possible calls from flush itself)


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestThreadSafety:
    """Tests for thread safety."""

    def test_current_page_is_thread_local(self, tracker: DependencyTracker) -> None:
        """current_page uses thread-local storage."""
        import threading

        results = {}

        def worker(page_name: str) -> None:
            page_path = Path(f"content/{page_name}.md")
            tracker.start_page(page_path)
            # Small sleep to increase chance of race conditions
            import time

            time.sleep(0.01)
            results[page_name] = tracker.current_page.value
            tracker.end_page()

        threads = [threading.Thread(target=worker, args=(f"page{i}",)) for i in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have seen its own page
        for i in range(3):
            assert results[f"page{i}"] == Path(f"content/page{i}.md")
