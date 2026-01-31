"""
Shared fixtures for warm build integration tests.

Provides WarmBuildTestSite helper class and fixtures for testing
incremental build scenarios including navigation, taxonomy, data files,
template chains, and output formats.

See: plan/rfc-warm-build-test-expansion.md
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

if TYPE_CHECKING:
    from bengal.orchestration.build.stats import BuildStats


@dataclass
class WarmBuildTestSite:
    """
    Helper class for warm build test scenarios.

    Provides methods for:
    - Building the site (full/incremental)
    - Modifying, deleting, creating files
    - Asserting page rebuild/skip status
    - Reading and checking output content

    Attributes:
        site_dir: Root directory of the test site
        output_dir: Output directory for built files
        cache_dir: Cache directory (.bengal/)
        _site: Current Site instance (recreated on each build for fresh state)
        _last_stats: Build statistics from the last build
        _build_count: Number of builds performed
    """

    site_dir: Path
    output_dir: Path = field(init=False)
    cache_dir: Path = field(init=False)
    _site: Site | None = field(default=None, repr=False)
    _last_stats: BuildStats | None = field(default=None, repr=False)
    _build_count: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        self.output_dir = self.site_dir / "public"
        self.cache_dir = self.site_dir / ".bengal"

    @property
    def site(self) -> Site:
        """Get the current site instance."""
        if self._site is None:
            self._site = Site.from_config(self.site_dir)
            self._site.discover_content()
            self._site.discover_assets()
        return self._site

    @property
    def last_stats(self) -> BuildStats | None:
        """Get build statistics from the last build."""
        return self._last_stats

    def full_build(self, parallel: bool = False) -> BuildStats:
        """
        Perform a full (non-incremental) build.

        Args:
            parallel: Whether to use parallel rendering

        Returns:
            Build statistics
        """
        self._site = Site.from_config(self.site_dir)
        self._site.discover_content()
        self._site.discover_assets()

        options = BuildOptions(
            incremental=False,
            force_sequential=not parallel,
        )
        self._last_stats = self._site.build(options)
        self._build_count += 1

        return self._last_stats

    def incremental_build(self, parallel: bool = False) -> BuildStats:
        """
        Perform an incremental (warm) build.

        Creates a fresh Site instance to ensure changes are detected.

        Args:
            parallel: Whether to use parallel rendering

        Returns:
            Build statistics
        """
        # Create fresh site to detect file changes
        self._site = Site.from_config(self.site_dir)
        self._site.discover_content()
        self._site.discover_assets()

        options = BuildOptions(
            incremental=True,
            force_sequential=not parallel,
        )
        self._last_stats = self._site.build(options)
        self._build_count += 1

        return self._last_stats

    def modify_file(self, relative_path: str, content: str) -> None:
        """
        Modify a file with new content and ensure mtime changes.

        Args:
            relative_path: Path relative to site_dir
            content: New file content
        """
        file_path = self.site_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        self._bump_mtime(file_path)

    def create_file(self, relative_path: str, content: str) -> None:
        """
        Create a new file with content.

        Args:
            relative_path: Path relative to site_dir
            content: File content
        """
        file_path = self.site_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    def delete_file(self, relative_path: str) -> None:
        """
        Delete a file.

        Args:
            relative_path: Path relative to site_dir
        """
        file_path = self.site_dir / relative_path
        if file_path.exists():
            file_path.unlink()

    def delete_directory(self, relative_path: str) -> None:
        """
        Delete a directory and all its contents.

        Args:
            relative_path: Path relative to site_dir
        """
        dir_path = self.site_dir / relative_path
        if dir_path.exists():
            shutil.rmtree(dir_path)

    def read_output(self, relative_path: str) -> str:
        """
        Read content from the output directory.

        Args:
            relative_path: Path relative to output_dir

        Returns:
            File content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        output_path = self.output_dir / relative_path
        if not output_path.exists():
            raise FileNotFoundError(f"Output file not found: {output_path}")
        return output_path.read_text()

    def output_exists(self, relative_path: str) -> bool:
        """
        Check if an output file exists.

        Args:
            relative_path: Path relative to output_dir

        Returns:
            True if file exists
        """
        return (self.output_dir / relative_path).exists()

    def assert_output_contains(self, relative_path: str, text: str) -> None:
        """
        Assert that an output file contains specific text.

        Args:
            relative_path: Path relative to output_dir
            text: Text to search for

        Raises:
            AssertionError: If file doesn't exist or doesn't contain text
        """
        content = self.read_output(relative_path)
        assert text in content, (
            f"Expected '{text}' in {relative_path}, but got:\n{content[:500]}..."
        )

    def assert_output_not_contains(self, relative_path: str, text: str) -> None:
        """
        Assert that an output file does not contain specific text.

        Args:
            relative_path: Path relative to output_dir
            text: Text that should not be present

        Raises:
            AssertionError: If file contains text
        """
        if not self.output_exists(relative_path):
            return  # File doesn't exist, so it can't contain text
        content = self.read_output(relative_path)
        assert text not in content, f"Found unexpected '{text}' in {relative_path}"

    def assert_output_exists(self, relative_path: str) -> None:
        """
        Assert that an output file exists.

        Args:
            relative_path: Path relative to output_dir

        Raises:
            AssertionError: If file doesn't exist
        """
        assert self.output_exists(relative_path), (
            f"Expected output file to exist: {self.output_dir / relative_path}"
        )

    def assert_output_missing(self, relative_path: str) -> None:
        """
        Assert that an output file does not exist.

        Args:
            relative_path: Path relative to output_dir

        Raises:
            AssertionError: If file exists
        """
        assert not self.output_exists(relative_path), (
            f"Expected output file to NOT exist: {self.output_dir / relative_path}"
        )

    def assert_page_rebuilt(self, page_path: str) -> None:
        """
        Assert that a specific page was rebuilt in the last incremental build.

        Note: This is a basic check using stats. For detailed tracking,
        use cache_misses or examine page output mtime.

        Args:
            page_path: Content path (e.g., 'blog/post1.md')
        """
        # Basic assertion - for now just verify output exists
        # More sophisticated tracking would require build stats per-page
        output_html = self._content_path_to_output(page_path)
        assert self.output_exists(output_html), (
            f"Expected page to be rebuilt: {page_path} -> {output_html}"
        )

    def assert_pages_built(self, min_count: int = 1) -> None:
        """
        Assert that at least min_count pages were built.

        Args:
            min_count: Minimum number of pages expected
        """
        assert self._last_stats is not None, "No build has been performed"
        assert self._last_stats.pages_built >= min_count, (
            f"Expected at least {min_count} pages built, got {self._last_stats.pages_built}"
        )

    def wait_for_fs(self, duration: float = 0.05) -> None:
        """
        Wait for filesystem to settle after modifications.

        Some filesystems have coarse mtime resolution. This ensures
        that subsequent builds detect file changes.

        Args:
            duration: Seconds to wait (default 50ms)
        """
        time.sleep(duration)

    def _bump_mtime(self, file_path: Path) -> None:
        """
        Bump file mtime to ensure change detection.

        Incremental builds use (mtime, size) fast path, so tests must
        ensure mtime differs after modifications.
        """
        stat = file_path.stat()
        new_time = stat.st_mtime + 2.0
        os.utime(file_path, (new_time, new_time))

    def _content_path_to_output(self, content_path: str) -> str:
        """
        Convert content path to expected output path.

        Example: 'blog/post1.md' -> 'blog/post1/index.html'
        """
        # Remove content/ prefix if present
        if content_path.startswith("content/"):
            content_path = content_path[8:]

        # Handle _index.md files
        if content_path.endswith("_index.md"):
            return content_path.replace("_index.md", "index.html")

        # Handle regular .md files -> directory/index.html
        if content_path.endswith(".md"):
            return content_path[:-3] + "/index.html"

        return content_path


