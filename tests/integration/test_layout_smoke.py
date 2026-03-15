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
        """Tag page (tag.html) writes real HTML for the routed page."""
        site_dir = _prepare_site(tmp_path, "test-taxonomy")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        tag_html = site_dir / "public" / "tags" / "python" / "index.html"
        assert tag_html.exists(), "Expected routed tag page HTML output"
        content = tag_html.read_text()

        assert "python" in content
        assert "post" in content.lower() or "Python" in content

    def test_tags_index_renders_with_expected_content(self, tmp_path):
        """Tags index (tags.html) writes real HTML for the routed page."""
        site_dir = _prepare_site(tmp_path, "test-taxonomy")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        tags_html = site_dir / "public" / "tags" / "index.html"
        assert tags_html.exists(), "Expected routed tags index HTML output"
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


class TestTracksLayoutSmoke:
    """Smoke tests for tracks/list.html and tracks/single.html via full build."""

    def test_tracks_index_renders_with_track_cards(self, tmp_path):
        """Tracks index (tracks/list.html) renders with track cards, not empty state."""
        site_dir = _prepare_site(tmp_path, "test-tracks")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        tracks_html = site_dir / "public" / "tracks" / "index.html"
        if not tracks_html.exists():
            tracks_txt = site_dir / "public" / "tracks" / "index.txt"
            assert tracks_txt.exists(), "Expected tracks index output"
            content = tracks_txt.read_text()
        else:
            content = tracks_html.read_text()

        assert "Getting Started" in content, "Expected track title from tracks.yaml"
        assert "No tracks defined" not in content, "site.data.tracks must be loaded"

    def test_track_single_renders_with_content(self, tmp_path):
        """Track single page (tracks/single.html) renders with track content."""
        site_dir = _prepare_site(tmp_path, "test-tracks")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        track_html = site_dir / "public" / "tracks" / "getting-started" / "index.html"
        if not track_html.exists():
            track_txt = site_dir / "public" / "tracks" / "getting-started" / "index.txt"
            assert track_txt.exists(), "Expected track single output"
            content = track_txt.read_text()
        else:
            content = track_html.read_text()

        assert "Getting Started Track" in content or "Page 1" in content
        assert len(content) > 50


class TestSearchLayoutSmoke:
    """Smoke tests for search.html via full build."""

    def test_search_page_renders(self, tmp_path):
        """Search page renders with search UI."""
        site_dir = _prepare_site(tmp_path, "test-basic")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        search_html = site_dir / "public" / "search" / "index.html"
        if not search_html.exists():
            search_txt = site_dir / "public" / "search" / "index.txt"
            assert search_txt.exists(), "Expected search page output"
            content = search_txt.read_text()
        else:
            content = search_html.read_text()

        assert "search" in content.lower()
        assert len(content) > 50


class Test404LayoutSmoke:
    """Smoke tests for 404.html via full build."""

    def test_404_page_renders(self, tmp_path):
        """404 page renders with not-found content."""
        site_dir = _prepare_site(tmp_path, "test-basic")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        notfound_html = site_dir / "public" / "404.html"
        assert notfound_html.exists(), "Expected 404.html output"
        content = notfound_html.read_text()

        assert (
            "404" in content
            or "not found" in content.lower()
            or "page not found" in content.lower()
        )
        assert len(content) > 50


class TestGraphLayoutSmoke:
    """Smoke tests for graph page via full build."""

    def test_graph_page_renders(self, tmp_path):
        """Graph page renders with graph content."""
        site_dir = _prepare_site(tmp_path, "test-basic")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        graph_html = site_dir / "public" / "graph" / "index.html"
        if not graph_html.exists():
            graph_txt = site_dir / "public" / "graph" / "index.txt"
            assert graph_txt.exists(), "Expected graph page output"
            content = graph_txt.read_text()
        else:
            content = graph_html.read_text()

        assert "graph" in content.lower() or "mermaid" in content.lower() or len(content) > 50


class TestHomeLayoutSmoke:
    """Smoke tests for home.html via full build."""

    def test_home_page_renders(self, tmp_path):
        """Home page renders with content."""
        site_dir = _prepare_site(tmp_path, "test-basic")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        index_html = site_dir / "public" / "index.html"
        if not index_html.exists():
            index_txt = site_dir / "public" / "index.txt"
            assert index_txt.exists(), "Expected home page output"
            content = index_txt.read_text()
        else:
            content = index_html.read_text()

        assert "Welcome" in content or "Home" in content
        assert len(content) > 50


class TestDocListLayoutSmoke:
    """Smoke tests for doc/list.html via full build."""

    def test_doc_list_renders(self, tmp_path):
        """Doc list (section index) renders with content."""
        site_dir = _prepare_site(tmp_path, "test-directives")
        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        sections_html = site_dir / "public" / "sections" / "index.html"
        if not sections_html.exists():
            sections_txt = site_dir / "public" / "sections" / "index.txt"
            assert sections_txt.exists(), "Expected sections index output"
            content = sections_txt.read_text()
        else:
            content = sections_html.read_text()

        assert "Sections" in content or "Nested" in content
        assert len(content) > 50
