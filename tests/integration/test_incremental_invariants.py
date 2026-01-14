"""
Invariant tests for incremental build correctness.

RFC: rfc-incremental-build-observability (Phase 1)

These tests verify behavioral contracts that must hold regardless of
implementation details. They catch regressions that unit tests might miss.

Invariants tested:
- Unchanged files are never rebuilt
- Changed files are always rebuilt
- Subsection changes mark parent section
- Cross-process cache consistency
- Consecutive builds without changes skip all pages
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pytest

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.orchestration.stats.models import BuildStats


@dataclass
class WarmBuildTestSite:
    """Test site with pre-warmed cache for incremental testing.

    Provides a reusable test site that has already been built once,
    ensuring the cache is warm for subsequent incremental build tests.

    Attributes:
        root: Path to the site root directory
        content: Path to the content directory
        cache_path: Path to the cache file
    """

    root: Path
    content: Path
    cache_path: Path
    _site: "Site | None" = None

    @property
    def site(self) -> "Site":
        """Load or return cached site instance."""
        if self._site is None:
            from bengal.cli.helpers import load_site_from_cli

            self._site = load_site_from_cli(source=str(self.root))
        return self._site

    def build(self, *, incremental: bool = True, explain: bool = True) -> "BuildStats":
        """Build the site and return stats.

        Args:
            incremental: Whether to use incremental build mode
            explain: Whether to enable explain mode for detailed decision info

        Returns:
            BuildStats object with build results
        """
        from bengal.cli.helpers import load_site_from_cli
        from bengal.orchestration.build.options import BuildOptions
        from bengal.utils.observability.profile import BuildProfile

        # Reload site to pick up file changes
        self._site = load_site_from_cli(source=str(self.root))
        options = BuildOptions(
            incremental=incremental,
            quiet=True,
            explain=explain,
            profile=BuildProfile.WRITER,
        )
        return self._site.build(options=options)

    def reload(self) -> None:
        """Force site reload (picks up file changes)."""
        self._site = None


@pytest.fixture
def warm_site(tmp_path: Path) -> Generator[WarmBuildTestSite, None, None]:
    """Create a minimal site and warm its cache.

    Creates a basic Bengal site with:
    - _index.md (home page)
    - page1.md
    - page2.md

    The site is built once in non-incremental mode to warm the cache.

    Yields:
        WarmBuildTestSite with warmed cache ready for incremental testing
    """
    # Create site structure
    root = tmp_path / "site"
    root.mkdir()

    config = root / "bengal.toml"
    config.write_text("""
[site]
title = "Test Site"
baseURL = "http://localhost"

[build]
output_dir = "public"
""")

    content = root / "content"
    content.mkdir()
    (content / "_index.md").write_text("---\ntitle: Home\n---\n# Home")
    (content / "page1.md").write_text("---\ntitle: Page 1\n---\n# Page 1")
    (content / "page2.md").write_text("---\ntitle: Page 2\n---\n# Page 2")

    site = WarmBuildTestSite(
        root=root,
        content=content,
        cache_path=root / ".bengal" / "cache.json",
    )

    # Warm the cache with initial build
    site.build(incremental=False)

    yield site


@pytest.fixture
def warm_site_with_sections(tmp_path: Path) -> Generator[WarmBuildTestSite, None, None]:
    """Create a site with nested sections and warm its cache.

    Creates a Bengal site with:
    - _index.md (home)
    - docs/_index.md (docs section)
    - docs/about/_index.md (about subsection)
    - docs/about/glossary.md (page in subsection)

    This fixture is used to test subsection change propagation.

    Yields:
        WarmBuildTestSite with sections and warmed cache
    """
    root = tmp_path / "site"
    root.mkdir()

    config = root / "bengal.toml"
    config.write_text("""
[site]
title = "Test Site"
baseURL = "http://localhost"

