"""
Integration tests for autodoc navigation.

These tests verify that autodoc-generated pages appear correctly in navigation
and that there are no URL collisions within autodoc namespaces.

Created after debugging session where CLI navigation was empty due to
URL collision between section index and root command page.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from bengal.core.site import Site


@pytest.fixture
def site_with_autodoc(tmp_path: Path) -> Site:
    """Create a minimal site with autodoc enabled for testing."""
    from bengal.core.site import Site

    # Create minimal site structure
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n# Home")

    config_dir = tmp_path / "config" / "_default"
    config_dir.mkdir(parents=True)

    # Site config
    (config_dir / "site.yaml").write_text(
        """
site:
  title: Test Site
  baseurl: ""
"""
    )

    # Autodoc config - enable CLI autodoc
    (config_dir / "autodoc.yaml").write_text(
        """
autodoc:
  cli:
    enabled: true
    app_path: bengal.cli:app
    output_prefix: cli
  python:
    enabled: false
"""
    )

    site = Site.from_config(tmp_path)
    return site


class TestURLUniqueness:
    """Tests that verify no URL collisions occur."""

    def test_no_duplicate_urls_in_site(self, site_with_autodoc: Site) -> None:
        """Every page should have a unique URL."""
        from bengal.orchestration.content import ContentOrchestrator

        content = ContentOrchestrator(site_with_autodoc)
        content.discover_content()

        urls_seen: dict[str, str] = {}
        duplicates: list[str] = []

        for page in site_with_autodoc.pages:
            url = getattr(page, "relative_url", None) or getattr(page, "url", "/")
            source = str(getattr(page, "source_path", page.title))

            if url in urls_seen:
                duplicates.append(
                    f"URL collision: {url}\n  Page 1: {urls_seen[url]}\n  Page 2: {source}"
                )
            else:
                urls_seen[url] = source

        assert not duplicates, "\n".join(duplicates)


class TestCLIAutodocNavigation:
    """Tests for CLI autodoc navigation."""

    @pytest.mark.skipif(
        not Path("bengal/cli/__init__.py").exists(),
        reason="CLI module not available",
    )
    def test_cli_section_exists_in_navtree(self, site_with_autodoc: Site) -> None:
        """CLI section should appear in NavTree."""
        from bengal.core.nav_tree import NavTree
        from bengal.orchestration.content import ContentOrchestrator

        content = ContentOrchestrator(site_with_autodoc)
        content.discover_content()

        # Skip if autodoc didn't find any CLI elements
        cli_sections = [s for s in site_with_autodoc.sections if s.name == "cli"]
        if not cli_sections:
            pytest.skip("CLI autodoc did not generate any sections")

        nav = NavTree.build(site_with_autodoc)
        cli_node = nav.find("/cli/")

        assert cli_node is not None, "CLI section not found in NavTree at /cli/"

    @pytest.mark.skipif(
        not Path("bengal/cli/__init__.py").exists(),
        reason="CLI module not available",
    )
    def test_cli_section_is_section_not_page(self, site_with_autodoc: Site) -> None:
        """CLI root should be a section node, not a page node."""
        from bengal.core.nav_tree import NavTree
        from bengal.orchestration.content import ContentOrchestrator

        content = ContentOrchestrator(site_with_autodoc)
        content.discover_content()

        # Skip if autodoc didn't find any CLI elements
        cli_sections = [s for s in site_with_autodoc.sections if s.name == "cli"]
        if not cli_sections:
            pytest.skip("CLI autodoc did not generate any sections")

        nav = NavTree.build(site_with_autodoc)
        cli_node = nav.find("/cli/")

        if cli_node is None:
            pytest.skip("CLI section not found in NavTree")

        # The node should represent a section, not just a page
        assert cli_node.section is not None or cli_node.is_index, (
            f"CLI node at /cli/ should be a section node, "
            f"got: section={cli_node.section}, is_index={cli_node.is_index}, "
            f"page={cli_node.page}"
        )

    @pytest.mark.skipif(
        not Path("bengal/cli/__init__.py").exists(),
        reason="CLI module not available",
    )
    def test_cli_section_has_children(self, site_with_autodoc: Site) -> None:
        """CLI section should have navigable children (subcommands)."""
        from bengal.core.nav_tree import NavTree
        from bengal.orchestration.content import ContentOrchestrator

        content = ContentOrchestrator(site_with_autodoc)
        content.discover_content()

        # Skip if autodoc didn't find any CLI elements
        cli_sections = [s for s in site_with_autodoc.sections if s.name == "cli"]
        if not cli_sections:
            pytest.skip("CLI autodoc did not generate any sections")

        nav = NavTree.build(site_with_autodoc)
        cli_node = nav.find("/cli/")

        if cli_node is None:
            pytest.skip("CLI section not found in NavTree")

        # Should have children (build, serve, clean, etc.)
        assert len(cli_node.children) > 0, (
            f"CLI section has no children in navigation. "
            f"Expected subcommands like build, serve, clean. "
            f"Node: {cli_node}"
        )


class TestNavTreeCollisions:
    """Tests that NavTree handles potential collisions correctly."""

    def test_section_index_and_page_at_same_url(self, tmp_path: Path) -> None:
        """
        Regression test: Section index and element page at same URL.

        This was the bug that caused CLI navigation to be empty.
        The root command page was overwriting the section node in NavTree.
        """
        from bengal.core.nav_tree import NavTree
        from bengal.core.page import Page
        from bengal.core.section import Section
        from bengal.core.site import Site

        # Create minimal site
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n")

        config_dir = tmp_path / "config" / "_default"
        config_dir.mkdir(parents=True)
        (config_dir / "site.yaml").write_text("site:\n  title: Test\n")

        site = Site.from_config(tmp_path)

        # Create a section with an index page
        section = Section.create_virtual(
            name="test",
            relative_url="/test/",
            title="Test Section",
            metadata={"type": "test"},
        )

        # Create section index page
        index_page = Page.create_virtual(
            source_id="__virtual__/test/section-index.md",
            title="Test Section Index",
            metadata={"type": "test"},
            output_path=site.output_dir / "test/index.html",
        )
        index_page._site = site
        section.index_page = index_page
        section.pages.append(index_page)

        # Add section to site
        site.sections.append(section)
        site.pages.append(index_page)

        # Build NavTree
        nav = NavTree.build(site)
        test_node = nav.find("/test/")

        # The section node should exist and represent the section
        assert test_node is not None, "Section node not found"
        assert test_node.section == section or test_node.is_index, (
            f"Node at /test/ should represent the section, not just a page. "
            f"Got: section={test_node.section}, page={test_node.page}"
        )
