"""
Layout smoke tests for full page templates.

Integration tests that build real sites and assert on rendered output.
Closes the gap between template function tests (unit) and E2E smoke.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


def _roots_dir() -> Path:
    """Path to tests/roots/."""
    return Path(__file__).parent.parent / "roots"


def _prepare_site(tmp_path: Path, testroot: str) -> Path:
    """Copy test root to tmp_path, excluding build artifacts."""
    root_path = _roots_dir() / testroot
    if not root_path.exists():
        available = [p.name for p in _roots_dir().iterdir() if p.is_dir()]
        raise ValueError(f"Test root '{testroot}' not found. Available: {', '.join(available)}")
    site_dir = tmp_path / "site"
    site_dir.mkdir(exist_ok=True)
    for item in root_path.iterdir():
        if item.name in (".bengal", "public"):
            continue
        dst = site_dir / item.name
        if item.is_file():
            shutil.copy2(item, dst)
        elif item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
    return site_dir


class TestTagLayoutSmoke:
    """Smoke tests for tag.html and tags.html via full build."""

    def test_tag_page_renders_with_expected_content(self, tmp_path):
        """Tag page (tag.html) renders with tag name and post count."""
        site_dir = _prepare_site(tmp_path, "test-taxonomy")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        tag_html = site_dir / "public" / "tags" / "python" / "index.html"
        if not tag_html.exists():
            tag_txt = site_dir / "public" / "tags" / "python" / "index.txt"
            assert tag_txt.exists(), "Expected tag output (html or txt)"
            content = tag_txt.read_text()
        else:
            content = tag_html.read_text()

        assert "python" in content
        assert "post" in content.lower() or "Python" in content

    def test_tags_index_renders_with_expected_content(self, tmp_path):
        """Tags index (tags.html) renders with tag list."""
        site_dir = _prepare_site(tmp_path, "test-taxonomy")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        tags_html = site_dir / "public" / "tags" / "index.html"
        if not tags_html.exists():
            tags_txt = site_dir / "public" / "tags" / "index.txt"
            assert tags_txt.exists(), "Expected tags index output"
            content = tags_txt.read_text()
        else:
            content = tags_html.read_text()

        assert "All Tags" in content or "tags" in content.lower()
        assert len(content) > 50


class TestArchiveLayoutSmoke:
    """Smoke tests for archive.html via full build."""

    def test_blog_archive_renders(self, tmp_path):
        """Archive layout renders for blog section."""
        site_dir = _prepare_site(tmp_path, "test-blog-paginated")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        posts_index = site_dir / "public" / "posts" / "index.html"
        if not posts_index.exists():
            posts_txt = site_dir / "public" / "posts" / "index.txt"
            assert posts_txt.exists(), "Expected blog/posts index output"
            content = posts_txt.read_text()
        else:
            content = posts_index.read_text()

        assert len(content) > 100
        assert "Post" in content or "post" in content


class TestBlogListLayoutSmoke:
    """Smoke tests for blog/list.html via full build."""

    def test_blog_list_renders_with_posts(self, tmp_path):
        """Blog list renders with post titles."""
        site_dir = _prepare_site(tmp_path, "test-blog-paginated")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        posts_index = site_dir / "public" / "posts" / "index.html"
        if not posts_index.exists():
            posts_index = site_dir / "public" / "posts" / "index.txt"
        assert posts_index.exists(), "Expected blog list output"
        content = posts_index.read_text()

        assert "post" in content.lower()


class TestDocSingleLayoutSmoke:
    """Smoke tests for doc/single.html via full build."""

    def test_doc_single_renders(self, tmp_path):
        """Doc single page renders with content."""
        site_dir = _prepare_site(tmp_path, "test-directives")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        doc_pages = list((site_dir / "public").rglob("**/index.html"))
        doc_pages.extend((site_dir / "public").rglob("**/index.txt"))
        assert len(doc_pages) >= 1, "Expected at least one doc page"
        content = doc_pages[0].read_text()
        assert len(content) > 50