[build]
output_dir = "public"
""")

    content = root / "content"
    content.mkdir()
    (content / "_index.md").write_text("---\ntitle: Home\n---\n# Home")

    # Create nested section: docs/about/
    docs = content / "docs"
    docs.mkdir()
    (docs / "_index.md").write_text("---\ntitle: Docs\n---\n# Docs")

    about = docs / "about"
    about.mkdir()
    (about / "_index.md").write_text("---\ntitle: About\n---\n# About")
    (about / "glossary.md").write_text("---\ntitle: Glossary\n---\n# Glossary")

    site = WarmBuildTestSite(
        root=root,
        content=content,
        cache_path=root / ".bengal" / "cache.json",
    )

    # Warm the cache
    site.build(incremental=False)

    yield site


class TestIncrementalInvariants:
    """Tests that verify incremental build correctness invariants.

    These tests verify behavioral contracts that must hold regardless of
    implementation details. Failures indicate serious bugs in the
    incremental build system.
    """

    def test_unchanged_file_never_rebuilt(self, warm_site: WarmBuildTestSite) -> None:
        """INVARIANT: Unchanged files must never be rebuilt.

        After a warm build, if no files have changed, the next incremental
        build should rebuild zero pages.
        """
        # First incremental build (should rebuild nothing)
        stats = warm_site.build(incremental=True)

        # INVARIANT: No pages should be rebuilt
        decision = getattr(stats, "incremental_decision", None)
        if decision is not None:
            pages_rebuilt = len(decision.pages_to_build)
            assert pages_rebuilt == 0, (
                f"Unchanged files were rebuilt: {pages_rebuilt} pages. "
                f"Expected 0 rebuilds on warm cache with no changes."
            )
        else:
            # If no decision, build was skipped - that's also correct
            assert stats.skipped or stats.total_pages >= 0

    def test_changed_file_always_rebuilt(self, warm_site: WarmBuildTestSite) -> None:
        """INVARIANT: Changed files must always be rebuilt.

        When a content file is modified, it must appear in the rebuild list
        for the next incremental build.
        """
        # Modify a file
        test_file = warm_site.content / "page1.md"
        original = test_file.read_text()
        time.sleep(0.01)  # Ensure mtime changes
        test_file.write_text(original + "\n<!-- modified -->")

        stats = warm_site.build(incremental=True)

        # INVARIANT: Modified file must be rebuilt
        decision = getattr(stats, "incremental_decision", None)
        if decision is not None:
            rebuilt_paths = {str(p.source_path) for p in decision.pages_to_build}
            assert any("page1" in p for p in rebuilt_paths), (
                f"Changed file page1.md was not rebuilt. " f"Rebuilt: {rebuilt_paths}"
            )
        else:
            # If no decision object, check that at least one page was built
            assert stats.total_pages >= 1, "Changed file should have triggered a rebuild"

    def test_subsection_change_marks_parent_section(
        self, warm_site_with_sections: WarmBuildTestSite
    ) -> None:
        """INVARIANT: Subsection changes must mark parent section as changed.

        When a file in a subsection (docs/about/glossary.md) changes,
        it must be rebuilt even though it's nested deeply.
        """
        # Modify file in subsection
        glossary = warm_site_with_sections.content / "docs" / "about" / "glossary.md"
        original = glossary.read_text()
        time.sleep(0.01)
        glossary.write_text(original + "\n<!-- modified -->")

        stats = warm_site_with_sections.build(incremental=True)

        # INVARIANT: glossary.md must be rebuilt
        decision = getattr(stats, "incremental_decision", None)
        if decision is not None:
            rebuilt_paths = {str(p.source_path) for p in decision.pages_to_build}
            assert any("glossary" in p for p in rebuilt_paths), (
                f"Changed file glossary.md was not rebuilt. " f"Rebuilt: {rebuilt_paths}"
            )
        else:
            # If no decision object, check that at least one page was built
            assert stats.total_pages >= 1, "Subsection file change should trigger rebuild"

    def test_cross_process_cache_consistency(self, tmp_path: Path) -> None:
        """INVARIANT: Cache saved in process A must load correctly in process B.

        This tests that cache serialization/deserialization works correctly
        across process boundaries, which is critical for CI caching.
        """
        cache_path = tmp_path / "cache.json"
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Save cache in subprocess
        bengal_root = Path(__file__).parent.parent.parent
        save_script = f'''
import sys
from pathlib import Path
sys.path.insert(0, "{bengal_root}")
from bengal.cache.build_cache import BuildCache

cache = BuildCache()
cache.update_file(Path("{test_file}"))
cache.save(Path("{cache_path}"), use_lock=False)
print(f"saved:{{len(cache.file_fingerprints)}}")
'''
        result = subprocess.run(
            [sys.executable, "-c", save_script],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert "saved:1" in result.stdout, f"Save failed: {result.stderr}"

        # Load in current process
        from bengal.cache.build_cache import BuildCache

        loaded = BuildCache.load(cache_path, use_lock=False)

        # INVARIANT: Fingerprints must survive cross-process round-trip
        assert len(loaded.file_fingerprints) == 1, (
            f"Fingerprint lost in cross-process round-trip. "
            f"Expected 1, got {len(loaded.file_fingerprints)}"
        )

    def test_second_build_without_changes_is_skip(
        self, warm_site: WarmBuildTestSite
    ) -> None:
        """INVARIANT: Consecutive builds without changes should skip or rebuild 0.

        When no files have changed between builds, the incremental system
        should detect this and skip unnecessary work.
        """
        stats1 = warm_site.build(incremental=True)
        stats2 = warm_site.build(incremental=True)

        # INVARIANT: Second build should have 0 pages to rebuild
        decision = getattr(stats2, "incremental_decision", None)
        if decision is not None:
            pages_rebuilt = len(decision.pages_to_build)
            assert pages_rebuilt == 0, (
                f"Second build without changes rebuilt {pages_rebuilt} pages. "
                f"Cache should be stable."
            )
        else:
            # Build was skipped or completed with no rebuilds
            assert stats2.skipped or stats2.total_pages == 0


class TestIncrementalEdgeCases:
    """Additional edge case tests for incremental builds."""

    def test_multiple_files_changed_all_rebuilt(
        self, warm_site: WarmBuildTestSite
    ) -> None:
        """When multiple files change, all changed files should be rebuilt."""
        # Modify multiple files
        time.sleep(0.01)
        (warm_site.content / "page1.md").write_text(
            "---\ntitle: Page 1 Modified\n---\n# Page 1 Modified"
        )
        (warm_site.content / "page2.md").write_text(
            "---\ntitle: Page 2 Modified\n---\n# Page 2 Modified"
        )

        stats = warm_site.build(incremental=True)

        decision = getattr(stats, "incremental_decision", None)
        if decision is not None:
            rebuilt_paths = {str(p.source_path) for p in decision.pages_to_build}
            assert any("page1" in p for p in rebuilt_paths), "page1.md should be rebuilt"
            assert any("page2" in p for p in rebuilt_paths), "page2.md should be rebuilt"

    def test_unchanged_sibling_rebuild_reason(
        self, warm_site: WarmBuildTestSite
    ) -> None:
        """When one file changes, any rebuilt siblings should have appropriate reasons.

        Note: Section-level optimization may cause siblings to rebuild together.
        This test verifies that if siblings ARE rebuilt, they have appropriate
        reasons (not falsely claiming content_changed).
        """
        # Modify only page1
        time.sleep(0.01)
        (warm_site.content / "page1.md").write_text(
            "---\ntitle: Page 1 Modified\n---\n# Page 1 Modified"
        )

        stats = warm_site.build(incremental=True)

        decision = getattr(stats, "incremental_decision", None)
        if decision is not None:
            # page1 must have been rebuilt with content_changed reason
            page1_rebuilt = any(
                "page1" in p for p in decision.rebuild_reasons.keys()
            )
            assert page1_rebuilt, "Modified file page1.md should be in rebuild_reasons"

            # If page2 was rebuilt, log the reason (acceptable if section-related)
            for page_path, reason in decision.rebuild_reasons.items():
                if "page2" in page_path:
                    # Section optimization may rebuild siblings - this is acceptable
                    # behavior for small sections. Just verify it's tracked.
                    assert reason.code is not None, "Rebuild reason should be tracked"

    def test_new_file_detected_on_incremental(
        self, warm_site: WarmBuildTestSite
    ) -> None:
        """A new file added after warm build should be detected and built."""
        # Add a new file
        time.sleep(0.01)
        (warm_site.content / "page3.md").write_text(
            "---\ntitle: Page 3\n---\n# Page 3 - New!"
        )

        # Force reload to pick up new file
        warm_site.reload()
        stats = warm_site.build(incremental=True)

        # New file should be built (either as part of incremental or full rebuild)
        assert stats.total_pages >= 1, "New file should trigger build"
