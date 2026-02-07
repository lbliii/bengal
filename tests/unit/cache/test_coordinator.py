"""
Tests for CacheCoordinator.

RFC: rfc-cache-invalidation-architecture
Tests unified page-level cache invalidation through CacheCoordinator.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.orchestration.build.coordinator import (
    CacheCoordinator,
    InvalidationEvent,
    PageInvalidationReason,
    _MAX_EVENTS,
)


@pytest.fixture
def mock_cache():
    """Create a mock BuildCache."""
    cache = MagicMock()
    cache.invalidate_rendered_output = MagicMock(return_value=True)
    cache.invalidate_parsed_content = MagicMock(return_value=True)
    cache.invalidate_fingerprint = MagicMock(return_value=True)
    cache.get_affected_pages = MagicMock(return_value=set())
    return cache


@pytest.fixture
def mock_tracker():
    """Create a mock DependencyTracker."""
    tracker = MagicMock()
    tracker.get_pages_using_data_file = MagicMock(return_value=set())
    return tracker


@pytest.fixture
def mock_site():
    """Create a mock Site."""
    site = MagicMock()
    site.pages = []
    return site


@pytest.fixture
def coordinator(mock_cache, mock_tracker, mock_site):
    """Create a CacheCoordinator with mocks."""
    return CacheCoordinator(mock_cache, mock_tracker, mock_site)


class TestPageInvalidationReason:
    """Tests for PageInvalidationReason enum."""

    def test_all_reasons_defined(self):
        """All expected reasons are defined."""
        expected = [
            "CONTENT_CHANGED",
            "DATA_FILE_CHANGED",
            "TEMPLATE_CHANGED",
            "TAXONOMY_CASCADE",
            "ASSET_CHANGED",
            "CONFIG_CHANGED",
            "MANUAL",
            "FULL_BUILD",
            "OUTPUT_MISSING",
        ]
        for reason in expected:
            assert hasattr(PageInvalidationReason, reason)

    def test_reasons_are_unique(self):
        """All reasons have unique values."""
        values = [r.value for r in PageInvalidationReason]
        assert len(values) == len(set(values))


class TestInvalidationEvent:
    """Tests for InvalidationEvent dataclass."""

    def test_event_creation(self):
        """Can create an event with required fields."""
        event = InvalidationEvent(
            page_path=Path("content/about.md"),
            reason=PageInvalidationReason.CONTENT_CHANGED,
            trigger="file_changed",
        )

        assert event.page_path == Path("content/about.md")
        assert event.reason == PageInvalidationReason.CONTENT_CHANGED
        assert event.trigger == "file_changed"
        assert event.caches_cleared == []

    def test_event_with_caches_cleared(self):
        """Can create an event with caches_cleared."""
        event = InvalidationEvent(
            page_path=Path("content/about.md"),
            reason=PageInvalidationReason.CONTENT_CHANGED,
            trigger="file_changed",
            caches_cleared=["rendered_output", "parsed_content"],
        )

        assert event.caches_cleared == ["rendered_output", "parsed_content"]


class TestCacheCoordinator:
    """Tests for CacheCoordinator class."""

    def test_initialization(self, coordinator, mock_cache, mock_tracker, mock_site):
        """Coordinator initializes correctly."""
        assert coordinator.cache is mock_cache
        assert coordinator.tracker is mock_tracker
        assert coordinator.site is mock_site
        assert coordinator._events == []

    def test_invalidate_page_clears_all_layers(self, coordinator, mock_cache):
        """invalidate_page clears rendered_output, parsed_content, fingerprint."""
        page_path = Path("content/about.md")

        event = coordinator.invalidate_page(
            page_path,
            PageInvalidationReason.CONTENT_CHANGED,
            trigger="test",
        )

        # Verify all cache layers were called
        mock_cache.invalidate_rendered_output.assert_called_once_with(page_path)
        mock_cache.invalidate_parsed_content.assert_called_once_with(page_path)
        mock_cache.invalidate_fingerprint.assert_called_once_with(page_path)

        # Verify event
        assert event.page_path == page_path
        assert event.reason == PageInvalidationReason.CONTENT_CHANGED
        assert event.trigger == "test"
        assert "rendered_output" in event.caches_cleared
        assert "parsed_content" in event.caches_cleared
        assert "fingerprint" in event.caches_cleared

    def test_invalidate_page_records_event(self, coordinator, mock_cache):
        """invalidate_page records event in events list."""
        page_path = Path("content/about.md")

        coordinator.invalidate_page(
            page_path,
            PageInvalidationReason.CONTENT_CHANGED,
            trigger="test",
        )

        assert len(coordinator.events) == 1
        assert coordinator.events[0].page_path == page_path

    def test_invalidate_page_handles_missing_caches(self, coordinator, mock_cache):
        """invalidate_page handles caches that return False (not present)."""
        mock_cache.invalidate_rendered_output.return_value = True
        mock_cache.invalidate_parsed_content.return_value = False
        mock_cache.invalidate_fingerprint.return_value = False

        page_path = Path("content/about.md")
        event = coordinator.invalidate_page(
            page_path,
            PageInvalidationReason.CONTENT_CHANGED,
            trigger="test",
        )

        assert event.caches_cleared == ["rendered_output"]

    def test_invalidate_for_data_file(self, coordinator, mock_cache, mock_tracker):
        """invalidate_for_data_file cascades to dependent pages."""
        data_file = Path("data/team.yaml")
        page1 = Path("content/about.md")
        page2 = Path("content/team.md")
        mock_tracker.get_pages_using_data_file.return_value = {page1, page2}

        events = coordinator.invalidate_for_data_file(data_file)

        assert len(events) == 2
        assert all(e.reason == PageInvalidationReason.DATA_FILE_CHANGED for e in events)
        assert all(e.trigger == str(data_file) for e in events)

    def test_invalidate_for_template(self, coordinator, mock_cache):
        """invalidate_for_template cascades to dependent pages."""
        template_path = Path("templates/base.html")
        page1 = "content/about.md"
        page2 = "content/team.md"
        mock_cache.get_affected_pages.return_value = {page1, page2}

        events = coordinator.invalidate_for_template(template_path)

        assert len(events) == 2
        assert all(e.reason == PageInvalidationReason.TEMPLATE_CHANGED for e in events)
        assert all(e.trigger == str(template_path) for e in events)

    def test_invalidate_taxonomy_cascade(self, coordinator, mock_cache):
        """invalidate_taxonomy_cascade invalidates term pages."""
        member_page = Path("content/blog/post.md")
        term_pages = {
            Path(".bengal/generated/tags/python/index.md"),
            Path(".bengal/generated/tags/tutorial/index.md"),
        }

        events = coordinator.invalidate_taxonomy_cascade(member_page, term_pages)

        assert len(events) == 2
        assert all(e.reason == PageInvalidationReason.TAXONOMY_CASCADE for e in events)
        assert all(e.trigger == str(member_page) for e in events)

    def test_invalidate_all(self, coordinator, mock_site, mock_cache):
        """invalidate_all invalidates all pages."""
        page1 = MagicMock()
        page1.source_path = Path("content/about.md")
        page2 = MagicMock()
        page2.source_path = Path("content/team.md")
        mock_site.pages = [page1, page2]

        count = coordinator.invalidate_all()

        assert count == 2
        assert len(coordinator.events) == 2
        assert all(e.reason == PageInvalidationReason.FULL_BUILD for e in coordinator.events)

    def test_events_property_returns_copy(self, coordinator, mock_cache):
        """events property returns a copy for thread safety."""
        coordinator.invalidate_page(
            Path("content/about.md"),
            PageInvalidationReason.CONTENT_CHANGED,
            trigger="test",
        )

        events1 = coordinator.events
        events2 = coordinator.events

        assert events1 is not events2
        assert events1 == events2

    def test_get_invalidation_summary(self, coordinator, mock_cache):
        """get_invalidation_summary groups events by reason."""
        coordinator.invalidate_page(
            Path("content/about.md"),
            PageInvalidationReason.CONTENT_CHANGED,
            trigger="test1",
        )
        coordinator.invalidate_page(
            Path("content/team.md"),
            PageInvalidationReason.CONTENT_CHANGED,
            trigger="test2",
        )
        coordinator.invalidate_page(
            Path("content/data.md"),
            PageInvalidationReason.DATA_FILE_CHANGED,
            trigger="data.yaml",
        )

        summary = coordinator.get_invalidation_summary()

        assert "CONTENT_CHANGED" in summary
        assert len(summary["CONTENT_CHANGED"]) == 2
        assert "DATA_FILE_CHANGED" in summary
        assert len(summary["DATA_FILE_CHANGED"]) == 1

    def test_clear_events(self, coordinator, mock_cache):
        """clear_events removes all events."""
        coordinator.invalidate_page(
            Path("content/about.md"),
            PageInvalidationReason.CONTENT_CHANGED,
            trigger="test",
        )
        assert len(coordinator.events) == 1

        coordinator.clear_events()

        assert len(coordinator.events) == 0

    def test_get_stats(self, coordinator, mock_cache):
        """get_stats returns invalidation statistics."""
        coordinator.invalidate_page(
            Path("content/about.md"),
            PageInvalidationReason.CONTENT_CHANGED,
            trigger="test1",
        )
        coordinator.invalidate_page(
            Path("content/team.md"),
            PageInvalidationReason.CONTENT_CHANGED,
            trigger="test2",
        )

        stats = coordinator.get_stats()

        assert stats["total_invalidations"] == 2
        assert stats["CONTENT_CHANGED"] == 2


class TestCacheCoordinatorThreadSafety:
    """Tests for thread safety of CacheCoordinator."""

    def test_concurrent_invalidation(self, mock_cache, mock_tracker, mock_site):
        """Events are logged safely under concurrent invalidation."""
        coordinator = CacheCoordinator(mock_cache, mock_tracker, mock_site)
        errors = []

        def invalidate_pages(start_idx: int):
            try:
                for i in range(100):
                    coordinator.invalidate_page(
                        Path(f"page_{start_idx}_{i}.md"),
                        PageInvalidationReason.CONTENT_CHANGED,
                        trigger="test",
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=invalidate_pages, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread safety violation: {errors}"
        assert len(coordinator.events) == 400


class TestCacheCoordinatorEventBounds:
    """Tests for event log bounds."""

    def test_events_trimmed_at_max(self, mock_cache, mock_tracker, mock_site):
        """Event log is trimmed when exceeding _MAX_EVENTS."""
        coordinator = CacheCoordinator(mock_cache, mock_tracker, mock_site)

        # Add more than _MAX_EVENTS
        for i in range(_MAX_EVENTS + 100):
            coordinator.invalidate_page(
                Path(f"page_{i}.md"),
                PageInvalidationReason.CONTENT_CHANGED,
                trigger="test",
            )

        # Should be trimmed to _MAX_EVENTS
        assert len(coordinator.events) == _MAX_EVENTS

        # Should keep the most recent events
        last_event = coordinator.events[-1]
        assert last_event.page_path == Path(f"page_{_MAX_EVENTS + 99}.md")
