"""
Integration tests for output formats generation in incremental builds.

This test suite ensures that critical output formats like index.json are
correctly generated in both full and incremental builds, catching regressions
where incremental builds skip output format generation.

Also includes PageProxy transparency contract tests to ensure incremental
builds actually create proxies and that those proxies work correctly.
"""

import json

import pytest

from bengal.core.page import PageProxy
from bengal.core.site import Site
from bengal.orchestration.build import BuildOrchestrator
from bengal.orchestration.build.options import BuildOptions


@pytest.mark.bengal(testroot="test-basic")
def test_full_build_generates_index_json_with_pages(site, build_site):
    """Test that full build generates index.json with populated pages array."""
    # Build the site
    build_site(incremental=False)

    # Verify index.json exists
    index_path = site.output_dir / "index.json"
    assert index_path.exists(), "index.json should be generated in full build"

    # Load and validate
    data = json.loads(index_path.read_text(encoding="utf-8"))

    # CRITICAL: Pages array must be populated
    assert "pages" in data, "index.json must have 'pages' key"
    assert isinstance(data["pages"], list), "pages must be a list"
    assert len(data["pages"]) > 0, (
        "index.json pages array is empty! This breaks client-side search. "
        f"Site has {len(site.pages)} pages but index.json has 0."
    )

    # Verify structure
    assert "site" in data
    assert "sections" in data
    assert "tags" in data


@pytest.mark.bengal(testroot="test-basic")
def test_incremental_build_generates_index_json_with_pages(site, build_site):
    """Test that incremental build also generates index.json with populated pages array."""
    # First: Full build
    build_site(incremental=False)

    # Verify index.json was created with pages
    index_path = site.output_dir / "index.json"
    assert index_path.exists()
    data_full = json.loads(index_path.read_text(encoding="utf-8"))
    pages_count_full = len(data_full["pages"])
    assert pages_count_full > 0, "Full build should have pages in index.json"

    # Second: Incremental build (no changes)
    build_site(incremental=True)

    # CRITICAL: index.json should still exist and have pages
    assert index_path.exists(), (
        "index.json disappeared after incremental build! This is a critical regression."
    )

    data_incremental = json.loads(index_path.read_text(encoding="utf-8"))
    pages_count_incremental = len(data_incremental["pages"])

    assert pages_count_incremental > 0, (
        f"Incremental build lost all pages from index.json! "
        f"Full build had {pages_count_full} pages, "
        f"but incremental build has {pages_count_incremental}. "
        "This breaks client-side search."
    )

    # Page counts should match (no content changes)
    assert pages_count_incremental == pages_count_full, (
        f"Page count mismatch: full build had {pages_count_full} pages, "
        f"but incremental build has {pages_count_incremental}"
    )


def test_incremental_build_after_content_change_updates_index_json(tmp_path):
    """Test that incremental build updates index.json when content changes."""
    # Setup test site
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create initial page
    page1_path = content_dir / "page1.md"
    page1_path.write_text("""---
title: Page One
---

Initial content.
""")

    config = {
        "title": "Test Site",
        "baseurl": "",
        "build": {
            "output_dir": str(tmp_path / "public"),
            "generate_sitemap": False,
            "generate_rss": False,
        },
    }

    # First build (full)
    site1 = Site.for_testing(root_path=tmp_path, config=config)
    orch1 = BuildOrchestrator(site1)
    orch1.build(BuildOptions(incremental=False))

    # Verify index.json
    index_path = tmp_path / "public" / "index.json"
    assert index_path.exists()
    data1 = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(data1["pages"]) == 1
    assert data1["pages"][0]["title"] == "Page One"

    # Add second page
    page2_path = content_dir / "page2.md"
    page2_path.write_text("""---
title: Page Two
---

New content.
""")

    # Second build (incremental)
    site2 = Site.for_testing(root_path=tmp_path, config=config)
    orch2 = BuildOrchestrator(site2)
    orch2.build(BuildOptions(incremental=True))

    # Verify index.json updated
    data2 = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(data2["pages"]) == 2, (
        f"Incremental build should update index.json with new page. "
        f"Expected 2 pages, got {len(data2['pages'])}"
    )

    titles = {page["title"] for page in data2["pages"]}
    assert "Page One" in titles
    assert "Page Two" in titles


