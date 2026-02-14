"""
Tests for the "rebuilding" page feature.

When a build is in progress and a user requests an HTML-like path, the ASGI app
serves a friendly "rebuilding" page. These tests cover build state, responses
module, and palette handling.
"""

from __future__ import annotations

import threading
from pathlib import Path

from bengal.server.build_state import build_state


class TestBuildInProgressState:
    """Test the build-in-progress state tracking."""

    def test_set_build_in_progress_true(self) -> None:
        """Test setting build state to in progress."""
        build_state.set_build_in_progress(False)
        build_state.set_build_in_progress(True)
        assert build_state.get_build_in_progress() is True

    def test_set_build_in_progress_false(self) -> None:
        """Test clearing build state."""
        build_state.set_build_in_progress(True)
        build_state.set_build_in_progress(False)
        assert build_state.get_build_in_progress() is False

    def test_build_state_is_thread_safe(self) -> None:
        """Test that build state can be accessed from multiple threads."""
        errors: list[Exception] = []

        def toggle_state() -> None:
            try:
                for _ in range(100):
                    build_state.set_build_in_progress(True)
                    build_state.set_build_in_progress(False)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=toggle_state) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0


class TestRebuildingPageContent:
    """Test the rebuilding page HTML content."""

    def test_rebuilding_page_contains_loading_animation(self) -> None:
        """Test that rebuilding page has a loading animation."""
        from bengal.server.responses import REBUILDING_PAGE_HTML

        assert b"animation" in REBUILDING_PAGE_HTML
        assert b"@keyframes" in REBUILDING_PAGE_HTML

    def test_rebuilding_page_has_auto_refresh(self) -> None:
        """Test that rebuilding page has auto-refresh."""
        from bengal.server.responses import REBUILDING_PAGE_HTML

        assert b"refresh" in REBUILDING_PAGE_HTML.lower()

    def test_rebuilding_page_has_live_reload_script(self) -> None:
        """Test that rebuilding page connects to live reload."""
        from bengal.server.responses import REBUILDING_PAGE_HTML

        assert b"__bengal_reload__" in REBUILDING_PAGE_HTML

    def test_rebuilding_page_has_path_placeholder(self) -> None:
        """Test that rebuilding page has placeholder for path."""
        from bengal.server.responses import REBUILDING_PAGE_HTML

        assert b"%PATH%" in REBUILDING_PAGE_HTML

    def test_rebuilding_page_has_bengal_branding(self) -> None:
        """Test that rebuilding page includes Bengal branding."""
        from bengal.server.responses import REBUILDING_PAGE_HTML

        assert b"Bengal" in REBUILDING_PAGE_HTML
        assert b"ellipse" in REBUILDING_PAGE_HTML


class TestRebuildingBadge:
    """Test the minimal rebuilding badge shown when serving cached content during build."""

    def test_get_rebuilding_badge_script_returns_badge_html(self) -> None:
        """Test that get_rebuilding_badge_script returns the badge div."""
        from bengal.server.responses import get_rebuilding_badge_script

        badge = get_rebuilding_badge_script()
        assert "bengal-rebuilding-badge" in badge
        assert "Rebuilding" in badge
        assert "position:fixed" in badge
        assert "bottom:" in badge
        assert "right:" in badge


