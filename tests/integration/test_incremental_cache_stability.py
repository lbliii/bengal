"""
Integration tests for incremental build cache stability.

RFC: rfc-cache-invalidation-fixes

These tests verify that incremental builds are stable and don't trigger
false full rebuilds due to cache invalidation bugs.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest


class TestIncrementalBuildStability:
    """
    Tests for incremental build stability.

    Verifies that:
    1. Consecutive incremental builds with no changes don't rebuild pages
    2. Touching templates without content changes doesn't trigger rebuilds
    3. Cache is consistent across builds

    """

    @pytest.fixture
    def minimal_site(self, tmp_path: Path) -> Path:
        """Create a minimal site for testing."""
        # Create bengal.toml
        config = tmp_path / "bengal.toml"
        config.write_text(
            """
[site]
title = "Test Site"
theme = "terminal"

[build]
incremental = true
"""
        )

        # Create content directory
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create index page
        index = content_dir / "index.md"
        index.write_text(
            """---
title: Home
---

# Welcome

This is the home page.
"""
        )

        # Create another page
        about = content_dir / "about.md"
        about.write_text(
            """---
title: About
---

# About Us

About content here.
"""
        )

        return tmp_path

    def test_consecutive_builds_no_changes(self, minimal_site: Path) -> None:
        """
        Three consecutive incremental builds with no changes should be instant.

        This is the main test case from the RFC to verify cache stability.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(minimal_site)
        paths.ensure_dirs()

        cache = BuildCache()

        # Track all content files
        content_dir = minimal_site / "content"
        for md_file in content_dir.glob("*.md"):
            cache.update_file(md_file)

        # Save cache
        cache.save(paths.build_cache)

        # Build 2: Load cache and verify no changes detected
        cache2 = BuildCache.load(paths.build_cache)

        changed_files = []
        for md_file in content_dir.glob("*.md"):
            if cache2.is_changed(md_file):
                changed_files.append(md_file)

        assert len(changed_files) == 0, f"Build 2 detected changes: {changed_files}"

        # Build 3: Same check (should also be stable)
        cache3 = BuildCache.load(paths.build_cache)

        changed_files = []
        for md_file in content_dir.glob("*.md"):
            if cache3.is_changed(md_file):
                changed_files.append(md_file)

        assert len(changed_files) == 0, f"Build 3 detected changes: {changed_files}"

    def test_template_touch_no_rebuild(self, minimal_site: Path) -> None:
        """
        Touching template without content change should not rebuild.

        Verifies Fix 4: Don't update unchanged template fingerprints.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(minimal_site)
        paths.ensure_dirs()

        # Create a template file
        templates_dir = minimal_site / "templates"
        templates_dir.mkdir(exist_ok=True)
        template = templates_dir / "base.html"
        template.write_text("{{ content }}")

        # Track template
        cache = BuildCache()
        cache.update_file(template)
        cache.save(paths.build_cache)

        # Touch template (mtime changes, content unchanged)
        time.sleep(0.01)
        template.touch()

        # Load cache and check if template is considered changed
        cache2 = BuildCache.load(paths.build_cache)

        # Template should NOT be considered changed (content hash matches)
        assert not cache2.is_changed(template), "Touch without change triggered rebuild"

    def test_config_hash_stability_across_loads(self, minimal_site: Path) -> None:
        """
        Config hash should be identical when loaded multiple times.

        Verifies Fix 1: Config hash stability.
        """
        from bengal.config import ConfigLoader
        from bengal.config.hash import compute_config_hash

        # Load config twice
        loader1 = ConfigLoader(minimal_site)
        loader2 = ConfigLoader(minimal_site)
        config1 = loader1.load()
        config2 = loader2.load()

        hash1 = compute_config_hash(config1)
        hash2 = compute_config_hash(config2)

        assert hash1 == hash2, f"Config hash differs: {hash1} vs {hash2}"

    def test_dependency_tracking_stable(self, minimal_site: Path) -> None:
        """
        Dependency tracking via EffectTracer should be stable across builds.

        Verifies that recorded effects persist and can be used for
        rebuild detection on subsequent builds.
        """
        from bengal.effects.effect import Effect
        from bengal.effects.tracer import EffectTracer

        # Create template and page
        templates_dir = minimal_site / "templates"
        templates_dir.mkdir(exist_ok=True)
        template = templates_dir / "single.html"
        template.write_text("<html>{{ content }}</html>")

        content_dir = minimal_site / "content"
        page = content_dir / "index.md"

        output_path = minimal_site / "public" / "index.html"

        # Build 1: Record effects
        tracer = EffectTracer()
        tracer.record(
            Effect(
                outputs=frozenset({output_path}),
                depends_on=frozenset({page, template}),
                invalidates=frozenset({"page:/"}),
                operation="render_page",
            )
        )

        # Persist effects
        effects_path = minimal_site / ".bengal" / "effects.json"
        effects_path.parent.mkdir(parents=True, exist_ok=True)
        tracer.save(effects_path)

        # Build 2: Load and verify
        tracer2 = EffectTracer.load(effects_path)

        # Template change should trigger rebuild of dependent page
        outputs = tracer2.outputs_needing_rebuild({template})
        assert output_path in outputs, "Template dependency not preserved"

        # Page source change should also trigger rebuild
        outputs2 = tracer2.outputs_needing_rebuild({page})
        assert output_path in outputs2, "Page source dependency not preserved"

    def test_content_change_detected_correctly(self, minimal_site: Path) -> None:
        """
        Actual content changes should be detected.

        Ensures fixes don't break legitimate change detection.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(minimal_site)
        paths.ensure_dirs()

        content_dir = minimal_site / "content"
        page = content_dir / "index.md"

        # Track page
        cache = BuildCache()
        cache.update_file(page)
        cache.save(paths.build_cache)

        # Modify page content
        time.sleep(0.01)
        page.write_text(
            """---
title: Home (Updated)
---

# Welcome

This is the updated home page.
"""
        )

        # Load cache and verify change detected
        cache2 = BuildCache.load(paths.build_cache)
        assert cache2.is_changed(page), "Content change not detected"

    def test_new_file_detected(self, minimal_site: Path) -> None:
        """
        New files should be detected as changed.

        Ensures fixes don't break new file detection.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(minimal_site)
        paths.ensure_dirs()

        content_dir = minimal_site / "content"

        # Track existing files
        cache = BuildCache()
        for md_file in content_dir.glob("*.md"):
            cache.update_file(md_file)
        cache.save(paths.build_cache)

        # Add new file
        new_page = content_dir / "new-page.md"
        new_page.write_text(
            """---
