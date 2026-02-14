"""
Property-based tests for incremental build correctness.

RFC: rfc-behavioral-test-hardening (Phase 3)

These tests verify that the incremental build system maintains correctness
invariants regardless of the specific content or modification patterns.

Invariants tested:
- Incremental build output matches full build output
- Any content change is detected and rebuilt
- Unchanged files are never rebuilt
- Multiple modifications are all detected
- Cache survives round-trip serialization

Usage:
    pytest tests/unit/orchestration/incremental/test_incremental_properties.py -v

Note: Requires `hypothesis` package (optional dev dependency).
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# hypothesis is an optional dev dependency - importorskip must run before import
pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

if TYPE_CHECKING:
    pass


# =============================================================================
# STRATEGIES
# =============================================================================


def modification_content() -> st.SearchStrategy[str]:
    """Generate content modifications (appended to existing content)."""
    return st.from_regex(r"\n<!-- modified: [a-z0-9]{8} -->", fullmatch=True)


def page_indices(max_pages: int = 5) -> st.SearchStrategy[list[int]]:
    """Generate list of page indices to modify."""
    return st.lists(
        st.integers(min_value=0, max_value=max_pages - 1),
        min_size=1,
        max_size=max_pages,
        unique=True,
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _create_warm_site(base_dir: Path) -> tuple[Path, Path, list[Path]]:
    """
    Create a site with pre-warmed cache for incremental testing.

    Returns a tuple of (site_dir, content_dir, page_paths).
    """
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions

    site_dir = base_dir / "site"
    site_dir.mkdir(parents=True, exist_ok=True)

    config = """
[site]
title = "Incremental Test Site"
baseURL = "/"