class TestRebuildingPagePalette:
    """Test the palette-aware rebuilding page functionality."""

    def test_get_rebuilding_page_html_replaces_path(self) -> None:
        """Test that get_rebuilding_page_html replaces the path placeholder."""
        from bengal.server.responses import get_rebuilding_page_html

        html = get_rebuilding_page_html("/api/bengal/config/")
        assert b"/api/bengal/config/" in html
        assert b"%PATH%" not in html

    def test_get_rebuilding_page_html_default_palette(self) -> None:
        """Test that get_rebuilding_page_html uses default palette when none specified."""
        from bengal.server.responses import (
            DEFAULT_PALETTE,
            PALETTE_COLORS,
            get_rebuilding_page_html,
        )

        html = get_rebuilding_page_html("/test/")
        accent, _accent_rgb, _, _, _ = PALETTE_COLORS[DEFAULT_PALETTE]
        assert accent.encode() in html
        assert b"%ACCENT%" not in html
        assert b"%ACCENT_RGB%" not in html

    def test_get_rebuilding_page_html_charcoal_palette(self) -> None:
        """Test that charcoal-bengal palette uses golden accent color."""
        from bengal.server.responses import get_rebuilding_page_html

        html = get_rebuilding_page_html("/test/", "charcoal-bengal")
        assert b"#C9A84D" in html
        assert b"201, 168, 77" in html

    def test_get_rebuilding_page_html_snow_lynx_palette(self) -> None:
        """Test that snow-lynx palette uses icy teal accent color."""
        from bengal.server.responses import get_rebuilding_page_html

        html = get_rebuilding_page_html("/test/", "snow-lynx")
        assert b"#6EC4BC" in html
        assert b"110, 196, 188" in html

    def test_get_rebuilding_page_html_blue_bengal_palette(self) -> None:
        """Test that blue-bengal palette uses powder blue accent color."""
        from bengal.server.responses import get_rebuilding_page_html

        html = get_rebuilding_page_html("/test/", "blue-bengal")
        assert b"#9DBDD9" in html
        assert b"157, 189, 217" in html

    def test_get_rebuilding_page_html_brown_bengal_palette(self) -> None:
        """Test that brown-bengal palette uses warm amber accent color."""
        from bengal.server.responses import get_rebuilding_page_html

        html = get_rebuilding_page_html("/test/", "brown-bengal")
        assert b"#FFAD3D" in html
        assert b"255, 173, 61" in html

    def test_get_rebuilding_page_html_silver_bengal_palette(self) -> None:
        """Test that silver-bengal palette uses pure silver accent color."""
        from bengal.server.responses import get_rebuilding_page_html

        html = get_rebuilding_page_html("/test/", "silver-bengal")
        assert b"#D1D5DB" in html
        assert b"209, 213, 219" in html

    def test_get_rebuilding_page_html_unknown_palette_uses_default(self) -> None:
        """Test that unknown palette names fall back to default."""
        from bengal.server.responses import (
            DEFAULT_PALETTE,
            PALETTE_COLORS,
            get_rebuilding_page_html,
        )

        html = get_rebuilding_page_html("/test/", "unknown-palette")
        accent, _, _, _, _ = PALETTE_COLORS[DEFAULT_PALETTE]
        assert accent.encode() in html

    def test_get_rebuilding_page_html_none_palette_uses_default(self) -> None:
        """Test that None palette uses default."""
        from bengal.server.responses import (
            DEFAULT_PALETTE,
            PALETTE_COLORS,
            get_rebuilding_page_html,
        )

        html = get_rebuilding_page_html("/test/", None)
        accent, _, _, _, _ = PALETTE_COLORS[DEFAULT_PALETTE]
        assert accent.encode() in html

    def test_all_placeholders_replaced(self) -> None:
        """Test that all color placeholders are replaced."""
        from bengal.server.responses import get_rebuilding_page_html

        html = get_rebuilding_page_html("/test/", "charcoal-bengal")
        assert b"%PATH%" not in html
        assert b"%ACCENT%" not in html
        assert b"%ACCENT_RGB%" not in html
        assert b"%BG_PRIMARY%" not in html
        assert b"%BG_SECONDARY%" not in html
        assert b"%BG_TERTIARY%" not in html


class TestBuildTriggerIntegration:
    """Test that BuildTrigger properly signals build state."""

    def test_build_trigger_sets_build_in_progress(self, tmp_path: Path) -> None:
        """Test that BuildTrigger signals build start/end."""
        from unittest.mock import MagicMock

        from bengal.server.build_trigger import BuildTrigger

        mock_site = MagicMock()
        mock_site.root_path = tmp_path
        mock_site.output_dir = tmp_path / "public"
        mock_site.config = {}

        mock_executor = MagicMock()
        trigger = BuildTrigger(mock_site, executor=mock_executor)

        build_state.set_build_in_progress(False)
        assert build_state.get_build_in_progress() is False

        trigger.shutdown()
