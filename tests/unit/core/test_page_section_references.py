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
        _raw_content="Content",
        _raw_metadata={"title": "Post 1"},
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
        _raw_content="Content",
        _raw_metadata={"title": "Post 1", "slug": "post-1"},
    )

    temp_site.sections = [blog]
    temp_site.register_sections()

    page._site = temp_site
    page._section = blog

    # Get original URL
    original_url = page.href

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
    assert page.href == original_url
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
            _raw_content="Content from disk",
            _raw_metadata={"title": "Post 1"},
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
        _raw_content="Content",
        _raw_metadata={"title": "Post 1"},
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
        _raw_content="Content",
        _raw_metadata={"title": "Post 1"},
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
        _raw_content="Content",
        _raw_metadata={"title": "Post 1"},
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
            _raw_content="Content from disk",
            _raw_metadata={"title": "Post 1"},
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
        _raw_content="Content",
        _raw_metadata={"title": "Post 1"},
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
        _raw_content="Content",
        _raw_metadata={"title": "Introduction"},
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


# ============================================================================
# Virtual Section Tests
# See: plan/active/rfc-page-section-reference-contract.md
# ============================================================================


def test_virtual_section_reference(temp_site):
    """Test that virtual pages have correct _section reference.

    Virtual sections have path=None and must use URL-based lookups.
    This test verifies the fix for the critical bug where virtual pages
    had flat navigation because _section was always None.

    See: plan/active/rfc-page-section-reference-contract.md

    """
    # Create virtual section (path=None like autodoc API sections)
    api_section = Section.create_virtual(
        name="api",
        relative_url="/api/",
        title="API Reference",
    )

    # Create virtual page for this section
    page = Page.create_virtual(
        source_id="api/index.md",
        title="API Index",
        content="API documentation",
    )

    temp_site.sections = [api_section]
    temp_site.register_sections()

    page._site = temp_site
    page._section = api_section  # Should store URL, not path

    # Verify section is accessible via URL-based lookup
    assert page._section == api_section
    assert page._section_path is None  # Not path-based
    assert page._section_url == "/api/"  # URL-based


def test_virtual_section_hierarchical_navigation(temp_site):
    """Test that virtual pages have hierarchical navigation, not flat.

    This is the key test for the RFC - virtual autodoc pages should
    show hierarchical navigation (api > core > module) instead of
    flat navigation (all modules at same level).

    """
    # Create nested virtual section hierarchy (like autodoc generates)
    core_section = Section.create_virtual(
        name="core",
        relative_url="/api/core/",
        title="Core Module",
    )

    api_section = Section.create_virtual(
        name="api",
        relative_url="/api/",
        title="API Reference",
    )

    # Set up parent relationship
    core_section.parent = api_section
    api_section.subsections = [core_section]

    # Create page in the nested section
    page = Page.create_virtual(
        source_id="api/core/page_module.md",
        title="Page Module",
        content="Documentation for Page class",
    )

    core_section.add_page(page)

    temp_site.sections = [api_section]
    temp_site.register_sections()

    page._site = temp_site
    page._section = core_section

    # Verify hierarchical navigation works
    assert page._section is not None, "Virtual page should have _section"
    assert page._section.name == "core"
    assert page._section.root.name == "api"

    # Verify navigation hierarchy is correct (not flat)
    hierarchy = page._section.hierarchy
    assert len(hierarchy) == 2
    assert hierarchy == ["api", "core"]


def test_virtual_section_url_registry(temp_site):
    """Test that Site.get_section_by_url() returns correct virtual section."""
    api_section = Section.create_virtual(
        name="api",
        relative_url="/api/",
        title="API Reference",
    )

    temp_site.sections = [api_section]
    temp_site.register_sections()

    # Verify URL-based lookup works
    found = temp_site.get_section_by_url("/api/")
    assert found == api_section
    assert found.title == "API Reference"


def test_mixed_regular_and_virtual_sections(temp_site):
    """Test that both regular and virtual pages have correct _section."""
    # Create regular section with path
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    # Create virtual section without path
    api_section = Section.create_virtual(
        name="api",
        relative_url="/api/",
        title="API Reference",
    )

    # Create pages
    blog_post = Page(
        source_path=temp_site.root_path / "content" / "blog" / "post1.md",
        _raw_content="Blog content",
        _raw_metadata={"title": "Post 1"},
    )

    api_page = Page.create_virtual(
        source_id="api/module.md",
        title="Module Docs",
        content="API content",
    )

    temp_site.sections = [blog, api_section]
    temp_site.register_sections()

    blog_post._site = temp_site
    blog_post._section = blog

    api_page._site = temp_site
    api_page._section = api_section

    # Verify both have correct sections
    assert blog_post._section == blog
    assert blog_post._section_path == blog.path  # Path-based

    assert api_page._section == api_section
    assert api_page._section_url == "/api/"  # URL-based


def test_virtual_section_setter_clears_both_references(temp_site):
    """Test that setting _section to None clears both path and URL."""
    page = Page(
        source_path=temp_site.root_path / "content" / "test.md",
        _raw_content="Content",
        _raw_metadata={"title": "Test"},
    )

    # First set to virtual section
    api_section = Section.create_virtual(
        name="api",
        relative_url="/api/",
        title="API",
    )
    temp_site.sections = [api_section]
    temp_site.register_sections()

    page._site = temp_site
    page._section = api_section

    assert page._section_url == "/api/"
    assert page._section_path is None

    # Then clear
    page._section = None

    assert page._section_path is None
    assert page._section_url is None
    assert page._section is None
