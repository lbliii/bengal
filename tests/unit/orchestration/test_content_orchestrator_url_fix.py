"""
Tests for ContentOrchestrator output_path setting.

Regression test for critical bug where child pages in sections had incorrect URLs
because output_path was not set until rendering phase.

Bug Symptoms:
- Source: content/reference/page-1.md
- Expected URL: /reference/page-1/
- Actual URL: /page-1/ (wrong! missing section prefix)
- Result: 404 errors, links broken in templates

Root Cause:
- page.href property depends on page.output_path
- If output_path is None, it falls back to f"/{slug}/"
- output_path was only set during rendering (too late)
- Templates accessed page.href before rendering → got wrong URLs

Fix:
- ContentOrchestrator now sets output_path immediately after discovery
- Ensures page.href returns correct paths before any template accesses it
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from bengal.core.site import Site
from bengal.orchestration.content import ContentOrchestrator


class TestContentOrchestratorOutputPathSetting:
    """Test that ContentOrchestrator sets output_path during discovery."""

    @pytest.fixture
    def test_site(self):
        """Create a temporary test site with nested content."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content_dir = root / "content"

            # Create directory structure
            (content_dir / "reference").mkdir(parents=True, exist_ok=True)
            (content_dir / "guides" / "advanced").mkdir(parents=True, exist_ok=True)

            # Create section index
            (content_dir / "reference" / "_index.md").write_text(
                "---\ntitle: Reference\ntype: doc\ncascade:\n  type: doc\n---\n# Reference"
            )

            # Create child pages in reference section
            (content_dir / "reference" / "page-1.md").write_text(
                "---\ntitle: Page 1\n---\n# Page 1 Content"
            )
            (content_dir / "reference" / "page-2.md").write_text(
                "---\ntitle: Page 2\n---\n# Page 2 Content"
            )

            # Create nested section
            (content_dir / "guides" / "advanced" / "_index.md").write_text(
                "---\ntitle: Advanced Guides\n---\n# Advanced"
            )
            (content_dir / "guides" / "advanced" / "optimization.md").write_text(
                "---\ntitle: Optimization\n---\n# Optimization Guide"
            )

            # Create site
            site = Site(root_path=root, config={})
            yield site

    def test_output_path_set_during_discovery(self, test_site):
        """
        Test that output_path is set for all pages immediately after discovery.

        This is the core regression test for the URL bug.
        """
        orchestrator = ContentOrchestrator(test_site)

        # Run discovery
        orchestrator.discover()

        # Verify ALL pages have output_path set
        for page in test_site.pages:
            assert page.output_path is not None, (
                f"Page {page.source_path.name} has no output_path after discovery! "
                f"This will cause incorrect URLs."
            )

            # Verify output_path is absolute
            assert page.output_path.is_absolute(), (
                f"Page {page.source_path.name} has relative output_path: {page.output_path}"
            )

            # Verify output_path is under output_dir
            assert page.output_path.is_relative_to(test_site.output_dir), (
                f"Page {page.source_path.name} output_path not under output_dir: {page.output_path}"
            )

    def test_child_pages_have_correct_urls_after_discovery(self, test_site):
        """
        Test that child pages in sections have correct URLs immediately after discovery.

        This ensures templates can access page.href without getting fallback slug-based URLs.
        """
        orchestrator = ContentOrchestrator(test_site)
        orchestrator.discover()

        # Find child pages in reference section
        reference_pages = [
            p
            for p in test_site.pages
            if "reference" in str(p.source_path) and p.source_path.stem not in ("_index", "index")
        ]

        assert len(reference_pages) >= 2, "Should have at least 2 child pages in reference section"

        # Verify URLs include section prefix
        for page in reference_pages:
            url = page.href
            assert url.startswith("/reference/"), (
                f"Page {page.source_path.name} has wrong URL: {url} "
                f"(should start with /reference/, not /{page.slug}/)"
            )

            # Verify URL is not just the slug
            assert url != f"/{page.slug}/", (
                f"Page {page.source_path.name} URL is slug-only fallback: {url} "
                f"(this means output_path was not set correctly)"
            )

    def test_nested_section_pages_have_correct_urls(self, test_site):
        """Test that pages in nested sections have correct full paths."""
        orchestrator = ContentOrchestrator(test_site)
        orchestrator.discover()

        # Find page in nested section (guides/advanced/optimization.md)
        nested_page = None
        for page in test_site.pages:
            if "optimization" in str(page.source_path).lower():
                nested_page = page
                break

        assert nested_page is not None, "Should find optimization.md in nested section"

        # Verify URL includes full path
        assert nested_page.href.startswith("/guides/advanced/"), (
            f"Nested page has wrong URL: {nested_page.href} "
            f"(should include full path /guides/advanced/...)"
        )

    def test_section_index_pages_have_correct_urls(self, test_site):
        """Test that section index pages (_index.md) have correct URLs."""
        orchestrator = ContentOrchestrator(test_site)
        orchestrator.discover()

        # Find _index.md pages
        index_pages = [p for p in test_site.pages if p.source_path.stem in ("_index", "index")]

        assert len(index_pages) >= 2, "Should have at least 2 index pages"

        for page in index_pages:
            # Index pages should have section URL (ending with /)
            assert page.href.endswith("/"), f"Index page URL should end with /: {page.href}"

            # Should not be just "/" unless it's the root index
            if "reference" in str(page.source_path):
                assert page.href == "/reference/", (
                    f"Reference index should be /reference/, got {page.href}"
                )
            elif "advanced" in str(page.source_path):
                assert page.href == "/guides/advanced/", (
                    f"Advanced index should be /guides/advanced/, got {page.href}"
                )

    def test_url_generation_works_before_rendering(self, test_site):
        """
        Simulate template accessing page.href before rendering phase.

        This mimics what happens in doc/list.html when it loops through child pages.
        """
        orchestrator = ContentOrchestrator(test_site)
        orchestrator.discover()

        # Get a section (like reference)
        reference_section = None
        for section in test_site.sections:
            if section.name == "reference":
                reference_section = section
                break

        assert reference_section is not None, "Should find reference section"

        # Simulate template loop: {% for page in section.pages %}
        nav_links = [{"title": page.title, "url": page.href} for page in reference_section.pages]

        # Verify all nav links have correct section prefix
        for link in nav_links:
            if link["title"] != "Reference":  # Skip the index page
                assert link["url"].startswith("/reference/"), (
                    f"Nav link for {link['title']} has wrong URL: {link['url']}"
                )

    def test_cascade_type_doc_preserves_urls(self, test_site):
        """
        Test that cascade: type: doc doesn't break URLs.

        This was the original symptom - adding cascade: doc caused 404s.
        """
        orchestrator = ContentOrchestrator(test_site)
        orchestrator.discover()

        # Find pages that inherited type: doc via cascade
        cascaded_pages = [
            p
            for p in test_site.pages
            if p.metadata.get("type") == "doc" and "cascade" not in p.metadata
        ]

        assert len(cascaded_pages) >= 2, "Should have pages with cascaded type: doc"

        # Verify cascaded pages still have correct URLs
        for page in cascaded_pages:
            # URL should include parent directory
            if "reference" in str(page.source_path):
                assert page.href.startswith("/reference/"), (
                    f"Cascaded doc page has wrong URL: {page.href}"
                )

    def test_no_duplicate_output_path_setting(self, test_site):
        """Test that output_path isn't set multiple times unnecessarily."""
        orchestrator = ContentOrchestrator(test_site)
        orchestrator.discover()

        # Save original output paths
        original_paths = {page.source_path: page.output_path for page in test_site.pages}

        # Call _set_output_paths again via site (shouldn't change anything)
        test_site._set_output_paths()

        # Verify paths unchanged
        for page in test_site.pages:
            assert page.output_path == original_paths[page.source_path], (
                f"Page {page.source_path.name} output_path changed on re-call"
            )


