"""
Tests for autodoc source self-validation (Phase 4 of RFC CI Cache Inputs).

Tests the AutodocTrackingMixin's ability to detect stale autodoc sources
independent of CI cache keys, providing defense-in-depth for cache correctness.

See: plan/rfc-ci-cache-inputs.md (Phase 4: Self-Validating Cache)
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from bengal.cache.build_cache.core import BuildCache
from bengal.utils.primitives.hashing import hash_file


class TestAutodocSourceMetadata:
    """Test autodoc source metadata storage and retrieval."""

    def test_add_autodoc_dependency_with_metadata(self, tmp_path):
        """Autodoc extraction stores source file hash and mtime."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        source_file = tmp_path / "src" / "module.py"
        source_file.parent.mkdir()
        source_file.write_text("def foo(): pass")

        cache = BuildCache()
        source_hash = hash_file(source_file, truncate=16)
        source_mtime = source_file.stat().st_mtime

        cache.add_autodoc_dependency(
            source_file,
            "api/module/index.md",
            site_root=site_root,
            source_hash=source_hash,
            source_mtime=source_mtime,
        )

        # Path normalized relative to site parent
        normalized_key = str(source_file.relative_to(tmp_path))
        assert normalized_key in cache.autodoc_source_metadata
        assert cache.autodoc_source_metadata[normalized_key] == (source_hash, source_mtime, {})

    def test_add_autodoc_dependency_without_metadata(self, tmp_path):
        """Missing metadata is rejected."""
        cache = BuildCache()

        with pytest.raises(ValueError, match="metadata required"):
            cache.add_autodoc_dependency(
                "/path/to/source.py",
                "api/module/index.md",
            )


