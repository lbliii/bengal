"""Tests for Page identity boundary (finalize_identity, PageIdentity).

Handoff checkpoint: page.identity raises RuntimeError if accessed before
finalize_identity() is called (i.e., before content phases complete).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.page import Page


class TestPageIdentityBeforeFinalize:
    """identity property raises RuntimeError before finalize_identity()."""

    def test_identity_raises_before_finalize(self, tmp_path: Path) -> None:
        """Accessing identity before finalize_identity raises RuntimeError."""
        page = Page(
            source_path=tmp_path / "content" / "about.md",
            _raw_content="# About",
            _raw_metadata={"title": "About"},
        )

        with pytest.raises(RuntimeError, match="PageIdentity not yet finalized"):
            _ = page.identity

    def test_identity_raises_message_includes_source_path(self, tmp_path: Path) -> None:
        """Error message includes source path for debugging."""
        source = tmp_path / "content" / "docs" / "guide.md"
        page = Page(
            source_path=source,
            _raw_content="# Guide",
            _raw_metadata={"title": "Guide"},
        )

        with pytest.raises(RuntimeError, match=r"guide\.md"):
            _ = page.identity

    def test_identity_raises_message_mentions_finalize(self, tmp_path: Path) -> None:
        """Error message instructs to call finalize_identity()."""
        page = Page(
            source_path=tmp_path / "test.md",
            _raw_content="# Test",
            _raw_metadata={},
        )

        with pytest.raises(RuntimeError, match="finalize_identity"):
            _ = page.identity


class TestPageFinalizeIdentity:
    """finalize_identity() populates PageIdentity correctly."""

    def test_finalize_identity_sets_identity(self, tmp_path: Path) -> None:
        """After finalize_identity, identity returns PageIdentity."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        page_path = content_dir / "about.md"
        page_path.write_text("---\ntitle: About\n---\n# About")

        page = Page(
            source_path=page_path,
            _raw_content="# About",
            _raw_metadata={"title": "About"},
        )
        page._section_path = content_dir
        page._site = None
        page.__dict__["_path"] = "/about/"  # href requires _path

        page.finalize_identity()

        ident = page.identity
        assert ident is not None
        assert ident.slug == "about"
        assert ident.source_path == str(page_path)
        assert ident.tag_slugs == frozenset()

    def test_finalize_identity_with_tags(self, tmp_path: Path) -> None:
        """finalize_identity includes tag_slugs as frozenset."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        page = Page(
            source_path=content_dir / "post.md",
            _raw_content="# Post",
            _raw_metadata={"title": "Post", "tags": ["python", "web"]},
        )
        page._section_path = content_dir
        page._site = None
        page.__dict__["_path"] = "/about/"  # href requires _path

        page.finalize_identity()

        assert page.identity.tag_slugs == frozenset({"python", "web"})

    def test_finalize_identity_section_path_outside_content(self, tmp_path: Path) -> None:
        """finalize_identity handles _section_path outside content_dir (ValueError fallback)."""
        # Page with section path that cannot be relative_to(content_dir)
        page = Page(
            source_path=tmp_path / "content" / "about.md",
            _raw_content="# About",
            _raw_metadata={"title": "About"},
        )
        # _section_path outside content - relative_to would raise ValueError
        page._section_path = tmp_path / "other" / "section"
        page._site = None
        page._cached_section_path_str = None
        page.__dict__["_path"] = "/about/"

        # Should not raise; falls back to str(_section_path)
        page.finalize_identity()

        assert page.identity is not None
        assert page.identity.section_path_str == str(page._section_path)
