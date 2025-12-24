"""Integration tests for Page.frontmatter property."""

from __future__ import annotations

from pathlib import Path

from bengal.core.page import Page
from bengal.core.page.frontmatter import Frontmatter


def test_page_frontmatter_typed_access(tmp_path: Path) -> None:
    """Page.frontmatter provides typed access to metadata."""
    page = Page(
        source_path=tmp_path / "test.md",
        content="# Test",
        metadata={"title": "My Post", "tags": ["python"], "custom": "value"},
    )

    # Typed access
    assert isinstance(page.frontmatter, Frontmatter)
    assert page.frontmatter.title == "My Post"
    assert page.frontmatter.tags == ["python"]

    # Extra fields
    assert page.frontmatter.extra["custom"] == "value"


def test_frontmatter_dict_syntax_works(tmp_path: Path) -> None:
    """Templates using dict syntax still work."""
    page = Page(
        source_path=tmp_path / "test.md",
        content="# Test",
        metadata={"title": "My Post"},
    )

    # Dict access (what templates use)
    assert page.frontmatter["title"] == "My Post"
    assert page.frontmatter.get("missing") is None


def test_frontmatter_cached(tmp_path: Path) -> None:
    """Frontmatter is cached after first access."""
    page = Page(
        source_path=tmp_path / "test.md",
        content="# Test",
        metadata={"title": "Test"},
    )

    fm1 = page.frontmatter
    fm2 = page.frontmatter

    assert fm1 is fm2  # Same instance


