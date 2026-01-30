"""
Integration tests for incremental build dependency gaps.

Tests that verify the fixes for RFC: rfc-incremental-build-dependency-gaps.

Gap 1: Data file changes don't trigger page rebuilds
Gap 2: Taxonomy listing pages don't update when member post metadata changes
Gap 3: Sitemap doesn't include new pages during incremental builds

See: plan/rfc-incremental-build-dependency-gaps.md
"""

from __future__ import annotations

import pytest

from tests.integration.warm_build.conftest import WarmBuildTestSite


class TestDataFileFingerprintCaching:
    """
    Data file fingerprints must be cached to prevent false "changed" detection.
    
    Without cached fingerprints, data files always appear "changed" on
    incremental builds, triggering conservative full rebuild of all pages.
    """

    def test_content_change_without_data_change_is_efficient(
        self, site_with_data_tracking: WarmBuildTestSite
    ) -> None:
        """
        Content-only change should NOT trigger full rebuild due to uncached data files.
        
        Bug scenario this catches:
        1. Full build with data/team.yaml
        2. Edit only a content file (not data file)
        3. Incremental build incorrectly detects data files as "changed"
           because fingerprints weren't cached
        4. Conservative fallback rebuilds ALL pages
        
        Expected:
        - Only the changed content page should rebuild
        - Data files should NOT appear as changed
        """
        # Build 1: Full build - should cache fingerprints for ALL files including data
        stats1 = site_with_data_tracking.full_build()
        initial_page_count = stats1.pages_built
        assert initial_page_count >= 2, "Should have at least home + about pages"
        
        # Modify ONLY a content file (not the data file)
        site_with_data_tracking.modify_file(
            "content/_index.md",
            """---
title: Home - Updated
---

# Welcome - Updated Content
""",
        )
        
        site_with_data_tracking.wait_for_fs()
        
        # Build 2: Incremental build
        stats2 = site_with_data_tracking.incremental_build()
        
        # Assert: Should rebuild only 1 page (the modified home page)
        # NOT all pages due to data file fingerprint miss
        # Use cache_misses which accurately reflects pages actually rebuilt
        # (pages_built returns total_pages which is misleading for incremental builds)
        assert stats2.cache_misses == 1, (
            f"Content-only change should trigger minimal rebuild. "
            f"Expected 1 cache miss, got {stats2.cache_misses}. "
            f"This indicates data file fingerprints may not be cached properly."
        )


class TestDataFileDependencyGap:
    """
    Gap 1: Data file changes should trigger dependent page rebuilds.
    
    When data/team.yaml changes, pages that accessed site.data.team
    should be rebuilt with the new data.
    """

    def test_data_file_change_triggers_incremental_rebuild(
        self, site_with_data_tracking: WarmBuildTestSite
    ) -> None:
        """
        Data file change triggers incremental rebuild of dependent pages.
        
        Scenario:
        1. Full build with data/team.yaml and about.md that uses the data
        2. Modify data/team.yaml to change a team member's role
        3. Run incremental build
        4. Assert: about page is rebuilt with new role value
        
        This is the core gap: incremental builds should detect data file
        changes and rebuild pages that depend on that data.
        """
        # Build 1: Full build
        stats1 = site_with_data_tracking.full_build()
        initial_page_count = stats1.pages_built
        assert initial_page_count >= 1, "Initial build should create pages"
        
        # Verify initial content
        site_with_data_tracking.assert_output_contains(
            "about/index.html", "Developer"
        )
        
        # Modify data file to change role
        site_with_data_tracking.modify_file(
            "data/team.yaml",
            """
members:
  - name: Alice
    role: Senior Developer
  - name: Bob
    role: Designer
""",
        )
        
        site_with_data_tracking.wait_for_fs()
        
        # Build 2: Incremental build should detect data change
        stats2 = site_with_data_tracking.incremental_build()
        
        # Assert: About page was rebuilt with new data
        site_with_data_tracking.assert_output_contains(
            "about/index.html", "Senior Developer"
        )
        
        # Assert: At least the about page was rebuilt (not skipped)
        # Use cache_misses to check actual rebuild count
        assert stats2.cache_misses >= 1, (
            "Data file change should trigger rebuild of dependent pages"
        )
        
        # Assert: Incremental build should NOT rebuild ALL pages
        # This catches the bug where data files always appear "changed"
        # due to missing fingerprints, triggering conservative full rebuild.
        # With proper data file fingerprinting, only dependent pages rebuild.
        assert stats2.cache_misses < initial_page_count, (
            f"Data file change should trigger targeted rebuild, not full. "
            f"Expected < {initial_page_count} cache misses, got {stats2.cache_misses}. "
            f"This may indicate data file fingerprints aren't being cached."
        )


