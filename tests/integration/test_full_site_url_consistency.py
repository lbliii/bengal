"""
Integration test for full site URL consistency.

Tests a complete site build with multiple content types, nested sections,
and various template patterns to ensure ALL URLs are correct throughout.

This is the ultimate regression test - if this passes, URLs work everywhere.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from bengal.core.site import Site
from bengal.orchestration.build import BuildOrchestrator


@pytest.mark.slow
class TestFullSiteUrlConsistency:
    """
    Integration tests ensuring URL consistency across full site builds.
    Marked slow due to full site construction.
    """

    @pytest.mark.parametrize(
        "page_path, expected_url",
        [
            ("content/index.md", "/"),
            ("content/blog/post1.md", "/blog/post1/"),
            ("content/docs/api/_index.md", "/docs/api/"),
            ("content/docs/api/endpoint.md", "/docs/api/endpoint/"),
            ("content/products/product-a.md", "/products/product-a/"),
        ],
    )
    def test_url_generation_consistency(self, shared_site_class, page_path, expected_url):
        """
        Test URL generation consistency across different page types and hierarchies.

        Uses shared site to avoid rebuilding for each param.
        """
        site = shared_site_class

        # Discover and build if not already (fixture handles)
        if not site.pages:
            site.discover_content()
            site.discover_assets()
            site.build(parallel=False)

        # Find the page
        test_page = None
        for page in site.pages:
            if str(page.source_path.relative_to(site.root_path)) == page_path:
                test_page = page
                break

        assert test_page is not None, f"Page {page_path} not found in site"

        # Verify URL
        actual_url = test_page.url
        assert actual_url == expected_url, f"Expected {expected_url}, got {actual_url}"

        # Additional checks: trailing slash, no double slashes, relative to baseurl
        assert actual_url.endswith("/"), "URLs should end with / for directories"
        assert "//" not in actual_url, "No double slashes"
        assert actual_url.startswith("/"), "Absolute path from root"

    def test_nested_sections_preserve_hierarchy(self, complete_site):
        """Deeply nested pages should include full path."""
        orchestrator = BuildOrchestrator(complete_site)
        orchestrator.content.discover()
        orchestrator.sections.finalize_sections()

        # Find optimization.md (deeply nested: docs/guides/advanced/optimization.md)
        optimization = None
        for page in complete_site.pages:
            if "optimization" in str(page.source_path):
                optimization = page
                break

        assert optimization is not None
        assert (
            optimization.url == "/docs/guides/advanced/optimization/"
        ), f"Deeply nested page has wrong URL: {optimization.url}"

    def test_cascade_types_preserved(self, complete_site):
        """All pages should have correct types from cascade."""
        orchestrator = BuildOrchestrator(complete_site)
        orchestrator.content.discover()
        orchestrator.sections.finalize_sections()

        # Check types
        type_checks = [
            ("installation", "doc"),
            ("post-1", "blog"),
            ("basics.md", ["tutorial", "doc"]),  # Could be either (multiple with same name)
            ("utils", "python-module"),  # Explicit type in frontmatter overrides cascade
        ]

        for filename, expected_type in type_checks:
            pages = [p for p in complete_site.pages if filename in str(p.source_path)]
            if pages:
                page = pages[0]
                actual_type = page.metadata.get("type")
                if isinstance(expected_type, list):
                    assert (
                        actual_type in expected_type
                    ), f"Page {filename} has wrong type: {actual_type}"
                else:
                    assert (
                        actual_type == expected_type
                    ), f"Page {filename} has wrong type: {actual_type}"

    def test_no_url_collisions(self, complete_site):
        """No two pages should have the same URL."""
        orchestrator = BuildOrchestrator(complete_site)
        orchestrator.content.discover()
        orchestrator.sections.finalize_sections()

        urls = [p.url for p in complete_site.pages]
        url_counts = {}
        for url in urls:
            url_counts[url] = url_counts.get(url, 0) + 1

        duplicates = {url: count for url, count in url_counts.items() if count > 1}
        assert not duplicates, f"Duplicate URLs found: {duplicates}"

    def test_all_output_paths_set(self, complete_site):
        """Every page should have output_path set after discovery."""
        orchestrator = BuildOrchestrator(complete_site)
        orchestrator.content.discover()
        orchestrator.sections.finalize_sections()

        missing_output_path = []
        for page in complete_site.pages:
            if page.output_path is None:
                missing_output_path.append(str(page.source_path))

        assert not missing_output_path, "Pages missing output_path:\n" + "\n".join(
            missing_output_path
        )

    def test_tagged_content_across_sections(self, complete_site):
        """Tagged content in different sections should maintain correct URLs."""
        orchestrator = BuildOrchestrator(complete_site)
        orchestrator.content.discover()
        orchestrator.sections.finalize_sections()

        # Find all pages with "python" tag
        python_pages = [p for p in complete_site.pages if "python" in p.metadata.get("tags", [])]

        # Should have pages from blog
        blog_python = [p for p in python_pages if "blog" in str(p.source_path)]
        assert len(blog_python) >= 2

        for page in blog_python:
            assert page.url.startswith("/blog/"), f"Tagged blog page wrong URL: {page.url}"

    def test_auto_generated_archives_work(self, complete_site):
        """Auto-generated archives should be created with correct URLs."""
        orchestrator = BuildOrchestrator(complete_site)
        orchestrator.content.discover()
        orchestrator.sections.finalize_sections()

        # Changelog should have auto-generated archive
        changelog_section = [s for s in complete_site.sections if s.name == "changelog"]

        if changelog_section:
            section = changelog_section[0]
            assert section.index_page is not None, "Archive should be auto-generated"

            # Archive should have correct URL
            assert (
                section.index_page.url == "/changelog/"
            ), f"Auto-generated archive wrong URL: {section.index_page.url}"

            # Child pages should have correct URLs
            release_pages = [
                p
                for p in complete_site.pages
                if "changelog" in str(p.source_path) and not p.metadata.get("_generated")
            ]

            for page in release_pages:
                assert page.url.startswith("/changelog/"), f"Changelog entry wrong URL: {page.url}"


class TestRealWorldScenario:
    """Test real-world usage scenario end-to-end."""

    def test_full_build_cycle(self):
        """Simulate complete build cycle like real usage."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content = root / "content"

            # Create minimal but realistic structure
            docs = content / "docs"
            (docs / "advanced").mkdir(parents=True, exist_ok=True)

            (docs / "_index.md").write_text(
                "---\ntitle: Documentation\ntype: doc\ncascade:\n  type: doc\n---"
            )
            (docs / "quickstart.md").write_text("---\ntitle: Quick Start\n---")
            (docs / "advanced" / "config.md").write_text("---\ntitle: Configuration\n---")

            # Build site
            site = Site(root_path=root, config={})
            orchestrator = BuildOrchestrator(site)

            # Discover
            orchestrator.content.discover()

            # Finalize
            orchestrator.sections.finalize_sections()

            # Verify URLs immediately after discovery (before rendering)
            quickstart = [p for p in site.pages if "quickstart" in str(p.source_path)][0]
            config = [p for p in site.pages if "config" in str(p.source_path)][0]

            assert (
                quickstart.url == "/docs/quickstart/"
            ), f"Quickstart wrong URL after discovery: {quickstart.url}"
            assert (
                config.url == "/docs/advanced/config/"
            ), f"Config wrong URL after discovery: {config.url}"

            # Types should be cascaded
            assert quickstart.metadata.get("type") == "doc"
            assert config.metadata.get("type") == "doc"
