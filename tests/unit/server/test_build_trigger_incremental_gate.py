"""Tests for BuildTrigger incremental gate."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.cache import BuildCache
from bengal.server.build_trigger import BuildTrigger


class TestBuildTriggerIncrementalGate:
    """Incremental vs full rebuild gate, including template dependents."""

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

        with patch("bengal.server.build_trigger.incremental_gate.SiteLike", object):
            assert trigger._should_regenerate_autodoc({schema_path}) is True

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

    @patch("bengal.server.build_trigger.incremental_gate.logger")
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

    def test_parent_theme_template_change_without_dependency_data_is_detected(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Dev-server template change checks use the active theme chain."""
        mock_site.root_path = tmp_path
        mock_site.theme = "child"

        themes_dir = tmp_path / "themes"
        parent_templates = themes_dir / "parent" / "templates"
        parent_templates.mkdir(parents=True)
        (themes_dir / "parent" / "theme.toml").write_text('name = "parent"\n')
        template_file = parent_templates / "base.html"
        template_file.write_text("<html></html>")

        child_templates = themes_dir / "child" / "templates"
        child_templates.mkdir(parents=True)
        (themes_dir / "child" / "theme.toml").write_text('name = "child"\nextends = "parent"\n')
        mock_site._cache = BuildCache(site_root=tmp_path)

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._is_template_change({template_file}) is True

    @patch("bengal.server.build_trigger.incremental_gate.logger")
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


class TestBuildTriggerTemplateCache:
    """Template directory cache and early-exit for non-HTML."""

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


def _build_trigger_events():
    from bengal.utils.observability.logger import _loggers

    name = "bengal.server.build_trigger"
    if name in _loggers:
        return _loggers[name].get_events()
    return []


class TestTemplateCacheLoadDiagnostics:
    """A BuildCache.load() failure during template-change detection must be logged (issue #472)."""

    def test_cache_load_failure_emits_diagnostic(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """When BuildCache.load() raises, the swallow must emit a debug breadcrumb, not vanish."""
        from types import SimpleNamespace

        from bengal.utils.observability.logger import (
            LogLevel,
            configure_logging,
            reset_loggers,
        )

        reset_loggers()
        configure_logging(level=LogLevel.DEBUG)

        # A build-cache file that exists so the load() path is taken.
        cache_path = tmp_path / "cache.json"
        cache_path.write_text("{}", encoding="utf-8")

        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Bare BuildTrigger to avoid heavy __init__.
        trigger = BuildTrigger.__new__(BuildTrigger)
        trigger.site = SimpleNamespace(
            _cache=None,
            root_path=tmp_path,
            config_service=SimpleNamespace(paths=SimpleNamespace(build_cache=cache_path)),
        )
        trigger._template_dirs = [template_dir]

        boom = OSError("synthetic cache corruption " + "y" * 200)

        def fail_load(*args, **kwargs):
            raise boom

        monkeypatch.setattr(
            "bengal.cache.BuildCache.load",
            staticmethod(fail_load),
        )

        try:
            # The changed template lives OUTSIDE the template dir so the
            # post-cache loop is a no-op; we only exercise the load() swallow.
            changed = {tmp_path / "elsewhere" / "page.html"}

            # Must not raise -- the swallow keeps the dev server alive.
            result = trigger._is_template_change(changed)
            assert result is False

            events = _build_trigger_events()
            matches = [e for e in events if e.message == "template_cache_load_failed"]
            assert matches, (
                "expected a 'template_cache_load_failed' diagnostic; "
                f"got {[e.message for e in events]}"
            )
            ev = matches[0]
            assert str(boom) in str(ev.context.get("error"))
            assert ev.context.get("error_type") == "OSError"
        finally:
            reset_loggers()