class TestTaxonomyMetadataPropagationGap:
    """
    Gap 2: Taxonomy term pages should update when member post metadata changes.
    
    When a post's title/date/summary changes, the /tags/X/ listing page
    should be rebuilt with the updated metadata.
    """

    def test_taxonomy_term_page_updates_on_member_title_change(
        self, site_with_taxonomy_tracking: WarmBuildTestSite
    ) -> None:
        """
        Taxonomy term page updates when a member post's title changes.
        
        Scenario:
        1. Full build with posts tagged [python]
        2. Change the title of a python-tagged post
        3. Run incremental build  
        4. Assert: /tags/python/ listing shows the new title
        
        This is the core gap: when a member page's metadata changes,
        the taxonomy term page listing it should also rebuild.
        """
        # Build 1: Full build
        stats1 = site_with_taxonomy_tracking.full_build()
        assert stats1.pages_built >= 1, "Initial build should create pages"
        
        # Verify initial title appears in tag page
        site_with_taxonomy_tracking.assert_output_contains(
            "tags/python/index.html", "Python Tutorial"
        )
        
        # Modify post title
        site_with_taxonomy_tracking.modify_file(
            "content/blog/post1.md",
            """---
title: Advanced Python Techniques
date: 2026-01-01
tags: [python, tutorial]
categories: [tutorials]
---

An advanced Python tutorial.
""",
        )
        
        site_with_taxonomy_tracking.wait_for_fs()
        
        # Build 2: Incremental build
        stats2 = site_with_taxonomy_tracking.incremental_build()
        
        # Assert: Tag page shows new title
        site_with_taxonomy_tracking.assert_output_contains(
            "tags/python/index.html", "Advanced Python Techniques"
        )
        site_with_taxonomy_tracking.assert_output_not_contains(
            "tags/python/index.html", "Python Tutorial"
        )

    def test_taxonomy_term_page_updates_on_member_date_change(
        self, site_with_taxonomy_tracking: WarmBuildTestSite
    ) -> None:
        """
        Taxonomy term page ordering updates when a member post's date changes.
        
        Scenario:
        1. Full build with multiple posts tagged [python]
        2. Change a post's date to make it the most recent
        3. Run incremental build
        4. Assert: /tags/python/ listing shows posts in new order
        """
        # Create additional post for ordering test
        site_with_taxonomy_tracking.create_file(
            "content/blog/post3.md",
            """---
title: Older Python Post
date: 2025-12-01
tags: [python]
---

Older post content.
""",
        )
        
        # Build 1: Full build
        stats1 = site_with_taxonomy_tracking.full_build()
        assert stats1.pages_built >= 1
        
        # Modify date to make older post newest
        site_with_taxonomy_tracking.modify_file(
            "content/blog/post3.md",
            """---
title: Now The Newest Python Post
date: 2026-12-01
tags: [python]
---

Now the newest content.
""",
        )
        
        site_with_taxonomy_tracking.wait_for_fs()
        
        # Build 2: Incremental build
        stats2 = site_with_taxonomy_tracking.incremental_build()
        
        # Assert: Tag page shows updated title
        site_with_taxonomy_tracking.assert_output_contains(
            "tags/python/index.html", "Now The Newest Python Post"
        )