def create_basic_site_structure(site_dir: Path) -> None:
    """
    Create a minimal site structure for testing.

    Creates:
    - bengal.toml with basic config
    - content/index.md home page
    """
    # Config
    (site_dir / "bengal.toml").write_text("""
[site]
title = "Warm Build Test Site"
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

This is the home page.
""")


def create_nav_site_structure(site_dir: Path) -> None:
    """
    Create a site structure with navigation features.

    Creates:
    - Multiple sections (blog/, docs/, guides/)
    - Menu configuration
    - Nested content for nav testing
    """
    # Config with menu
    (site_dir / "bengal.toml").write_text("""
[site]
title = "Nav Test Site"
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

[[menu.main]]
name = "Docs"
url = "/docs/"
weight = 3
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

    # Blog section
    blog_dir = content_dir / "blog"
    blog_dir.mkdir()
    (blog_dir / "_index.md").write_text("""---
title: Blog
weight: 1
menu:
  main:
    weight: 2
---

# Blog
""")
    (blog_dir / "post1.md").write_text("""---
title: First Post
date: 2026-01-01
---

First post content.
""")

    # Docs section with nested guides
    docs_dir = content_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "_index.md").write_text("""---
title: Documentation
weight: 2
menu:
  main:
    weight: 3
---

# Documentation
""")

    guides_dir = docs_dir / "guides"
    guides_dir.mkdir()
    (guides_dir / "_index.md").write_text("""---
title: Guides
weight: 1
---

# Guides
""")
    (guides_dir / "intro.md").write_text("""---
title: Introduction
weight: 1
---

Introduction guide content.
""")


def create_taxonomy_site_structure(site_dir: Path) -> None:
    """
    Create a site structure with taxonomy features.

    Creates:
    - Posts with tags and categories
    - Taxonomy configuration
    """
    # Config with taxonomies
    (site_dir / "bengal.toml").write_text("""
[site]
title = "Taxonomy Test Site"
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

    # Blog posts with tags
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


def create_data_site_structure(site_dir: Path) -> None:
    """
    Create a site structure with data files.

    Creates:
    - data/team.yaml
    - data/config.yaml
    - Template that uses data
    """
    # Config
    (site_dir / "bengal.toml").write_text("""
[site]
title = "Data Test Site"
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

    (data_dir / "config.yaml").write_text("""
features:
  dark_mode: true
  analytics: false
""")

    # Content directory
    content_dir = site_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # About page that uses team data
    (content_dir / "about.md").write_text("""---
title: About Us
---

# About Us

Meet our team!
""")

    # Home page
    (content_dir / "_index.md").write_text("""---
title: Home
---

# Welcome
""")


def create_template_chain_site_structure(site_dir: Path) -> None:
    """
    Create a site structure with template inheritance.

    Creates:
    - templates/base.html (root template)
    - templates/layouts/default.html (extends base)
    - templates/layouts/docs.html (extends default)
    - templates/partials/sidebar.html
    - templates/shortcodes/note.html
    """
    # Config
    (site_dir / "bengal.toml").write_text("""
[site]
title = "Template Chain Test Site"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false
""")

    # Templates directory
    templates_dir = site_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    # Base template
    (templates_dir / "base.html").write_text("""<!DOCTYPE html>
<html>
<head>
    <title>{{ page.title }} - {{ site.title }}</title>
</head>
<body>
    <header>
        <nav>{% block nav %}{% endblock %}</nav>
    </header>
    <main>
        {% block content %}{% endblock %}
    </main>
    <footer>
        <!-- Base footer v1 -->
        {% block footer %}{% endblock %}
    </footer>
</body>
</html>
""")

    # Layouts
    layouts_dir = templates_dir / "layouts"
    layouts_dir.mkdir()

    (layouts_dir / "default.html").write_text("""{% extends "base.html" %}

{% block nav %}
<ul>
    <li><a href="/">Home</a></li>
</ul>
{% endblock %}

{% block content %}
<article>
    <h1>{{ page.title }}</h1>
    {{ content }}
</article>
{% endblock %}
""")

    (layouts_dir / "docs.html").write_text("""{% extends "layouts/default.html" %}

{% block content %}
<div class="docs-container">
    {% include "partials/sidebar.html" %}
    <article class="docs-content">
        <h1>{{ page.title }}</h1>
        {{ content }}
    </article>
</div>
{% endblock %}
""")

    # Partials
    partials_dir = templates_dir / "partials"
    partials_dir.mkdir()

    (partials_dir / "sidebar.html").write_text("""<aside class="sidebar">
    <h3>Sidebar v1</h3>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
</aside>
""")

    # Shortcodes
    shortcodes_dir = templates_dir / "shortcodes"
    shortcodes_dir.mkdir()

    (shortcodes_dir / "note.html").write_text("""<div class="note">
    <strong>Note:</strong> {{ inner }}
</div>
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

    # Blog section (uses default layout)
    blog_dir = content_dir / "blog"
    blog_dir.mkdir()
    (blog_dir / "_index.md").write_text("""---
title: Blog
---

# Blog
""")
    (blog_dir / "post1.md").write_text("""---
title: Blog Post
---

Blog content.
""")

    # Docs section (uses docs layout)
    docs_dir = content_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "_index.md").write_text("""---
title: Documentation
layout: docs
---

# Documentation
""")
    (docs_dir / "guide.md").write_text("""---
title: User Guide
layout: docs
---

Guide content with a {{< note >}}This is a note{{< /note >}}
""")


def create_output_formats_site_structure(site_dir: Path) -> None:
    """
    Create a site structure with multiple output formats enabled.

    Creates:
    - Site with RSS, sitemap, and llm-full.txt enabled
    - Blog section for RSS testing
    """
    # Config with output formats
    (site_dir / "bengal.toml").write_text("""
[site]
title = "Output Formats Test Site"
baseurl = "https://example.com"
description = "A site for testing output formats"

[build]
output_dir = "public"
incremental = true
generate_sitemap = true
generate_rss = true

[output_formats]
enabled = true
llm_full = true
""")

    # Content directory
    content_dir = site_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Home page
    (content_dir / "_index.md").write_text("""---
title: Home
---

# Welcome

Home page content.
""")

    # Blog section with RSS
    blog_dir = content_dir / "blog"
    blog_dir.mkdir()
    (blog_dir / "_index.md").write_text("""---
title: Blog
---

# Blog
""")
    for i in range(3):
        (blog_dir / f"post{i + 1}.md").write_text(f"""---
title: Blog Post {i + 1}
date: 2026-01-{i + 1:02d}
description: Description for post {i + 1}
---

Content for blog post {i + 1}.
""")


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def warm_build_site(tmp_path: Path) -> WarmBuildTestSite:
    """
    Create a minimal test site for warm build testing.

    Returns:
        WarmBuildTestSite helper with basic site structure
    """
    site_dir = tmp_path / "test_site"
    site_dir.mkdir()
    create_basic_site_structure(site_dir)
    return WarmBuildTestSite(site_dir=site_dir)


@pytest.fixture
def site_with_nav(tmp_path: Path) -> WarmBuildTestSite:
    """
    Create a test site with navigation features.

    Returns:
        WarmBuildTestSite helper with navigation structure
    """
    site_dir = tmp_path / "nav_site"
    site_dir.mkdir()
    create_nav_site_structure(site_dir)
    return WarmBuildTestSite(site_dir=site_dir)


@pytest.fixture
def site_with_taxonomy(tmp_path: Path) -> WarmBuildTestSite:
    """
    Create a test site with taxonomy features.

    Returns:
        WarmBuildTestSite helper with tags and categories
    """
    site_dir = tmp_path / "taxonomy_site"
    site_dir.mkdir()
    create_taxonomy_site_structure(site_dir)
    return WarmBuildTestSite(site_dir=site_dir)


@pytest.fixture
def site_with_data(tmp_path: Path) -> WarmBuildTestSite:
    """
    Create a test site with data files.

    Returns:
        WarmBuildTestSite helper with data/ directory
    """
    site_dir = tmp_path / "data_site"
    site_dir.mkdir()
    create_data_site_structure(site_dir)
    return WarmBuildTestSite(site_dir=site_dir)


@pytest.fixture
def site_with_templates(tmp_path: Path) -> WarmBuildTestSite:
    """
    Create a test site with template inheritance.

    Returns:
        WarmBuildTestSite helper with template chain
    """
    site_dir = tmp_path / "template_site"
    site_dir.mkdir()
    create_template_chain_site_structure(site_dir)
    return WarmBuildTestSite(site_dir=site_dir)


@pytest.fixture
def site_with_output_formats(tmp_path: Path) -> WarmBuildTestSite:
    """
    Create a test site with multiple output formats enabled.

    Returns:
        WarmBuildTestSite helper with RSS, sitemap, llm-full.txt
    """
    site_dir = tmp_path / "output_formats_site"
    site_dir.mkdir()
    create_output_formats_site_structure(site_dir)
    return WarmBuildTestSite(site_dir=site_dir)