class TestStaleAutodocDetection:
    """Test detection of stale autodoc sources."""

    def test_unchanged_autodoc_not_stale(self, tmp_path):
        """Unchanged source files are not marked stale."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        source_file = tmp_path / "src" / "module.py"
        source_file.parent.mkdir()
        source_file.write_text("def foo(): pass")

        # Get mtime AFTER writing to ensure consistency
        source_mtime = source_file.stat().st_mtime

        cache = BuildCache()
        cache.add_autodoc_dependency(
            source_file,
            "api/module/index.md",
            site_root=site_root,
            source_hash=hash_file(source_file, truncate=16),
            source_mtime=source_mtime,
        )

        # File hasn't changed, so stale check should use cached mtime
        stale = cache.get_stale_autodoc_sources(site_root)
        normalized_key = str(source_file.relative_to(tmp_path))
        assert normalized_key not in stale

    def test_changed_autodoc_detected_as_stale(self, tmp_path):
        """Changed source files are detected as stale."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        source_file = tmp_path / "src" / "module.py"
        source_file.parent.mkdir()
        source_file.write_text("def foo(): pass")

        cache = BuildCache()
        cache.add_autodoc_dependency(
            source_file,
            "api/module/index.md",
            site_root=site_root,
            source_hash=hash_file(source_file, truncate=16),
            source_mtime=source_file.stat().st_mtime,
        )

        # Modify source (changes both content and mtime)
        time.sleep(0.01)  # Ensure mtime changes
        source_file.write_text("def foo(): return 42")

        stale = cache.get_stale_autodoc_sources(site_root)
        normalized_key = str(source_file.relative_to(tmp_path))
        assert normalized_key in stale

    def test_deleted_autodoc_source_detected(self, tmp_path):
        """Deleted source files are detected as stale."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        source_file = tmp_path / "src" / "module.py"
        source_file.parent.mkdir()
        source_file.write_text("def foo(): pass")

        cache = BuildCache()
        normalized_key = str(source_file.relative_to(tmp_path))
        cache.add_autodoc_dependency(
            source_file,
            "api/module/index.md",
            site_root=site_root,
            source_hash=hash_file(source_file, truncate=16),
            source_mtime=source_file.stat().st_mtime,
        )

        # Delete source
        source_file.unlink()

        stale = cache.get_stale_autodoc_sources(site_root)
        assert normalized_key in stale

    def test_cache_migration_marks_all_stale(self, tmp_path):
        """Missing metadata is treated as an error."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        source_file = tmp_path / "src" / "module.py"
        source_file.parent.mkdir()
        source_file.write_text("def foo(): pass")

        cache = BuildCache()
        normalized_key = str(source_file.relative_to(tmp_path))

        # Simulate old cache: has dependencies but no metadata (pre-v0.1.8)
        cache.autodoc_dependencies[normalized_key] = {"api/module/index.md"}
        # autodoc_source_metadata is empty

        from bengal.errors import BengalCacheError

        with pytest.raises(BengalCacheError):
            cache.get_stale_autodoc_sources(site_root)

    def test_mtime_unchanged_skips_hash(self, tmp_path):
        """mtime-first optimization skips hash computation when mtime unchanged.

        This test verifies the optimization indirectly: if mtime hasn't changed,
        the file should not be marked stale (no hash computation needed).
        """
        site_root = tmp_path / "site"
        site_root.mkdir()
        source_file = tmp_path / "src" / "module.py"
        source_file.parent.mkdir()
        source_file.write_text("def foo(): pass")

        # Get mtime AFTER writing
        source_mtime = source_file.stat().st_mtime

        cache = BuildCache()
        cache.add_autodoc_dependency(
            source_file,
            "api/module/index.md",
            site_root=site_root,
            source_hash=hash_file(source_file, truncate=16),
            source_mtime=source_mtime,
        )

        # Without modifying the file, mtime check should pass (no hash needed)
        stale = cache.get_stale_autodoc_sources(site_root)

        # File unchanged - should not be stale
        assert len(stale) == 0

    def test_touched_file_without_content_change(self, tmp_path):
        """File touched but content unchanged is not marked stale (mtime + hash check)."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        source_file = tmp_path / "src" / "module.py"
        source_file.parent.mkdir()
        original_content = "def foo(): pass"
        source_file.write_text(original_content)

        cache = BuildCache()
        original_hash = hash_file(source_file, truncate=16)
        original_mtime = source_file.stat().st_mtime

        cache.add_autodoc_dependency(
            source_file,
            "api/module/index.md",
            site_root=site_root,
            source_hash=original_hash,
            source_mtime=original_mtime,
        )

        # Touch file (change mtime but not content)
        time.sleep(0.01)
        source_file.write_text(original_content)  # Same content, new mtime

        stale = cache.get_stale_autodoc_sources(site_root)
        normalized_key = str(source_file.relative_to(tmp_path))

        # Should NOT be stale because content hash matches
        assert normalized_key not in stale


class TestAutodocStats:
    """Test autodoc statistics reporting."""

    def test_get_autodoc_stats_includes_metadata_coverage(self, tmp_path):
        """Stats include metadata coverage percentage."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        source1 = tmp_path / "src" / "module1.py"
        source1.parent.mkdir()
        source1.write_text("def foo(): pass")
        source2 = tmp_path / "src" / "module2.py"
        source2.write_text("def bar(): pass")

        cache = BuildCache()

        # Add two with metadata
        cache.add_autodoc_dependency(
            source1,
            "api/module1/index.md",
            site_root=site_root,
            source_hash=hash_file(source1, truncate=16),
            source_mtime=source1.stat().st_mtime,
        )
        cache.add_autodoc_dependency(
            source2,
            "api/module2/index.md",
            site_root=site_root,
            source_hash=hash_file(source2, truncate=16),
            source_mtime=source2.stat().st_mtime,
        )

        stats = cache.get_autodoc_stats()

        assert stats["autodoc_source_files"] == 2
        assert stats["sources_with_metadata"] == 2
        assert stats["metadata_coverage_pct"] == 100.0


class TestCachePersistence:
    """Test that autodoc source metadata is properly saved and loaded."""

    def test_save_and_load_preserves_metadata(self, tmp_path):
        """Autodoc source metadata is preserved across cache save/load."""
        cache_path = tmp_path / "cache.json"
        site_root = tmp_path / "site"
        site_root.mkdir()
        source_file = tmp_path / "src" / "module.py"
        source_file.parent.mkdir()
        source_file.write_text("def foo(): pass")

        # Create cache with metadata
        cache1 = BuildCache()
        source_hash = hash_file(source_file, truncate=16)
        source_mtime = source_file.stat().st_mtime

        cache1.add_autodoc_dependency(
            source_file,
            "api/module/index.md",
            site_root=site_root,
            source_hash=source_hash,
            source_mtime=source_mtime,
        )

        # Save cache
        cache1.save(cache_path, use_lock=False)

        # Load cache
        cache2 = BuildCache.load(cache_path, use_lock=False)

        # Verify metadata preserved
        normalized_key = str(source_file.relative_to(tmp_path))
        assert normalized_key in cache2.autodoc_source_metadata
        loaded_hash, loaded_mtime, loaded_doc_hashes = cache2.autodoc_source_metadata[
            normalized_key
        ]
        assert loaded_hash == source_hash
        assert loaded_mtime == source_mtime
        assert loaded_doc_hashes == {}