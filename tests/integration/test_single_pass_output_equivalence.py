"""Integration tests for single-pass token capture output equivalence.

Validates that HTML output is identical whether using single_pass_tokens=True
or single_pass_tokens=False. This ensures the optimization doesn't change
rendered content.

Related RFC: plan/drafted/rfc-single-pass-ast-html.md
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from bengal.core.site import Site
from tests._testing.normalize import normalize_html

# Files to exclude from comparison (contain non-deterministic content unrelated to markdown)
EXCLUDED_FILES = {
    "graph/index.html",  # Graph IDs are non-deterministic
    "search/index.html",  # Search index may vary
}


def _extract_markdown_content(html: str) -> str:
    """Extract the markdown-rendered content from HTML.

    Focuses comparison on the actual markdown output, excluding:
    - Navigation (varies by page discovery order)
    - Sidebar, breadcrumbs, related pages
    - Header/footer
    - Internal links (template-generated, not from markdown)

    Args:
        html: Full HTML page content

    Returns:
        Just the markdown-rendered portion, cleaned of navigation artifacts
    """
    # Strip structural elements
    html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL)
    html = re.sub(r"<header[^>]*>.*?</header>", "", html, flags=re.DOTALL)
    html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL)
    html = re.sub(r"<aside[^>]*>.*?</aside>", "", html, flags=re.DOTALL)

    # Strip breadcrumb-like sections
    html = re.sub(r'<[^>]*class="[^"]*breadcrumb[^"]*"[^>]*>.*?</[^>]+>', "", html, flags=re.DOTALL)

    # Strip pagination/related pages sections
    html = re.sub(r'<[^>]*class="[^"]*pagination[^"]*"[^>]*>.*?</[^>]+>', "", html, flags=re.DOTALL)
    html = re.sub(r'<[^>]*class="[^"]*related[^"]*"[^>]*>.*?</[^>]+>', "", html, flags=re.DOTALL)
    html = re.sub(r'<[^>]*class="[^"]*page-nav[^"]*"[^>]*>.*?</[^>]+>', "", html, flags=re.DOTALL)

    # Strip internal links that look like navigation (hrefs starting with /)
    # but preserve external links and anchors
    html = re.sub(r'<a[^>]*href="/[^"#]*"[^>]*>.*?</a>', "[NAV_LINK]", html, flags=re.DOTALL)

    return html


def _build_site_from_root(
    rootdir: Path, tmp_path: Path, testroot: str, single_pass: bool, suffix: str
) -> dict[str, str]:
    """Build site with specified single_pass_tokens and collect all HTML files.

    Args:
        rootdir: Path to tests/roots/
        tmp_path: Temporary directory for this test
        testroot: Name of test root to use
        single_pass: Value for markdown.ast_cache.single_pass_tokens
        suffix: Unique suffix for site directory

    Returns:
        Dict mapping relative path to normalized HTML content
    """
    root_path = rootdir / testroot
    site_dir = tmp_path / f"site_{suffix}"
    site_dir.mkdir()

    # Copy test root to site directory
    shutil.copytree(root_path, site_dir, dirs_exist_ok=True)

    # Create site and configure
    site = Site.from_config(site_dir)
    if "markdown" not in site.config:
        site.config["markdown"] = {}
    if "ast_cache" not in site.config["markdown"]:
        site.config["markdown"]["ast_cache"] = {}
    site.config["markdown"]["ast_cache"]["single_pass_tokens"] = single_pass
    site.config["markdown"]["ast_cache"]["persist_tokens"] = False

    site.discover_content()
    site.discover_assets()
    site.build(parallel=False)

    # Collect all HTML files (excluding non-deterministic files)
    html_files: dict[str, str] = {}
    for html_path in site.output_dir.rglob("*.html"):
        rel_path = str(html_path.relative_to(site.output_dir))
        # Skip files known to have non-deterministic content unrelated to markdown
        if rel_path in EXCLUDED_FILES:
            continue
        content = html_path.read_text(encoding="utf-8")
        # Extract markdown content (strip navigation that varies by discovery order)
        content = _extract_markdown_content(content)
        html_files[rel_path] = normalize_html(content)

    return html_files


def test_basic_site_output_identical_with_single_pass(rootdir, tmp_path):
    """Test that basic site output is identical with single_pass_tokens=True vs False."""
    # Build with single_pass_tokens=False (baseline)
    html_off = _build_site_from_root(
        rootdir, tmp_path, "test-basic", single_pass=False, suffix="off"
    )

    # Build with single_pass_tokens=True (optimized)
    html_on = _build_site_from_root(rootdir, tmp_path, "test-basic", single_pass=True, suffix="on")

    # Compare file counts
    assert len(html_off) == len(html_on), (
        f"Different number of HTML files: "
        f"single_pass=False has {len(html_off)}, single_pass=True has {len(html_on)}"
    )

    # Compare file contents
    for rel_path in html_off:
        assert rel_path in html_on, f"Missing file with single_pass=True: {rel_path}"

        if html_off[rel_path] != html_on[rel_path]:
            # Find first difference for debugging
            lines_off = html_off[rel_path].splitlines()
            lines_on = html_on[rel_path].splitlines()

            for i, (line_off, line_on) in enumerate(zip(lines_off, lines_on, strict=False)):
                if line_off != line_on:
                    pytest.fail(
                        f"Output differs in {rel_path} at line {i + 1}:\n"
                        f"  single_pass=False: {line_off[:100]!r}\n"
                        f"  single_pass=True:  {line_on[:100]!r}"
                    )

            # Length difference
            if len(lines_off) != len(lines_on):
                pytest.fail(
                    f"Output differs in {rel_path}: "
                    f"single_pass=False has {len(lines_off)} lines, "
                    f"single_pass=True has {len(lines_on)} lines"
                )


def test_directive_heavy_site_output_identical_with_single_pass(rootdir, tmp_path):
    """Test that directive-heavy content produces identical output.

    Uses test-directives root which includes:
    - Admonitions (note, warning, tip, important)
    - Nested content in directives
    - Code blocks inside directives
    """
    # Build with single_pass_tokens=False (baseline)
    html_off = _build_site_from_root(
        rootdir, tmp_path, "test-directives", single_pass=False, suffix="off"
    )

    # Build with single_pass_tokens=True (optimized)
    html_on = _build_site_from_root(
        rootdir, tmp_path, "test-directives", single_pass=True, suffix="on"
    )

    # Compare file counts
    assert len(html_off) == len(html_on), (
        f"Different number of HTML files: "
        f"single_pass=False has {len(html_off)}, single_pass=True has {len(html_on)}"
    )

    # Compare each file
    differences: list[str] = []
    for rel_path in sorted(html_off.keys()):
        if rel_path not in html_on:
            differences.append(f"Missing with single_pass=True: {rel_path}")
            continue

        if html_off[rel_path] != html_on[rel_path]:
            # Find and report first difference
            lines_off = html_off[rel_path].splitlines()
            lines_on = html_on[rel_path].splitlines()
            diff_detail = ""
            for i, (line_off, line_on) in enumerate(zip(lines_off, lines_on, strict=False)):
                if line_off != line_on:
                    diff_detail = (
                        f"\n      First diff at line {i + 1}:\n"
                        f"        OFF: {line_off[:120]!r}\n"
                        f"        ON:  {line_on[:120]!r}"
                    )
                    break
            differences.append(f"Content differs: {rel_path}{diff_detail}")

    if differences:
        pytest.fail(
            "Output differs between single_pass_tokens modes:\n"
            + "\n".join(f"  - {d}" for d in differences)
        )


def test_variable_substitution_output_identical_with_single_pass(site_factory, tmp_path):
    """Test that variable substitution produces identical output.

    Creates a test site with {{ page.title }} and {{ site.title }} variables
    to ensure the preprocess path works identically in both modes.
    """
    # Create minimal test site with variable substitution
    site_dir = tmp_path / "var_site"
    site_dir.mkdir()
    content_dir = site_dir / "content"
    content_dir.mkdir()

    # Config
    (site_dir / "bengal.toml").write_text(
        """