title: New Page
---

# New Page

New content here.
"""
        )

        # Load cache and verify new file detected
        cache2 = BuildCache.load(paths.build_cache)
        assert cache2.is_changed(new_page), "New file not detected as changed"


class TestCacheOutputMismatch:
    """
    Regression tests for cache/output mismatch scenarios.

    Bug: When .bengal cache is restored but output directory is cleaned
    (e.g., CI with `rm -rf public/*`), Bengal incorrectly skipped rebuilding
    because cache said "nothing changed".

    Fix: phase_incremental_filter now checks if output is missing BEFORE
    deciding to skip, forcing a full rebuild when output is empty.

    """

    @pytest.fixture
    def site_with_cache(self, tmp_path: Path) -> Path:
        """Create a site with cache but empty output directory."""
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths

        # Create config
        config = tmp_path / "bengal.toml"
        config.write_text(
            """
[site]
title = "Test Site"
theme = "terminal"

[build]
incremental = true
output_dir = "public"
"""
        )

        # Create content
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text(
            """---
title: Home
---

# Welcome
"""
        )

        # Create paths and cache (simulating previous successful build)
        paths = BengalPaths(tmp_path)
        paths.ensure_dirs()

        cache = BuildCache()
        cache.update_file(content_dir / "index.md")
        cache.last_build = time.strftime("%Y-%m-%dT%H:%M:%S")
        cache.save(paths.build_cache)

        # Create output directory but leave it EMPTY (simulating rm -rf public/*)
        output_dir = tmp_path / "public"
        output_dir.mkdir(exist_ok=True)
        # No index.html, no assets - this simulates the CI bug

        return tmp_path

    def test_forces_rebuild_when_output_missing(self, site_with_cache: Path) -> None:
        """
        When cache exists but output is empty, should force full rebuild.

        Regression test for: GitHub Actions builds with cached .bengal but rm -rf public/*
        """
        # Load site
        from bengal.core.site import Site
        from bengal.orchestration.build import BuildOrchestrator
        from bengal.orchestration.build.provenance_filter import (
            phase_incremental_filter_provenance,
        )
        from bengal.output import CLIOutput

        site = Site.from_config(site_with_cache)

        # Initialize orchestrator
        orchestrator = BuildOrchestrator(site)

        # CRITICAL: Discover content first (simulates phase_discovery)
        orchestrator.content.discover_content()
        orchestrator.content.discover_assets()

        # Initialize incremental orchestrator
        cache = orchestrator.incremental.initialize(enabled=True)

        # Run incremental filter
        cli = CLIOutput()
        build_start = time.time()

        result = phase_incremental_filter_provenance(
            orchestrator=orchestrator,
            cli=cli,
            incremental=True,
            verbose=False,
            cache=cache,
            build_start=build_start,
        )

        # CRITICAL: Should NOT return None (skip) - should force rebuild
        assert result is not None, (
            "phase_incremental_filter returned None (skip) when output is missing! "
            "This is the bug: cache exists but output is empty, should force rebuild."
        )

        # Should include pages to build
        assert len(result.pages_to_build) > 0, (
            "pages_to_build is empty when output is missing - should force full rebuild"
        )

    def test_detects_missing_index_html(self, site_with_cache: Path) -> None:
        """
        Specifically test that missing index.html triggers rebuild.
        """
        output_dir = site_with_cache / "public"

        # Create assets directory but no index.html
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        (assets_dir / "style.css").write_text("body {}")

        # Output has assets but no HTML - should still rebuild

        from bengal.core.site import Site
        from bengal.orchestration.build import BuildOrchestrator
        from bengal.orchestration.build.provenance_filter import (
            phase_incremental_filter_provenance,
        )
        from bengal.output import CLIOutput

        site = Site.from_config(site_with_cache)
        orchestrator = BuildOrchestrator(site)

        # Discover content first
        orchestrator.content.discover_content()
        orchestrator.content.discover_assets()

        cache = orchestrator.incremental.initialize(enabled=True)

        result = phase_incremental_filter_provenance(
            orchestrator=orchestrator,
            cli=CLIOutput(),
            incremental=True,
            verbose=False,
            cache=cache,
            build_start=time.time(),
        )

        assert result is not None, "Should rebuild when index.html is missing"
        assert len(result.pages_to_build) > 0

    def test_detects_missing_assets(self, site_with_cache: Path) -> None:
        """
        Specifically test that missing assets directory triggers rebuild.
        """
        output_dir = site_with_cache / "public"

        # Create index.html but no assets
        (output_dir / "index.html").write_text("<html></html>")
        # No assets directory - should trigger rebuild

        from bengal.core.site import Site
        from bengal.orchestration.build import BuildOrchestrator
        from bengal.orchestration.build.provenance_filter import (
            phase_incremental_filter_provenance,
        )
        from bengal.output import CLIOutput

        site = Site.from_config(site_with_cache)
        orchestrator = BuildOrchestrator(site)

        # Discover content first
        orchestrator.content.discover_content()
        orchestrator.content.discover_assets()

        cache = orchestrator.incremental.initialize(enabled=True)

        result = phase_incremental_filter_provenance(
            orchestrator=orchestrator,
            cli=CLIOutput(),
            incremental=True,
            verbose=False,
            cache=cache,
            build_start=time.time(),
        )

        # Should trigger rebuild (result not None)
        assert result is not None, "Should rebuild when assets directory is missing"
        # Pages should be rebuilt (the key indicator)
        assert len(result.pages_to_build) > 0, "Pages should be rebuilt when output is incomplete"


class TestAutodocOutputMismatch:
    """
    Regression tests for autodoc output missing scenarios.

    Bug: When .bengal cache is restored in CI but site/public/api/ (autodoc output)
    was not cached, Bengal incorrectly skipped rebuilding virtual pages because
    the cache said "source files unchanged".

    Fix: _check_autodoc_output_missing() now checks if autodoc output directories
    exist and contain content before deciding to skip.

    """

    @pytest.fixture
    def site_with_autodoc_cache(self, tmp_path: Path) -> Path:
        """Create a site with autodoc config, cache, but missing autodoc output."""
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths

        # Create config with autodoc enabled
        config = tmp_path / "bengal.toml"
        config.write_text(
            """
[site]
title = "Test Site"
theme = "terminal"

[build]
incremental = true
output_dir = "public"

[autodoc.python]
enabled = true
source_dirs = ["src/mypackage"]
output_prefix = "api"
"""
        )

        # Create content
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text(
            """---
title: Home
---

# Welcome
"""
        )

        # Create fake source directory (autodoc needs something to reference)
        src_dir = tmp_path / "src" / "mypackage"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text('"""My package."""\n')

        # Create paths and cache with autodoc dependencies
        paths = BengalPaths(tmp_path)
        paths.ensure_dirs()

        cache = BuildCache()
        cache.update_file(content_dir / "index.md")
        cache.last_build = time.strftime("%Y-%m-%dT%H:%M:%S")
        # Simulate previous autodoc build by adding dependencies
        cache.autodoc_tracker.autodoc_dependencies = {
            "src/mypackage/__init__.py": {"api/mypackage/index.md"}
        }
        cache.save(paths.build_cache)

        # Create output directory with HTML and assets (so basic checks pass)
        # BUT no api/ directory (simulating missing autodoc output)
        output_dir = tmp_path / "public"
        output_dir.mkdir(exist_ok=True)
        (output_dir / "index.html").write_text("<html></html>")
        assets_dir = output_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "style.css").write_text("body {}")
        (assets_dir / "script.js").write_text("console.log('hi')")
        (assets_dir / "icons").mkdir()
        # No api/ directory - this simulates the CI bug

        return tmp_path

    def test_detects_missing_autodoc_output(self, site_with_autodoc_cache: Path) -> None:
        """
        When cache has autodoc dependencies but api/ output is missing, should rebuild.

        Regression test for: Warm CI builds where .bengal is cached but public/api/ is not.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths
        from bengal.orchestration.build.initialization import _check_autodoc_output_missing

        # Create a mock orchestrator-like object
        class MockOrchestrator:
            def __init__(self, path: Path) -> None:
                from bengal.core.site import Site

                self.site = Site.from_config(path)

        orchestrator = MockOrchestrator(site_with_autodoc_cache)
        paths = BengalPaths(site_with_autodoc_cache)
        cache = BuildCache.load(paths.build_cache)

        # Check should detect missing autodoc output
        result = _check_autodoc_output_missing(orchestrator, cache)

        assert result is True, (
            "_check_autodoc_output_missing returned False when api/ directory is missing! "
            "This means warm CI builds will 404 on virtual pages."
        )

    def test_passes_when_autodoc_output_exists(self, site_with_autodoc_cache: Path) -> None:
        """
        When autodoc output exists, should not trigger rebuild.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths
        from bengal.orchestration.build.initialization import _check_autodoc_output_missing

        # Create the api/ directory with content
        output_dir = site_with_autodoc_cache / "public"
        api_dir = output_dir / "api"
        api_dir.mkdir()
        mypackage_dir = api_dir / "mypackage"
        mypackage_dir.mkdir()
        (mypackage_dir / "index.html").write_text("<html></html>")

        class MockOrchestrator:
            def __init__(self, path: Path) -> None:
                from bengal.core.site import Site

                self.site = Site.from_config(path)

        orchestrator = MockOrchestrator(site_with_autodoc_cache)
        paths = BengalPaths(site_with_autodoc_cache)
        cache = BuildCache.load(paths.build_cache)

        # Check should pass (output exists)
        result = _check_autodoc_output_missing(orchestrator, cache)

        assert result is False, (
            "_check_autodoc_output_missing returned True when api/ directory exists! "
            "This would cause unnecessary full rebuilds."
        )

    def test_no_autodoc_config_returns_false(self, tmp_path: Path) -> None:
        """
        Sites without autodoc config should not trigger rebuild.

        Edge case: Prevents false positives on sites that don't use autodoc.
        """
        from bengal.cache import BuildCache
        from bengal.orchestration.build.initialization import _check_autodoc_output_missing

        # Create config WITHOUT autodoc
        config = tmp_path / "bengal.toml"
        config.write_text(
            """
[site]
title = "Test Site"
theme = "terminal"

[build]
output_dir = "public"
"""
        )

        # Create minimal content
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Hi\n")

        # Create output
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>")

        class MockOrchestrator:
            def __init__(self, path: Path) -> None:
                from bengal.core.site import Site

                self.site = Site.from_config(path)

        orchestrator = MockOrchestrator(tmp_path)
        cache = BuildCache()  # Empty cache, no autodoc_dependencies

        result = _check_autodoc_output_missing(orchestrator, cache)

        assert result is False, (
            "Sites without autodoc config should not trigger autodoc output check"
        )

    def test_cli_autodoc_missing(self, tmp_path: Path) -> None:
        """
        CLI autodoc uses different prefix (cli/) - should detect when missing.

        Edge case: CLI autodoc has different default prefix than Python autodoc.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths
        from bengal.orchestration.build.initialization import _check_autodoc_output_missing

        # Create config with CLI autodoc enabled
        config = tmp_path / "bengal.toml"
        config.write_text(
            """
[site]
title = "Test Site"
theme = "terminal"

[build]
output_dir = "public"

[autodoc.cli]
enabled = true
module = "myapp.cli"
output_prefix = "cli"
"""
        )

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Hi\n")

        # Create paths and cache with CLI autodoc dependencies
        paths = BengalPaths(tmp_path)
        paths.ensure_dirs()

        cache = BuildCache()
        cache.autodoc_tracker.autodoc_dependencies = {"myapp/cli.py": {"cli/commands/index.md"}}
        cache.save(paths.build_cache)

        # Create output with everything EXCEPT cli/ directory
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>")
        assets_dir = output_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "style.css").write_text("body {}")
        (assets_dir / "script.js").write_text("")
        (assets_dir / "icons").mkdir()

        class MockOrchestrator:
            def __init__(self, path: Path) -> None:
                from bengal.core.site import Site

                self.site = Site.from_config(path)

        orchestrator = MockOrchestrator(tmp_path)
        cache = BuildCache.load(paths.build_cache)

        result = _check_autodoc_output_missing(orchestrator, cache)

        assert result is True, "CLI autodoc output (cli/) missing should trigger rebuild"

    def test_empty_autodoc_dir_triggers_rebuild(self, site_with_autodoc_cache: Path) -> None:
        """
        Directory exists but has no index.html - should still trigger rebuild.

        Edge case: Partial/corrupted output where directory exists but is empty.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths
        from bengal.orchestration.build.initialization import _check_autodoc_output_missing

        # Create api/ directory but leave it EMPTY (no index.html)
        output_dir = site_with_autodoc_cache / "public"
        api_dir = output_dir / "api"
        api_dir.mkdir()
        # No index.html inside - simulates partial/failed build

        class MockOrchestrator:
            def __init__(self, path: Path) -> None:
                from bengal.core.site import Site

                self.site = Site.from_config(path)

        orchestrator = MockOrchestrator(site_with_autodoc_cache)
        paths = BengalPaths(site_with_autodoc_cache)
        cache = BuildCache.load(paths.build_cache)

        result = _check_autodoc_output_missing(orchestrator, cache)

        assert result is True, "Empty autodoc directory (no index.html) should trigger rebuild"

    def test_auto_derived_prefix(self, tmp_path: Path) -> None:
        """
        When output_prefix is empty, Bengal auto-derives from source_dirs.

        Edge case: Common pattern where users don't specify output_prefix.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths
        from bengal.orchestration.build.initialization import _check_autodoc_output_missing

        # Create config with autodoc but NO output_prefix (auto-derive)
        config = tmp_path / "bengal.toml"
        config.write_text(
            """
[site]
title = "Test Site"
theme = "terminal"

[build]
output_dir = "public"

[autodoc.python]
enabled = true
source_dirs = ["src/mypackage"]
# No output_prefix - should auto-derive to "api/mypackage"
"""
        )

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Hi\n")

        src_dir = tmp_path / "src" / "mypackage"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text('"""Package."""\n')

        paths = BengalPaths(tmp_path)
        paths.ensure_dirs()

        cache = BuildCache()
        cache.autodoc_tracker.autodoc_dependencies = {
            "src/mypackage/__init__.py": {"api/mypackage/index.md"}
        }
        cache.save(paths.build_cache)

        # Create output WITHOUT the auto-derived api/mypackage/ directory
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>")
        assets_dir = output_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "style.css").write_text("body {}")
        (assets_dir / "script.js").write_text("")
        (assets_dir / "icons").mkdir()

        class MockOrchestrator:
            def __init__(self, path: Path) -> None:
                from bengal.core.site import Site

                self.site = Site.from_config(path)

        orchestrator = MockOrchestrator(tmp_path)
        cache = BuildCache.load(paths.build_cache)

        result = _check_autodoc_output_missing(orchestrator, cache)

        assert result is True, "Auto-derived prefix (api/mypackage) missing should trigger rebuild"
