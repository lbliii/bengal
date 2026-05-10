"""Tests for BuildTrigger."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.cache import BuildCache
from bengal.orchestration.build.options import BuildCompletionPolicy
from bengal.orchestration.stats import ReloadHint
from bengal.server.build_trigger import BuildTrigger
from bengal.server.reload_types import BuildReloadInfo, SerializedOutputRecord


class TestBuildTrigger:
    """Tests for BuildTrigger class."""

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        result = MagicMock()
        result.success = True
        result.pages_built = 5
        result.build_time_ms = 100.0
        result.error_message = None
        result.changed_outputs = ()
        executor.submit.return_value = result
        return executor

    def test_init(self, mock_site: MagicMock, mock_executor: MagicMock) -> None:
        """Test BuildTrigger initialization."""
        trigger = BuildTrigger(
            site=mock_site,
            host="localhost",
            port=5173,
            executor=mock_executor,
        )

        assert trigger.site is mock_site
        assert trigger.host == "localhost"
        assert trigger.port == 5173
        assert trigger._executor is mock_executor

    def test_skips_content_hash_baseline_for_typed_watcher_rebuild(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Normal watcher rebuilds use typed outputs instead of pre-build tree scans."""
        controller = MagicMock()
        controller._use_content_hashes = True
        trigger = BuildTrigger(site=mock_site, executor=mock_executor, controller=controller)

        assert trigger._should_capture_content_hash_baseline(["content/page.md"]) is False
        assert trigger._should_capture_content_hash_baseline([]) is True

    def test_openapi_ref_dependency_triggers_autodoc_regeneration(
        self, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Changed OpenAPI ref files should regenerate autodoc, not only the root spec."""
        from bengal.cache.paths import BengalPaths

        root = tmp_path / "site"
        api_dir = root / "api"
        api_dir.mkdir(parents=True)
        spec_path = api_dir / "openapi.yaml"
        schema_path = api_dir / "schemas.yaml"
        spec_path.write_text("openapi: 3.1.0\n", encoding="utf-8")
        schema_path.write_text("User:\n  type: object\n", encoding="utf-8")

        paths = BengalPaths(root)
        paths.ensure_dirs()
        cache = BuildCache()
        cache.autodoc_tracker.add_autodoc_dependency(
            schema_path.resolve(),
            "api/demo/schemas/User.md",
            site_root=root,
            source_hash="schema-hash",
            source_mtime=schema_path.stat().st_mtime,
            content_hash="doc-hash",
        )
        cache.save(paths.build_cache)

        site = MagicMock()
        site.root_path = root
        site.output_dir = root / "public"
        site.config = {
            "autodoc": {
                "openapi": {
                    "enabled": True,
                    "spec_file": "api/openapi.yaml",
                }
            }
        }
        site.theme = None
        site._cache = cache
        site.config_service.paths.build_cache = paths.build_cache

        trigger = BuildTrigger(site=site, executor=mock_executor)

        with patch("bengal.server.build_trigger.SiteLike", object):
            assert trigger._should_regenerate_autodoc({schema_path}) is True

    def test_shutdown_calls_executor_shutdown(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Test that shutdown calls executor shutdown."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.shutdown()

        mock_executor.shutdown.assert_called_once_with(wait=True)

    def test_can_use_reactive_path_single_md_modified(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _can_use_reactive_path returns True for content-only .md edit."""
        md_file = tmp_path / "content" / "page.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("---\ntitle: Test\n---\nOriginal body")
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # First call: no cache, populates cache and returns False
        result = trigger._can_use_reactive_path({md_file}, {"modified"})
        assert result is False

        # Change body only (frontmatter unchanged)
        md_file.write_text("---\ntitle: Test\n---\nNew body")
        result = trigger._can_use_reactive_path({md_file}, {"modified"})
        assert result is True

    def test_can_use_reactive_path_rejects_multiple_files(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _can_use_reactive_path returns False for multiple files."""
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        a.write_text("---\ntitle: A\n---\nA")
        b.write_text("---\ntitle: B\n---\nB")
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._can_use_reactive_path({a, b}, {"modified"}) is False

    def test_can_use_reactive_path_rejects_created_event(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _can_use_reactive_path returns False for created event."""
        md_file = tmp_path / "page.md"
        md_file.write_text("---\ntitle: Test\n---\nBody")
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._can_use_reactive_path({md_file}, {"created"}) is False

    def test_can_use_reactive_path_rejects_non_md(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _can_use_reactive_path returns False for non-.md files."""
        txt_file = tmp_path / "file.txt"
        txt_file.write_text("content")
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._can_use_reactive_path({txt_file}, {"modified"}) is False

    def test_seed_content_hash_cache_populates_cache(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that seed_content_hash_cache populates cache for content pages."""
        md_file = tmp_path / "content" / "page.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("---\ntitle: Test\n---\nOriginal body")

        page = MagicMock()
        page.source_path = md_file
        page._section = None
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        assert md_file in trigger._content_hash_cache
        entry = trigger._content_hash_cache[md_file]
        assert entry.frontmatter_hash
        assert entry.content_hash

    def test_first_edit_uses_reactive_path_after_seed(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that first content-only edit uses reactive path after seed."""
        md_file = tmp_path / "content" / "page.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("---\ntitle: Test\n---\nOriginal body")

        page = MagicMock()
        page.source_path = md_file
        page._section = None
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        # Simulate user editing body only
        md_file.write_text("---\ntitle: Test\n---\nEdited body")
        result = trigger._can_use_reactive_path({md_file}, {"modified"})
        assert result is True

    def test_reactive_path_rejects_page_with_rendered_section_index(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Leaf pages with rendered section indexes need the warm build path."""
        md_file = tmp_path / "content" / "docs" / "page.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("---\ntitle: Test\n---\nOriginal body")

        index_page = MagicMock()
        index_page.output_path = tmp_path / "public" / "docs" / "index.html"
        section = MagicMock()
        section.index_page = index_page
        page = MagicMock()
        page.source_path = md_file
        page._section = section
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        md_file.write_text("---\ntitle: Test\n---\nEdited body")

        assert trigger._can_use_reactive_path({md_file}, {"modified"}) is False

    def test_seed_content_hash_cache_section_page(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that seed_content_hash_cache works for section _index.md."""
        index_file = tmp_path / "content" / "docs" / "_index.md"
        index_file.parent.mkdir(parents=True)
        index_file.write_text("---\ntitle: Docs\n---\nSection intro.")

        page = MagicMock()
        page.source_path = index_file
        page._section = None
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        assert index_file in trigger._content_hash_cache
        index_file.write_text("---\ntitle: Docs\n---\nUpdated intro.")
        assert trigger._can_use_reactive_path({index_file}, {"modified"}) is True

    def test_seed_content_hash_cache_skips_non_md(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that seed_content_hash_cache skips non-.md pages."""
        txt_file = tmp_path / "content" / "readme.txt"
        txt_file.parent.mkdir(parents=True)
        txt_file.write_text("No frontmatter")

        page = MagicMock()
        page.source_path = txt_file
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        assert txt_file not in trigger._content_hash_cache

    def test_seed_content_hash_cache_skips_no_frontmatter(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that seed_content_hash_cache skips files without frontmatter."""
        md_file = tmp_path / "content" / "page.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("No frontmatter here, just body.")

        page = MagicMock()
        page.source_path = md_file
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        assert md_file not in trigger._content_hash_cache

    def test_needs_full_rebuild_for_structural_changes(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Test that structural changes trigger full rebuild."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Created file
        assert trigger._needs_full_rebuild({Path("test.md")}, {"created"}) is True

        # Deleted file
        assert trigger._needs_full_rebuild({Path("test.md")}, {"deleted"}) is True

        # Moved file
        assert trigger._needs_full_rebuild({Path("test.md")}, {"moved"}) is True

        # Modified file (should not need full rebuild)
        assert trigger._needs_full_rebuild({Path("test.md")}, {"modified"}) is False

    def test_needs_full_rebuild_for_template_changes(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that template changes trigger full rebuild."""
        # Create a real template directory
        mock_site.root_path = tmp_path
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._is_template_change({template_file}) is True

    @patch("bengal.rendering.engines.create_engine")
    def test_template_change_uses_incremental_when_dependents_are_known(
        self,
        mock_create_engine: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Known template dependents can be handled by an incremental rebuild."""
        mock_site.root_path = tmp_path
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        page_path = tmp_path / "content" / "page.md"
        cache = BuildCache(site_root=tmp_path)
        cache.record_page_templates(str(page_path), frozenset({"base.html"}))
        mock_site._cache = cache
        mock_create_engine.return_value.has_capability.return_value = True

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._is_template_change({template_file}) is False

    @patch("bengal.server.build_trigger.logger")
    @patch("bengal.rendering.engines.create_engine")
    def test_template_change_logs_incremental_decision(
        self,
        mock_create_engine: MagicMock,
        mock_logger: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Template changes with known dependents explain the incremental path."""
        mock_site.root_path = tmp_path
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        page_path = tmp_path / "content" / "page.md"
        cache = BuildCache(site_root=tmp_path)
        cache.record_page_templates(str(page_path), frozenset({"base.html"}))
        mock_site._cache = cache
        mock_create_engine.return_value.has_capability.return_value = True

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._is_template_change({template_file}) is False
        mock_logger.info.assert_any_call(
            "template_change_incremental",
            template=str(template_file),
            affected_pages=1,
        )

    def test_template_change_without_dependency_data_stays_conservative(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Template changes fall back to full rebuild when dependency data is missing."""
        mock_site.root_path = tmp_path
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")
        mock_site._cache = BuildCache(site_root=tmp_path)

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._is_template_change({template_file}) is True

    @patch("bengal.server.build_trigger.logger")
    def test_template_change_logs_missing_dependency_data(
        self,
        mock_logger: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Template dependency cache misses explain why a full rebuild is needed."""
        mock_site.root_path = tmp_path
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")
        mock_site._cache = BuildCache(site_root=tmp_path)

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._is_template_change({template_file}) is True
        mock_logger.info.assert_any_call(
            "template_change_full_rebuild",
            template=str(template_file),
            affected_pages=0,
            reason="dependency_data_missing",
            suggestion="Run one full build to populate template dependency data.",
        )

    def test_template_change_with_known_orphan_template_is_ignored(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """A changed template with known empty dependents does not force a rebuild."""
        mock_site.root_path = tmp_path
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "orphan.html"
        template_file.write_text("<html></html>")

        cache = BuildCache(site_root=tmp_path)
        cache.record_page_templates(
            str(tmp_path / "content" / "page.md"),
            frozenset({"base.html"}),
        )
        mock_site._cache = cache

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._is_template_change({template_file}) is False

    def test_detect_nav_changes_finds_nav_frontmatter(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that nav frontmatter detection works."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a test file with nav frontmatter
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test Page
weight: 10
---

Content here.
"""
        )

        result = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file in result

    def test_detect_nav_changes_skips_non_nav_frontmatter(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that non-nav frontmatter is skipped."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a test file without nav-affecting frontmatter
        # (no title, weight, order, draft, headless, etc.)
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
author: Someone
description: A test page
tags:
  - test
---

Content here.
"""
        )

        result = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file not in result

    def test_detect_nav_changes_skips_when_full_rebuild(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that nav detection is skipped for full rebuilds."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test
weight: 10
---
"""
        )

        result = trigger._detect_nav_changes({test_file}, needs_full_rebuild=True)
        assert len(result) == 0


class TestVersionScopedBuilds:
    """
    Tests for version-scoped build functionality.

    RFC: rfc-versioned-docs-pipeline-integration (Phase 3)

    """

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        result = MagicMock()
        result.success = True
        result.pages_built = 5
        result.build_time_ms = 100.0
        result.error_message = None
        result.changed_outputs = ()
        executor.submit.return_value = result
        return executor

    def test_init_with_version_scope(self, mock_site: MagicMock, mock_executor: MagicMock) -> None:
        """Test BuildTrigger initialization with version_scope."""
        trigger = BuildTrigger(
            site=mock_site,
            host="localhost",
            port=5173,
            executor=mock_executor,
            version_scope="v2",
        )

        assert trigger.version_scope == "v2"

    def test_init_without_version_scope(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Test BuildTrigger initialization without version_scope."""
        trigger = BuildTrigger(
            site=mock_site,
            host="localhost",
            port=5173,
            executor=mock_executor,
        )

        assert trigger.version_scope is None

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_version_scope_passed_to_build_request(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that version_scope is applied to site config before warm build."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        # mock_site.build() must return a real stats object for warm build
        mock_stats = MagicMock()
        mock_stats.total_pages = 5
        mock_stats.changed_outputs = []
        mock_site.build.return_value = mock_stats

        trigger = BuildTrigger(
            site=mock_site,
            executor=mock_executor,
            version_scope="v2",
        )

        trigger.trigger_build(
            changed_paths={Path("test.md")},
            event_types={"modified"},
        )

        # Warm builds call site.build() directly (not executor.submit)
        mock_site.build.assert_called_once()
        # Version scope is set on site.config before build
        assert mock_site.config["_version_scope"] == "v2"

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_no_version_scope_in_build_request(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that site.config has no _version_scope when not set."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        mock_stats = MagicMock()
        mock_stats.total_pages = 5
        mock_stats.changed_outputs = []
        mock_site.build.return_value = mock_stats

        trigger = BuildTrigger(
            site=mock_site,
            executor=mock_executor,
        )

        trigger.trigger_build(
            changed_paths={Path("test.md")},
            event_types={"modified"},
        )

        mock_site.build.assert_called_once()
        assert "_version_scope" not in mock_site.config


class TestBuildTriggerIntegration:
    """Integration tests for BuildTrigger."""

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        result = MagicMock()
        result.success = True
        result.pages_built = 5
        result.build_time_ms = 100.0
        result.error_message = None
        result.changed_outputs = ()
        executor.submit.return_value = result
        return executor

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_trigger_build_calls_site_build(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that trigger_build calls site.build() directly (warm build)."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        mock_stats = MagicMock()
        mock_stats.total_pages = 5
        mock_stats.changed_outputs = []
        mock_site.build.return_value = mock_stats

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        trigger.trigger_build(
            changed_paths={Path("test.md")},
            event_types={"modified"},
        )

        # Warm builds call site.build() directly
        mock_site.build.assert_called_once()
        build_opts = mock_site.build.call_args[1]["options"]
        assert Path("test.md") in build_opts.changed_sources
        assert build_opts.completion_policy is BuildCompletionPolicy.SERVE_READY


class TestBuildTriggerCaching:
    """Tests for BuildTrigger caching optimizations.

    RFC: rfc-server-package-optimizations

    """

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        return executor

    def test_frontmatter_cache_hit(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that frontmatter parsing is cached by mtime."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a test file with nav frontmatter
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test Page
weight: 10
---

Content here.
"""
        )

        # First call - cache miss
        result1 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result1 is True
        assert test_file in trigger._frontmatter_cache

        # Second call - cache hit (same mtime)
        result2 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result2 is True

    def test_frontmatter_cache_invalidation_on_mtime_change(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that frontmatter cache is invalidated when mtime changes."""
        import os
        import time

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create initial file with nav frontmatter
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test Page
weight: 10
---
"""
        )

        # First call
        result1 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result1 is True

        # Modify file (change content, touch mtime)
        time.sleep(0.01)  # Ensure mtime changes
        test_file.write_text(
            """---
author: Someone
---
"""
        )
        # Force mtime update
        os.utime(test_file, None)

        # Second call - should re-parse due to mtime change
        result2 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result2 is False  # No nav-affecting keys now

    def test_frontmatter_partial_read(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that only first 4KB is read for frontmatter."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a file with frontmatter and lots of content
        large_content = "x" * 100000  # 100KB of content
        test_file = tmp_path / "large.md"
        test_file.write_text(
            f"""---
title: Large File
---

{large_content}
"""
        )

        # Should still detect nav frontmatter without reading entire file
        result = trigger._has_nav_affecting_frontmatter(test_file)
        assert result is True

    def test_template_dirs_cached(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that template directories are cached."""
        mock_site.root_path = tmp_path

        # Create template directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # First call - populates cache
        dirs1 = trigger._get_template_dirs()
        assert templates_dir in dirs1

        # Second call - returns cached
        dirs2 = trigger._get_template_dirs()
        assert dirs1 == dirs2

        # Should be same list object (cached)
        assert dirs1 is dirs2

    def test_template_change_early_exit_non_html(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that template check exits early for non-.html files."""
        mock_site.root_path = tmp_path

        # Create template directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Non-HTML files should not be detected as template changes
        non_html_paths = {
            Path(templates_dir / "style.css"),
            Path(tmp_path / "content" / "post.md"),
        }

        result = trigger._is_template_change(non_html_paths)
        assert result is False

    def test_detect_nav_changes_uses_cache(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _detect_nav_changes uses the frontmatter cache."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test
weight: 5
---
"""
        )

        # First detection
        result1 = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file in result1

        # File should be cached now
        assert test_file in trigger._frontmatter_cache

        # Second detection should use cache
        result2 = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file in result2


class TestBuildTriggerErrorHandling:
    """
    Tests for BuildTrigger error handling.

    BUG FIX: Error handling should not mutate the changed_paths set.
    Previously, using set.pop() would modify the set unexpectedly.
    """

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor that raises an exception."""
        executor = MagicMock()
        executor.submit.side_effect = RuntimeError("Build failed")
        return executor

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.show_error")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.build_trigger.create_dev_error")
    @patch("bengal.server.build_trigger.get_dev_server_state")
    def test_changed_paths_not_mutated_on_error(
        self,
        mock_get_state: MagicMock,
        mock_create_error: MagicMock,
        mock_controller: MagicMock,
        mock_show_error: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """
        Test that changed_paths set is not mutated during error handling.

        BUG FIX: Previously used set.pop() which would modify the set.
        Now uses next(iter(...)) which doesn't modify the set.
        """
        mock_pre_hooks.return_value = True
        mock_state = MagicMock()
        mock_state.record_failure.return_value = True
        mock_get_state.return_value = mock_state
        mock_context = MagicMock()
        mock_context.get_likely_cause.return_value = "test"
        mock_context.quick_actions = []
        mock_context.auto_fixable = False
        mock_context.auto_fix_command = None
        mock_create_error.return_value = mock_context

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a set of changed paths
        original_paths = {Path("a.md"), Path("b.md"), Path("c.md")}
        paths_copy = original_paths.copy()

        # Trigger build which will raise an exception
        trigger.trigger_build(paths_copy, {"modified"})

        # The set should NOT have been modified by the error handler
        # (Previously, pop() would remove an element)
        assert len(paths_copy) == 3
        assert paths_copy == original_paths

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.show_error")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.build_trigger.get_dev_server_state")
    def test_trigger_file_extracted_without_mutation(
        self,
        mock_get_state: MagicMock,
        mock_controller: MagicMock,
        mock_show_error: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that trigger_file is extracted without modifying the set.

        The warm build path calls site.build() directly, so we make that
        raise to exercise the error handler (the executor mock is unused
        because warm builds bypass subprocess execution).
        """
        mock_pre_hooks.return_value = True
        mock_state = MagicMock()
        mock_state.record_failure.return_value = True
        mock_get_state.return_value = mock_state
        # Make site.build() raise so the error handler runs
        mock_site.build.side_effect = RuntimeError("Build failed")

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        paths = {Path("test.md")}
        trigger.trigger_build(paths, {"modified"})

        # Error handler should have been invoked (show_error called)
        mock_show_error.assert_called_once()

        # Set should still have the element (not mutated by error handler)
        assert len(paths) == 1


class TestBuildTriggerQueuing:
    """Tests for BuildTrigger change queuing during builds.

    When a build is in progress, changes should be queued instead of discarded.
    This prevents lost changes during rapid editing (important for autodoc pages).

    """

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        result = MagicMock()
        result.success = True
        result.pages_built = 5
        result.build_time_ms = 100.0
        result.error_message = None
        result.changed_outputs = ()
        executor.submit.return_value = result
        return executor

    def test_pending_changes_initialized_empty(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Test that pending changes are initialized as empty sets."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._pending_changes == set()
        assert trigger._pending_event_types == set()

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_changes_queued_when_build_in_progress(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that changes are queued when a build is in progress."""
        import threading

        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        # Control build timing via site.build (warm builds call it directly)
        build_started = threading.Event()
        build_can_finish = threading.Event()

        def slow_build(*args, **kwargs):
            build_started.set()
            build_can_finish.wait(timeout=5.0)
            stats = MagicMock()
            stats.total_pages = 5
            stats.changed_outputs = []
            return stats

        mock_site.build.side_effect = slow_build

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Start first build in background thread
        first_build = threading.Thread(
            target=trigger.trigger_build,
            args=({Path("first.md")}, {"modified"}),
        )
        first_build.start()

        # Wait for first build to start
        build_started.wait(timeout=5.0)

        # Try to trigger second build while first is in progress
        trigger.trigger_build({Path("second.md")}, {"created"})

        # Changes should be queued
        assert Path("second.md") in trigger._pending_changes
        assert "created" in trigger._pending_event_types

        # Let first build finish
        build_can_finish.set()
        first_build.join(timeout=5.0)

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_queued_changes_trigger_another_build(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that queued changes trigger another build after first completes."""
        import threading

        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        # Track build calls via site.build (warm builds)
        build_call_count = 0
        build_started = threading.Event()
        build_can_finish = threading.Event()

        def tracking_build(*args, **kwargs):
            nonlocal build_call_count
            build_call_count += 1
            if build_call_count == 1:
                build_started.set()
                build_can_finish.wait(timeout=5.0)
            stats = MagicMock()
            stats.total_pages = 5
            stats.changed_outputs = []
            return stats

        mock_site.build.side_effect = tracking_build

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Start first build in background thread
        first_build = threading.Thread(
            target=trigger.trigger_build,
            args=({Path("first.md")}, {"modified"}),
        )
        first_build.start()

        # Wait for first build to start
        build_started.wait(timeout=5.0)

        # Queue a second change
        trigger.trigger_build({Path("second.md")}, {"created"})

        # Let first build finish (which should trigger second build)
        build_can_finish.set()
        first_build.join(timeout=5.0)

        # Should have two builds: first + queued
        assert mock_site.build.call_count == 2

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_multiple_queued_changes_batched(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that multiple queued changes are batched into a single build."""
        import threading

        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        build_call_count = 0
        build_started = threading.Event()
        build_can_finish = threading.Event()

        def tracking_build(*args, **kwargs):
            nonlocal build_call_count
            build_call_count += 1
            if build_call_count == 1:
                build_started.set()
                build_can_finish.wait(timeout=5.0)
            stats = MagicMock()
            stats.total_pages = 5
            stats.changed_outputs = []
            return stats

        mock_site.build.side_effect = tracking_build

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Start first build
        first_build = threading.Thread(
            target=trigger.trigger_build,
            args=({Path("first.md")}, {"modified"}),
        )
        first_build.start()
        build_started.wait(timeout=5.0)

        # Queue multiple changes while first build is running
        trigger.trigger_build({Path("second.md")}, {"created"})
        trigger.trigger_build({Path("third.md")}, {"modified"})
        trigger.trigger_build({Path("fourth.md")}, {"deleted"})

        # All should be queued
        assert len(trigger._pending_changes) == 3
        assert {"created", "modified", "deleted"} == trigger._pending_event_types

        # Let first build finish
        build_can_finish.set()
        first_build.join(timeout=5.0)

        # Should have exactly 2 builds: first + batched queued changes
        assert mock_site.build.call_count == 2

    @patch("bengal.server.build_trigger.time.sleep")
    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_no_stabilization_delay_with_double_buffer(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_sleep: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Double-buffered output eliminates the need for stabilization delays.

        Queued builds execute immediately because the ASGI app serves from the
        active buffer, which is never written to during a build.
        """
        import threading

        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        build_call_count = 0
        build_started = threading.Event()
        build_can_finish = threading.Event()

        def tracking_build(*args, **kwargs):
            nonlocal build_call_count
            build_call_count += 1
            if build_call_count == 1:
                build_started.set()
                build_can_finish.wait(timeout=5.0)
            stats = MagicMock()
            stats.total_pages = 5
            stats.changed_outputs = []
            return stats

        mock_site.build.side_effect = tracking_build

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        first_build = threading.Thread(
            target=trigger.trigger_build,
            args=({Path("first.md")}, {"modified"}),
        )
        first_build.start()
        build_started.wait(timeout=5.0)

        trigger.trigger_build({Path("second.md")}, {"created"})

        build_can_finish.set()
        first_build.join(timeout=5.0)

        assert mock_site.build.call_count == 2
        mock_sleep.assert_not_called()


class TestReloadDecisionFlow:
    """Tests for simplified reload decision flow.

    The reload decision flow uses typed outputs from builds:
    1. Primary: Typed outputs (CSS-only vs full reload)
    2. Fallback: Path-based decision (when types unavailable)
    """

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        return executor

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_typed_outputs_css_only_reload(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that CSS-only outputs trigger CSS-only reload."""
        from bengal.server.reload_controller import ReloadDecision

        mock_controller.decide_from_outputs.return_value = ReloadDecision(
            action="reload-css", reason="css-only", changed_paths=("style.css",)
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # CSS-only outputs
        changed_outputs = (
            SerializedOutputRecord("style.css", "css", "asset"),
            SerializedOutputRecord("theme.css", "css", "asset"),
        )
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("assets/style.css",),
                changed_outputs=changed_outputs,
                reload_hint=None,
            )
        )

        # Should use decide_from_outputs
        mock_controller.decide_from_outputs.assert_called_once()
        mock_send_reload.assert_called_once_with("reload-css", "css-only", ("style.css",))

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_typed_outputs_full_reload(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that HTML outputs trigger full reload."""
        from bengal.server.reload_controller import ReloadDecision

        mock_controller.decide_from_outputs.return_value = ReloadDecision(
            action="reload", reason="content-changed", changed_paths=("index.html",)
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # HTML outputs
        changed_outputs = (
            SerializedOutputRecord("index.html", "html", "render"),
            SerializedOutputRecord("about.html", "html", "render"),
        )
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/index.md",),
                changed_outputs=changed_outputs,
                reload_hint=None,
            )
        )

        mock_controller.decide_from_outputs.assert_called_once()
        mock_send_reload.assert_called_once_with("reload", "content-changed", ("index.html",))

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_no_outputs_but_sources_changed_triggers_reload(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test fallback reload when sources changed but no typed outputs recorded."""
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Sources changed but empty outputs (fallback case)
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/draft.md",),
                changed_outputs=(),
                reload_hint=None,
            )
        )

        # Should trigger full reload via fallback
        mock_send_reload.assert_called_once_with("reload", "source-change-no-outputs", ())

    @patch("bengal.server.build_trigger.default_reload_controller")
    def test_no_outputs_no_sources_suppresses_reload(
        self,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that empty outputs AND empty sources suppress reload."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # No sources, no outputs
        trigger._handle_reload(
            BuildReloadInfo(changed_files=(), changed_outputs=(), reload_hint=None)
        )

        # Should NOT call decide_from_outputs or send reload
        mock_controller.decide_from_outputs.assert_not_called()
        mock_controller.decide_from_changed_paths.assert_not_called()

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_reload_hint_none_with_empty_outputs_still_triggers_fallback_reload(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """When outputs empty, reload_hint must not suppress fallback reload.

        Build now sets reload_hint=None when outputs empty. This test validates
        backward compatibility: if reload_hint='none' is passed with empty outputs
        (legacy path), we still run the fallback so changed_files triggers reload.
        """
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # reload_hint=NONE (from empty outputs) but sources changed
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/contact.md",),
                changed_outputs=(),
                reload_hint=ReloadHint.NONE,
            )
        )

        # Fallback should trigger reload despite reload_hint
        mock_send_reload.assert_called_once_with("reload", "source-change-no-outputs", ())

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_fallback_to_path_based_decision(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test fallback to path-based decision when type reconstruction fails."""
        from bengal.server.reload_controller import ReloadDecision

        mock_controller.decide_from_changed_paths.return_value = ReloadDecision(
            action="reload", reason="content-changed", changed_paths=("index.html",)
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Invalid output type that can't be reconstructed
        changed_outputs = (SerializedOutputRecord("index.html", "invalid_type", "render"),)
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/index.md",),
                changed_outputs=changed_outputs,
                reload_hint=None,
            )
        )

        # Should fall back to decide_from_changed_paths
        mock_controller.decide_from_outputs.assert_not_called()
        mock_controller.decide_from_changed_paths.assert_called_once()

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_reload_hint_none_with_outputs_returns_early(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """When reload_hint='none' and we have typed outputs, suppress reload."""
        from bengal.orchestration.stats import ReloadHint

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/index.md",),
                changed_outputs=(SerializedOutputRecord("index.html", "html", "render"),),
                reload_hint=ReloadHint.NONE,
            )
        )

        mock_send_reload.assert_not_called()

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_content_hash_aggregate_only_suppresses_reload(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """When content-hash says aggregate-only and no source files changed, suppress reload."""
        from bengal.server.reload_controller import EnhancedReloadDecision, ReloadDecision

        mock_controller.decide_from_outputs.return_value = ReloadDecision(
            action="reload", reason="content-changed", changed_paths=("sitemap.xml",)
        )
        mock_controller._use_content_hashes = True
        mock_controller._baseline_content_hashes = {"sitemap.xml": "abc"}
        mock_controller.decide_with_content_hashes.return_value = EnhancedReloadDecision(
            action="reload",
            reason="aggregate-only",
            changed_paths=("sitemap.xml",),
            content_changes=(),
            aggregate_changes=("sitemap.xml",),
            asset_changes=(),
        )

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Empty changed_files: build was triggered by something other than user edit
        # (e.g. timer, cache validation). Content-hash says aggregate-only → suppress.
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=(),
                changed_outputs=(SerializedOutputRecord("sitemap.xml", "html", "postprocess"),),
                reload_hint=None,
            )
        )

        mock_send_reload.assert_not_called()

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_reload_bypass_when_decision_none_but_sources_changed(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """When decision is 'none' (not aggregate-only) but changed_files non-empty, bypass."""
        from bengal.server.reload_controller import ReloadDecision

        mock_controller.decide_from_outputs.return_value = ReloadDecision(
            action="none", reason="throttled", changed_paths=()
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/contact.md",),
                changed_outputs=(SerializedOutputRecord("index.html", "html", "render"),),
                reload_hint=None,
            )
        )

        mock_send_reload.assert_called_once_with("reload", "source-changes-bypass", ())

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_fallback_source_change_skips_content_hash_filtering(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Fallback-source-change must not run content-hash filtering (always reload)."""
        mock_controller._use_content_hashes = True
        mock_controller._baseline_content_hashes = {"x": "y"}

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Empty outputs, sources changed → fallback-source-change
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/contact.md",),
                changed_outputs=(),
                reload_hint=None,
            )
        )

        # Should trigger reload despite content-hash being enabled
        mock_send_reload.assert_called_once_with("reload", "source-change-no-outputs", ())
        mock_controller.decide_with_content_hashes.assert_not_called()


class TestBuildStabilizationTiming:
    """Tests for build stabilization timing behavior."""

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.content_dir = Path("/test/site/content")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        result = MagicMock()
        result.success = True
        result.pages_built = 5
        result.build_time_ms = 100.0
        result.error_message = None
        result.changed_outputs = ()
        executor.submit.return_value = result
        return executor

    @patch("bengal.server.build_trigger.time.sleep")
    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_no_delay_for_first_build(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_sleep: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that no stabilization delay is applied for the first build.

        The delay only applies when triggering a queued build after
        another build completes.
        """
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True
        mock_controller.decide_from_changed_paths.return_value = MagicMock(
            action="reload", reason="test", changed_paths=()
        )

        sleep_calls = []

        def instant_submit(request, **kwargs):
            result = MagicMock()
            result.success = True
            result.pages_built = 5
            result.build_time_ms = 100.0
            result.error_message = None
            result.changed_outputs = ()
            return result

        def tracking_sleep(seconds):
            sleep_calls.append(seconds)

        mock_executor.submit.side_effect = instant_submit
        mock_sleep.side_effect = tracking_sleep

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Single build (no queued changes)
        trigger.trigger_build({Path("only.md")}, {"modified"})

        # No stabilization delay should have been called
        # (we only delay when processing queued changes)
        assert 0.1 not in sleep_calls, f"Unexpected delay for first build: {sleep_calls}"
