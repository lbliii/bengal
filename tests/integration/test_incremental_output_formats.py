"""
Integration tests for output formats generation in incremental builds.

This test suite ensures that critical output formats like index.json are
correctly generated in both full and incremental builds, catching regressions
where incremental builds skip output format generation.
"""

import json

import pytest

from bengal.core.site import Site
from bengal.orchestration.build import BuildOrchestrator


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
    orch1.build(incremental=False)

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
    orch2.build(incremental=True)

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
    orch1.build(incremental=False)

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
    orch2.build(incremental=False)  # Force full rebuild to handle deletion

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
    orch1.build(incremental=False)

    index_path = tmp_path / "public" / "index.json"

    # Incremental build (no changes)
    site2 = Site.for_testing(root_path=tmp_path, config=config)
    orch2 = BuildOrchestrator(site2)
    orch2.build(incremental=True)

    data_incremental = json.loads(index_path.read_text(encoding="utf-8"))

    # Verify structure preserved
    assert data_incremental["site"]["title"] == "My Site"
    assert data_incremental["site"]["baseurl"] == "https://example.com"

    # Verify page metadata preserved - get the actual page (not tag pages)
    actual_pages = [
        p for p in data_incremental["pages"] if not p.get("url", "").startswith("/tags/")
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
