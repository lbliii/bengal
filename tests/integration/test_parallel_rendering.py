"""Integration tests for parallel page rendering.

Regression tests for bugs that only manifest under parallel rendering
(e.g. K-RUN-007: import macros resolving to Undefined).

Uses test-blog-paginated (28 pages) which exceeds parallel_threshold (5)
and uses blog/single.html with newsletter_cta import.
"""

from pathlib import Path

import pytest

from tests._testing.cli import run_cli


@pytest.mark.bengal(testroot="test-blog-paginated")
@pytest.mark.integration
def test_parallel_blog_build_completes_without_render_errors(site, build_site) -> None:
    """K-RUN-007 regression: parallel build of blog site must complete.

    Full rebuild with parallel=True exercises blog/single.html (newsletter_cta
    import) under concurrent render. Fails without the newsletter_cta guard.
    """
    build_site(parallel=True)

    # Verify build produced output
    assert site.output_dir.exists()
    post_html = site.output_dir / "posts" / "post-01" / "index.html"
    assert post_html.exists(), "Blog post HTML should exist"
    assert post_html.stat().st_size > 0, "Post HTML should not be empty"

    # Sanity: post content present
    html = post_html.read_text(encoding="utf-8")
    assert "Blog Post 01" in html or "Test Pagination" in html


@pytest.mark.bengal(testroot="test-blog-paginated")
@pytest.mark.integration
def test_production_full_rebuild_via_cli(site) -> None:
    """Production build smoke: CLI full rebuild must succeed.

    Exercises same path as `bengal site build --environment production --clean-output`.
    """
    site_dir = site.root_path
    result = run_cli(
        ["site", "build", "--environment", "production", "--clean-output"],
        cwd=str(site_dir),
        timeout=120,
    )
    assert result.returncode == 0, f"Production build failed: {result.stderr}"

    output_dir = Path(site_dir) / "public"
    assert (output_dir / "posts" / "post-01" / "index.html").exists()
