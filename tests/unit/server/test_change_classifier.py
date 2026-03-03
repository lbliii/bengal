"""Unit tests for change classifier."""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.server.build_trigger import ContentHashCacheEntry
from bengal.server.change_classifier import (
    RebuildTier,
    classify_change,
)


class TestClassifyChange:
    """Test classify_change for each tier."""

    def test_structural_created_returns_full(self) -> None:
        """Created event -> FULL."""
        scope = classify_change(
            changed_paths={Path("/site/content/page.md")},
            event_types={"created"},
            content_hash_cache={},
            cascade_block_hashes={},
            site=None,
            is_template_change=False,
            should_regenerate_autodoc=False,
            is_shared_content_change=False,
            is_version_config_change=False,
            is_svg_icon_change=False,
        )
        assert scope.tier == RebuildTier.FULL

    def test_structural_deleted_returns_full(self) -> None:
        """Deleted event -> FULL."""
        scope = classify_change(
            changed_paths={Path("/site/content/page.md")},
            event_types={"deleted"},
            content_hash_cache={},
            cascade_block_hashes={},
            site=None,
            is_template_change=False,
            should_regenerate_autodoc=False,
            is_shared_content_change=False,
            is_version_config_change=False,
            is_svg_icon_change=False,
        )
        assert scope.tier == RebuildTier.FULL

    def test_template_change_returns_full(self) -> None:
        """Template change -> FULL."""
        scope = classify_change(
            changed_paths={Path("/site/templates/base.html")},
            event_types={"modified"},
            content_hash_cache={},
            cascade_block_hashes={},
            site=None,
            is_template_change=True,
            should_regenerate_autodoc=False,
            is_shared_content_change=False,
            is_version_config_change=False,
            is_svg_icon_change=False,
        )
        assert scope.tier == RebuildTier.FULL

    def test_multiple_md_returns_full(self) -> None:
        """Multiple .md files -> FULL."""
        scope = classify_change(
            changed_paths={
                Path("/site/content/a.md"),
                Path("/site/content/b.md"),
            },
            event_types={"modified"},
            content_hash_cache={},
            cascade_block_hashes={},
            site=None,
            is_template_change=False,
            should_regenerate_autodoc=False,
            is_shared_content_change=False,
            is_version_config_change=False,
            is_svg_icon_change=False,
        )
        assert scope.tier == RebuildTier.FULL

    def test_body_only_single_md_frontmatter_unchanged(self, tmp_path: Path) -> None:
        """Single .md, frontmatter hash unchanged -> BODY_ONLY."""
        page_md = tmp_path / "page.md"
        page_md.write_text("---\ntitle: Page\n---\nBody content.\n")

        import hashlib

        fm_hash = hashlib.sha256(str(sorted({"title": "Page"}.items())).encode()).hexdigest()[:16]
        content_hash = "abc123"
        cache_entry = ContentHashCacheEntry(
            mtime=page_md.stat().st_mtime,
            frontmatter_hash=fm_hash,
            content_hash=content_hash,
        )
        content_hash_cache = {page_md.resolve(): cache_entry}

        scope = classify_change(
            changed_paths={page_md},
            event_types={"modified"},
            content_hash_cache=content_hash_cache,
            cascade_block_hashes={},
            site=None,
            is_template_change=False,
            should_regenerate_autodoc=False,
            is_shared_content_change=False,
            is_version_config_change=False,
            is_svg_icon_change=False,
        )
        assert scope.tier == RebuildTier.BODY_ONLY
        assert scope.changed_page == page_md

    def test_frontmatter_single_md_unchanged_cascade(self, tmp_path: Path) -> None:
        """Single .md, frontmatter changed (not cascade) -> FRONTMATTER."""
        page_md = tmp_path / "page.md"
        page_md.write_text("---\ntitle: New Title\nweight: 2\n---\nBody.\n")

        # Old cache has different frontmatter hash
        old_fm_hash = "oldhash1234567890"
        cache_entry = ContentHashCacheEntry(
            mtime=0.0,
            frontmatter_hash=old_fm_hash,
            content_hash="x",
        )
        content_hash_cache = {page_md.resolve(): cache_entry}

        scope = classify_change(
            changed_paths={page_md},
            event_types={"modified"},
            content_hash_cache=content_hash_cache,
            cascade_block_hashes={},
            site=None,
            is_template_change=False,
            should_regenerate_autodoc=False,
            is_shared_content_change=False,
            is_version_config_change=False,
            is_svg_icon_change=False,
        )
        assert scope.tier == RebuildTier.FRONTMATTER
        assert scope.changed_page == page_md

    def test_cascade_index_md_cascade_block_changed(self, tmp_path: Path) -> None:
        """Single _index.md, cascade block changed -> CASCADE."""
        index_md = tmp_path / "_index.md"
        index_md.write_text("---\ntitle: Docs\ncascade:\n  type: doc\n  version: '2'\n---\n")

        # Old cascade hash (different)
        cascade_block_hashes = {index_md.resolve(): "oldcascadehash"}
        content_hash_cache = {}

        scope = classify_change(
            changed_paths={index_md},
            event_types={"modified"},
            content_hash_cache=content_hash_cache,
            cascade_block_hashes=cascade_block_hashes,
            site=None,
            is_template_change=False,
            should_regenerate_autodoc=False,
            is_shared_content_change=False,
            is_version_config_change=False,
            is_svg_icon_change=False,
        )
        assert scope.tier == RebuildTier.CASCADE
        assert scope.changed_page == index_md
        assert scope.cascade_dirty is True

    def test_full_rebuild_keys_upgrade_to_full(self, tmp_path: Path) -> None:
        """Frontmatter change with permalink -> FULL."""
        page_md = tmp_path / "page.md"
        page_md.write_text("---\ntitle: Page\npermalink: /custom/\n---\nBody.\n")

        scope = classify_change(
            changed_paths={page_md},
            event_types={"modified"},
            content_hash_cache={},
            cascade_block_hashes={},
            site=None,
            is_template_change=False,
            should_regenerate_autodoc=False,
            is_shared_content_change=False,
            is_version_config_change=False,
            is_svg_icon_change=False,
        )
        assert scope.tier == RebuildTier.FULL
