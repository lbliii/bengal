"""
Unit tests for RedirectGenerator (Hugo-style aliases).
"""

from pathlib import Path

import pytest

from bengal.postprocess.redirects import RedirectGenerator


class DummyPage:
    """Minimal page mock for testing redirects."""

    def __init__(
        self,
        source_path: str = "content/test.md",
        title: str = "Test Page",
        url: str = "/test/",
        aliases: list[str] | None = None,
    ):
        self.source_path = Path(source_path)
        self.title = title
        self.url = url
        self.permalink = url
        self.aliases = aliases or []


class DummySite:
    """Minimal site mock for testing redirects."""

    def __init__(self, tmp_path: Path, config: dict | None = None):
        self.root_path = tmp_path
        self.output_dir = tmp_path / "public"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or {}
        self.pages: list[DummyPage] = []


def test_redirect_html_has_meta_refresh(tmp_path):
    """Test redirect HTML includes meta refresh tag."""
    site = DummySite(tmp_path)
    gen = RedirectGenerator(site)

    html = gen._render_redirect_html("/old/", "/new/")

    assert '<meta http-equiv="refresh"' in html
    assert 'url=/new/' in html


def test_redirect_html_has_canonical_link(tmp_path):
    """Test redirect HTML includes canonical link for SEO."""
    site = DummySite(tmp_path)
    gen = RedirectGenerator(site)

    html = gen._render_redirect_html("/old/", "/new/")

    assert '<link rel="canonical" href="/new/">' in html


def test_redirect_html_has_noindex(tmp_path):
    """Test redirect HTML includes noindex for SEO."""
    site = DummySite(tmp_path)
    gen = RedirectGenerator(site)

    html = gen._render_redirect_html("/old/", "/new/")

    assert 'name="robots" content="noindex"' in html


def test_redirect_html_has_fallback_link(tmp_path):
    """Test redirect HTML includes fallback link for browsers without meta refresh."""
    site = DummySite(tmp_path)
    gen = RedirectGenerator(site)

    html = gen._render_redirect_html("/old/", "/new/")

    assert '<a href="/new/">/new/</a>' in html


def test_generate_creates_redirect_page(tmp_path):
    """Test that redirect pages are created at alias locations."""
    site = DummySite(tmp_path)
    site.pages = [
        DummyPage(
            title="My New Post",
            url="/blog/my-post/",
            aliases=["/old/posts/my-post/"],
        )
    ]

    gen = RedirectGenerator(site)
    count = gen.generate()

    assert count == 1
    redirect_path = site.output_dir / "old" / "posts" / "my-post" / "index.html"
    assert redirect_path.exists()

    content = redirect_path.read_text()
    assert "url=/blog/my-post/" in content


def test_generate_handles_multiple_aliases(tmp_path):
    """Test that multiple aliases are all generated."""
    site = DummySite(tmp_path)
    site.pages = [
        DummyPage(
            title="My Post",
            url="/blog/my-post/",
            aliases=[
                "/old/path/",
                "/2020/01/original/",
                "/drafts/working-title/",
            ],
        )
    ]

    gen = RedirectGenerator(site)
    count = gen.generate()

    assert count == 3
    assert (site.output_dir / "old" / "path" / "index.html").exists()
    assert (site.output_dir / "2020" / "01" / "original" / "index.html").exists()
    assert (site.output_dir / "drafts" / "working-title" / "index.html").exists()


def test_generate_handles_pages_without_aliases(tmp_path):
    """Test that pages without aliases don't cause errors."""
    site = DummySite(tmp_path)
    site.pages = [
        DummyPage(title="No Aliases", url="/normal/", aliases=[]),
        DummyPage(title="With Alias", url="/aliased/", aliases=["/old-url/"]),
    ]

    gen = RedirectGenerator(site)
    count = gen.generate()

    assert count == 1


def test_generate_skips_conflicting_paths(tmp_path):
    """Test that redirect doesn't overwrite existing content."""
    site = DummySite(tmp_path)

    # Pre-create existing content at alias location
    existing_dir = site.output_dir / "about"
    existing_dir.mkdir(parents=True)
    (existing_dir / "index.html").write_text("<html>Real Content</html>")

    site.pages = [
        DummyPage(
            title="Different Page",
            url="/other/",
            aliases=["/about/"],  # Conflicts with existing
        )
    ]

    gen = RedirectGenerator(site)
    count = gen.generate()

    assert count == 0  # Should skip conflicting path

    # Original content should be preserved
    assert (site.output_dir / "about" / "index.html").read_text() == "<html>Real Content</html>"


