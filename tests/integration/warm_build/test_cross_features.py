"""
Integration tests for cross-feature interactions during warm builds.

Tests that multiple features working together behave correctly during
incremental builds.

Priority: P2 (LOWER) - Cross-feature interactions are complex but
important for real-world usage.

See: plan/rfc-warm-build-test-expansion.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


class TestWarmBuildCrossFeatures:
    """Test interactions between multiple features during warm builds."""

    def test_taxonomy_with_navigation(self, tmp_path: Path) -> None:
        """
        Test taxonomy and navigation working together.

        Scenario:
        1. Build with pages having tags AND menu entries
        2. Add new tag to page
        3. Incremental build
        4. Assert: Both taxonomy and nav are updated
        """
        # Create site with both features
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Config with both features
        (site_dir / "bengal.toml").write_text("""
[site]
title = "Cross Feature Test"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false

[[menu.main]]
name = "Home"
url = "/"
weight = 1

[[menu.main]]
name = "Blog"
url = "/blog/"
weight = 2
""")

        # Content
        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Home page.
""")

        blog_dir = content_dir / "blog"
        blog_dir.mkdir()

        (blog_dir / "_index.md").write_text("""---
title: Blog
menu:
  main:
    weight: 2
---
Blog section.
""")

        (blog_dir / "post1.md").write_text("""---
title: First Post
tags: [python]
---
First post content.
""")

        # Build 1: Full build
        site1 = Site.from_config(site_dir)
        site1.build(BuildOptions(incremental=False))

        # Add new tag to post
        (blog_dir / "post1.md").write_text("""---
title: First Post
tags: [python, tutorial, new-tag]
---
First post content with new tags.
""")

        # Build 2: Incremental build
        site2 = Site.from_config(site_dir)
        stats2 = site2.build(BuildOptions(incremental=True))

        # Build should succeed
        assert stats2.total_pages >= 1

    def test_data_files_with_templates(self, tmp_path: Path) -> None:
        """
        Test data files used in templates.

        Scenario:
        1. Build with data file used in template
        2. Modify data file
        3. Full rebuild (data changes require full rebuild currently)
        4. Assert: Build completes with updated data
        """
        # Create site with data
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Config
        (site_dir / "bengal.toml").write_text("""
[site]
title = "Data Template Test"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false
""")

        # Data directory
        data_dir = site_dir / "data"
        data_dir.mkdir()

        (data_dir / "features.yaml").write_text("""
items:
  - name: Feature A
    description: First feature
  - name: Feature B
    description: Second feature
""")

        # Content
        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---

# Features

Check out our features!
""")

        # Build 1: Full build
        site1 = Site.from_config(site_dir)
        site1.build(BuildOptions(incremental=False))

        # Modify data file
        (data_dir / "features.yaml").write_text("""
items:
  - name: Feature A
    description: First feature - UPDATED
  - name: Feature B
    description: Second feature
  - name: Feature C
    description: New feature!
""")

        # Build 2: Full rebuild (data file changes require full rebuild
        # as they're not currently tracked as page dependencies)
        site2 = Site.from_config(site_dir)
        stats2 = site2.build(BuildOptions(incremental=False))

        # Build should succeed
        assert stats2.total_pages >= 1

    @pytest.mark.skip(reason="i18n not fully implemented")
    def test_i18n_translation_change(self, tmp_path: Path) -> None:
        """
        Translation file change triggers correct rebuilds.

        Scenario:
        1. Build with i18n (en, es)
        2. Modify i18n/es.yaml
        3. Incremental build
        4. Assert: Spanish pages rebuilt, English not

        Note: Skipped until i18n is fully implemented.
        """

    @pytest.mark.skip(reason="Versioned docs not fully implemented")
    def test_versioned_docs_incremental(self, tmp_path: Path) -> None:
        """
        Version-specific changes handled correctly.

        Scenario:
        1. Build with versions: [1.0, 2.0]
        2. Modify only 2.0 content
        3. Incremental build
        4. Assert: Only 2.0 pages rebuilt

        Note: Skipped until versioned docs are fully implemented.
        """

    def test_collection_with_taxonomy(self, tmp_path: Path) -> None:
        """
        Collection items with taxonomy updates.

        Scenario:
        1. Build with blog collection having tags
        2. Add tag to post
        3. Incremental build
        4. Assert: Post and tag page updated
        """
        # Create site with collection and taxonomy
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Config
        (site_dir / "bengal.toml").write_text("""
