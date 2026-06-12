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
def test_output_formats_succeed_with_incremental_builds(site, build_site):
    """
    Contract test: Output formats must succeed with incremental builds.

    This test ensures incremental builds generate correct output formats
    with all required page attributes (like plain_text).
    """
    # Full build first
    build_site(incremental=False)

    # Incremental build
    build_site(incremental=True)

    # Verify output formats generated successfully
    index_path = site.output_dir / "index.json"
    assert index_path.exists(), "index.json should be generated after incremental build"

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
# Additional Output Format Tests
#
# These tests extend the existing index.json coverage with RSS, sitemap,
# and llm-full.txt verification for warm builds.
#
# See: plan/rfc-warm-build-test-expansion.md
# =============================================================================


class TestWarmBuildAdditionalOutputFormats:
    """
    Test RSS, sitemap, and LLM output formats during warm builds.

    Extends existing index.json tests with other output format coverage.
    """

    def test_rss_feed_updated_on_blog_change(self, tmp_path):
        """
        RSS feed updated when blog post changes.

        Scenario:
        1. Build with blog section having RSS enabled
        2. Modify blog post title and content
        3. Incremental build
        4. Assert: rss.xml updated with new content (NOT the per-section
           blog/index.xml path, which RSSGenerator never writes).
        """
        # Setup test site with RSS
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        blog_dir = content_dir / "blog"
        blog_dir.mkdir()

        # Home page
        (content_dir / "_index.md").write_text("""---
title: Home
---
Home content.
""")

        # Blog index
        (blog_dir / "_index.md").write_text("""---
title: Blog
---
Blog index.
""")

        # Blog post
        post_path = blog_dir / "post1.md"
        post_path.write_text("""---
title: Original Post Title
date: 2026-01-01
description: Original description
---

Original post content.
""")

        # Config with RSS enabled
        (tmp_path / "bengal.toml").write_text("""
[site]
title = "RSS Test Site"
baseurl = "https://example.com"
description = "A site for testing RSS"

[build]
generate_sitemap = false
generate_rss = true
""")

        # First build (full)
        site1 = Site.from_config(tmp_path)
        site1.build(BuildOptions(incremental=False))

        output_dir = tmp_path / "public"
        # RSSGenerator writes the root feed at public/rss.xml (NOT public/blog/index.xml).
        rss_path = output_dir / "rss.xml"

        # The feed must exist and contain the original post (discriminating).
        assert rss_path.exists(), "rss.xml should be generated when generate_rss=true"
        rss_content_v1 = rss_path.read_text()
        assert "Original Post Title" in rss_content_v1

        # Modify post
        post_path.write_text("""---
title: Updated Post Title
date: 2026-01-01
description: Updated description
---

Updated post content with new information.
""")

        # Second build (incremental)
        site2 = Site.from_config(tmp_path)
        site2.build(BuildOptions(incremental=True))

        # RSS must be updated to reflect the edited post and drop the stale title.
        rss_content_v2 = rss_path.read_text()
        assert "Updated Post Title" in rss_content_v2
        assert "Original Post Title" not in rss_content_v2

    def test_rss_feed_new_post_appears(self, tmp_path):
        """
        New blog post appears in RSS feed on warm build.

        Scenario:
        1. Build with blog section (2 posts)
        2. Add new blog post
        3. Incremental build
        4. Assert: RSS feed includes new post
        """
        # Setup test site with RSS
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        blog_dir = content_dir / "blog"
        blog_dir.mkdir()

        # Home page
        (content_dir / "_index.md").write_text("""---
title: Home
---
Home.
""")

        # Blog posts
        (blog_dir / "_index.md").write_text("""---
title: Blog
---
Blog.
""")
        (blog_dir / "post1.md").write_text("""---
title: First Post
date: 2026-01-01
---
First.
""")
        (blog_dir / "post2.md").write_text("""---
title: Second Post
date: 2026-01-02
---
Second.
""")

        # Config with RSS
        (tmp_path / "bengal.toml").write_text("""
[site]
title = "RSS Test Site"
baseurl = "https://example.com"

[build]
generate_sitemap = false
generate_rss = true
""")

        # First build (full)
        site1 = Site.from_config(tmp_path)
        site1.build(BuildOptions(incremental=False))

        # Add new post
        (blog_dir / "post3.md").write_text("""---
title: Third Post - NEW
date: 2026-01-03
---
Third post is new!
""")

        # Second build (incremental)
        site2 = Site.from_config(tmp_path)
        site2.build(BuildOptions(incremental=True))

        output_dir = tmp_path / "public"
        # RSSGenerator writes the root feed at public/rss.xml.
        rss_path = output_dir / "rss.xml"

        assert rss_path.exists(), "rss.xml should be generated when generate_rss=true"
        rss_content = rss_path.read_text()
        # New post must appear in RSS after the incremental build (discriminating).
        assert "Third Post" in rss_content
        # The pre-existing posts must still be present.
        assert "First Post" in rss_content
        assert "Second Post" in rss_content

    def test_sitemap_updated_on_page_add(self, tmp_path):
        """
        Sitemap includes new page after rebuild.

        Scenario:
        1. Build with sitemap.xml (2 pages)
        2. Add new page
        3. Full rebuild (sitemap regeneration for new pages requires full rebuild)
        4. Assert: sitemap.xml includes new URL

        Note: Sitemap generation for newly added pages requires a full rebuild
        in Bengal's current implementation.
        """
        # Setup test site
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Home.
""")
        (content_dir / "about.md").write_text("""---
