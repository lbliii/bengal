"""
Unit tests for Site section registry (path-based lookups).

Tests the section registry infrastructure that enables stable
section references across rebuilds.
"""

import platform
from pathlib import Path

import pytest

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

    (content_dir / "docs").mkdir()
    (content_dir / "docs" / "_index.md").write_text("---\ntitle: Docs\n---\n")
    (content_dir / "docs" / "guides").mkdir()
    (content_dir / "docs" / "guides" / "_index.md").write_text("---\ntitle: Guides\n---\n")

    site = Site(root_path=tmp_path, config={"site": {"title": "Test Site"}})
    return site


def test_register_sections_builds_registry(temp_site):
    """Test that register_sections() builds the registry correctly."""
    # Create sections manually
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    docs = Section(
        name="docs",
        path=temp_site.root_path / "content" / "docs",
        metadata={"title": "Docs"},
        pages=[],
        subsections=[],
    )

    temp_site.sections = [blog, docs]

    # Register sections
    temp_site.register_sections()

    # Verify registry was built
    assert temp_site.registry.section_count == 2

    # Verify sections are accessible
    assert temp_site.get_section_by_path("blog") == blog
    assert temp_site.get_section_by_path("docs") == docs


def test_get_section_by_path_normalized(temp_site):
    """Test that path normalization works correctly."""
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    temp_site.sections = [blog]
    temp_site.register_sections()

    # Test different path formats
    assert temp_site.get_section_by_path("blog") == blog
    assert temp_site.get_section_by_path(Path("blog")) == blog
    assert temp_site.get_section_by_path(temp_site.root_path / "content" / "blog") == blog


def test_get_section_by_path_case_insensitive(temp_site):
    """Test case-insensitive lookups on macOS/Windows."""
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    temp_site.sections = [blog]
    temp_site.register_sections()

    # On macOS/Windows, case-insensitive lookups should work
    system = platform.system()
    if system in ("Darwin", "Windows"):
        assert temp_site.get_section_by_path("BLOG") == blog
        assert temp_site.get_section_by_path("Blog") == blog
    else:
        # On Linux, case-sensitive
        assert temp_site.get_section_by_path("BLOG") is None
        assert temp_site.get_section_by_path("Blog") is None


def test_get_section_by_path_symlinks(temp_site, tmp_path):
    """Test that symlink resolution works correctly."""
    # Create a real directory
    real_dir = tmp_path / "content" / "real_blog"
    real_dir.mkdir()
    (real_dir / "_index.md").write_text("---\ntitle: Blog\n---\n")

    # Create a symlink (skip on Windows if symlinks not supported)
    try:
        symlink_dir = tmp_path / "content" / "blog_link"
        symlink_dir.symlink_to(real_dir)

        blog = Section(
            name="blog_link",
            path=symlink_dir,
            metadata={"title": "Blog"},
            pages=[],
            subsections=[],
        )

        temp_site.sections = [blog]
        temp_site.register_sections()

        # Both the symlink and real path should resolve to the same section
        section_via_symlink = temp_site.get_section_by_path(symlink_dir)
        section_via_real = temp_site.get_section_by_path(real_dir)

        # Both should point to the same section
        assert section_via_symlink == blog
        assert section_via_real == blog

    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform")


def test_registry_recursive_subsections(temp_site):
    """Test that nested sections are registered recursively."""
    # Create nested structure
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

    temp_site.sections = [docs]
    temp_site.register_sections()

    # Verify both parent and child are registered
    assert temp_site.registry.section_count == 2
    assert temp_site.get_section_by_path("docs") == docs
    assert temp_site.get_section_by_path("docs/guides") == guides


def test_get_section_by_path_missing(temp_site):
    """Test that missing sections return None."""
    temp_site.sections = []
    temp_site.register_sections()

    # Non-existent section should return None
    assert temp_site.get_section_by_path("nonexistent") is None
    assert temp_site.get_section_by_path("does/not/exist") is None


def test_registry_performance(temp_site):
    """Test that registry lookups are O(1)."""
    import time

    # Create many sections
    sections = []
    for i in range(100):
        section = Section(
            name=f"section_{i}",
            path=temp_site.root_path / "content" / f"section_{i}",
            metadata={"title": f"Section {i}"},
            pages=[],
            subsections=[],
        )
        sections.append(section)

    temp_site.sections = sections
    temp_site.register_sections()

    # Time lookups
    start = time.perf_counter()
    for i in range(100):
        temp_site.get_section_by_path(f"section_{i}")
    elapsed = time.perf_counter() - start

    # Average lookup should be < 1ms (very fast)
    # Note: includes path normalization, exists() checks, etc.
    avg_us = (elapsed / 100) * 1_000_000
    assert avg_us < 1000, f"Lookup too slow: {avg_us:.2f}µs per lookup"


def test_registry_rebuilt_on_call(temp_site):
    """Test that calling register_sections() rebuilds the registry."""
    blog = Section(
        name="blog",
        path=temp_site.root_path / "content" / "blog",
        metadata={"title": "Blog"},
        pages=[],
        subsections=[],
    )

    temp_site.sections = [blog]
    temp_site.register_sections()

    assert temp_site.registry.section_count == 1

    # Add another section
    docs = Section(
        name="docs",
        path=temp_site.root_path / "content" / "docs",
        metadata={"title": "Docs"},
        pages=[],
        subsections=[],
    )

    temp_site.sections.append(docs)
    temp_site.register_sections()

    # Registry should now have both sections
    assert temp_site.registry.section_count == 2
    assert temp_site.get_section_by_path("blog") == blog
    assert temp_site.get_section_by_path("docs") == docs