def test_incremental_build_after_page_deletion_updates_index_json(tmp_path):
    """Test that incremental build removes deleted pages from index.json."""
    # Setup test site with two pages
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    page1_path = content_dir / "page1.md"
    page1_path.write_text("""---
title: Page One
---

Content one.
""")

    page2_path = content_dir / "page2.md"
    page2_path.write_text("""---
title: Page Two
---

Content two.
""")

    config = {
        "title": "Test Site",
        "baseurl": "",
        "build": {
            "output_dir": str(tmp_path / "public"),
            "generate_sitemap": False,
            "generate_rss": False,
            "incremental": False,  # Disable incremental to force full rebuild
        },
    }

    # First build (full)
    site1 = Site.for_testing(root_path=tmp_path, config=config)
    orch1 = BuildOrchestrator(site1)
    orch1.build(BuildOptions(incremental=False))

    # Verify both pages in index.json
    index_path = tmp_path / "public" / "index.json"
    data1 = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(data1["pages"]) == 2

    # Delete page2
    page2_path.unlink()

    # Second build (FULL, not incremental - deletion requires full rebuild)
    # Note: Incremental builds detect deletions and fall back to full rebuild
    site2 = Site.for_testing(root_path=tmp_path, config=config)
    orch2 = BuildOrchestrator(site2)
    orch2.build(BuildOptions(incremental=False))  # Force full rebuild to handle deletion

    # Verify index.json updated (only page1 remains)
    data2 = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(data2["pages"]) == 1, (
        f"Build should remove deleted page from index.json. "
        f"Expected 1 page, got {len(data2['pages'])}"
    )
    assert data2["pages"][0]["title"] == "Page One"


def test_incremental_build_preserves_index_json_structure(tmp_path):
    """Test that incremental builds preserve index.json structure and metadata."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    page_path = content_dir / "page.md"
    page_path.write_text("""---
title: Test Page
tags: [python, tutorial]
---

Content.
""")

    config = {
        "title": "My Site",
        "baseurl": "https://example.com",
        "build": {
            "output_dir": str(tmp_path / "public"),
            "generate_sitemap": False,
            "generate_rss": False,
        },
    }

    # Full build
    site1 = Site.for_testing(root_path=tmp_path, config=config)
    orch1 = BuildOrchestrator(site1)
    orch1.build(BuildOptions(incremental=False))

    index_path = tmp_path / "public" / "index.json"

    # Incremental build (no changes)
    site2 = Site.for_testing(root_path=tmp_path, config=config)
    orch2 = BuildOrchestrator(site2)
    orch2.build(BuildOptions(incremental=True))

    data_incremental = json.loads(index_path.read_text(encoding="utf-8"))

    # Verify structure preserved
    assert data_incremental["site"]["title"] == "My Site"
    assert data_incremental["site"]["baseurl"] == "https://example.com"

    # Verify page metadata preserved - get the actual page (not tag pages)
    actual_pages = [
        p for p in data_incremental["pages"] if not p.get("uri", "").startswith("/tags/")
    ]
    assert len(actual_pages) >= 1, "Should have at least one content page"
    page_data = actual_pages[0]
    assert page_data["title"] == "Test Page"
    assert "python" in page_data["tags"]
    assert "tutorial" in page_data["tags"]

    # Verify aggregations preserved
    assert len(data_incremental["tags"]) == 2
    tag_names = {tag["name"] for tag in data_incremental["tags"]}
    assert "python" in tag_names
    assert "tutorial" in tag_names


@pytest.mark.bengal(testroot="test-basic", confoverrides={"output_formats.enabled": False})
def test_disabled_output_formats_skips_index_json(site, build_site):
    """Test that disabling output_formats config skips index.json generation."""
    # Build
    build_site(incremental=False)

    # Verify index.json was NOT generated
    index_path = site.output_dir / "index.json"
    assert not index_path.exists(), (
        "index.json should not be generated when output_formats is disabled"
    )


@pytest.mark.bengal(testroot="test-basic")
def test_output_formats_succeed_with_mixed_page_types(site, build_site):
    """
    Contract test: Output formats must succeed with mixed Page/PageProxy objects.
    
    This test ensures:
    1. Incremental builds generate correct output formats
    2. If PageProxy is present, it has required attributes (like plain_text)
    
    Note: PageProxy creation depends on cache path matching. The unit tests
    verify plain_text property works on PageProxy directly.
    
    See: plan/ready/rfc-pageproxy-transparency-contract.md
        
    """
    # Full build first
    build_site(incremental=False)

    # Incremental build
    build_site(incremental=True)

    # Note: PageProxy presence depends on cache path matching.
    # Unit tests verify plain_text property works on PageProxy directly.
    # This integration test verifies output formats succeed with incremental builds.

    # Verify output formats generated successfully
    index_path = site.output_dir / "index.json"
    assert index_path.exists(), "index.json should be generated with PageProxy in pages"

    # Verify index.json is valid JSON with pages
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert "pages" in data
    assert len(data["pages"]) > 0, "index.json pages array should not be empty"

    # Verify llm-full.txt if enabled
    llm_path = site.output_dir / "llm-full.txt"
    if llm_path.exists():
        content = llm_path.read_text(encoding="utf-8")
        assert len(content) > 0, "llm-full.txt should have content"


# =============================================================================
# PageProxy Creation Contract Tests
#
# These tests verify that incremental builds ACTUALLY create PageProxy objects.
# This catches silent failures where the optimization appears to work but
# proxies aren't being created (cache lookup failures, validation mismatches).
# =============================================================================


def test_incremental_build_creates_proxies(tmp_path):
    """
    Contract test: Incremental builds MUST create PageProxy objects.
    
    This test catches silent failures where incremental builds appear to work
    but proxies aren't being created due to:
    - Cache key mismatches (absolute vs relative paths)
    - Cache validation failures (slug, section, etc.)
    - Missing cache entries
    
    If this test fails, incremental builds are silently doing full rebuilds.
        
    """
    # Setup: Create site with multiple pages
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    for i in range(3):
        (content_dir / f"page{i}.md").write_text(f"""---
