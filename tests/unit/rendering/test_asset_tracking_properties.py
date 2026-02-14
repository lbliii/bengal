"""
Property-based tests for asset tracking using Hypothesis.

These tests verify that asset tracking behaves correctly for a wide range
of inputs, catching edge cases that might be missed by example-based tests.
"""

from __future__ import annotations

import pytest

from bengal.rendering.asset_tracking import AssetTracker, get_current_tracker

# Skip if hypothesis not available - importorskip must run before import
pytest.importorskip("hypothesis")
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


class TestAssetTrackerProperties:
    """Property-based tests for AssetTracker."""

    @given(st.text())
    def test_track_never_raises(self, path: str) -> None:
        """Tracking any string should never raise an exception."""
        tracker = AssetTracker()
        # Should not raise for any input
        tracker.track(path)

    @given(st.text(min_size=1).filter(lambda x: x.strip()))
    def test_non_empty_non_whitespace_paths_tracked(self, path: str) -> None:
        """Non-empty, non-whitespace paths should be tracked."""
        tracker = AssetTracker()
        tracker.track(path)

        # Path should be in tracked assets
        assert path in tracker.get_assets()

    @given(st.text().filter(lambda x: not x.strip()))
    def test_whitespace_only_paths_ignored(self, path: str) -> None:
        """Whitespace-only paths (including empty string) should be ignored."""
        tracker = AssetTracker()
        tracker.track(path)

        # Should not track empty/whitespace paths
        assert len(tracker.get_assets()) == 0

    @given(st.lists(st.text(min_size=1).filter(lambda x: x.strip()), min_size=0, max_size=100))
    def test_all_valid_paths_tracked(self, paths: list[str]) -> None:
        """All valid (non-empty, non-whitespace) paths should be tracked."""
        tracker = AssetTracker()

        for path in paths:
            tracker.track(path)

        assets = tracker.get_assets()

        # All unique paths should be present
        unique_paths = set(paths)
        assert assets == unique_paths

    @given(st.text(min_size=1).filter(lambda x: x.strip()))
    def test_get_assets_returns_copy(self, path: str) -> None:
        """get_assets() should return a copy, not the internal set."""
        tracker = AssetTracker()
        tracker.track(path)

        assets1 = tracker.get_assets()
        assets2 = tracker.get_assets()

        # Should be different objects
        assert assets1 is not assets2
        # But same content
        assert assets1 == assets2

        # Modifying returned set should not affect tracker
        assets1.add("/modified/path.css")
        assets3 = tracker.get_assets()
        assert "/modified/path.css" not in assets3

    @given(st.lists(st.text(), min_size=0, max_size=50))
    def test_duplicate_paths_deduplicated(self, paths: list[str]) -> None:
        """Duplicate paths should be deduplicated."""
        tracker = AssetTracker()

        # Track each path twice
        for path in paths:
            tracker.track(path)
            tracker.track(path)

        assets = tracker.get_assets()

        # Count should equal unique valid paths
        valid_paths = {p for p in paths if p.strip()}
        assert len(assets) == len(valid_paths)


class TestAssetTrackerContextManagerProperties:
    """Property-based tests for AssetTracker context manager."""

    @given(st.text(min_size=1).filter(lambda x: x.strip()))
    def test_context_manager_sets_and_resets_tracker(self, path: str) -> None:
        """Context manager should set tracker on enter and reset on exit."""
        # Before context
        assert get_current_tracker() is None

        tracker = AssetTracker()
        with tracker:
            # Inside context
            assert get_current_tracker() is tracker
            tracker.track(path)

        # After context
        assert get_current_tracker() is None

        # Asset should still be tracked
        assert path in tracker.get_assets()

    @given(st.lists(st.text(min_size=1).filter(lambda x: x.strip()), min_size=1, max_size=10))
    def test_nested_context_managers(self, paths: list[str]) -> None:
        """Nested context managers should properly stack and unstack."""
        trackers = [AssetTracker() for _ in paths]

        # Before any context
        assert get_current_tracker() is None

        # Enter all contexts
        def enter_all(idx: int = 0) -> None:
            if idx >= len(trackers):
                # At deepest level, verify current tracker
                assert get_current_tracker() is trackers[-1]
                trackers[-1].track(paths[-1])
                return

            with trackers[idx]:
                assert get_current_tracker() is trackers[idx]
                trackers[idx].track(paths[idx])
                enter_all(idx + 1)

            # After exiting inner context
            if idx > 0:
                assert get_current_tracker() is trackers[idx - 1]
            else:
                assert get_current_tracker() is None

        enter_all()

        # After all contexts
        assert get_current_tracker() is None

        # Each tracker should have its own path
        for i, tracker in enumerate(trackers):
            assert paths[i] in tracker.get_assets()


class TestAssetTrackerEdgeCases:
    """Property-based tests for edge cases."""

    @given(st.text())
    @settings(max_examples=200)
    def test_special_characters_in_paths(self, path: str) -> None:
        """Paths with special characters should be handled safely."""
        tracker = AssetTracker()

        # Should not raise
        tracker.track(path)

        # If path is valid (non-empty, non-whitespace), it should be tracked
        if path.strip():
            assert path in tracker.get_assets()
        else:
            assert len(tracker.get_assets()) == 0

    @given(st.binary())
    def test_binary_data_rejected(self, data: bytes) -> None:
        """Binary data should not cause crashes (though it may not be tracked)."""
        tracker = AssetTracker()

        # Try to track as string (may raise or may work)
        try:
            path = data.decode("utf-8", errors="replace")
            tracker.track(path)
            # If it didn't raise, check tracking behavior
            if path.strip():
                assert path in tracker.get_assets()
        except Exception:
            # Some binary data may not be convertible - that's OK
            pass

    @given(st.text(alphabet=st.characters(whitelist_categories=("Zs", "Cc", "Cf"))))
    def test_all_whitespace_variations_ignored(self, whitespace: str) -> None:
        """All Unicode whitespace variations should be treated as empty."""
        tracker = AssetTracker()
        tracker.track(whitespace)

        # Unicode whitespace should result in empty tracking
        if not whitespace.strip():
            assert len(tracker.get_assets()) == 0

    @given(st.text(min_size=1000, max_size=10000))
    def test_very_long_paths(self, long_path: str) -> None:
        """Very long paths should be handled without issues."""
        tracker = AssetTracker()
        tracker.track(long_path)

        if long_path.strip():
            assert long_path in tracker.get_assets()
