"""
Unit tests for Theme Controls (Document Application RFC Phase 3).

Tests the popover-based theme controls migration including:
- Popover attributes presence
- Fallback to classic dropdown when disabled
"""

from __future__ import annotations

import pytest


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
        assert 'popovertarget="theme-menu"' in html
        assert 'id="theme-menu"' in html
        assert "popover" in html

    @pytest.mark.skip(
        reason="Fallback to classic dropdown not yet implemented - templates always use native popover"
    )
    def test_fallback_to_classic_when_popover_disabled(self, site_builder):
        """Theme menu should use classic dropdown when popover disabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "dropdowns": "enhanced",  # Not popover
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Should use classic JS dropdown
        assert 'aria-haspopup="true"' in html
        assert 'aria-expanded="false"' in html
        # Should NOT have popover attributes
        assert 'popovertarget="theme-menu"' not in html

    @pytest.mark.skip(
        reason="Fallback to classic dropdown not yet implemented - templates always use native popover"
    )
    def test_fallback_when_doc_app_disabled(self, site_builder):
        """Theme menu should use classic dropdown when document_application disabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": False,
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Should use classic JS dropdown
        assert 'aria-haspopup="true"' in html
        # Should NOT have popover attributes
        assert 'popovertarget="theme-menu"' not in html

    @pytest.mark.skip(
        reason="Fallback to classic dropdown not yet implemented - templates always use native popover"
    )
    def test_fallback_when_native_popovers_feature_disabled(self, site_builder):
        """Theme menu should use classic dropdown when native_popovers feature disabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "dropdowns": "popover",
                    },
                    "features": {
                        "native_popovers": False,
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Should use classic JS dropdown
        assert 'aria-haspopup="true"' in html
        # Should NOT have popover attributes
        assert 'popovertarget="theme-menu"' not in html


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
