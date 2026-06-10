"""
Unit tests for Theme Controls (Document Application RFC Phase 3).

Tests the popover-based theme controls migration including:
- Popover attributes presence
"""

from __future__ import annotations


class TestThemeControlsPopover:
    """Tests for popover-based theme controls."""

    def test_popover_attributes_present_when_enabled(self, site_builder):
        """Theme menu should use popover attribute when enabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "dropdowns": "popover",
                    },
                    "features": {
                        "native_popovers": True,
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Template uses dynamic IDs: theme-menu-desktop and theme-menu-mobile
        assert (
            'popovertarget="theme-menu-desktop"' in html
            or 'popovertarget="theme-menu-mobile"' in html
        )
        assert 'id="theme-menu-desktop"' in html or 'id="theme-menu-mobile"' in html
        assert "popover" in html


class TestThemeControlsAccessibility:
    """Tests for theme controls accessibility."""

    def test_popover_has_accessible_label(self, site_builder):
        """Popover trigger should have accessible label."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "dropdowns": "popover",
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert 'aria-label="Open theme menu"' in html or 'title="Theme presets"' in html

    def test_theme_options_are_buttons(self, site_builder):
        """Theme options should be buttons for keyboard access."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "dropdowns": "popover",
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert 'class="theme-option"' in html
        assert 'data-appearance="system"' in html
        assert 'data-palette="snow-lynx"' in html