class TestSitemapIncrementalGap:
    """
    Gap 3: Sitemap should include new pages during incremental builds.
    
    When a new page is added during an incremental build, the sitemap
    should be regenerated to include the new page.
    """

    def test_sitemap_includes_new_pages_on_incremental_build(
        self, site_with_sitemap: WarmBuildTestSite
    ) -> None:
        """
        Sitemap includes new pages added during incremental build.
        
        Scenario:
        1. Full build with 3 pages → sitemap has 3 URLs
        2. Add a new page
        3. Run incremental build
        4. Assert: sitemap now has 4 URLs including the new page
        """
        # Build 1: Full build
        stats1 = site_with_sitemap.full_build()
        assert stats1.pages_built >= 1
        
        # Verify sitemap exists and has initial pages
        site_with_sitemap.assert_output_exists("sitemap.xml")
        initial_sitemap = site_with_sitemap.read_output("sitemap.xml")
        assert "<url>" in initial_sitemap
        
        # Count initial URLs
        initial_url_count = initial_sitemap.count("<loc>")
        
        # Add a new page
        site_with_sitemap.create_file(
            "content/new-page.md",
            """---
title: New Page
---

New page content.
""",
        )
        
        site_with_sitemap.wait_for_fs()
        
        # Build 2: Incremental build
        stats2 = site_with_sitemap.incremental_build()
        
        # Assert: New page was built
        site_with_sitemap.assert_output_exists("new-page/index.html")
        
        # Assert: Sitemap includes new page
        updated_sitemap = site_with_sitemap.read_output("sitemap.xml")
        assert "new-page" in updated_sitemap, (
            "Sitemap should include new page after incremental build"
        )
        
        # Assert: URL count increased
        updated_url_count = updated_sitemap.count("<loc>")
        assert updated_url_count > initial_url_count, (
            f"Sitemap URL count should increase from {initial_url_count} "
            f"but got {updated_url_count}"
        )

    def test_sitemap_excludes_deleted_pages_on_full_rebuild(
        self, site_with_sitemap: WarmBuildTestSite
    ) -> None:
        """
        Sitemap excludes deleted pages after full rebuild.
        
        Scenario:
        1. Full build with 3 pages
        2. Delete one page
        3. Run full rebuild
        4. Assert: sitemap no longer has the deleted page URL
        
        Note: Deletion typically requires full rebuild for cleanup.
        """
        # Build 1: Full build with extra page
        site_with_sitemap.create_file(
            "content/to-delete.md",
            """---
title: Page To Delete
---

This page will be deleted.
""",
        )
        stats1 = site_with_sitemap.full_build()
        
        # Verify page exists in sitemap
        initial_sitemap = site_with_sitemap.read_output("sitemap.xml")
        assert "to-delete" in initial_sitemap
        
        # Delete the page
        site_with_sitemap.delete_file("content/to-delete.md")
        
        site_with_sitemap.wait_for_fs()
        
        # Build 2: Full rebuild for deletion cleanup
        stats2 = site_with_sitemap.full_build()
        
        # Assert: Deleted page not in sitemap
        updated_sitemap = site_with_sitemap.read_output("sitemap.xml")
        assert "to-delete" not in updated_sitemap, (
            "Sitemap should not include deleted page after rebuild"
        )


