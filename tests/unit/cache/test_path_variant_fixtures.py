"""Path-variant test fixtures for path key alignment.

Asserts cache hits, lookups, and rebuild decisions are identical across
different path representations (relative, absolute, resolved).

RFC: Path Key Alignment Plan - Prevention
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.build.contracts.keys import content_key
from bengal.cache.build_cache import BuildCache


class TestPathVariantCacheConsistency:
    """Cache behavior identical across path format variants."""

    @pytest.fixture
    def site_with_content(self, tmp_path: Path) -> Path:
        """Create minimal site with content/docs/foo.md."""
        content_dir = tmp_path / "content" / "docs"
        content_dir.mkdir(parents=True)
        (content_dir / "foo.md").write_text("# Foo")
        return tmp_path

    def test_get_file_fingerprint_same_result_across_path_variants(
        self, site_with_content: Path
    ) -> None:
        """get_file_fingerprint returns same result for relative, absolute, resolved."""
        cache = BuildCache(site_root=site_with_content)
        content_file = site_with_content / "content" / "docs" / "foo.md"

        # Store with absolute path
        from bengal.cache.build_cache.fingerprint import FileFingerprint

        cache.set_file_fingerprint(
            content_file,
            FileFingerprint(mtime=1.0, size=10, hash="abc123"),
        )

        # Lookup with different path representations - all should hit
        relative = Path("content/docs/foo.md")
        absolute = site_with_content / "content" / "docs" / "foo.md"
        resolved = (site_with_content / "content" / "docs" / "foo.md").resolve()

        # content_key requires absolute path for relative input
        rel_abs = site_with_content / relative
        fp_rel = cache.get_file_fingerprint(rel_abs)
        fp_abs = cache.get_file_fingerprint(absolute)
        fp_res = cache.get_file_fingerprint(resolved)

        assert fp_rel == fp_abs == fp_res
        assert fp_rel is not None
        assert fp_rel.hash == "abc123"

    def test_content_key_normalizes_path_variants(self, tmp_path: Path) -> None:
        """content_key produces same key for same logical path."""
        rel = Path("content/docs/foo.md")
        abs_path = tmp_path / "content" / "docs" / "foo.md"
        resolved = abs_path.resolve()

        key_rel = content_key(tmp_path / rel, tmp_path)
        key_abs = content_key(abs_path, tmp_path)
        key_res = content_key(resolved, tmp_path)

        assert key_rel == key_abs == key_res
        assert key_rel == "content/docs/foo.md"