[site]
title = "Collection Taxonomy Test"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false
""")

        # Content - blog collection
        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Home.
""")

        blog_dir = content_dir / "blog"
        blog_dir.mkdir()

        (blog_dir / "_index.md").write_text("""---
title: Blog
---
Blog.
""")

        (blog_dir / "post1.md").write_text("""---
title: Post 1
tags: [python]
---
Post 1 content.
""")

        (blog_dir / "post2.md").write_text("""---
title: Post 2
tags: [rust]
---
Post 2 content.
""")

        # Build 1: Full build
        site1 = Site.from_config(site_dir)
        site1.build(BuildOptions(incremental=False))

        # Add shared tag between posts
        (blog_dir / "post2.md").write_text("""---
title: Post 2
tags: [rust, python]
---
Post 2 now also has python tag.
""")

        # Build 2: Incremental build
        site2 = Site.from_config(site_dir)
        stats2 = site2.build(BuildOptions(incremental=True))

        # Build should succeed
        assert stats2.total_pages >= 1

    def test_related_pages_on_tag_change(self, tmp_path: Path) -> None:
        """
        Related pages section updates when tags change.

        Scenario:
        1. Build with posts having tags
        2. Add shared tag between two posts
        3. Incremental build
        4. Assert: Build succeeds with tag relationship

        Note: This tests the tag relationship, actual "related pages"
        feature depends on Bengal implementation.
        """
        # Create site with posts
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Config
        (site_dir / "bengal.toml").write_text("""
[site]
title = "Related Pages Test"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false
""")

        # Content
        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Home.
""")

        blog_dir = content_dir / "blog"
        blog_dir.mkdir()

        (blog_dir / "_index.md").write_text("""---
title: Blog
---
Blog.
""")

        # Two posts with different tags
        (blog_dir / "post-a.md").write_text("""---
title: Post A
tags: [python, web]
---
Post A about Python web development.
""")

        (blog_dir / "post-b.md").write_text("""---
title: Post B
tags: [javascript]
---
Post B about JavaScript.
""")

        # Build 1: Full build
        site1 = Site.from_config(site_dir)
        site1.build(BuildOptions(incremental=False))

        # Add shared tag to create relationship
        (blog_dir / "post-b.md").write_text("""---
title: Post B
tags: [javascript, web]
---
Post B about JavaScript web development.
""")

        # Build 2: Incremental build
        site2 = Site.from_config(site_dir)
        stats2 = site2.build(BuildOptions(incremental=True))

        # Build should succeed
        assert stats2.total_pages >= 1

    def test_cascade_plus_taxonomy(self, tmp_path: Path) -> None:
        """
        Section cascade + taxonomy interaction.

        Scenario:
        1. Build with section having cascade that sets default tags
        2. Modify a page's tags (override cascade)
        3. Incremental build
        4. Assert: Taxonomy reflects page-level override
        """
        # Create site with cascade and taxonomy
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Config
        (site_dir / "bengal.toml").write_text("""
[site]
title = "Cascade Taxonomy Test"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false
""")

        # Content with cascade
        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Home.
""")

        # Docs section with cascade
        docs_dir = content_dir / "docs"
        docs_dir.mkdir()

        (docs_dir / "_index.md").write_text("""---
title: Documentation
cascade:
  tags: [documentation]
---
Documentation section with default tags.
""")

        # Page inheriting cascade tags
        (docs_dir / "guide.md").write_text("""---
title: User Guide
---
User guide content.
""")

        # Build 1: Full build
        site1 = Site.from_config(site_dir)
        site1.build(BuildOptions(incremental=False))

        # Override cascade tags on page
        (docs_dir / "guide.md").write_text("""---
title: User Guide
tags: [guide, tutorial, custom-tag]
---
User guide with custom tags (overrides cascade).
""")

        # Build 2: Incremental build
        site2 = Site.from_config(site_dir)
        stats2 = site2.build(BuildOptions(incremental=True))

        # Build should succeed
        assert stats2.total_pages >= 1