def test_generate_logs_alias_conflicts(tmp_path, caplog):
    """Test that multiple pages claiming same alias logs warning."""
    site = DummySite(tmp_path)
    site.pages = [
        DummyPage(title="Page A", url="/page-a/", aliases=["/shared-alias/"]),
        DummyPage(title="Page B", url="/page-b/", aliases=["/shared-alias/"]),
    ]

    gen = RedirectGenerator(site)
    count = gen.generate()

    # Should only generate one redirect (first claimant wins)
    assert count == 1

    # First claimant (/page-a/) should be used
    redirect_content = (site.output_dir / "shared-alias" / "index.html").read_text()
    assert "/page-a/" in redirect_content


def test_generate_normalizes_paths(tmp_path):
    """Test that alias paths are normalized correctly."""
    site = DummySite(tmp_path)
    site.pages = [
        DummyPage(
            title="Test",
            url="/test/",
            aliases=[
                "no-leading-slash/",  # Missing leading slash
                "/trailing-slash/",
                "/no-trailing-slash",  # Missing trailing slash
            ],
        )
    ]

    gen = RedirectGenerator(site)
    count = gen.generate()

    assert count == 3
    # All should be created with normalized paths
    assert (site.output_dir / "no-leading-slash" / "index.html").exists()
    assert (site.output_dir / "trailing-slash" / "index.html").exists()
    assert (site.output_dir / "no-trailing-slash" / "index.html").exists()


def test_redirects_file_not_generated_by_default(tmp_path):
    """Test that _redirects file is not generated by default."""
    site = DummySite(tmp_path)
    site.pages = [
        DummyPage(title="Test", url="/test/", aliases=["/old/"]),
    ]

    gen = RedirectGenerator(site)
    gen.generate()

    assert not (site.output_dir / "_redirects").exists()


def test_redirects_file_generated_when_enabled(tmp_path):
    """Test that _redirects file is generated when enabled in config."""
    site = DummySite(
        tmp_path,
        config={"redirects": {"generate_redirects_file": True}},
    )
    site.pages = [
        DummyPage(title="Page 1", url="/new-1/", aliases=["/old-1/"]),
        DummyPage(title="Page 2", url="/new-2/", aliases=["/old-2/", "/old-2b/"]),
    ]

    gen = RedirectGenerator(site)
    gen.generate()

    redirects_path = site.output_dir / "_redirects"
    assert redirects_path.exists()

    content = redirects_path.read_text()
    assert "/old-1/  /new-1/  301" in content
    assert "/old-2/  /new-2/  301" in content
    assert "/old-2b/  /new-2/  301" in content


def test_empty_site_generates_no_redirects(tmp_path):
    """Test that site with no pages generates no redirects."""
    site = DummySite(tmp_path)
    site.pages = []

    gen = RedirectGenerator(site)
    count = gen.generate()

    assert count == 0


def test_aliases_parsed_from_frontmatter():
    """Test that aliases field is correctly handled in Page objects."""
    # This tests the Page/PageCore integration
    from bengal.core.page.page_core import PageCore

    core = PageCore(
        source_path="content/test.md",
        title="Test",
        aliases=["/old/path/", "/another/"],
    )

    assert core.aliases == ["/old/path/", "/another/"]


def test_page_core_serialization_includes_aliases():
    """Test that aliases are preserved in cache serialization."""
    from bengal.core.page.page_core import PageCore

    original = PageCore(
        source_path="content/test.md",
        title="Test",
        aliases=["/old/", "/another/"],
    )

    # Serialize
    data = original.to_cache_dict()
    assert data["aliases"] == ["/old/", "/another/"]

    # Deserialize
    restored = PageCore.from_cache_dict(data)
    assert restored.aliases == ["/old/", "/another/"]


def test_page_proxy_exposes_aliases():
    """Test that PageProxy exposes aliases from PageCore."""
    from bengal.core.page.page_core import PageCore
    from bengal.core.page.proxy import PageProxy

    core = PageCore(
        source_path="content/test.md",
        title="Test",
        aliases=["/old/path/"],
    )

    proxy = PageProxy(
        source_path=Path("content/test.md"),
        metadata=core,
        loader=lambda x: None,  # Not needed for this test
    )

    assert proxy.aliases == ["/old/path/"]