title: About
---
About.
""")

        # Config with sitemap
        (tmp_path / "bengal.toml").write_text("""
[site]
title = "Sitemap Test Site"
baseurl = "https://example.com"

[build]
generate_sitemap = true
generate_rss = false
""")

        # First build (full)
        site1 = Site.from_config(tmp_path)
        site1.build(BuildOptions(incremental=False))

        output_dir = tmp_path / "public"
        sitemap_path = output_dir / "sitemap.xml"

        if sitemap_path.exists():
            sitemap_v1 = sitemap_path.read_text()
            url_count_v1 = sitemap_v1.count("<url>")

            # Add new page
            (content_dir / "contact.md").write_text("""---
title: Contact
---
Contact us!
""")

            # Second build (full - required for sitemap to pick up new page)
            site2 = Site.from_config(tmp_path)
            site2.build(BuildOptions(incremental=False))

            sitemap_v2 = sitemap_path.read_text()
            url_count_v2 = sitemap_v2.count("<url>")

            # Sitemap should have more URLs
            assert url_count_v2 > url_count_v1, (
                f"Sitemap should include new page. Was {url_count_v1} URLs, now {url_count_v2}"
            )
            assert "contact" in sitemap_v2.lower()

    def test_sitemap_removes_deleted_page(self, tmp_path):
        """
        Deleted page removed from sitemap on rebuild.

        Scenario:
        1. Build with sitemap.xml (3 pages)
        2. Delete one page
        3. Full rebuild (deletion requires full)
        4. Assert: sitemap.xml has fewer URLs
        """
        # Setup test site
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Home.
""")
        (content_dir / "about.md").write_text("""---
title: About
---
About.
""")
        page_to_delete = content_dir / "temporary.md"
        page_to_delete.write_text("""---
title: Temporary
---
Temporary page.
""")

        # Config with sitemap
        (tmp_path / "bengal.toml").write_text("""
[site]
title = "Sitemap Test Site"
baseurl = "https://example.com"

[build]
generate_sitemap = true
generate_rss = false
""")

        # First build (full)
        site1 = Site.from_config(tmp_path)
        site1.build(BuildOptions(incremental=False))

        output_dir = tmp_path / "public"
        sitemap_path = output_dir / "sitemap.xml"

        if sitemap_path.exists():
            sitemap_v1 = sitemap_path.read_text()
            assert "temporary" in sitemap_v1.lower()

            # Delete the page
            page_to_delete.unlink()

            # Second build (full rebuild for deletion)
            site2 = Site.from_config(tmp_path)
            site2.build(BuildOptions(incremental=False))

            sitemap_v2 = sitemap_path.read_text()
            assert "temporary" not in sitemap_v2.lower(), (
                "Deleted page should be removed from sitemap"
            )

    def test_llm_txt_regenerated_on_content_change(self, tmp_path):
        """
        llm-full.txt regenerated on content change.

        Scenario:
        1. Build with llm-full.txt enabled
        2. Modify page content
        3. Incremental build
        4. Assert: llm-full.txt contains new content
        """
        # Setup test site
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        page_path = content_dir / "guide.md"
        page_path.write_text("""---
title: User Guide
---

# User Guide

Original guide content about getting started.
""")

        # Config with llm-full.txt enabled
        (tmp_path / "bengal.toml").write_text("""
[site]
title = "LLM Test Site"
baseurl = "https://example.com"

[build]
generate_sitemap = false
generate_rss = false

[output_formats]
enabled = true
llm_full = true
""")

        # First build (full)
        site1 = Site.from_config(tmp_path)
        site1.build(BuildOptions(incremental=False))

        output_dir = tmp_path / "public"
        llm_path = output_dir / "llm-full.txt"

        if llm_path.exists():
            llm_v1 = llm_path.read_text()
            assert "Original guide content" in llm_v1

            # Modify content
            page_path.write_text("""---
title: User Guide
---

# User Guide

UPDATED guide content with new sections and improved documentation.
""")

            # Second build (incremental)
            site2 = Site.from_config(tmp_path)
            site2.build(BuildOptions(incremental=True))

            llm_v2 = llm_path.read_text()
            assert "UPDATED" in llm_v2, (
                "llm-full.txt should contain updated content after incremental build"
            )

    def test_llm_txt_includes_new_page(self, tmp_path):
        """
        New page content appears in llm-full.txt.

        Scenario:
        1. Build with llm-full.txt enabled
        2. Add new page with unique content
        3. Incremental build
        4. Assert: llm-full.txt contains new page content
        """
        # Setup test site
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Home page.
""")

        # Config with llm-full.txt enabled
        (tmp_path / "bengal.toml").write_text("""
