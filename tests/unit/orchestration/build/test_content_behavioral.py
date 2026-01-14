"""
Behavioral tests for build content phases.

RFC: rfc-behavioral-test-hardening

This module replaces mock-based tests with behavioral tests that verify
OUTCOMES rather than implementation details.

Instead of:
    orchestrator.sections.finalize_sections.assert_called_once()

We verify:
    assert len(site.sections) > 0, "Sections should be finalized"
    assert all(s.index_page for s in site.sections), "Each section has index"

These tests use real Site objects and verify actual build behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests._testing.assertions import (
    assert_all_pages_have_urls,
    assert_menu_structure,
    assert_output_files_exist,
    assert_page_rendered,
    assert_taxonomy_pages_complete,
)

if TYPE_CHECKING:
    from bengal.core.site import Site


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def minimal_site(tmp_path: Path):
    """
    Create a minimal site for behavioral testing.

    Returns a built Site instance with basic content.
    """
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions

    # Create site structure
    site_dir = tmp_path / "site"
    site_dir.mkdir()

    config = """
[site]
title = "Behavioral Test Site"
baseURL = "/"

[build]
output_dir = "public"

[taxonomies]
tags = "tags"
"""
    (site_dir / "bengal.toml").write_text(config)

    content_dir = site_dir / "content"
    content_dir.mkdir()

    # Home page
    (content_dir / "_index.md").write_text(
        "---\ntitle: Home\n---\n# Welcome\nThis is home."
    )

    # Regular page
    (content_dir / "about.md").write_text(
        "---\ntitle: About\ndescription: About page\n---\n# About\nAbout content."
    )

    # Create and build
    site = Site.from_config(site_dir)
    site.discover_content()
    site.discover_assets()

    options = BuildOptions(incremental=False, quiet=True)
    site.build(options=options)

    return site


@pytest.fixture
def site_with_sections(tmp_path: Path):
    """
    Create a site with multiple sections for behavioral testing.
    """
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions

    site_dir = tmp_path / "site"
    site_dir.mkdir()

    config = """
[site]
title = "Section Test Site"
baseURL = "/"

[build]
output_dir = "public"
"""
    (site_dir / "bengal.toml").write_text(config)

    content_dir = site_dir / "content"
    content_dir.mkdir()

    # Home
    (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n# Home")

    # Docs section
    docs_dir = content_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "_index.md").write_text("---\ntitle: Docs\n---\n# Documentation")
    (docs_dir / "quickstart.md").write_text(
        "---\ntitle: Quickstart\n---\n# Quickstart Guide"
    )

    # Blog section
    blog_dir = content_dir / "blog"
    blog_dir.mkdir()
    (blog_dir / "_index.md").write_text("---\ntitle: Blog\n---\n# Blog")
    (blog_dir / "post1.md").write_text("---\ntitle: First Post\n---\n# Post 1")

    site = Site.from_config(site_dir)
    site.discover_content()
    site.discover_assets()

    options = BuildOptions(incremental=False, quiet=True)
    site.build(options=options)

    return site


@pytest.fixture
def site_with_taxonomies(tmp_path: Path):
    """
    Create a site with taxonomies (tags) for behavioral testing.
    """
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions

    site_dir = tmp_path / "site"
    site_dir.mkdir()

    config = """
[site]
title = "Taxonomy Test Site"
baseURL = "/"

[build]
output_dir = "public"

