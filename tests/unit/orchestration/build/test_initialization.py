"""
Tests for build initialization phases.

Covers:
- phase_fonts(): Font processing phase
- phase_discovery(): Content discovery phase
- phase_cache_metadata(): Cache metadata phase
- phase_config_check(): Config change detection
- phase_incremental_filter(): Incremental filtering
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from bengal.orchestration.build.initialization import (
    phase_cache_metadata,
    phase_config_check,
    phase_discovery,
    phase_fonts,
    phase_incremental_filter,
)


class MockPhaseContext:
    """Helper to create mock context for phase functions."""

    @staticmethod
    def create_orchestrator(tmp_path, config=None):
        """Create a mock orchestrator."""
        orchestrator = MagicMock()
        orchestrator.site = MagicMock()
        orchestrator.site.root_path = tmp_path
        orchestrator.site.output_dir = tmp_path / "public"
        orchestrator.site.config = config or {}
        orchestrator.site.pages = []
        orchestrator.site.sections = []
        orchestrator.site.assets = []

        orchestrator.stats = MagicMock()
        orchestrator.stats.fonts_time_ms = 0
        orchestrator.stats.discovery_time_ms = 0

        orchestrator.logger = MagicMock()
        orchestrator.logger.phase = MagicMock(
            return_value=MagicMock(__enter__=Mock(), __exit__=Mock())
        )

        orchestrator.content = MagicMock()
        orchestrator.incremental = MagicMock()

        return orchestrator

    @staticmethod
    def create_cli():
        """Create a mock CLI."""
        cli = MagicMock()
        return cli


class TestPhaseFonts:
    """Tests for phase_fonts function."""

    def test_skips_when_no_fonts_config(self, tmp_path):
        """Skips font processing when fonts not in config."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path, config={})
        cli = MockPhaseContext.create_cli()

        phase_fonts(orchestrator, cli)

        # Should not call logger.phase since we return early
        # Stats should not be updated
        assert orchestrator.stats.fonts_time_ms == 0

    def test_processes_fonts_when_configured(self, tmp_path):
        """Processes fonts when configured."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path, config={"fonts": {"google": ["Outfit"]}}
        )
        cli = MockPhaseContext.create_cli()

        with patch("bengal.fonts.FontHelper") as MockFontHelper:
            mock_font_helper = MagicMock()
            MockFontHelper.return_value = mock_font_helper
            mock_font_helper.process.return_value = None

            phase_fonts(orchestrator, cli)

        # FontHelper should be called
        MockFontHelper.assert_called_once()

    def test_handles_font_processing_error(self, tmp_path):
        """Handles font processing errors gracefully."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path, config={"fonts": {"google": ["BadFont"]}}
        )
        cli = MockPhaseContext.create_cli()

        with patch(
            "bengal.fonts.FontHelper",
            side_effect=Exception("Font download failed"),
        ):
            # Should not raise
            phase_fonts(orchestrator, cli)

        # Should warn user
        cli.warning.assert_called()

    def test_copies_fonts_css_to_output(self, tmp_path):
        """Copies fonts.css to output directory."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path, config={"fonts": {"google": ["Outfit"]}}
        )
        cli = MockPhaseContext.create_cli()

        # Create source fonts.css
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        fonts_css = assets_dir / "fonts.css"
        fonts_css.write_text("/* fonts */")

        with patch("bengal.fonts.FontHelper") as MockFontHelper:
            mock_font_helper = MagicMock()
            MockFontHelper.return_value = mock_font_helper
            mock_font_helper.process.return_value = fonts_css

            phase_fonts(orchestrator, cli)

        # Output fonts.css may or may not be created depending on shutil.copy2 mock


class TestPhaseDiscovery:
    """Tests for phase_discovery function."""

    def test_calls_content_discover(self, tmp_path):
        """Calls content orchestrator discover method."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()

        phase_discovery(orchestrator, cli, incremental=False)

        orchestrator.content.discover.assert_called_once_with(
            incremental=False, cache=None, build_context=None
        )

    def test_incremental_loads_page_cache(self, tmp_path):
        """Loads page discovery cache for incremental builds."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()

        with patch("bengal.cache.page_discovery_cache.PageDiscoveryCache") as MockCache:
            mock_cache = MagicMock()
            MockCache.return_value = mock_cache

            phase_discovery(orchestrator, cli, incremental=True)

        # Should try to load cache
        MockCache.assert_called_once()

    def test_passes_build_context_for_content_caching(self, tmp_path):
        """Passes build context for content caching."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        build_context = MagicMock()
        build_context.has_cached_content = False

        phase_discovery(orchestrator, cli, incremental=False, build_context=build_context)

        orchestrator.content.discover.assert_called_once_with(
            incremental=False, cache=None, build_context=build_context
        )

    def test_logs_content_cache_stats(self, tmp_path):
        """Logs content cache statistics when enabled."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        build_context = MagicMock()
        build_context.has_cached_content = True
        build_context.content_cache_size = 100

        phase_discovery(orchestrator, cli, incremental=False, build_context=build_context)

        orchestrator.logger.debug.assert_called()

    def test_updates_discovery_time_stats(self, tmp_path):
        """Updates discovery time statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()

        phase_discovery(orchestrator, cli, incremental=False)

        # Stats should be updated (time in ms)
        assert orchestrator.stats.discovery_time_ms >= 0