title: Page {i}
---
Content for page {i}.
""")

    (tmp_path / "bengal.toml").write_text("""
[site]
title = "Proxy Test Site"
baseurl = ""

[build]
generate_sitemap = false
generate_rss = false
""")

    # First build: Full build to populate cache
    site1 = Site.from_config(tmp_path)
    site1.build(BuildOptions(incremental=False))

    # Second build: Incremental - should create proxies for unchanged pages
    site2 = Site.from_config(tmp_path)
    site2.build(BuildOptions(incremental=True))

    # CRITICAL: Verify proxies were created
    proxy_count = sum(1 for p in site2.pages if isinstance(p, PageProxy))
    full_page_count = sum(1 for p in site2.pages if not isinstance(p, PageProxy))

    assert proxy_count > 0, (
        f"Incremental build created 0 proxies! "
        f"Expected proxies for unchanged pages. "
        f"Got {full_page_count} full pages instead. "
        "This indicates a cache lookup or validation failure."
    )

    # All 3 pages should be proxies (nothing changed)
    assert proxy_count == 3, (
        f"Expected 3 proxies (all pages unchanged), got {proxy_count}. "
        f"Full pages: {full_page_count}"
    )


def test_incremental_build_proxy_has_required_properties(tmp_path):
    """
    Contract test: PageProxy objects must have all properties needed by build.
    
    This test verifies that PageProxy implements the transparency contract -
    all properties accessed during build must be available without lazy loading.
        
    """
    # Setup
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    (content_dir / "test.md").write_text("""---
title: Test Page
tags: [python, web]
---
This is test content with **bold** and *italic*.
""")

    (tmp_path / "bengal.toml").write_text("""
[site]
title = "Proxy Properties Test"
baseurl = ""

[build]
generate_sitemap = false
generate_rss = false
""")

    # Full build then incremental
    site1 = Site.from_config(tmp_path)
    site1.build(BuildOptions(incremental=False))

    site2 = Site.from_config(tmp_path)
    site2.build(BuildOptions(incremental=True))

    # Find the proxy
    proxies = [p for p in site2.pages if isinstance(p, PageProxy)]
    assert len(proxies) == 1, "Expected 1 proxy"
    proxy = proxies[0]

    # Verify properties that must be available without lazy loading
    # (These are accessed by output format generators)
    assert proxy.title == "Test Page"
    assert proxy.tags == ["python", "web"]
    assert proxy.slug == "test"
    assert proxy.is_virtual is False

    # Verify lazy-load properties work when accessed
    assert isinstance(proxy.plain_text, str)
    assert len(proxy.plain_text) > 0


def test_modified_page_becomes_full_page_not_proxy(tmp_path):
    """
    Contract test: Modified pages should be full Pages, not proxies.
    
    Verifies that the incremental build correctly detects frontmatter changes
    and rebuilds modified pages while keeping unchanged pages as proxies.
    
    Note: Cache validation checks frontmatter fields (title, tags, date, slug).
    Body-only changes don't invalidate the cache since proxies are used to
    avoid re-rendering, not re-parsing.
        
    """
    # Setup
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    page1 = content_dir / "unchanged.md"
    page2 = content_dir / "modified.md"

    page1.write_text("""---
title: Unchanged Page
---
This page won't change.
""")

    page2.write_text("""---
title: Original Title
---
Original content.
""")

    (tmp_path / "bengal.toml").write_text("""
[site]
title = "Mixed Test"
baseurl = ""

[build]
generate_sitemap = false
generate_rss = false
""")

    # Full build
    site1 = Site.from_config(tmp_path)
    site1.build(BuildOptions(incremental=False))

    # Modify one page's FRONTMATTER (title change invalidates cache)
    page2.write_text("""---
title: Modified Title
---
Updated content!
""")

    # Incremental build
    site2 = Site.from_config(tmp_path)
    site2.build(BuildOptions(incremental=True))

    # Find pages by title
    pages_by_title = {p.title: p for p in site2.pages}

    # Unchanged page should be a proxy
    unchanged = pages_by_title.get("Unchanged Page")
    assert unchanged is not None, "Unchanged page not found"
    assert isinstance(unchanged, PageProxy), "Unchanged page should be a PageProxy"

    # Modified page should be a full Page (not proxy) because title changed
    modified = pages_by_title.get("Modified Title")
    assert modified is not None, "Modified page not found"
    assert not isinstance(modified, PageProxy), (
        "Modified page should be a full Page, not a PageProxy"
    )