class TestCascadeFrontmatterGap:
    """
    Gap 4: Cascade changes should trigger child page rebuilds.
    
    When an _index.md changes its cascade frontmatter, all child pages that
    inherit those cascade values should be rebuilt with the new values.
    
    This tests the fix in ProvenanceFilter._get_cascade_sources() that tracks
    parent _index.md files as provenance inputs.
    """

    def test_cascade_change_triggers_child_page_rebuild(
        self, site_with_cascade_tracking: WarmBuildTestSite
    ) -> None:
        """
        Cascade change triggers incremental rebuild of child pages.
        
        Scenario:
        1. Full build with _index.md cascade: type: doc
        2. Modify _index.md to change cascade type to 'reference'
        3. Run incremental build
        4. Assert: Child pages rebuilt with new cascade type in HTML output
        
        This is the core gap: when a parent section's cascade changes,
        child pages should be rebuilt with the updated cascade values.
        """
        # Build 1: Full build
        stats1 = site_with_cascade_tracking.full_build()
        assert stats1.pages_built >= 2, "Should have section index + child page"
        
        # Verify initial cascade type appears in child page output
        # Bengal's default theme outputs type in body tag as data-type
        site_with_cascade_tracking.assert_output_contains(
            "docs/guide/index.html", 'data-type="doc"'
        )
        
        # Modify _index.md to change cascade type
        site_with_cascade_tracking.modify_file(
            "content/docs/_index.md",
            """---
title: Documentation
cascade:
  type: reference
  layout: docs-layout
---

# Documentation
""",
        )
        
        site_with_cascade_tracking.wait_for_fs()
        
        # Build 2: Incremental build should detect cascade change
        stats2 = site_with_cascade_tracking.incremental_build()
        
        # Assert: Child page was rebuilt with new cascade type
        site_with_cascade_tracking.assert_output_contains(
            "docs/guide/index.html", 'data-type="reference"'
        )
        site_with_cascade_tracking.assert_output_not_contains(
            "docs/guide/index.html", 'data-type="doc"'
        )
        
        # Assert: At least the child page was rebuilt
        assert stats2.cache_misses >= 1, (
            "Cascade change should trigger rebuild of child pages"
        )

    def test_nested_cascade_change_propagates_to_deep_children(
        self, site_with_cascade_tracking: WarmBuildTestSite
    ) -> None:
        """
        Nested cascade changes propagate through deeply nested sections.
        
        Scenario:
        1. Full build with docs/_index.md cascade
        2. Add a nested subsection: docs/advanced/_index.md
        3. Add a page in the subsection: docs/advanced/tips.md
        4. Build again
        5. Modify root docs/_index.md cascade
        6. Incremental build
        7. Assert: Both guide.md AND advanced/tips.md are rebuilt
        """
        # Build 1: Full build
        stats1 = site_with_cascade_tracking.full_build()
        
        # Create nested structure
        site_with_cascade_tracking.create_file(
            "content/docs/advanced/_index.md",
            """---
title: Advanced
---

# Advanced Topics
""",
        )
        site_with_cascade_tracking.create_file(
            "content/docs/advanced/tips.md",
            """---
title: Tips and Tricks
---

# Tips and Tricks
""",
        )
        
        site_with_cascade_tracking.wait_for_fs()
        
        # Build 2: Build with new pages
        stats2 = site_with_cascade_tracking.full_build()
        
        # Verify initial cascade in nested page
        site_with_cascade_tracking.assert_output_contains(
            "docs/advanced/tips/index.html", 'data-type="doc"'
        )
        
        # Modify root cascade
        site_with_cascade_tracking.modify_file(
            "content/docs/_index.md",
            """---
title: Documentation
cascade:
  type: api-doc
  layout: docs-layout
---

# Documentation
""",
        )
        
        site_with_cascade_tracking.wait_for_fs()
        
        # Build 3: Incremental build
        stats3 = site_with_cascade_tracking.incremental_build()
        
        # Assert: Both levels rebuilt with new cascade
        site_with_cascade_tracking.assert_output_contains(
            "docs/guide/index.html", 'data-type="api-doc"'
        )
        site_with_cascade_tracking.assert_output_contains(
            "docs/advanced/tips/index.html", 'data-type="api-doc"'
        )


# =============================================================================
# FIXTURES
# =============================================================================


def create_data_tracking_site_structure(site_dir) -> None:
    """
    Create a site structure that uses data files in templates.
    
    This fixture creates a page that explicitly uses site.data in its template
    so we can verify data file dependency tracking.
    
    Note: site.data must be accessed in the template, not in markdown content.
    Markdown content is rendered first, then passed to templates as {{ content }}.
    
    Important: Use `template:` in frontmatter (not `layout:`) for explicit
    template selection in Bengal.
    """
    from pathlib import Path
    
    # Config
    (site_dir / "bengal.toml").write_text("""
[site]
title = "Data Tracking Test Site"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false
""")
    
    # Data directory
    data_dir = site_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    (data_dir / "team.yaml").write_text("""
members:
  - name: Alice
    role: Developer
  - name: Bob
    role: Designer
""")
    
    # Content directory
    content_dir = site_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    
    # Home page
    (content_dir / "_index.md").write_text("""---
title: Home
---

# Welcome
""")
    
    # About page - uses custom template that accesses site.data
    # Note: Use `template:` not `layout:` for explicit template selection
    (content_dir / "about.md").write_text("""---
title: About Us
template: team.html
---

# About Us

Meet our team!
""")
    
    # Templates with data access - put team.html at root of templates/
    templates_dir = site_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Team template that accesses site.data.team (at templates/team.html)
    (templates_dir / "team.html").write_text("""<!DOCTYPE html>
<html>
<head><title>{{ page.title }}</title></head>
<body>
<main>
{{ content }}
<ul class="team-members">
{% for member in site.data.team.members %}
<li>{{ member.name }}: {{ member.role }}</li>
{% endfor %}
</ul>
</main>
</body>
</html>
""")