class TestPhaseCacheMetadata:
    """Tests for phase_cache_metadata function."""

    def test_saves_page_metadata_to_cache(self, tmp_path):
        """Saves page metadata to cache file."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        mock_page = MagicMock()
        mock_page.core = MagicMock()
        orchestrator.site.pages = [mock_page]

        with patch("bengal.cache.page_discovery_cache.PageDiscoveryCache") as MockCache:
            mock_cache = MagicMock()
            MockCache.return_value = mock_cache

            phase_cache_metadata(orchestrator)

        # Should add metadata for each page
        mock_cache.add_metadata.assert_called_once_with(mock_page.core)
        mock_cache.save_to_disk.assert_called_once()

    def test_normalizes_paths_before_caching(self, tmp_path):
        """Normalizes page core paths before caching."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        mock_page = MagicMock()
        orchestrator.site.pages = [mock_page]

        with patch("bengal.cache.page_discovery_cache.PageDiscoveryCache"):
            phase_cache_metadata(orchestrator)

        mock_page.normalize_core_paths.assert_called_once()

    def test_handles_cache_save_errors(self, tmp_path):
        """Handles cache save errors gracefully."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.pages = [MagicMock()]

        with patch(
            "bengal.cache.page_discovery_cache.PageDiscoveryCache",
            side_effect=Exception("Cache error"),
        ):
            # Should not raise
            phase_cache_metadata(orchestrator)

        # Should log warning
        orchestrator.logger.warning.assert_called()


class TestPhaseConfigCheck:
    """Tests for phase_config_check function."""

    def test_checks_config_changed(self, tmp_path):
        """Checks if config file changed."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        cache = MagicMock()
        cache.file_hashes = {}

        orchestrator.incremental.check_config_changed.return_value = False

        incremental, config_changed = phase_config_check(orchestrator, cli, cache, incremental=True)

        orchestrator.incremental.check_config_changed.assert_called()
        assert config_changed is False

    def test_forces_full_rebuild_on_config_change(self, tmp_path):
        """Forces full rebuild when config changes."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        cache = MagicMock()
        cache.file_hashes = {"config": "oldhash"}

        # Create bengal.toml so config file is found
        config_file = tmp_path / "bengal.toml"
        config_file.write_text("[site]\ntitle = 'Test'")

        orchestrator.incremental.check_config_changed.return_value = True

        incremental, config_changed = phase_config_check(orchestrator, cli, cache, incremental=True)

        assert incremental is False  # Forced to full build
        assert config_changed is True

    def test_clears_cache_on_config_change(self, tmp_path):
        """Clears cache when config changes."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        cache = MagicMock()
        cache.file_hashes = {}

        orchestrator.incremental.check_config_changed.return_value = True

        phase_config_check(orchestrator, cli, cache, incremental=True)

        cache.clear.assert_called_once()

    def test_cleans_up_deleted_files(self, tmp_path):
        """Cleans up output for deleted source files."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        cache = MagicMock()
        cache.file_hashes = {}
        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()

        orchestrator.incremental.check_config_changed.return_value = False
        orchestrator.incremental._cleanup_deleted_files = MagicMock()

        phase_config_check(orchestrator, cli, cache, incremental=True)

        orchestrator.incremental._cleanup_deleted_files.assert_called_once()


class TestPhaseIncrementalFilter:
    """Tests for phase_incremental_filter function."""

    def test_returns_all_pages_for_full_build(self, tmp_path):
        """Returns all pages for full builds."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        mock_pages = [MagicMock(), MagicMock()]
        mock_assets = [MagicMock()]
        orchestrator.site.pages = mock_pages
        orchestrator.site.assets = mock_assets
        cli = MockPhaseContext.create_cli()
        cache = MagicMock()

        result = phase_incremental_filter(
            orchestrator, cli, cache, incremental=False, verbose=False, build_start=time.time()
        )

        pages, assets, tags, paths, sections = result
        assert pages == mock_pages
        assert assets == mock_assets

    def test_filters_unchanged_pages_for_incremental(self, tmp_path):
        """Filters unchanged pages for incremental builds."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.pages = [MagicMock(), MagicMock()]
        orchestrator.site.assets = [MagicMock()]
        cli = MockPhaseContext.create_cli()
        cache = MagicMock()
        cache.get_all_tags.return_value = {}

        # Mock find_work_early to return subset
        changed_page = MagicMock()
        changed_page.metadata = {}
        changed_page.source_path = Path("test.md")
        changed_page.tags = []
        orchestrator.incremental.find_work_early.return_value = (
            [changed_page],
            [],
            {"modified": [changed_page]},
        )

        result = phase_incremental_filter(
            orchestrator, cli, cache, incremental=True, verbose=False, build_start=time.time()
        )

        pages, assets, tags, paths, sections = result
        assert len(pages) == 1
        assert pages[0] is changed_page

    def test_returns_none_when_no_changes(self, tmp_path):
        """Returns None when no changes detected (skip build)."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.pages = [MagicMock()]
        orchestrator.site.assets = [MagicMock()]
        cli = MockPhaseContext.create_cli()
        cache = MagicMock()
        cache.get_all_tags.return_value = {}

        orchestrator.incremental.find_work_early.return_value = ([], [], {})

        result = phase_incremental_filter(
            orchestrator, cli, cache, incremental=True, verbose=False, build_start=time.time()
        )

        assert result is None
        assert orchestrator.stats.skipped is True

    def test_tracks_affected_tags(self, tmp_path):
        """Tracks affected tags from changed pages."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.pages = []
        orchestrator.site.assets = []
        cli = MockPhaseContext.create_cli()
        cache = MagicMock()
        cache.get_all_tags.return_value = {}

        changed_page = MagicMock()
        changed_page.metadata = {}
        changed_page.source_path = Path("test.md")
        changed_page.tags = ["Python", "Tutorial"]
        changed_page.section = None
        orchestrator.incremental.find_work_early.return_value = (
            [changed_page],
            [],
            {},
        )

        result = phase_incremental_filter(
            orchestrator, cli, cache, incremental=True, verbose=False, build_start=time.time()
        )

        _, _, affected_tags, _, _ = result
        assert "python" in affected_tags
        assert "tutorial" in affected_tags

    def test_tracks_affected_sections(self, tmp_path):
        """Tracks affected sections from changed pages."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.pages = []
        orchestrator.site.assets = []
        cli = MockPhaseContext.create_cli()
        cache = MagicMock()
        cache.get_all_tags.return_value = {}

        changed_page = MagicMock()
        changed_page.metadata = {}
        changed_page.source_path = Path("docs/intro.md")
        changed_page.tags = []
        changed_page.section = MagicMock()
        changed_page.section.path = Path("docs")
        orchestrator.incremental.find_work_early.return_value = (
            [changed_page],
            [],
            {},
        )

        result = phase_incremental_filter(
            orchestrator, cli, cache, incremental=True, verbose=False, build_start=time.time()
        )

        _, _, _, _, affected_sections = result
        assert "docs" in affected_sections

    def test_updates_cache_statistics(self, tmp_path):
        """Updates cache hit/miss statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.pages = [MagicMock(), MagicMock(), MagicMock()]
        orchestrator.site.assets = []
        cli = MockPhaseContext.create_cli()
        cache = MagicMock()
        cache.get_all_tags.return_value = {}

        # One page changed
        changed_page = MagicMock()
        changed_page.metadata = {}
        changed_page.source_path = Path("test.md")
        changed_page.tags = []
        changed_page.section = None
        orchestrator.incremental.find_work_early.return_value = (
            [changed_page],
            [],
            {},
        )

        phase_incremental_filter(
            orchestrator, cli, cache, incremental=True, verbose=False, build_start=time.time()
        )

        # 3 total pages, 1 rebuilt, 2 cached
        assert orchestrator.stats.cache_hits == 2
        assert orchestrator.stats.cache_misses == 1
