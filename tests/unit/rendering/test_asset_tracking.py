"""
Tests for render-time asset tracking.

RFC: rfc-build-performance-optimizations Phase 2
"""

from __future__ import annotations

from bengal.core.site import Site
from bengal.rendering.asset_tracking import AssetTracker, get_current_tracker
from bengal.rendering.assets import resolve_asset_url


class TestAssetTracker:
    """Tests for AssetTracker class."""

    def test_track_assets(self) -> None:
        """Test tracking assets."""
        tracker = AssetTracker()

        tracker.track("/assets/css/style.css")
        tracker.track("/assets/js/app.js")

        assets = tracker.get_assets()
        assert "/assets/css/style.css" in assets
        assert "/assets/js/app.js" in assets
        assert len(assets) == 2

    def test_context_manager(self) -> None:
        """Test tracker as context manager."""
        tracker = AssetTracker()

        assert get_current_tracker() is None

        with tracker:
            assert get_current_tracker() is tracker
            tracker.track("/assets/test.css")

        assert get_current_tracker() is None
        assert "/assets/test.css" in tracker.get_assets()

    def test_track_empty_string_ignored(self) -> None:
        """Test that empty strings are not tracked."""
        tracker = AssetTracker()

        tracker.track("")
        tracker.track("  ")

        assets = tracker.get_assets()
        assert len(assets) == 0

    def test_get_assets_returns_copy(self) -> None:
        """Test that get_assets() returns a copy."""
        tracker = AssetTracker()
        tracker.track("/assets/test.css")

        assets1 = tracker.get_assets()
        assets2 = tracker.get_assets()

        # Should be different objects
        assert assets1 is not assets2
        # But same content
        assert assets1 == assets2


class TestAssetTrackingIntegration:
    """Integration tests for asset tracking with resolve_asset_url."""

    def test_resolve_asset_url_tracks_assets(self, tmp_path) -> None:
        """Test that resolve_asset_url tracks assets when tracker is active."""
        site = Site(
            root_path=tmp_path,
            config={},
        )

        tracker = AssetTracker()
        with tracker:
            # Resolve asset URLs - should be tracked
            url1 = resolve_asset_url("css/style.css", site)
            url2 = resolve_asset_url("js/app.js", site)

        # Check that assets were tracked
        assets = tracker.get_assets()
        assert "css/style.css" in assets
        assert "js/app.js" in assets

        # URLs should still be resolved correctly
        assert url1
        assert url2

    def test_resolve_asset_url_no_tracking_when_inactive(self, tmp_path) -> None:
        """Test that resolve_asset_url doesn't track when tracker is inactive."""
        site = Site(
            root_path=tmp_path,
            config={},
        )

        # No tracker active
        assert get_current_tracker() is None

        # Resolve asset URLs - should not track
        url = resolve_asset_url("css/style.css", site)

        # Should still work (no error)
        assert url

        # But no tracker to check (this is expected behavior)

    def test_tracking_with_multiple_assets(self, tmp_path) -> None:
        """Test tracking multiple assets in sequence."""
        site = Site(
            root_path=tmp_path,
            config={},
        )

        tracker = AssetTracker()
        with tracker:
            resolve_asset_url("css/style.css", site)
            resolve_asset_url("css/theme.css", site)
            resolve_asset_url("js/app.js", site)
            resolve_asset_url("images/logo.png", site)

        assets = tracker.get_assets()
        assert len(assets) == 4
        assert "css/style.css" in assets
        assert "css/theme.css" in assets
        assert "js/app.js" in assets
        assert "images/logo.png" in assets