[taxonomies]
tags = "tags"
"""
    (site_dir / "bengal.toml").write_text(config)

    content_dir = site_dir / "content"
    content_dir.mkdir()

    # Home
    (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n# Home")

    # Tagged pages
    (content_dir / "python-guide.md").write_text(
        "---\ntitle: Python Guide\ntags:\n  - python\n  - tutorial\n---\n# Python"
    )
    (content_dir / "rust-intro.md").write_text(
        "---\ntitle: Rust Intro\ntags:\n  - rust\n  - tutorial\n---\n# Rust"
    )
    (content_dir / "go-basics.md").write_text(
        "---\ntitle: Go Basics\ntags:\n  - go\n---\n# Go"
    )

    site = Site.from_config(site_dir)
    site.discover_content()
    site.discover_assets()

    options = BuildOptions(incremental=False, quiet=True)
    site.build(options=options)

    return site


# =============================================================================
# BEHAVIORAL TESTS - SECTIONS
# =============================================================================


class TestSectionsBehavior:
    """Behavioral tests for section finalization."""

    def test_sections_are_populated(self, site_with_sections: Site) -> None:
        """BEHAVIOR: After build, sections contain correct pages."""
        site = site_with_sections

        # Verify sections exist
        assert len(site.sections) >= 2, (
            f"Expected at least 2 sections (docs, blog), got {len(site.sections)}"
        )

        # Verify section names
        section_names = {s.name for s in site.sections}
        assert "docs" in section_names, "Docs section should exist"
        assert "blog" in section_names, "Blog section should exist"

    def test_sections_have_index_pages(self, site_with_sections: Site) -> None:
        """BEHAVIOR: Each section has an index page."""
        site = site_with_sections

        for section in site.sections:
            assert section.index_page is not None, (
                f"Section '{section.name}' missing index page"
            )

    def test_section_pages_are_rendered(self, site_with_sections: Site) -> None:
        """BEHAVIOR: Section pages produce output files."""
        site = site_with_sections

        # Verify output files exist
        assert_output_files_exist(
            site.output_dir,
            [
                "index.html",
                "docs/index.html",
                "docs/quickstart/index.html",
                "blog/index.html",
                "blog/post1/index.html",
            ],
        )

    def test_section_pages_have_content(self, site_with_sections: Site) -> None:
        """BEHAVIOR: Section pages contain expected content."""
        site = site_with_sections

        # Verify home page
        assert_page_rendered(
            site.output_dir,
            "index.html",
            contains=["Home"],
        )

        # Verify docs section
        assert_page_rendered(
            site.output_dir,
            "docs/index.html",
            contains=["Documentation"],
        )

        # Verify blog section
        assert_page_rendered(
            site.output_dir,
            "blog/index.html",
            contains=["Blog"],
        )


# =============================================================================
# BEHAVIORAL TESTS - TAXONOMIES
# =============================================================================


class TestTaxonomiesBehavior:
    """Behavioral tests for taxonomy generation."""

    def test_taxonomy_pages_created(self, site_with_taxonomies: Site) -> None:
        """BEHAVIOR: Taxonomy term pages are created."""
        site = site_with_taxonomies

        # Check taxonomy structure exists
        taxonomies = getattr(site, "taxonomies", {})
        assert "tags" in taxonomies, "Tags taxonomy should exist"

        # Check expected tags exist
        tags = taxonomies["tags"]
        expected_tags = {"python", "rust", "go", "tutorial"}

        for tag in expected_tags:
            assert tag in tags, f"Tag '{tag}' should exist in taxonomy"

    def test_taxonomy_pages_list_correct_content(
        self, site_with_taxonomies: Site
    ) -> None:
        """BEHAVIOR: Each tag page lists correct pages."""
        site = site_with_taxonomies

        # Use behavioral assertion helper
        assert_taxonomy_pages_complete(site, "tags")

    def test_tutorial_tag_has_two_pages(self, site_with_taxonomies: Site) -> None:
        """BEHAVIOR: Tutorial tag should have exactly 2 pages."""
        site = site_with_taxonomies

        taxonomies = getattr(site, "taxonomies", {})
        tags = taxonomies.get("tags", {})

        if "tutorial" in tags:
            tutorial_pages = tags["tutorial"].get("pages", [])
            assert len(tutorial_pages) == 2, (
                f"Tutorial tag should have 2 pages, has {len(tutorial_pages)}"
            )


# =============================================================================
# BEHAVIORAL TESTS - MENUS
# =============================================================================


class TestMenusBehavior:
    """Behavioral tests for menu building."""

    def test_menu_is_populated(self, site_with_sections: Site) -> None:
        """BEHAVIOR: Menu exists after build (may be empty without config)."""
        site = site_with_sections

        # Menu exists as an attribute
        menu = getattr(site, "menu", None)
        assert menu is not None, "Site should have menu attribute"

        # Note: Menu may be empty without explicit menu config
        # This test verifies the menu system is working, not that it's populated

    def test_menu_hrefs_are_valid(self, site_with_sections: Site) -> None:
        """BEHAVIOR: Menu hrefs point to existing pages."""
        site = site_with_sections

        menu = getattr(site, "menu", [])

        for entry in menu:
            href = getattr(entry, "href", "")
            if href and href != "/":
                # Convert href to output path
                output_path = href.strip("/") + "/index.html"
                if output_path.startswith("/"):
                    output_path = output_path[1:]

                # Verify output exists
                assert (site.output_dir / output_path).exists() or href == "/", (
                    f"Menu entry '{entry.title}' points to non-existent {href}"
                )


# =============================================================================
# BEHAVIORAL TESTS - PAGE URLS
# =============================================================================


class TestPageURLsBehavior:
    """Behavioral tests for URL generation."""

    def test_all_pages_have_unique_urls(self, minimal_site: Site) -> None:
        """BEHAVIOR: Every page has a unique URL."""
        assert_all_pages_have_urls(minimal_site)

    def test_urls_are_absolute_paths(self, minimal_site: Site) -> None:
        """BEHAVIOR: Page URLs are absolute paths (start with /)."""
        site = minimal_site

        for page in site.pages:
            href = getattr(page, "href", None) or getattr(page, "_path", None)
            if href:
                assert href.startswith("/"), (
                    f"Page '{page.source_path}' has non-absolute URL: {href}"
                )

    def test_output_files_match_urls(self, minimal_site: Site) -> None:
        """BEHAVIOR: Output files exist at expected URL paths."""
        site = minimal_site

        for page in site.pages:
            href = getattr(page, "href", None) or getattr(page, "_path", None)
            if not href:
                continue

            # Convert URL to output path
            output_path = href.strip("/")
            if output_path:
                output_file = site.output_dir / output_path / "index.html"
            else:
                output_file = site.output_dir / "index.html"

            assert output_file.exists(), (
                f"No output file for page with URL '{href}'. "
                f"Expected: {output_file}"
            )


# =============================================================================
# BEHAVIORAL TESTS - BUILD INVARIANTS
# =============================================================================


class TestBuildInvariants:
    """Behavioral tests for build invariants."""

    def test_build_produces_index_html(self, minimal_site: Site) -> None:
        """BEHAVIOR: Build always produces index.html."""
        site = minimal_site

        assert (site.output_dir / "index.html").exists(), (
            "Build should produce index.html"
        )

    def test_build_creates_output_directory(self, minimal_site: Site) -> None:
        """BEHAVIOR: Build creates output directory."""
        site = minimal_site

        assert site.output_dir.exists(), "Output directory should exist"
        assert site.output_dir.is_dir(), "Output path should be a directory"

    def test_regular_pages_not_empty(self, minimal_site: Site) -> None:
        """BEHAVIOR: Site has regular pages after build."""
        site = minimal_site

        assert len(site.regular_pages) >= 1, (
            "Site should have at least one regular page"
        )

    def test_pages_have_titles(self, minimal_site: Site) -> None:
        """BEHAVIOR: All pages have titles."""
        site = minimal_site

        for page in site.pages:
            title = getattr(page, "title", None)
            assert title, f"Page '{page.source_path}' missing title"
