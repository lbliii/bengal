"""
Unit tests for View Transitions feature (Document Application RFC).

Tests the View Transitions API integration including:
- Meta tag generation based on config
- Transition style attributes
- Speculation rules generation
"""

from __future__ import annotations


class TestViewTransitionsMetaTag:
    """Tests for view transition meta tag generation."""

    def test_meta_tag_present_when_enabled(self, site_builder):
        """View transition meta tag should be present when enabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "navigation": {
                        "view_transitions": True,
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert '<meta name="view-transition" content="same-origin">' in html

    def test_meta_tag_absent_when_disabled(self, site_builder):
        """View transition meta tag should be absent when disabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "navigation": {
                        "view_transitions": False,
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert '<meta name="view-transition"' not in html

    def test_meta_tag_absent_when_doc_app_disabled(self, site_builder):
        """View transition meta tag should be absent when document_application is disabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": False,
                    "navigation": {
                        "view_transitions": True,
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert '<meta name="view-transition"' not in html

    def test_transition_style_attribute_slide(self, site_builder):
        """Transition style attribute should be added for non-default styles."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "navigation": {
                        "view_transitions": True,
                        "transition_style": "slide",
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert 'data-transition-style="slide"' in html

    def test_transition_style_attribute_none_for_crossfade(self, site_builder):
        """Transition style attribute should not be added for default crossfade."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "navigation": {
                        "view_transitions": True,
                        "transition_style": "crossfade",
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert "data-transition-style" not in html


class TestSpeculationRules:
    """Tests for speculation rules generation."""

    def test_speculation_rules_present_when_enabled(self, site_builder):
        """Speculation rules script should be present when enabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "speculation": {
                        "enabled": True,
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert '<script type="speculationrules">' in html
        assert '"prerender"' in html
        assert '"prefetch"' in html

    def test_speculation_rules_absent_when_disabled(self, site_builder):
        """Speculation rules script should be absent when disabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "speculation": {
                        "enabled": False,
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert '<script type="speculationrules">' not in html

    def test_speculation_rules_eagerness_config(self, site_builder):
        """Speculation rules should use configured eagerness levels."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "speculation": {
                        "enabled": True,
                        "prerender": {
                            "eagerness": "moderate",
                        },
                        "prefetch": {
                            "eagerness": "eager",
                        },
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Check that the configured eagerness values appear in the rules
        assert '"eagerness": "moderate"' in html
        assert '"eagerness": "eager"' in html

    def test_speculation_feature_flag_disables(self, site_builder):
        """Speculation rules should be disabled via feature flag."""
        site = site_builder(
            config={
                "title": "Test Site",
                "document_application": {
                    "enabled": True,
                    "speculation": {
                        "enabled": True,
                    },
                    "features": {
                        "speculation_rules": False,
                    },
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert '<script type="speculationrules">' not in html


class TestDocumentApplicationDefaults:
    """Tests for document application default configuration."""

    def test_default_config_enables_view_transitions(self, site_builder):
        """Default config should enable view transitions."""
        site = site_builder(
            config={"title": "Test Site"},
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # By default, view transitions should be enabled
        assert '<meta name="view-transition" content="same-origin">' in html

    def test_default_config_enables_speculation(self, site_builder):
        """Default config should enable speculation rules."""
        site = site_builder(
            config={"title": "Test Site"},
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # By default, speculation rules should be enabled
        assert '<script type="speculationrules">' in html

    def test_default_eagerness_is_conservative(self, site_builder):
        """Default eagerness should be conservative for bandwidth concerns."""
        site = site_builder(
            config={"title": "Test Site"},
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert '"eagerness": "conservative"' in html