[site]
title = "Test Site"
base_url = "https://example.com"

[markdown]
parser = "mistune"
""",
        encoding="utf-8",
    )

    # Content with variable substitution
    (content_dir / "index.md").write_text(
        """---
title: "Variable Test Page"
---

# {{ page.title }}

This page belongs to {{ site.title }}.

:::{note}
Page title is: {{ page.title }}
:::
""",
        encoding="utf-8",
    )

    from bengal.core.site import Site

    # Build with single_pass=False
    site_off = Site.from_config(site_dir)
    site_off.config["markdown"]["ast_cache"] = {
        "single_pass_tokens": False,
        "persist_tokens": False,
    }
    site_off.discover_content()
    site_off.discover_assets()
    site_off.build(parallel=False)

    html_off = (site_off.output_dir / "index.html").read_text(encoding="utf-8")
    html_off_norm = normalize_html(html_off)

    # Clean output
    shutil.rmtree(site_off.output_dir)

    # Build with single_pass=True
    site_on = Site.from_config(site_dir)
    site_on.config["markdown"]["ast_cache"] = {
        "single_pass_tokens": True,
        "persist_tokens": False,
    }
    site_on.discover_content()
    site_on.discover_assets()
    site_on.build(parallel=False)

    html_on = (site_on.output_dir / "index.html").read_text(encoding="utf-8")
    html_on_norm = normalize_html(html_on)

    # Compare
    assert html_off_norm == html_on_norm, (
        "Variable substitution output differs between single_pass_tokens modes"
    )

    # Verify variable substitution actually worked
    assert "Variable Test Page" in html_on
    assert "Test Site" in html_on
