"""
Unit tests for Mobile Navigation (Document Application RFC Phase 4).

Tests the native dialog-based mobile navigation including:
- Dialog element presence
- ARIA attributes
- Fallback to classic drawer when disabled
"""

from __future__ import annotations


class TestMobileNavDialog:
    """Tests for native dialog-based mobile navigation."""

    def test_dialog_element_present_when_enabled(self, site_builder):
        """Mobile nav should use dialog element when enabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "modals": "native_dialog",
                    },
                    "features": {
                        "native_dialogs": True,
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert '<dialog id="mobile-nav-dialog"' in html
        assert 'class="mobile-nav-dialog"' in html

    def test_fallback_to_classic_when_dialog_disabled(self, site_builder):
        """Mobile nav should use classic drawer when dialog disabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "modals": "enhanced",  # Not native_dialog
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Should use classic nav element
        assert 'class="mobile-nav"' in html
        assert 'data-bengal="mobile-nav"' in html
        # Should NOT have dialog
        assert '<dialog id="mobile-nav-dialog"' not in html

    def test_fallback_when_doc_app_disabled(self, site_builder):
        """Mobile nav should use classic drawer when document_application disabled."""
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
        # Should use classic nav element
        assert 'class="mobile-nav"' in html
        # Should NOT have dialog
        assert '<dialog id="mobile-nav-dialog"' not in html

    def test_fallback_when_native_dialogs_feature_disabled(self, site_builder):
        """Mobile nav should use classic drawer when native_dialogs feature disabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "modals": "native_dialog",
                    },
                    "features": {
                        "native_dialogs": False,
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Should use classic nav element
        assert 'class="mobile-nav"' in html
        # Should NOT have dialog
        assert '<dialog id="mobile-nav-dialog"' not in html


class TestMobileNavAccessibility:
    """Tests for mobile navigation accessibility."""

    def test_dialog_has_aria_label(self, site_builder):
        """Dialog should have accessible label."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "modals": "native_dialog",
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert 'aria-label="Mobile navigation"' in html

    def test_close_button_is_submit(self, site_builder):
        """Close button should be form submit for native dialog close."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "modals": "native_dialog",
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert 'type="submit"' in html
        assert 'value="close"' in html

    def test_toggle_button_opens_dialog(self, site_builder):
        """Toggle button should call showModal()."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "interactivity": {
                        "modals": "native_dialog",
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert "showModal()" in html
