"""
Integration tests for Link Previews feature.

Tests the end-to-end rendering of link preview configuration,
template output, and JavaScript inclusion.

See: plan/drafted/rfc-link-previews.md
See: plan/rfc-cross-site-xref-link-previews.md
"""

from __future__ import annotations

import json

import pytest

from bengal.config.defaults import get_default
from tests._testing.fixtures import build_ephemeral_site_at

_INDEX = "---\ntitle: Home\n---\nWelcome"


@pytest.fixture(scope="module")
def site_lp_enabled_json_on(tmp_path_factory):
    """One build shared by tests that only assert on enabled + JSON output."""
    base = tmp_path_factory.mktemp("lp_en_json_on")
    site = build_ephemeral_site_at(
        base / "ephemeral_site",
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
        content={"_index.md": _INDEX},
    )
    site.build()
    return site


@pytest.fixture(scope="module")
def site_lp_disabled_json(tmp_path_factory):
    base = tmp_path_factory.mktemp("lp_dis_json")
    site = build_ephemeral_site_at(
        base / "ephemeral_site",
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
        content={"_index.md": _INDEX},
    )
    site.build()
    return site


@pytest.fixture(scope="module")
def site_lp_enabled_no_json(tmp_path_factory):
    base = tmp_path_factory.mktemp("lp_no_json")
    site = build_ephemeral_site_at(
        base / "ephemeral_site",
        config={
            "title": "Test Site",
            "output_formats": {
                "enabled": True,
                "per_page": [],
            },
            "link_previews": {
                "enabled": True,
            },
        },
        content={"_index.md": _INDEX},
    )
    site.build()
    return site


@pytest.fixture(scope="module")
def site_lp_custom_hover(tmp_path_factory):
    base = tmp_path_factory.mktemp("lp_custom")
    site = build_ephemeral_site_at(
        base / "ephemeral_site",
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
        content={"_index.md": _INDEX},
    )
    site.build()
    return site


@pytest.fixture(scope="module")
def site_lp_json_multi_page(tmp_path_factory):
    """Single build with multiple pages for JSON generation tests."""
    base = tmp_path_factory.mktemp("lp_json_multi")
    site = build_ephemeral_site_at(
        base / "ephemeral_site",
        config={
            "title": "Test Site",
            "output_formats": {
                "enabled": True,
                "per_page": ["json"],
            },
        },
        content={
            "_index.md": _INDEX,
            "about.md": "---\ntitle: About\n---\nAbout us",
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
    return site


@pytest.fixture(scope="module")
def site_lp_json_css_default(tmp_path_factory):
    base = tmp_path_factory.mktemp("lp_css_def")
    site = build_ephemeral_site_at(
        base / "ephemeral_site",
        config={
            "title": "Test Site",
            "output_formats": {
                "enabled": True,
                "per_page": ["json"],
            },
        },
        content={"_index.md": _INDEX},
    )
    site.build()
    return site


@pytest.fixture(scope="module")
def site_lp_default_previews(tmp_path_factory):
    """No explicit link_previews — defaults apply."""
    base = tmp_path_factory.mktemp("lp_def_pv")
    site = build_ephemeral_site_at(
        base / "ephemeral_site",
        config={
            "title": "Test Site",
            "output_formats": {
                "enabled": True,
                "per_page": ["json"],
            },
        },
        content={"_index.md": _INDEX},
    )
    site.build()
    return site


class TestLinkPreviewsTemplateRendering:
    """Test that link previews config is rendered correctly in templates."""

    def test_config_bridge_present_when_enabled(self, site_lp_enabled_json_on):
        """Config bridge script block should be present when enabled."""
        html = site_lp_enabled_json_on.read_output("index.html")
        assert 'id="bengal-config"' in html
        assert "linkPreviews" in html
        assert '"enabled": true' in html

    def test_config_bridge_absent_when_disabled(self, site_lp_disabled_json):
        """Config bridge should not be present when link previews disabled."""
        html = site_lp_disabled_json.read_output("index.html")
        assert 'id="bengal-config"' not in html
        assert "linkPreviews" not in html

    def test_config_bridge_absent_without_json(self, site_lp_enabled_no_json):
        """Config bridge should not be present without per-page JSON."""
        html = site_lp_enabled_no_json.read_output("index.html")
        assert "linkPreviews" not in html

    def test_script_included_when_enabled(self, site_lp_enabled_json_on):
        """Link previews script should be included when enabled."""
        html = site_lp_enabled_json_on.read_output("index.html")
        assert "link-previews" in html

    def test_custom_config_values_rendered(self, site_lp_custom_hover):
        """Custom config values should be rendered in config bridge."""
        html = site_lp_custom_hover.read_output("index.html")
        assert '"hoverDelay": 400' in html
        assert '"showSection": false' in html
        assert '"maxTags": 5' in html


class TestLinkPreviewsJsonGeneration:
    """Test that per-page JSON files are generated correctly."""

    def test_json_file_created_for_each_page(self, site_lp_json_multi_page):
        """Each page should have a corresponding JSON file."""
        out = site_lp_json_multi_page.output_dir
        assert (out / "index.json").exists()
        assert (out / "about" / "index.json").exists()

    def test_json_contains_preview_data(self, site_lp_json_multi_page):
        """JSON should contain data needed for previews."""
        json_path = site_lp_json_multi_page.output_dir / "docs" / "getting-started" / "index.json"
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

    def test_css_includes_link_preview_styles(self, site_lp_json_css_default):
        """Link preview CSS should be bundled in theme styles."""
        css_dir = site_lp_json_css_default.output_dir / "assets" / "css"
        css_files = list(css_dir.glob("style*.css"))
        assert len(css_files) > 0, "No CSS file found"

        css = css_files[0].read_text()
        assert ".link-preview" in css


class TestLinkPreviewsDefaultBehavior:
    """Test default behavior without explicit configuration."""

    def test_enabled_by_default_with_json(self, site_lp_default_previews):
        """Link previews should be enabled by default when JSON is enabled."""
        html = site_lp_default_previews.read_output("index.html")
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
                },
            },
            content={"_index.md": "---\ntitle: Home\n---\nTest"},
        )
        site.build()
        html = site.read_output("index.html")
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
        assert "rosettes.dev" in html
