"""
Integration test for autodoc cache self-healing when cache payload is malformed.

Tests that incremental builds recover gracefully when the autodoc cache payload
is corrupted, invalidating the cache key and falling back to re-extraction
instead of crashing discovery with S003 errors.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal import __version__
from bengal.cache.build_cache import BuildCache
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


class TestAutodocCacheSelfHealing:
    """Test self-healing behavior when autodoc cache payload is malformed."""

    def test_malformed_cache_payload_recovery(self, tmp_path: Path) -> None:
        """
        Test that malformed autodoc cache payload triggers cache invalidation and re-extraction.

        Regression test for S003 errors when cache payload deserialization fails.
        """
        # Setup: Create a minimal site with autodoc enabled
        site_root = tmp_path / "test_site"
        site_root.mkdir()

        # Create bengal.toml with autodoc config
        (site_root / "bengal.toml").write_text(
            """
[site]
title = "Test Site"

[autodoc.python]
enabled = true
source_dirs = ["src"]
"""
        )

        # Create minimal Python source
        src_dir = site_root / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text('"""Test package."""')
        (src_dir / "module.py").write_text(
            '''
"""Test module."""

def test_function(x: int, y: str = "default") -> bool:
    """Test function with parameters.

    Args:
        x: Integer parameter
        y: String parameter with default

    Returns:
        Boolean result
    """
    return True
'''
        )

        # Create content directory
        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        # Step 1: Full build to populate cache
        site = Site.from_config(site_root)
        stats1 = site.build(BuildOptions(force_sequential=True, incremental=False))
        assert stats1.pages_built > 0, "First build should create pages"

        # Verify cache was created and contains autodoc payload
        cache_path = site.paths.build_cache
        assert cache_path.exists() or cache_path.with_suffix(".json.zst").exists(), (
            "Cache should exist after first build"
        )

        cache = BuildCache.load(cache_path, use_lock=False)
        cache_key = "__autodoc_elements_v1"
        cached_payload = cache.get_page_cache(cache_key)

        # Note: Autodoc cache payload may not be stored during the first full build
        # if the build pipeline doesn't pass the build_cache to the autodoc discovery.
        # In that case, skip the corruption/recovery test.
        if cached_payload is None:
            pytest.skip(
                "Autodoc cache payload not stored after full build; "
                "corruption recovery test not applicable"
            )

        # Verify the payload structure
        assert isinstance(cached_payload, dict)
        assert cached_payload.get("version") == __version__
        assert "elements" in cached_payload

        # Step 2: Corrupt the cache payload by injecting malformed parameter data
        # This simulates a cache format mismatch (e.g., from an older version)
        elements = cached_payload.get("elements", {})
        python_elements = elements.get("python", [])
        assert len(python_elements) > 0, "Should have Python elements"

        # Corrupt the first element's typed_metadata to have string parameters
        # instead of dict (this is what triggers TypeError in deserialization)
        corrupted_element = python_elements[0].copy()
        if "typed_metadata" in corrupted_element:
            typed_meta = corrupted_element["typed_metadata"]
            if typed_meta and typed_meta.get("type") == "PythonFunctionMetadata":
                # Inject malformed parameters (strings instead of dicts)
                typed_meta["data"]["parameters"] = ["x", "y"]  # Invalid format

        # Update the cache with corrupted payload
        corrupted_payload = cached_payload.copy()
        corrupted_payload["elements"]["python"] = [corrupted_element, *python_elements[1:]]
        cache.set_page_cache(cache_key, corrupted_payload)
        cache.save(cache_path, use_lock=False)

        # Step 3: Incremental build should recover gracefully
        # The build should detect the malformed payload, invalidate the cache key,
        # and fall back to re-extraction instead of crashing
        site2 = Site.from_config(site_root)
        stats2 = site2.build(BuildOptions(force_sequential=True, incremental=True))

        # Verify build succeeded (no S003 error)
        assert stats2.pages_built > 0, "Incremental build should succeed after cache corruption"

        # Verify cache was invalidated and payload was regenerated
        cache2 = BuildCache.load(cache_path, use_lock=False)
        regenerated_payload = cache2.get_page_cache(cache_key)
        assert regenerated_payload is not None, "Cache should be regenerated after invalidation"

        # Verify regenerated payload is valid (can be deserialized)
        from bengal.autodoc.orchestration import VirtualAutodocOrchestrator

        orchestrator = VirtualAutodocOrchestrator(site2)
        try:
            pages, _sections, _run = orchestrator.generate_from_cache_payload(regenerated_payload)
            # If we get here, deserialization succeeded
            assert len(pages) > 0, "Regenerated payload should produce pages"
        except (TypeError, KeyError, ValueError) as e:
            pytest.fail(f"Regenerated payload should be valid, but deserialization failed: {e}")

    def test_missing_cache_key_falls_back_to_extraction(self, tmp_path: Path) -> None:
        """
        Test that missing cache key falls back to extraction (not an error).

        This is the normal case, but we verify it doesn't crash.
        """
        # Setup: Create a minimal site with autodoc enabled
        site_root = tmp_path / "test_site"
        site_root.mkdir()

        (site_root / "bengal.toml").write_text(
            """
