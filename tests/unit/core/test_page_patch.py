"""Unit tests for Page.patch()."""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.page import Page


class TestPagePatch:
    """Test Page.patch() for surgical rebuild."""

    def test_patch_updates_metadata_and_content(self) -> None:
        """patch() updates _raw_metadata and _raw_content."""
        page = Page(
            source_path=Path("content/docs/page.md"),
            _raw_metadata={"title": "Old", "weight": 1},
            _raw_content="Old body",
        )
        changed = page.patch(
            {"title": "New", "weight": 2},
            "New body",
        )
        assert page._raw_metadata["title"] == "New"
        assert page._raw_metadata["weight"] == 2
        assert page._raw_content == "New body"
        assert "title" in changed
        assert "weight" in changed

    def test_patch_syncs_tags_version_aliases(self) -> None:
        """patch() syncs tags, version, aliases from metadata."""
        page = Page(
            source_path=Path("content/docs/page.md"),
            _raw_metadata={"tags": ["a"], "version": "1", "aliases": ["/old"]},
            _raw_content="",
        )
        page.patch(
            {"tags": ["b", "c"], "version": "2", "aliases": ["/new"]},
            "",
        )
        assert page.tags == ["b", "c"]
        assert page.version == "2"
        assert page.aliases == ["/new"]

    def test_patch_returns_changed_keys(self) -> None:
        """patch() returns set of changed frontmatter keys."""
        page = Page(
            source_path=Path("content/docs/page.md"),
            _raw_metadata={"title": "A", "x": 1},
            _raw_content="",
        )
        changed = page.patch({"title": "B", "x": 1, "y": 2}, "")
        assert changed == {"title", "y"}

    def test_patch_invalidates_caches(self) -> None:
        """patch() clears cached properties."""
        page = Page(
            source_path=Path("content/docs/page.md"),
            _raw_metadata={"title": "Old"},
            _raw_content="Content",
        )
        _ = page.word_count  # Populate cache
        page.patch({"title": "New"}, "New content")
        assert "word_count" not in page.__dict__