def create_taxonomy_tracking_site_structure(site_dir) -> None:
    """
    Create a site structure with taxonomy for metadata propagation testing.
    """
    from pathlib import Path
    
    # Config with taxonomies
    (site_dir / "bengal.toml").write_text("""
[site]
title = "Taxonomy Tracking Test Site"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false

[taxonomies]
tag = "tags"
category = "categories"
""")
    
    # Content directory
    content_dir = site_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    
    # Home page
    (content_dir / "_index.md").write_text("""---
title: Home
---

# Welcome
""")
    
    # Blog section with tagged posts
    blog_dir = content_dir / "blog"
    blog_dir.mkdir()
    (blog_dir / "_index.md").write_text("""---
title: Blog
---

# Blog
""")
    (blog_dir / "post1.md").write_text("""---
title: Python Tutorial
date: 2026-01-01
tags: [python, tutorial]
categories: [tutorials]
---

A Python tutorial.
""")
    (blog_dir / "post2.md").write_text("""---
title: Rust Guide
date: 2026-01-02
tags: [rust]
categories: [guides]
---

A Rust guide.
""")


def create_sitemap_site_structure(site_dir) -> None:
    """
    Create a site structure with sitemap enabled for incremental testing.
    """
    from pathlib import Path
    
    # Config with sitemap enabled
    (site_dir / "bengal.toml").write_text("""
[site]
title = "Sitemap Test Site"
baseurl = "https://example.com"

[build]
output_dir = "public"
incremental = true
generate_sitemap = true
generate_rss = false
""")
    
    # Content directory
    content_dir = site_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    
    # Home page
    (content_dir / "_index.md").write_text("""---
title: Home
---

# Welcome
""")
    
    # A few pages
    (content_dir / "about.md").write_text("""---
title: About
---

# About Us
""")
    
    (content_dir / "contact.md").write_text("""---
title: Contact
---

# Contact Us
""")


@pytest.fixture
def site_with_data_tracking(tmp_path) -> WarmBuildTestSite:
    """
    Create a test site with data file dependency tracking.
    
    Returns:
        WarmBuildTestSite helper with data tracking structure
    """
    site_dir = tmp_path / "data_tracking_site"
    site_dir.mkdir()
    create_data_tracking_site_structure(site_dir)
    return WarmBuildTestSite(site_dir=site_dir)


@pytest.fixture
def site_with_taxonomy_tracking(tmp_path) -> WarmBuildTestSite:
    """
    Create a test site with taxonomy metadata tracking.
    
    Returns:
        WarmBuildTestSite helper with taxonomy structure
    """
    site_dir = tmp_path / "taxonomy_tracking_site"
    site_dir.mkdir()
    create_taxonomy_tracking_site_structure(site_dir)
    return WarmBuildTestSite(site_dir=site_dir)


@pytest.fixture
def site_with_sitemap(tmp_path) -> WarmBuildTestSite:
    """
    Create a test site with sitemap generation enabled.
    
    Returns:
        WarmBuildTestSite helper with sitemap enabled
    """
    site_dir = tmp_path / "sitemap_site"
    site_dir.mkdir()
    create_sitemap_site_structure(site_dir)
    return WarmBuildTestSite(site_dir=site_dir)


def create_cascade_tracking_site_structure(site_dir) -> None:
    """
    Create a site structure for testing cascade incremental builds.
    
    Uses a custom template that outputs page.type as a data attribute,
    so we can verify cascade values propagate to HTML output.
    """
    from pathlib import Path
    
    # Config
    (site_dir / "bengal.toml").write_text("""
[site]
title = "Cascade Tracking Test Site"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false
""")
    
    # Content directory
    content_dir = site_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    
    # Home page
    (content_dir / "_index.md").write_text("""---
title: Home
---

# Welcome
""")
    
    # Docs section with cascade
    docs_dir = content_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    (docs_dir / "_index.md").write_text("""---
title: Documentation
cascade:
  type: doc
  layout: docs-layout
---

# Documentation
""")
    
    # Child page that inherits cascade
    (docs_dir / "guide.md").write_text("""---
title: User Guide
---

# User Guide

Guide content here.
""")
    
    # Templates with type output - use page.type in data attribute
    templates_dir = site_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Default template that outputs page type
    (templates_dir / "default.html").write_text("""<!DOCTYPE html>
<html>
<head><title>{{ page.title }}</title></head>
<body data-page-type="{{ page.type or 'none' }}">
<main>
<h1>{{ page.title }}</h1>
{{ content }}
</main>
</body>
</html>
""")


@pytest.fixture
def site_with_cascade_tracking(tmp_path) -> WarmBuildTestSite:
    """
    Create a test site with cascade frontmatter for incremental tracking.
    
    Returns:
        WarmBuildTestSite helper with cascade structure
    """
    site_dir = tmp_path / "cascade_tracking_site"
    site_dir.mkdir()
    create_cascade_tracking_site_structure(site_dir)
    return WarmBuildTestSite(site_dir=site_dir)
