"""Integration tests for content build with parallel rendering.

Validates that content templates render correctly under parallel rendering.
Uses docs layout (macro-heavy, stable) and blog layout (blog/single.html).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


@pytest.fixture
def temp_site() -> Path:
    """Create a temporary site with docs and blog content (excerpt edge cases)."""
    temp_dir = Path(tempfile.mkdtemp())
    (temp_dir / "bengal.toml").write_text(
        '[site]\ntitle = "Content Build Test"\nbaseurl = "/"\n\n'
        '[build]\ncontent_dir = "content"\noutput_dir = "public"\ntheme = "default"\n\n'
        "[markdown]\n"
    )
    content = temp_dir / "content"
    content.mkdir(parents=True)

    docs = content / "docs"
    docs.mkdir()
    (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
    (docs / "page1.md").write_text(
        "---\ntitle: First Page\ndescription: A short summary.\n---\n\nBody content here.\n"
    )
    (docs / "page2.md").write_text(
        "---\ntitle: Second Page\ndescription: A short summary.\nexcerpt: A short summary.\n---\n\n"
    )

    posts = content / "posts"
    posts.mkdir()
    (posts / "_index.md").write_text(
        "---\ntype: blog\ntitle: Posts\ndescription: Blog posts\n---\n"
    )
    (posts / "hello.md").write_text(
        "---\ntype: blog\ntitle: Hello World\ndate: '2026-03-01'\ndescription: First post.\n---\n\nHello from the blog.\n"
    )
    (posts / "series-part1.md").write_text(
        "---\ntype: blog\ntitle: Series Part 1\ndate: '2026-03-02'\ndescription: First in series.\n"
        "series:\n  id: test-series\n  name: Test Series\n  part: 1\n  total: 2\n---\n\nPart one content.\n"
    )
    (posts / "series-part2.md").write_text(
        "---\ntype: blog\ntitle: Series Part 2\ndate: '2026-03-03'\ndescription: Second in series.\n"
        "series:\n  id: test-series\n  name: Test Series\n  part: 2\n  total: 2\n---\n\nPart two content.\n"
    )

    tutorial = content / "tutorial"
    tutorial.mkdir()
    (tutorial / "_index.md").write_text(
        "---\ntype: tutorial\ntitle: Tutorials\ndescription: Learning guides\n---\n"
    )
    (tutorial / "step1.md").write_text(
        "---\ntype: tutorial\ntitle: Step 1\ndescription: First step.\n---\n\nStep one content.\n"
    )

    yield temp_dir
    shutil.rmtree(temp_dir)


def test_content_build_parallel_all_pages_render(temp_site: Path) -> None:
    """Full build with parallel rendering produces index.html for all pages."""
    site = Site(root_path=temp_site, config={})
    site.build(BuildOptions(force_sequential=False))

    output = temp_site / "public"
    page1_html = output / "docs" / "page1" / "index.html"
    page2_html = output / "docs" / "page2" / "index.html"

    assert page1_html.exists(), f"docs/page1/index.html not found in {output}"
    assert page2_html.exists(), f"docs/page2/index.html not found in {output}"

    html1 = page1_html.read_text()
    html2 = page2_html.read_text()

    assert len(html1) > 100, "page1 HTML too short"
    assert len(html2) > 100, "page2 HTML too short"
    assert "First Page" in html1
    assert "Second Page" in html2


def test_content_build_excerpt_edge_case(temp_site: Path) -> None:
    """Page with excerpt == description still renders (content-transform fallback)."""
    site = Site(root_path=temp_site, config={})
    site.build(BuildOptions(force_sequential=False))

    output = temp_site / "public"
    page2_html = output / "docs" / "page2" / "index.html"
    assert page2_html.exists()
    html = page2_html.read_text()
    assert "Second Page" in html
    assert len(html) > 100


def test_content_build_blog_post_renders(temp_site: Path) -> None:
    """Blog post renders under parallel build (blog/single.html template)."""
    site = Site(root_path=temp_site, config={})
    site.build(BuildOptions(force_sequential=False))

    output = temp_site / "public"
    post_html = output / "posts" / "hello" / "index.html"
    assert post_html.exists(), f"posts/hello/index.html not found in {output}"
    html = post_html.read_text()
    assert "Hello World" in html
    assert "Hello from the blog" in html


def test_content_build_excerpt_extracted_without_headings(temp_site: Path) -> None:
    """Page with no headings still gets excerpt extracted (Bug 1 fix)."""
    site = Site(root_path=temp_site, config={})
    site.build(BuildOptions(force_sequential=False))

    output = temp_site / "public"
    post_html = output / "posts" / "hello" / "index.html"
    assert post_html.exists()
    html = post_html.read_text()
    # Body content proves page parsed; excerpt extracted from first block when no headings
    assert "Hello from the blog" in html
    # Posts index renders with post cards (excerpt or description fallback)
    list_html = (output / "posts" / "index.html").read_text()
    assert "Hello World" in list_html
    assert "Hello from the blog" in list_html or "First post." in list_html


def test_content_build_series_post_renders(temp_site: Path) -> None:
    """Blog posts with series frontmatter render (series-nav uses site.indexes.series)."""
    site = Site(root_path=temp_site, config={})
    site.build(BuildOptions(force_sequential=False))

    output = temp_site / "public"
    part1_html = output / "posts" / "series-part1" / "index.html"
    part2_html = output / "posts" / "series-part2" / "index.html"
    assert part1_html.exists(), f"posts/series-part1/index.html not found in {output}"
    assert part2_html.exists(), f"posts/series-part2/index.html not found in {output}"

    html1 = part1_html.read_text()
    html2 = part2_html.read_text()
    assert "Series Part 1" in html1
    assert "Series Part 2" in html2
    assert "Test Series" in html1
    assert "Test Series" in html2
    assert "Part one content" in html1
    assert "Part two content" in html2


def test_content_build_enriched_index_cross_type(temp_site: Path) -> None:
    """Blog and tutorial sections with enriched index pages render (Bug 2 fix)."""
    site = Site(root_path=temp_site, config={})
    site.build(BuildOptions(force_sequential=False))

    output = temp_site / "public"
    # Blog index (enriched) renders with posts
    blog_index = output / "posts" / "index.html"
    assert blog_index.exists(), f"posts/index.html not found in {output}"
    blog_html = blog_index.read_text()
    assert "Posts" in blog_html
    assert "Hello World" in blog_html

    # Tutorial index (enriched) renders with step
    tutorial_index = output / "tutorial" / "index.html"
    assert tutorial_index.exists(), f"tutorial/index.html not found in {output}"
    tutorial_html = tutorial_index.read_text()
    assert "Tutorials" in tutorial_html
    assert "Step 1" in tutorial_html
