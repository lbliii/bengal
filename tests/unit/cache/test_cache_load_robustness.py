"""
Tests for cache loading robustness.

These tests verify that cache loading works correctly across:
- Process boundaries (cold start scenarios)
- Exception handling paths
- Silent failure prevention

RFC: Addresses gap identified in Python 3.14 import scoping bug
where cache loading failed silently, causing all pages to rebuild.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from bengal.cache.build_cache import BuildCache


class TestCacheLoadRobustness:
    """Tests for cache loading that catches silent failures."""

    def test_load_returns_non_empty_cache_after_save(self, tmp_path: Path) -> None:
        """
        Verify that load() actually loads data, not an empty fallback.

        This catches bugs where load() fails silently and returns BuildCache()
        instead of the actual cached data.
        """
        cache = BuildCache()

        # Create and track a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Content")
        cache.update_file(test_file)

        # Add some metadata to verify full roundtrip
        cache.config_hash = "test_hash_12345"

        # Save cache
        cache_path = tmp_path / "cache.json"
        cache.save(cache_path)

        # Load in same process (basic sanity check)
        loaded = BuildCache.load(cache_path)

        # CRITICAL: These assertions catch silent load failures
        assert len(loaded.file_fingerprints) > 0, (
            "Cache load returned empty fingerprints! "
            "This indicates a silent load failure - cache.load() likely "
            "caught an exception and returned BuildCache() instead of data."
        )
        assert loaded.config_hash == "test_hash_12345", (
            "Cache load returned wrong config_hash! "
            "Expected 'test_hash_12345', got '{loaded.config_hash}'"
        )
        assert loaded.last_build is not None, (
            "Cache load returned None last_build! "
            "The cache should have a last_build timestamp after save()."
        )

    def test_load_compressed_cache_has_data(self, tmp_path: Path) -> None:
        """
        Specifically test that compressed cache (.json.zst) loads with data.

        The Python 3.14 bug was specifically in the compressed load path
        where an import scoping issue caused silent failure.
        """
        cache = BuildCache()

        # Create multiple files to ensure non-trivial cache
        for i in range(5):
            test_file = tmp_path / f"page{i}.md"
            test_file.write_text(f"# Page {i}")
            cache.update_file(test_file)
            cache.taxonomy_index.add_taxonomy_dependency(f"tag:test{i}", test_file)

        # Save cache (compressed by default)
        cache_path = tmp_path / "cache.json"
        cache.save(cache_path)

        # Verify compressed file was created
        compressed_path = cache_path.with_suffix(".json.zst")
        assert compressed_path.exists(), "Compressed cache file not created"

        # Load and verify
        loaded = BuildCache.load(cache_path)

        assert len(loaded.file_fingerprints) == 5, (
            f"Expected 5 fingerprints, got {len(loaded.file_fingerprints)}. "
            "Compressed cache load may have failed silently."
        )
        assert len(loaded.taxonomy_index.taxonomy_deps) == 5, (
            f"Expected 5 taxonomy deps, got {len(loaded.taxonomy_index.taxonomy_deps)}. "
            "Compressed cache load may have partially failed."
        )

    def test_cross_process_cache_roundtrip(self, tmp_path: Path) -> None:
        """
        Verify cache survives process restart (simulates cold start).

        This is the critical test that was missing - it exercises the
        exact scenario where the Python 3.14 bug manifested:
        1. Build 1: Save cache and exit
        2. Build 2: Load cache in new process

        The bug caused step 2 to silently fail, returning empty cache.
        """
        cache_path = tmp_path / "cache.json"
        test_file = tmp_path / "content.md"

        # Create test file
        test_file.write_text("# Test Content for Cross-Process Test")

        # Step 1: Save cache in subprocess (simulates first build)
        save_script = f'''
import sys
sys.path.insert(0, "{Path(__file__).parent.parent.parent.parent}")
from pathlib import Path
from bengal.cache.build_cache import BuildCache

cache = BuildCache()
test_file = Path("{test_file}")
cache.update_file(test_file)
cache.config_hash = "cross_process_test"

cache_path = Path("{cache_path}")
cache.save(cache_path)

# Verify save worked
print(f"Saved {{len(cache.file_fingerprints)}} fingerprints")
'''

        result = subprocess.run(
            [sys.executable, "-c", save_script],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0, f"Save subprocess failed: {result.stderr}"
        assert "Saved 1 fingerprints" in result.stdout

        # Step 2: Load cache in DIFFERENT subprocess (simulates cold start)
        load_script = f'''
import sys
sys.path.insert(0, "{Path(__file__).parent.parent.parent.parent}")
from pathlib import Path
from bengal.cache.build_cache import BuildCache

cache_path = Path("{cache_path}")
loaded = BuildCache.load(cache_path)

# CRITICAL: Verify data was actually loaded
fingerprint_count = len(loaded.file_fingerprints)
config_hash = loaded.config_hash
last_build = loaded.last_build

print(f"fingerprints={{fingerprint_count}}")
print(f"config_hash={{config_hash}}")
print(f"last_build={{last_build}}")

# Exit with error if load failed silently
if fingerprint_count == 0:
    print("ERROR: Cache load returned empty fingerprints!")
    sys.exit(1)
if config_hash != "cross_process_test":
    print(f"ERROR: Wrong config_hash: {{config_hash}}")
    sys.exit(1)
'''

        result = subprocess.run(
            [sys.executable, "-c", load_script],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        # Parse output for debugging
        print(f"Load subprocess output:\n{result.stdout}")
        if result.stderr:
            print(f"Load subprocess stderr:\n{result.stderr}")

        assert result.returncode == 0, (
            f"Cross-process cache load failed!\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}\n"
            "This indicates the cache loading has a bug that only manifests "
            "when loading in a fresh process (cold start scenario)."
        )
        assert "fingerprints=1" in result.stdout, "Cache fingerprints not loaded in subprocess"
        assert "config_hash=cross_process_test" in result.stdout, (
            "Cache config_hash not preserved across processes"
        )


class TestCacheExceptionHandling:
    """Tests for cache exception handling paths."""

    def test_corrupted_compressed_cache_returns_empty(self, tmp_path: Path) -> None:
        """
        Verify that corrupted compressed cache returns empty (not crashes).

        This tests the exception handling path that had the import scoping bug.
        """
        cache_path = tmp_path / "cache.json"
        compressed_path = cache_path.with_suffix(".json.zst")

        # Write garbage to compressed file
        compressed_path.write_bytes(b"not valid zstd data at all")

        # Should return empty cache, not crash
        loaded = BuildCache.load(cache_path)

        assert len(loaded.file_fingerprints) == 0, "Corrupted cache should return empty BuildCache"

    def test_invalid_json_in_cache_returns_empty(self, tmp_path: Path) -> None:
        """
        Verify that invalid JSON returns empty cache.
        """
        cache_path = tmp_path / "cache.json"
        cache_path.write_text("{ not valid json }")

        loaded = BuildCache.load(cache_path)

        assert len(loaded.file_fingerprints) == 0

    def test_missing_cache_returns_empty(self, tmp_path: Path) -> None:
        """
        Verify that missing cache file returns empty cache.
        """
        cache_path = tmp_path / "nonexistent" / "cache.json"

        loaded = BuildCache.load(cache_path)

        assert len(loaded.file_fingerprints) == 0

    def test_partial_cache_data_loads_gracefully(self, tmp_path: Path) -> None:
        """
        Verify that cache with missing fields loads with defaults.

        This tests backward compatibility when cache format evolves.
        """
        cache_path = tmp_path / "cache.json"

        # Write minimal valid cache (missing many fields)
        minimal_cache = {
            "version": BuildCache.VERSION,
            "file_fingerprints": {"test.md": {"mtime": 1234.0, "size": 100}},
            # Missing: dependencies, taxonomy_deps, etc.
        }
        cache_path.write_text(json.dumps(minimal_cache))

        loaded = BuildCache.load(cache_path)

        # Should load the fingerprint
        assert len(loaded.file_fingerprints) == 1
        # Should have empty defaults for missing fields
        assert len(loaded.dependencies) == 0
        assert len(loaded.taxonomy_index.taxonomy_deps) == 0


class TestCacheChangeDetection:
    """Tests for is_changed() behavior with loaded cache."""

    def test_is_changed_detects_unchanged_file_from_loaded_cache(self, tmp_path: Path) -> None:
        """
        Verify that is_changed() correctly identifies unchanged files
        after loading cache from disk.

        This is the exact scenario that was broken by the Python 3.14 bug:
        - Cache loaded but actually empty (silent failure)
        - is_changed() returns True for all files (because not in cache)
        - All pages rebuilt unnecessarily
        """
        # Create and track file
        test_file = tmp_path / "page.md"
        test_file.write_text("# Unchanged Content")

        cache = BuildCache()
        cache.update_file(test_file)

        # Save cache
        cache_path = tmp_path / "cache.json"
        cache.save(cache_path)

        # Load cache (simulating next build)
        loaded = BuildCache.load(cache_path)

        # CRITICAL: File should NOT be detected as changed
        # If cache loaded empty, this would return True (BUG!)
        is_changed = loaded.is_changed(test_file)

        assert not is_changed, (
            "Unchanged file detected as changed after cache load! "
            "This indicates cache.load() failed silently and returned empty cache. "
            f"Cache has {len(loaded.file_fingerprints)} fingerprints."
        )

    def test_is_changed_detects_modified_file_from_loaded_cache(self, tmp_path: Path) -> None:
        """
        Verify that is_changed() correctly identifies modified files.

        This ensures our fix doesn't break legitimate change detection.
        """
        # Create and track file
        test_file = tmp_path / "page.md"
        test_file.write_text("# Original Content")

        cache = BuildCache()
        cache.update_file(test_file)

        # Save cache
        cache_path = tmp_path / "cache.json"
        cache.save(cache_path)

        # Modify file
        test_file.write_text("# Modified Content That Is Different")

        # Load cache and check
        loaded = BuildCache.load(cache_path)
        is_changed = loaded.is_changed(test_file)

        assert is_changed, "Modified file should be detected as changed"

    def test_is_changed_returns_true_for_new_file(self, tmp_path: Path) -> None:
        """
        Verify that is_changed() returns True for files not in cache.
        """
        cache = BuildCache()

        # Save empty cache
        cache_path = tmp_path / "cache.json"
        cache.save(cache_path)

        # Create new file AFTER saving cache
        new_file = tmp_path / "new_page.md"
        new_file.write_text("# New Content")

        # Load cache and check new file
        loaded = BuildCache.load(cache_path)
        is_changed = loaded.is_changed(new_file)

        assert is_changed, "New file should be detected as changed"
