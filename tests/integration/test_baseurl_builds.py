"""Integration tests for baseurl handling during builds.

Validates that baseurl configuration (via config and BENGAL_BASEURL env var)
correctly affects asset links, page URLs, index.json output, template data
attributes, and graph JSON node URLs.

Uses Phase 1 infrastructure: @pytest.mark.bengal with test-baseurl root.
"""

import json
import re

import pytest


@pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/bengal"})
def test_build_with_path_baseurl(site, build_site):
    """Test that path-based baseurl is applied to assets and URLs."""
    # Build the site with baseurl="/bengal"
    build_site()

    # Assert assets and index.json present
    assert (site.output_dir / "assets").exists()
    index_path = site.output_dir / "index.json"
    assert index_path.exists()

    # Validate HTML contains baseurl-prefixed CSS
    html = (site.output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="/bengal/assets/css/style' in html

    # Validate index.json shape and baseurl
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data.get("site", {}).get("baseurl") == "/bengal"
    assert isinstance(data.get("pages"), list)
    if data["pages"]:
        sample = data["pages"][0]
        assert "url" in sample and "uri" in sample


@pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/bengal"})
def test_template_data_attributes_include_baseurl(site, build_site):
    """Test that template data-page-url attributes include baseurl.

    Regression test for: graph-contextual data-page-url was using
    page.relative_url instead of page.url, causing URL mismatch in JS.
    """
    build_site()

    html = (site.output_dir / "index.html").read_text(encoding="utf-8")

    # Check for data-page-url attribute with baseurl prefix
    # Pattern: data-page-url="/bengal/..." (should include baseurl)
    data_url_pattern = re.search(r'data-page-url="([^"]*)"', html)
    if data_url_pattern:
        data_url = data_url_pattern.group(1)
        # If data-page-url exists, it should include baseurl
        assert data_url.startswith("/bengal"), (
            f"data-page-url should include baseurl, got: {data_url}"
        )


@pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/bengal"})
def test_graph_json_urls_not_doubled(site, build_site):
    """Test that graph.json URLs don't have doubled baseurl.

    Regression test for: GraphVisualizer was prepending baseurl even when
    page.url already included it, causing /bengal/bengal/... paths.
    """
    build_site()

    graph_path = site.output_dir / "graph" / "graph.json"
    if not graph_path.exists():
        pytest.skip("graph.json not generated (graph feature may be disabled)")

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])

    for node in nodes:
        url = node.get("url", "")
        # URL should NOT contain doubled baseurl
        assert "/bengal/bengal/" not in url, f"Graph node URL has doubled baseurl: {url}"
        # URL should start with baseurl (if internal)
        if url.startswith("/"):
            assert url.startswith("/bengal/"), f"Graph node URL missing baseurl: {url}"


@pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/bengal"})
def test_internal_markdown_links_transformed(site, build_site):
    """Test that internal markdown links get baseurl prepended.

    Regression test for: Standard markdown links like [text](/path/) were
    not transformed to include baseurl, breaking links on GitHub Pages.

    Note: This tests the link_transformer module, which transforms links
    within markdown-rendered content. Template-generated links (like RSS)
    are handled separately by templates using {{ url }} filters.
    """
    build_site()

    # Check any HTML file that might have internal links
    html_files = list(site.output_dir.glob("**/*.html"))
    assert html_files, "No HTML files generated"

    # Known template-generated links that are handled separately
    # These are not from markdown content, so link_transformer doesn't apply
    template_links = {"/rss.xml", "/sitemap.xml", "/index.json", "/llms.txt"}

    for html_file in html_files[:5]:  # Check first 5 files
        html = html_file.read_text(encoding="utf-8")

        # Find links within <article> or <main> content (markdown-rendered area)
        # This excludes header/footer template links
        content_match = re.search(
            r"<(?:article|main)[^>]*>(.*?)</(?:article|main)>", html, re.DOTALL
        )
        if not content_match:
            continue

        content_html = content_match.group(1)

        # Find all href="/..." links in content area
        internal_links = re.findall(r'href="(/[^"]*)"', content_html)

        for link in internal_links:
            # Skip asset links, known template links, and root
            if (
                link.startswith("/bengal/assets/")
                or link == "/"
                or link in template_links
                or link.startswith("/bengal")
            ):
                continue

            # Internal content links should have baseurl prefix
            pytest.fail(
                f"Internal content link missing baseurl in {html_file.name}: {link}\n"
                f"Expected: /bengal{link}"
            )


def test_build_with_env_absolute_baseurl(site_factory, monkeypatch):
    """Test that BENGAL_BASEURL env var overrides config baseurl."""
    from bengal.orchestration.build.options import BuildOptions

    # Override baseurl via environment variable BEFORE creating site
    monkeypatch.setenv("BENGAL_BASEURL", "https://example.com/sub")

    # Create site with empty baseurl (env var will override)
    site = site_factory("test-baseurl", confoverrides={"site.baseurl": ""})

    # Build the site
    options = BuildOptions(force_sequential=True, incremental=False)
    site.build(options)

    # Validate HTML contains absolute baseurl-prefixed CSS
    html = (site.output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="https://example.com/sub/assets/css/style' in html

    # Validate index.json uses absolute baseurl
    index_path = site.output_dir / "index.json"
    assert index_path.exists()
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data.get("site", {}).get("baseurl") == "https://example.com/sub"
    assert isinstance(data.get("pages"), list)
    if data["pages"]:
        sample = data["pages"][0]
        assert sample["url"].startswith("https://example.com/sub/")