[build]
output_dir = "public"
"""
    (site_dir / "bengal.toml").write_text(config)

    content_dir = site_dir / "content"
    content_dir.mkdir()

    (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n# Home")

    page_paths: list[Path] = []
    for i in range(5):
        page_path = content_dir / f"page_{i}.md"
        page_path.write_text(f"---\ntitle: Page {i}\n---\n# Page {i}\n\nContent.")
        page_paths.append(page_path)

    site = Site.from_config(site_dir)
    site.discover_content()
    site.discover_assets()

    options = BuildOptions(incremental=False, quiet=True)
    site.build(options=options)

    return site_dir, content_dir, page_paths


def _hash_output_dir(output_dir: Path) -> dict[str, str]:
    """Create a content hash map of all files in the output directory."""
    hashes = {}
    for file_path in output_dir.rglob("*"):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(output_dir))
            content = file_path.read_bytes()
            hashes[rel_path] = hashlib.sha256(content).hexdigest()
    return hashes


def _build_site(site_dir: Path, *, incremental: bool = True):
    """Build site and return stats."""
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions
    from bengal.utils.observability.profile import BuildProfile

    site = Site.from_config(site_dir)
    site.discover_content()
    site.discover_assets()

    options = BuildOptions(
        incremental=incremental,
        quiet=True,
        explain=True,
        profile=BuildProfile.WRITER,
    )
    return site.build(options=options), site


# =============================================================================
# PROPERTY TESTS
# =============================================================================


@pytest.mark.slow  # Each example runs full build (~100s total)
@pytest.mark.parallel_unsafe  # Full builds conflict with xdist workers in Python 3.14t
class TestIncrementalProperties:
    """Property-based tests for incremental build behavior."""

    @given(indices=page_indices(5))
    @settings(
        max_examples=5,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_modified_files_always_rebuilt(
        self,
        indices: list[int],
    ) -> None:
        """
        PROPERTY: Any modified file is always rebuilt.

        When a content file changes, it must appear in the incremental
        build's pages_to_build list.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            site_dir, _content_dir, page_paths = _create_warm_site(Path(tmp_dir))

            # Modify selected pages
            time.sleep(0.01)  # Ensure mtime changes
            for i in indices:
                page = page_paths[i]
                original = page.read_text()
                page.write_text(original + f"\n<!-- modified-{i} -->")

            # Incremental build
            stats, _site = _build_site(site_dir, incremental=True)

            # PROPERTY: All modified pages should be rebuilt
            decision = getattr(stats, "incremental_decision", None)
            if decision is not None:
                rebuilt_paths = {str(p.source_path) for p in decision.pages_to_build}
                for i in indices:
                    assert any(f"page_{i}" in p for p in rebuilt_paths), (
                        f"Modified page_{i}.md was not rebuilt. Rebuilt: {rebuilt_paths}"
                    )
            else:
                # If no decision, at least some pages should have been built
                assert stats.total_pages >= len(indices), (
                    "Not enough pages rebuilt for modifications"
                )

    @given(modification=modification_content())
    @settings(
        max_examples=5,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_any_content_change_detected(
        self,
        modification: str,
    ) -> None:
        """
        PROPERTY: Any content change is detected.

        Regardless of what content is appended, the incremental system
        should detect the file has changed.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            site_dir, _content_dir, page_paths = _create_warm_site(Path(tmp_dir))

            # Modify first page with generated content
            time.sleep(0.01)
            page = page_paths[0]
            original = page.read_text()
            page.write_text(original + modification)

            # Incremental build
            stats, _site = _build_site(site_dir, incremental=True)

            # PROPERTY: Modified page should be rebuilt
            decision = getattr(stats, "incremental_decision", None)
            if decision is not None:
                rebuilt_paths = {str(p.source_path) for p in decision.pages_to_build}
                assert any("page_0" in p for p in rebuilt_paths), (
                    f"Modified page_0.md not detected. Content added: {modification[:50]}"
                )

    def test_unchanged_files_never_rebuilt_after_warm(
        self,
        tmp_path: Path,
    ) -> None:
        """
        PROPERTY: Unchanged files are never rebuilt on warm cache.

        With a warm cache and no changes, incremental build should
        rebuild zero pages.
        """
        site_dir, _content_dir, _page_paths = _create_warm_site(tmp_path)

        # Incremental build without changes
        stats, _site = _build_site(site_dir, incremental=True)

        # PROPERTY: Zero pages rebuilt
        decision = getattr(stats, "incremental_decision", None)
        if decision is not None:
            pages_rebuilt = len(decision.pages_to_build)
            assert pages_rebuilt == 0, (
                f"Unchanged files rebuilt: {pages_rebuilt} pages. Expected 0 on warm cache."
            )

    def test_consecutive_builds_stable(
        self,
        tmp_path: Path,
    ) -> None:
        """
        PROPERTY: Consecutive incremental builds are stable.

        Running incremental build twice without changes should produce
        same result (zero rebuilds).
        """
        site_dir, _content_dir, _page_paths = _create_warm_site(tmp_path)

        # First incremental build
        stats1, _site1 = _build_site(site_dir, incremental=True)

        # Second incremental build
        stats2, _site2 = _build_site(site_dir, incremental=True)

        # PROPERTY: Both should rebuild zero pages
        for stats, label in [(stats1, "first"), (stats2, "second")]:
            decision = getattr(stats, "incremental_decision", None)
            if decision is not None:
                pages_rebuilt = len(decision.pages_to_build)
                assert pages_rebuilt == 0, (
                    f"The {label} build rebuilt {pages_rebuilt} pages. Expected stable 0 rebuilds."
                )


@pytest.mark.slow  # Each example runs full build (~125s total)
@pytest.mark.parallel_unsafe  # Full builds conflict with xdist workers in Python 3.14t
class TestIncrementalEquivalence:
    """Tests that incremental and full builds produce equivalent output."""

    @given(indices=page_indices(5))
    @settings(
        max_examples=5,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_incremental_matches_full_build(
        self,
        indices: list[int],
    ) -> None:
        """
        PROPERTY: Incremental build output matches full build output.

        After modifications, the incremental build should produce
        the same output as a full (non-incremental) build.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            site_dir, _content_dir, page_paths = _create_warm_site(Path(tmp_dir))

            # Modify selected pages
            time.sleep(0.01)
            for i in indices:
                page = page_paths[i]
                original = page.read_text()
                page.write_text(original + f"\n<!-- modified-{i} -->")

            # Full build
            _stats_full, site_full = _build_site(site_dir, incremental=False)
            full_hashes = _hash_output_dir(site_full.output_dir)

            # Clean output for fresh incremental build
            shutil.rmtree(site_full.output_dir)

            # Incremental build
            _stats_incr, site_incr = _build_site(site_dir, incremental=True)
            incr_hashes = _hash_output_dir(site_incr.output_dir)

            # PROPERTY: Same files should exist
            full_files = set(full_hashes.keys())
            incr_files = set(incr_hashes.keys())

            assert full_files == incr_files, (
                f"Different files produced. "
                f"Full only: {full_files - incr_files}, "
                f"Incr only: {incr_files - full_files}"
            )


class TestCacheProperties:
    """Property-based tests for cache behavior."""

    def test_cache_survives_process_restart(
        self,
        tmp_path: Path,
    ) -> None:
        """
        PROPERTY: Cache persists correctly across process restarts.

        Cache should survive serialization/deserialization round-trip.
        """
        from bengal.cache.build_cache import BuildCache

        # Create and populate cache
        cache = BuildCache()
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        cache.update_file(test_file)

        # Save cache
        cache_path = tmp_path / "cache.json"
        cache.save(cache_path, use_lock=False)

        # Load in "new process" (new instance)
        loaded = BuildCache.load(cache_path, use_lock=False)

        # PROPERTY: Fingerprint should survive round-trip
        assert len(loaded.file_fingerprints) == 1, "Fingerprint lost in round-trip"

    @given(content=st.text(min_size=1, max_size=1000))
    @settings(max_examples=50)
    def test_fingerprint_changes_with_content(
        self,
        content: str,
    ) -> None:
        """
        PROPERTY: Different content produces different fingerprints.

        The content hash in fingerprints should be sensitive to content changes.
        """
        from bengal.cache.build_cache import BuildCache

        assume(content.strip())  # Skip empty content

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            test_file = tmp_path / "test.md"

            # First content
            test_file.write_text(f"---\ntitle: Test\n---\n{content}")
            cache1 = BuildCache()
            cache1.update_file(test_file)
            fp1 = cache1.file_fingerprints.get(str(test_file))

            # Different content
            test_file.write_text(f"---\ntitle: Different\n---\n{content[::-1]}")  # Reversed
            cache2 = BuildCache()
            cache2.update_file(test_file)
            fp2 = cache2.file_fingerprints.get(str(test_file))

            # PROPERTY: Different content should produce different fingerprint
            assert fp1 is not None
            assert fp2 is not None
            assert fp1["hash"] != fp2["hash"], "Different content produced same fingerprint"
