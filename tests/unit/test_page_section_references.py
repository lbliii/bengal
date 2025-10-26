"""
Unit tests for Page/PageProxy path-based section references.

Tests the _section property implementation that enables stable
section references across rebuilds.
"""

from pathlib import Path

import pytest

from bengal.core.page import Page, PageProxy
from bengal.core.section import Section
from bengal.core.site import Site


@pytest.fixture
def temp_site(tmp_path):
    """Create a temporary site for testing."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create test content structure
    (content_dir / "blog").mkdir()
    (content_dir / "blog" / "_index.md").write_text("---\ntitle: Blog\n---\n")
    (content_dir / "blog" / "post1.md").write_text("---\ntitle: Post 1\n---\nContent")

    site = Site(root_path=tmp_path, config={"site": {"title": "Test Site"}})
    return site


def test_section_reference_survives_recreation(temp_site):
    """Test that section references survive object recreation."""
    # Create original section
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    # Create page with section reference
    page = Page(
        source_path=temp_site.root_path / "content" / "blog" / "post1.md",
        content="Content",
        metadata={"title": "Post 1"},
    )

    temp_site.sections = [blog]
    temp_site.register_sections()

    page._site = temp_site
    page._section = blog  # This stores the path

    # Verify section is accessible
    assert page._section == blog
    assert page._section_path == blog.path

    # Simulate object recreation (like in incremental builds)
    # Create a NEW Section object with the same path
    blog_recreated = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog (Updated)"},
        pages=[],
        subsections=[],
    )

    temp_site.sections = [blog_recreated]
    temp_site.register_sections()

    # Page should now resolve to the NEW section object
    assert page._section == blog_recreated
    assert page._section is not blog  # Different object in memory
    assert page._section.title == "Blog (Updated)"


def test_page_url_stable_across_rebuilds(temp_site):
    """Test that page URLs remain correct after section recreation."""
    # Create section and page
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    page = Page(
        source_path=temp_site.root_path / "content" / "blog" / "post1.md",
        content="Content",
        metadata={"title": "Post 1", "slug": "post-1"},
    )

    temp_site.sections = [blog]
    temp_site.register_sections()

    page._site = temp_site
    page._section = blog

    # Get original URL
    original_url = page.url

    # Recreate section (simulate incremental build)
    blog_recreated = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    temp_site.sections = [blog_recreated]
    temp_site.register_sections()

    # URL should still be correct
    assert page.url == original_url
    assert page._section == blog_recreated


def test_proxy_url_without_forcing_load(temp_site):
    """Test that PageProxy can access section without forcing full load."""
    # Create section
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    temp_site.sections = [blog]
    temp_site.register_sections()

    # Create a page for the loader to return
    def loader(source_path):
        page = Page(
            source_path=source_path,
            content="Content from disk",
            metadata={"title": "Post 1"},
        )
        page._site = temp_site
        return page

    # Create proxy with metadata
    from bengal.cache.page_discovery_cache import PageMetadata

    metadata = PageMetadata(
        source_path=str(temp_site.root_path / "content" / "blog" / "post1.md"),
        title="Post 1",
        date=None,
        tags=[],
        slug="post-1",
        section=str(blog.path),
        weight=0,
        lang=None,
    )

    proxy = PageProxy(
        source_path=temp_site.root_path / "content" / "blog" / "post1.md",
        metadata=metadata,
        loader=loader,
    )

    proxy._site = temp_site
    proxy._section = blog  # Sets _section_path

    # Access section WITHOUT forcing load
    assert proxy._lazy_loaded is False
    section = proxy._section
    assert section == blog
    assert proxy._lazy_loaded is False  # Still not loaded!


def test_section_setter_stores_path(temp_site):
    """Test that setting _section stores the path, not the object."""
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    page = Page(
        source_path=temp_site.root_path / "content" / "blog" / "post1.md",
        content="Content",
        metadata={"title": "Post 1"},
    )

    temp_site.sections = [blog]
    temp_site.register_sections()
    page._site = temp_site

    # Set section
    page._section = blog

    # Verify path was stored, not the object
    assert page._section_path == blog.path
    assert isinstance(page._section_path, Path)


def test_missing_section_counter_gated_warnings(temp_site, caplog):
    """Test that missing section warnings are counter-gated."""
    page = Page(
        source_path=temp_site.root_path / "content" / "blog" / "post1.md",
        content="Content",
        metadata={"title": "Post 1"},
    )

    page._site = temp_site
    page._section_path = Path("nonexistent")  # Set to a path that doesn't exist

    temp_site.register_sections()  # Empty registry

    # Access section multiple times
    for _i in range(10):
        _ = page._section

    # Check that warnings were limited (not 10 warnings)
    # With counter-gating, we expect: 3 warnings + 1 summary = 4 total
    warning_count = sum(
        1
        for record in caplog.records
        if "section" in record.getMessage().lower() and "not found" in record.getMessage().lower()
    )

    # Should have limited warnings (not 10)
    assert warning_count <= 4, f"Too many warnings: {warning_count}"


def test_section_none_handling(temp_site):
    """Test that None sections are handled correctly."""
    page = Page(
        source_path=temp_site.root_path / "content" / "post1.md",
        content="Content",
        metadata={"title": "Post 1"},
    )

    page._site = temp_site

    # Set section to None
    page._section = None

    assert page._section_path is None
    assert page._section is None


def test_proxy_section_property_delegate(temp_site):
    """Test that PageProxy._section delegates to full page when loaded."""
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    temp_site.sections = [blog]
    temp_site.register_sections()

    def loader(source_path):
        page = Page(
            source_path=source_path,
            content="Content from disk",
            metadata={"title": "Post 1"},
        )
        page._site = temp_site
        page._section = blog
        return page

    from bengal.cache.page_discovery_cache import PageMetadata

    metadata = PageMetadata(
        source_path=str(temp_site.root_path / "content" / "blog" / "post1.md"),
        title="Post 1",
        date=None,
        tags=[],
        slug="post-1",
        section=str(blog.path),
        weight=0,
        lang=None,
    )

    proxy = PageProxy(
        source_path=temp_site.root_path / "content" / "blog" / "post1.md",
        metadata=metadata,
        loader=loader,
    )

    proxy._site = temp_site
    proxy._section = blog

    # Force load by accessing content
    _ = proxy.content

    assert proxy._lazy_loaded is True

    # Now _section should delegate to full page
    assert proxy._section == blog
    assert proxy._full_page._section == blog


def test_page_parent_property_uses_section(temp_site):
    """Test that page.parent property correctly uses _section."""
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    page = Page(
        source_path=temp_site.root_path / "content" / "blog" / "post1.md",
        content="Content",
        metadata={"title": "Post 1"},
    )

    temp_site.sections = [blog]
    temp_site.register_sections()

    page._site = temp_site
    page._section = blog

    # parent property should return the section
    assert page.parent == blog


def test_page_ancestors_uses_section(temp_site):
    """Test that page.ancestors correctly uses _section hierarchy."""
    guides = Section(
        name="guides",
        path=temp_site.root_path / "content" / "docs" / "guides",
        metadata={"title": "Guides"},
        pages=[],
        subsections=[],
    )

    docs = Section(
        name="docs",
        path=temp_site.root_path / "content" / "docs",
        metadata={"title": "Docs"},
        pages=[],
        subsections=[guides],
    )

    guides.parent = docs

    page = Page(
        source_path=temp_site.root_path / "content" / "docs" / "guides" / "intro.md",
        content="Content",
        metadata={"title": "Introduction"},
    )

    temp_site.sections = [docs]
    temp_site.register_sections()

    page._site = temp_site
    page._section = guides

    # ancestors should work correctly
    ancestors = page.ancestors
    assert len(ancestors) == 2
    assert ancestors[0] == guides
    assert ancestors[1] == docs