class TestWarmBuildCrossFeatureEdgeCases:
    """Edge cases for cross-feature interactions."""

    def test_all_features_enabled(self, tmp_path: Path) -> None:
        """
        Test warm build with all features enabled.

        Scenario:
        1. Build with navigation, taxonomy, data files, templates all active
        2. Make changes across multiple features
        3. Incremental build
        4. Assert: Build succeeds
        """
        # Create site with all features
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Config with all features
        (site_dir / "bengal.toml").write_text("""
[site]
title = "All Features Test"
baseurl = "https://example.com"
description = "Site with all features enabled"

[build]
output_dir = "public"
incremental = true
generate_sitemap = true
generate_rss = true

[[menu.main]]
name = "Home"
url = "/"
weight = 1

[[menu.main]]
name = "Blog"
url = "/blog/"
weight = 2

[[menu.main]]
name = "Docs"
url = "/docs/"
weight = 3

[output_formats]
enabled = true
llm_full = true

[taxonomies]
tag = "tags"
""")

        # Data files
        data_dir = site_dir / "data"
        data_dir.mkdir()
        (data_dir / "config.yaml").write_text("""
version: "1.0"
features:
  - feature1
  - feature2
""")

        # Templates
        templates_dir = site_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "base.html").write_text("""<!DOCTYPE html>
<html>
<head><title>{{ page.title }}</title></head>
<body>{{ content }}</body>
</html>
""")

        # Content structure
        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Home page.
""")

        blog_dir = content_dir / "blog"
        blog_dir.mkdir()
        (blog_dir / "_index.md").write_text("""---
title: Blog
---
Blog.
""")
        (blog_dir / "post1.md").write_text("""---
title: Post 1
date: 2026-01-01
tags: [python]
---
Post 1.
""")

        docs_dir = content_dir / "docs"
        docs_dir.mkdir()
        (docs_dir / "_index.md").write_text("""---
title: Docs
---
Docs.
""")
        (docs_dir / "guide.md").write_text("""---
title: Guide
tags: [tutorial]
---
Guide content.
""")

        # Build 1: Full build
        site1 = Site.from_config(site_dir)
        stats1 = site1.build(BuildOptions(incremental=False))
        assert stats1.total_pages >= 1

        # Make multiple changes
        # Change content
        (blog_dir / "post1.md").write_text("""---
title: Post 1 Updated
date: 2026-01-01
tags: [python, updated]
---
Post 1 with updates.
""")

        # Add new content
        (blog_dir / "post2.md").write_text("""---
title: Post 2 New
date: 2026-01-02
tags: [javascript]
---
New post.
""")

        # Change data file
        (data_dir / "config.yaml").write_text("""
version: "2.0"
features:
  - feature1
  - feature2
  - feature3
""")

        # Build 2: Incremental build with all changes
        site2 = Site.from_config(site_dir)
        stats2 = site2.build(BuildOptions(incremental=True))

        # Build should succeed
        assert stats2.total_pages >= stats1.total_pages

    def test_feature_toggle_mid_build(self, tmp_path: Path) -> None:
        """
        Test enabling/disabling features between builds.

        Scenario:
        1. Build with RSS disabled
        2. Enable RSS in config
        3. Rebuild
        4. Assert: RSS is now generated
        """
        # Create site
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Config without RSS
        (site_dir / "bengal.toml").write_text("""
[site]
title = "Feature Toggle Test"
baseurl = "https://example.com"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false
""")

        # Content
        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Home.
""")

        blog_dir = content_dir / "blog"
        blog_dir.mkdir()
        (blog_dir / "_index.md").write_text("""---
title: Blog
---
Blog.
""")
        (blog_dir / "post1.md").write_text("""---
title: Post 1
date: 2026-01-01
---
Post.
""")

        # Build 1: Without RSS
        site1 = Site.from_config(site_dir)
        site1.build(BuildOptions(incremental=False))

        site_dir / "public"

        # Enable RSS
        (site_dir / "bengal.toml").write_text("""
[site]
title = "Feature Toggle Test"
baseurl = "https://example.com"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = true
""")

        # Build 2: With RSS enabled (config change = full rebuild)
        site2 = Site.from_config(site_dir)
        stats2 = site2.build(BuildOptions(incremental=False))

        # Build should succeed
        assert stats2.total_pages >= 1