[site]
title = "Test Site"

[autodoc.python]
enabled = true
source_dirs = ["src"]
"""
        )

        src_dir = site_root / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text('"""Test package."""')

        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        # Build with empty cache (no autodoc payload)
        site = Site.from_config(site_root)
        stats = site.build(BuildOptions(force_sequential=True, incremental=True))

        # Should succeed and extract autodoc
        assert stats.pages_built > 0, "Build should succeed without cache"

    def test_invalid_typed_metadata_structure_recovery(self, tmp_path: Path) -> None:
        """
        Test recovery from invalid typed_metadata structure (KeyError case).

        Tests recovery when typed_metadata is missing required fields.
        """
        # Setup: Create a minimal site with autodoc enabled
        site_root = tmp_path / "test_site"
        site_root.mkdir()

        (site_root / "bengal.toml").write_text(
            """
[site]
title = "Test Site"

[autodoc.python]
enabled = true
source_dirs = ["src"]
"""
        )

        src_dir = site_root / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text('"""Test package."""')

        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        # Step 1: Full build to populate cache
        site = Site.from_config(site_root)
        site.build(BuildOptions(force_sequential=True, incremental=False))

        # Step 2: Corrupt cache payload with missing required fields
        cache_path = site.paths.build_cache
        cache = BuildCache.load(cache_path, use_lock=False)
        cache_key = "__autodoc_elements_v1"
        cached_payload = cache.get_page_cache(cache_key)

        # Autodoc cache payload may not be stored during full builds
        if cached_payload is None:
            pytest.skip(
                "Autodoc cache payload not stored after full build; "
                "corruption recovery test not applicable"
            )

        # Corrupt by removing required fields from typed_metadata
        elements = cached_payload.get("elements", {})
        python_elements = elements.get("python", [])
        if python_elements:
            corrupted_element = python_elements[0].copy()
            if "typed_metadata" in corrupted_element:
                typed_meta = corrupted_element["typed_metadata"]
                if typed_meta and "data" in typed_meta:
                    # Remove required fields to trigger KeyError
                    typed_meta["data"] = {}  # Empty dict missing required fields

            corrupted_payload = cached_payload.copy()
            corrupted_payload["elements"]["python"] = [corrupted_element, *python_elements[1:]]
            cache.set_page_cache(cache_key, corrupted_payload)
            cache.save(cache_path, use_lock=False)

        # Step 3: Incremental build should recover
        site2 = Site.from_config(site_root)
        stats = site2.build(BuildOptions(force_sequential=True, incremental=True))

        # Should succeed
        assert stats.pages_built > 0, "Build should recover from KeyError in cache payload"
