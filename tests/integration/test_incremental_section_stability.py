"""
Integration tests for incremental section stability.

Tests that section references remain stable during dev server rebuilds
when _index.md files are edited, ensuring URLs and cascade metadata
are preserved correctly.
"""

import time

import pytest

from bengal.core.site import Site


@pytest.fixture
def test_site_dir(tmp_path):
    """Create a test site with sections and pages."""
    site_dir = tmp_path / "test_site"
    site_dir.mkdir()

    # Create content structure
    content = site_dir / "content"
    content.mkdir()

    # Create blog section
    blog = content / "blog"
    blog.mkdir()
    (blog / "_index.md").write_text("""---
title: Blog
cascade:
  show_sidebar: true
  layout: post
---

Blog section.
""")

    # Create blog posts
    (blog / "post1.md").write_text("""---
title: First Post
date: 2024-01-01
---

First post content.
""")

    (blog / "post2.md").write_text("""---
title: Second Post
date: 2024-01-02
---

Second post content.
""")

    # Create docs section with subsection
    docs = content / "docs"
    docs.mkdir()
    (docs / "_index.md").write_text("""---
title: Documentation
cascade:
  type: docs
---

Documentation section.
""")

    guides = docs / "guides"
    guides.mkdir()
    (guides / "_index.md").write_text("""---
title: Guides
cascade:
  difficulty: beginner
---

Guides subsection.
""")

    (guides / "intro.md").write_text("""---
title: Introduction
---

Introduction guide.
""")

    # Create config
    config_dir = site_dir / "config"
    config_dir.mkdir()
    default_dir = config_dir / "_default"
    default_dir.mkdir()

    (default_dir / "site.yaml").write_text("""
title: Test Site
baseurl: http://localhost:5173
""")

    (default_dir / "build.yaml").write_text("""
output_dir: public
incremental: true
""")

    return site_dir


def test_live_server_section_changes(test_site_dir):
    """Test basic dev server workflow with section changes."""
    # Initial build
    site = Site.from_config(test_site_dir)
    site.discover_content()

    # Verify initial state
    # site.sections only contains top-level sections (blog, docs)
    # guides is a subsection of docs
    assert len(site.sections) == 2  # blog, docs (guides is subsection)
    # Pages: post1, post2, blog/_index, intro, docs/_index, guides/_index
    assert len(site.pages) >= 3  # At least the 3 content pages

    # Find blog section
    blog_section = next(s for s in site.sections if s.name == "blog")
    assert blog_section.title == "Blog"

    # Find blog posts and verify they have the section
    # Note: this includes _index.md as well as post1.md and post2.md
    blog_posts = [p for p in site.pages if "blog" in str(p.source_path)]
    assert len(blog_posts) >= 2  # At least the 2 posts (+ _index)

    for post in blog_posts:
        assert post._section == blog_section
        # Note: URL generation happens during build/render phase, not discovery
        # The section reference is correct, which is what we're testing


def test_dev_server_index_edit_preserves_cascades(test_site_dir):
    """Test that editing _index.md preserves cascade metadata."""
    # Initial build
    site = Site.from_config(test_site_dir)
    site.discover_content()

    # Get blog posts
    blog_posts = [p for p in site.pages if "blog" in str(p.source_path)]
    post1 = next(p for p in blog_posts if "post1" in str(p.source_path))

    # Verify initial cascade
    assert post1.metadata.get("show_sidebar") is True
    assert post1.metadata.get("layout") == "post"

    # Simulate editing _index.md (change cascade)
    blog_index = test_site_dir / "content" / "blog" / "_index.md"
    blog_index.write_text("""---
title: Blog Updated
cascade:
  show_sidebar: false
  layout: article
  new_field: added
---

Updated blog section.
""")

    # Simulate incremental rebuild (reset and rediscover)
    site.reset_ephemeral_state()
    site.discover_content()

    # Find the post again
    blog_posts = [p for p in site.pages if "blog" in str(p.source_path)]
    post1_rebuilt = next(p for p in blog_posts if "post1" in str(p.source_path))

    # Verify cascade was updated
    assert post1_rebuilt.metadata.get("show_sidebar") is False
    assert post1_rebuilt.metadata.get("layout") == "article"
    assert post1_rebuilt.metadata.get("new_field") == "added"

    # Verify section reference is still valid
    # Get the NEW blog section from the rebuilt site
    blog_section_new = next(s for s in site.sections if s.name == "blog")
    assert post1_rebuilt._section is not None
    assert post1_rebuilt._section == blog_section_new
    assert blog_section_new.title == "Blog Updated"

    # Note: URL generation happens during rendering phase, not discovery
    # The section reference is correct, which is what we're testing here
    assert post1_rebuilt._section.name == "blog"


