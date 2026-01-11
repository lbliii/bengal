"""
Integration tests for Link Previews feature.

Tests the end-to-end rendering of link preview configuration,
template output, and JavaScript inclusion.

See: plan/drafted/rfc-link-previews.md
See: plan/rfc-cross-site-xref-link-previews.md
"""

from __future__ import annotations

from bengal.config.defaults import get_default


class TestLinkPreviewsTemplateRendering:
    """Test that link previews config is rendered correctly in templates."""

    def test_config_bridge_present_when_enabled(self, site_builder):
        """Config bridge script block should be present when enabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
                "link_previews": {
                    "enabled": True,
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert 'id="bengal-config"' in html
        assert "linkPreviews" in html
        assert '"enabled": true' in html

    def test_config_bridge_absent_when_disabled(self, site_builder):
        """Config bridge should not be present when link previews disabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
                "link_previews": {
                    "enabled": False,
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Config bridge should not be present when disabled
        # Note: bengal-config might exist for other features, so we check for linkPreviews
        if 'id="bengal-config"' in html:
            assert '"enabled": true' not in html or "linkPreviews" not in html

    def test_config_bridge_absent_without_json(self, site_builder):
        """Config bridge should not be present without per-page JSON."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": [],  # No JSON
                },
                "link_previews": {
                    "enabled": True,
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Should not have link previews config without JSON
        assert "linkPreviews" not in html

    def test_script_included_when_enabled(self, site_builder):
        """Link previews script should be included when enabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
                "link_previews": {
                    "enabled": True,
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Script may have fingerprint hash in name, e.g., link-previews.af9b6471.js
        assert "link-previews" in html

    def test_custom_config_values_rendered(self, site_builder):
        """Custom config values should be rendered in config bridge."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
                "link_previews": {
                    "enabled": True,
                    "hover_delay": 400,
                    "show_section": False,
                    "max_tags": 5,
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        assert '"hoverDelay": 400' in html
        assert '"showSection": false' in html
        assert '"maxTags": 5' in html


class TestLinkPreviewsJsonGeneration:
    """Test that per-page JSON files are generated correctly."""

    def test_json_file_created_for_each_page(self, site_builder):
        """Each page should have a corresponding JSON file."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
            },
            content={
                "_index.md": "---\ntitle: Home\n---\nWelcome",
                "about.md": "---\ntitle: About\n---\nAbout us",
            },
        )
        site.build()

        # Check JSON files exist
        assert (site.output_dir / "index.json").exists()
        assert (site.output_dir / "about" / "index.json").exists()

    def test_json_contains_preview_data(self, site_builder):
        """JSON should contain data needed for previews."""
        import json

        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
            },
            content={
                "docs/getting-started.md": """---
title: Getting Started
description: Learn how to install Bengal
tags:
  - setup
  - beginner
---

This is a guide to getting started with Bengal. It covers installation,
configuration, and your first build.
""",
            },
        )
        site.build()

        json_path = site.output_dir / "docs" / "getting-started" / "index.json"
        assert json_path.exists()

        data = json.loads(json_path.read_text())
        assert data["title"] == "Getting Started"
        assert "excerpt" in data
        assert "reading_time" in data
        assert "word_count" in data
        assert "tags" in data
        assert "setup" in data["tags"]


class TestLinkPreviewsCss:
    """Test that link preview CSS is included."""

    def test_css_includes_link_preview_styles(self, site_builder):
        """Link preview CSS should be bundled in theme styles."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        # Find CSS file (may have fingerprint in name)
        css_dir = site.output_dir / "assets" / "css"
        css_files = list(css_dir.glob("style*.css"))
        assert len(css_files) > 0, "No CSS file found"

        css = css_files[0].read_text()
        # Should have link-preview classes (bundled via @import)
        assert ".link-preview" in css


class TestLinkPreviewsDefaultBehavior:
    """Test default behavior without explicit configuration."""

    def test_enabled_by_default_with_json(self, site_builder):
        """Link previews should be enabled by default when JSON is enabled."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
                # No explicit link_previews config
            },
            content={"_index.md": "---\ntitle: Home\n---\nWelcome"},
        )
        site.build()

        html = site.read_output("index.html")
        # Should have link previews enabled by default
        # Script may have fingerprint hash in name, e.g., link-previews.af9b6471.js
        assert "link-previews" in html
        assert "linkPreviews" in html


class TestCrossSiteLinkPreviewsDefaults:
    """Test cross-site link preview configuration defaults.

    See: plan/rfc-cross-site-xref-link-previews.md
    """

    def test_allowed_hosts_defaults_to_empty(self):
        """allowed_hosts defaults to empty list (same-origin only)."""
        assert get_default("link_previews", "allowed_hosts") == []

    def test_allowed_schemes_defaults_to_https(self):
        """allowed_schemes defaults to HTTPS only."""
        assert get_default("link_previews", "allowed_schemes") == ["https"]

    def test_host_failure_threshold_defaults_to_three(self):
        """host_failure_threshold defaults to 3."""
        assert get_default("link_previews", "host_failure_threshold") == 3


class TestCrossSiteLinkPreviewsConfigBridge:
    """Test cross-site config is rendered in config bridge template."""

    def test_config_bridge_includes_allowed_hosts_when_configured(self, site_builder):
        """Config bridge should include allowedHosts when configured."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
                "link_previews": {
                    "enabled": True,
                    "allowed_hosts": ["example.com", "other.dev"],
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nTest"},
        )
        site.build()
        html = site.read_output("index.html")
        assert '"allowedHosts": ["example.com", "other.dev"]' in html

    def test_config_bridge_includes_allowed_schemes(self, site_builder):
        """Config bridge should include allowedSchemes."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
                "link_previews": {
                    "enabled": True,
                    "allowed_schemes": ["https", "http"],
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nTest"},
        )
        site.build()
        html = site.read_output("index.html")
        assert '"allowedSchemes": ["https", "http"]' in html

    def test_config_bridge_includes_host_failure_threshold(self, site_builder):
        """Config bridge should include hostFailureThreshold."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
                "link_previews": {
                    "enabled": True,
                    "host_failure_threshold": 5,
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nTest"},
        )
        site.build()
        html = site.read_output("index.html")
        assert '"hostFailureThreshold": 5' in html

    def test_config_bridge_defaults_when_not_configured(self, site_builder):
        """Config bridge should include defaults for cross-site options."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
                "link_previews": {
                    "enabled": True,
                    # No cross-site config - use defaults
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nTest"},
        )
        site.build()
        html = site.read_output("index.html")
        # Should have default values
        assert '"allowedHosts": []' in html
        assert '"allowedSchemes": ["https"]' in html
        assert '"hostFailureThreshold": 3' in html

    def test_ecosystem_hosts_configuration(self, site_builder):
        """Test typical ecosystem host configuration."""
        site = site_builder(
            config={
                "title": "Test Site",
                "output_formats": {
                    "enabled": True,
                    "per_page": ["json"],
                },
                "link_previews": {
                    "enabled": True,
                    "allowed_hosts": [
                        "lbliii.github.io",
                        "kida.dev",
                        "rosettes.dev",
                    ],
                    "allowed_schemes": ["https"],
                    "host_failure_threshold": 3,
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nTest"},
        )
        site.build()
        html = site.read_output("index.html")
        assert "lbliii.github.io" in html
        assert "kida.dev" in html
        assert "rosettes.dev" in html