class TestRegressionScenarios:
    """Test specific scenarios that triggered the original bug."""

    def test_docs_quickstart_scenario(self):
        """
        Test the exact scenario from the bug report:
        - User runs `bengal new site mysite`
        - Chooses docs template
        - Child pages appear at wrong URLs
        """
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content_dir = root / "content"

            # Simulate docs template structure
            getting_started = content_dir / "getting-started"
            getting_started.mkdir(parents=True, exist_ok=True)

            # Create _index.md with cascade
            (getting_started / "_index.md").write_text(
                "---\n"
                "title: Getting Started\n"
                "type: doc\n"
                "cascade:\n"
                "  type: doc\n"
                "---\n"
                "# Getting Started"
            )

            # Create child pages
            (getting_started / "installation.md").write_text(
                "---\ntitle: Installation\n---\n# Install"
            )
            (getting_started / "quickstart.md").write_text(
                "---\ntitle: Quick Start\n---\n# Quick Start"
            )

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()

            # Find child pages
            child_pages = [
                p for p in site.pages if p.source_path.stem in ("installation", "quickstart")
            ]

            # The bug: these would have URLs /installation/ and /quickstart/
            # Fixed: they should have /getting-started/installation/ etc.
            for page in child_pages:
                assert page.href.startswith("/getting-started/"), (
                    f"Child page {page.source_path.name} has incorrect URL: {page.href}\n"
                    f"Expected to start with /getting-started/, got {page.href}\n"
                    f"This is the original bug - child pages missing section prefix!"
                )

    def test_showcase_example_urls(self):
        """Test that showcase example has correct URLs."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content_dir = root / "content" / "docs" / "writing"
            content_dir.mkdir(parents=True, exist_ok=True)

            # Create writing section
            (content_dir / "_index.md").write_text(
                "---\ntitle: Writing Guide\ntype: doc\ncascade:\n  type: doc\n---"
            )
            (content_dir / "getting-started.md").write_text(
                "---\ntitle: Getting Started\n---\n# Start"
            )
            (content_dir / "markdown-basics.md").write_text(
                "---\ntitle: Markdown Basics\n---\n# Basics"
            )

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()

            # These pages should have full path URLs
            for page in site.pages:
                if page.source_path.stem in ("getting-started", "markdown-basics"):
                    assert page.href.startswith("/docs/writing/"), (
                        f"Showcase page {page.source_path.name} has wrong URL: {page.href}"
                    )