def test_dev_server_create_delete_files(test_site_dir):
    """Test that creating and deleting files maintains correct structure."""
    # Initial build
    site = Site.from_config(test_site_dir)
    site.discover_content()

    initial_page_count = len(site.pages)

    # Create new file
    new_post = test_site_dir / "content" / "blog" / "post3.md"
    new_post.write_text("""---
title: Third Post
date: 2024-01-03
---

New post content.
""")

    # Rebuild
    site.reset_ephemeral_state()
    site.discover_content()

    # Verify post was added
    assert len(site.pages) == initial_page_count + 1
    post3 = next(p for p in site.pages if "post3" in str(p.source_path))
    # Get the NEW blog section from the rebuilt site
    blog_section_new = next(s for s in site.sections if s.name == "blog")
    assert post3._section == blog_section_new
    # Note: The initial cascade has show_sidebar: true
    assert post3.metadata.get("show_sidebar") is True  # From cascade

    # Delete the post
    new_post.unlink()

    # Rebuild again
    site.reset_ephemeral_state()
    site.discover_content()

    # Verify post was removed
    assert len(site.pages) == initial_page_count
    assert not any("post3" in str(p.source_path) for p in site.pages)


def test_subsection_cascade_inheritance(test_site_dir):
    """Test that subsection cascades work correctly across rebuilds."""
    # Initial build
    site = Site.from_config(test_site_dir)
    site.discover_content()

    # Find intro page in guides subsection
    intro = next(p for p in site.pages if "intro" in str(p.source_path))

    # Should inherit cascade from both docs and guides
    assert intro.metadata.get("type") == "docs"  # From docs
    assert intro.metadata.get("difficulty") == "beginner"  # From guides

    # Update guides cascade
    guides_index = test_site_dir / "content" / "docs" / "guides" / "_index.md"
    guides_index.write_text("""---
title: Guides Updated
cascade:
  difficulty: advanced
  new_guide_field: true
---

Updated guides.
""")

    # Rebuild
    site.reset_ephemeral_state()
    site.discover_content()

    # Find intro page again
    intro_rebuilt = next(p for p in site.pages if "intro" in str(p.source_path))

    # Verify updated cascade
    assert intro_rebuilt.metadata.get("type") == "docs"  # Still from docs
    assert intro_rebuilt.metadata.get("difficulty") == "advanced"  # Updated
    assert intro_rebuilt.metadata.get("new_guide_field") is True  # New field

    # Verify section hierarchy is correct
    assert intro_rebuilt._section is not None
    assert intro_rebuilt._section.name == "guides"
    assert intro_rebuilt._section.parent is not None
    assert intro_rebuilt._section.parent.name == "docs"


def test_section_url_stability_across_rebuilds(test_site_dir):
    """Test that page URLs remain stable across multiple rebuilds."""
    # Initial build
    site = Site.from_config(test_site_dir)
    site.discover_content()

    # Get URLs from first build
    urls_before = {p.source_path: p.url for p in site.pages}

    # Rebuild multiple times
    for _ in range(3):
        site.reset_ephemeral_state()
        site.discover_content()

        # Verify URLs haven't changed
        urls_after = {p.source_path: p.url for p in site.pages}
        assert urls_before == urls_after


def test_section_reference_performance(test_site_dir):
    """Test that section lookups remain fast during rebuilds."""
    # Create more pages for meaningful performance test
    blog = test_site_dir / "content" / "blog"
    for i in range(20):  # Reduced to avoid date issues
        (blog / f"post{i + 10}.md").write_text(f"""---
title: Post {i + 10}
---

Content for post {i + 10}.
""")

    # Build
    site = Site.from_config(test_site_dir)

    # Time the discovery with section lookups
    start = time.perf_counter()
    site.discover_content()
    elapsed = time.perf_counter() - start

    # Should complete in reasonable time (< 1 second for 20+ pages)
    assert elapsed < 1.0, f"Discovery too slow: {elapsed:.3f}s"

    # Verify all pages have correct section references
    blog_section = next(s for s in site.sections if s.name == "blog")
    blog_pages = [p for p in site.pages if "blog" in str(p.source_path)]

    for page in blog_pages:
        assert page._section == blog_section
        # Each lookup should be O(1)
        lookup_start = time.perf_counter()
        _ = page._section
        lookup_elapsed = time.perf_counter() - lookup_start
        assert lookup_elapsed < 0.001, f"Lookup too slow: {lookup_elapsed:.6f}s"