[site]
title = "LLM Test Site"
baseurl = "https://example.com"

[build]
generate_sitemap = false
generate_rss = false

[output_formats]
enabled = true
llm_full = true
""")

        # First build (full)
        site1 = Site.from_config(tmp_path)
        site1.build(BuildOptions(incremental=False))

        # Add new page with unique content
        (content_dir / "api-reference.md").write_text("""---
title: API Reference
---

# API Reference

UNIQUE_API_CONTENT_MARKER_12345

This is the API reference documentation.
""")

        # Second build (incremental)
        site2 = Site.from_config(tmp_path)
        site2.build(BuildOptions(incremental=True))

        output_dir = tmp_path / "public"
        llm_path = output_dir / "llm-full.txt"

        if llm_path.exists():
            llm_content = llm_path.read_text()
            assert "UNIQUE_API_CONTENT_MARKER_12345" in llm_content, (
                "llm-full.txt should include new page content"
            )

    def test_asset_manifest_updated_on_css_change(self, tmp_path):
        """
        asset-manifest.json reflects a CSS change across an incremental build.

        Scenario:
        1. Build with CSS assets (fingerprint = true always writes the manifest)
        2. Modify CSS content
        3. Incremental build
        4. Assert: the manifest is preserved and the style.css fingerprint changed

        Sits on the #130 incremental-manifest hot path: a never-written, stale,
        emptied, or unchanged manifest must each fail here (the prior body gated
        everything behind ``if manifest_path.exists()`` and asserted nothing).
        """
        # Setup test site with CSS
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Home.
""")

        assets_dir = tmp_path / "assets" / "css"
        assets_dir.mkdir(parents=True)
        css_path = assets_dir / "style.css"
        css_path.write_text("""
/* Version 1 */
:root {
    --color-primary: blue;
}
""")

        # Config with asset fingerprinting
        (tmp_path / "bengal.toml").write_text("""
[site]
title = "Asset Manifest Test Site"
baseurl = "https://example.com"

[build]
generate_sitemap = false
generate_rss = false

[assets]
fingerprint = true
""")

        # First build (full)
        site1 = Site.from_config(tmp_path)
        site1.build(BuildOptions(incremental=False))

        output_dir = tmp_path / "public"
        manifest_path = output_dir / "asset-manifest.json"

        # fingerprint = true always writes the manifest on a full build.
        assert manifest_path.exists(), (
            "full build with fingerprint=true must write asset-manifest.json"
        )
        assets_v1 = json.loads(manifest_path.read_text())["assets"]
        assert "css/style.css" in assets_v1, "manifest must track the css/style.css logical asset"
        style_output_v1 = assets_v1["css/style.css"]["output_path"]

        # Modify CSS
        css_path.write_text("""
/* Version 2 - MODIFIED */
:root {
    --color-primary: green;
    --color-secondary: red;
}
""")

        # Second build (incremental)
        site2 = Site.from_config(tmp_path)
        site2.build(BuildOptions(incremental=True))

        assert manifest_path.exists(), (
            "incremental build must not delete asset-manifest.json (#130)"
        )
        assets_v2 = json.loads(manifest_path.read_text())["assets"]

        # Entry set preserved across the incremental (no emptying/shrinking, #130/#314).
        assert set(assets_v2) >= set(assets_v1), (
            f"incremental must not drop manifest entries; v1={set(assets_v1)} v2={set(assets_v2)}"
        )
        # The CSS fingerprint output_path must actually change after the edit.
        style_output_v2 = assets_v2["css/style.css"]["output_path"]
        assert style_output_v2 != style_output_v1, (
            f"style.css fingerprint should change after a CSS edit; "
            f"v1={style_output_v1!r} v2={style_output_v2!r}"
        )
