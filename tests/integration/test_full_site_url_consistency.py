"""
Integration test for full site URL consistency.

Tests a complete site build with multiple content types, nested sections,
and various template patterns to ensure ALL URLs are correct throughout.

This is the ultimate regression test - if this passes, URLs work everywhere.
"""


import pytest


@pytest.mark.slow
class TestFullSiteUrlConsistency:
    """
    Integration tests ensuring URL consistency across full site builds.
    Marked slow due to full site construction.
    """

    @pytest.mark.parametrize(
        "page_path, expected_url",
        [
            ("content/page_0.md", "/page_0/"),
            ("content/page_1.md", "/page_1/"),
            ("content/page_2.md", "/page_2/"),
            ("content/page_3.md", "/page_3/"),
            ("content/page_4.md", "/page_4/"),
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

    def test_no_url_collisions(self, shared_site_class):
        """No two pages should have the same URL."""
        site = shared_site_class
        if not site.pages:
            site.discover_content()
            site.discover_assets()
            site.build(parallel=False)

        urls = [p.url for p in site.pages]
        url_counts = {}
        for url in urls:
            url_counts[url] = url_counts.get(url, 0) + 1

        duplicates = {url: count for url, count in url_counts.items() if count > 1}
        assert not duplicates, f"Duplicate URLs found: {duplicates}"

    def test_all_output_paths_set(self, shared_site_class):
        """Every page should have output_path set after discovery."""
        site = shared_site_class
        if not site.pages:
            site.discover_content()
            site.discover_assets()
            site.build(parallel=False)

        missing_output_path = []
        for page in site.pages:
            if page.output_path is None:
                missing_output_path.append(str(page.source_path))

        assert not missing_output_path, "Pages missing output_path:\n" + "\n".join(
            missing_output_path
        )
