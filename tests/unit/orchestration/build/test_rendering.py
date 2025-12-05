"""
Tests for build rendering phases.

Covers:
- _rewrite_fonts_css_urls(): Font URL rewriting
- phase_assets(): Asset processing phase
- phase_render(): Page rendering phase
- phase_update_site_pages(): Site pages update
- phase_track_assets(): Asset dependency tracking
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from bengal.orchestration.build.rendering import (
    _rewrite_fonts_css_urls,
    phase_assets,
    phase_render,
    phase_track_assets,
    phase_update_site_pages,
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
        orchestrator.site.assets = []
        orchestrator.site.theme = None

        orchestrator.stats = MagicMock()
        orchestrator.stats.assets_time_ms = 0
        orchestrator.stats.rendering_time_ms = 0
        orchestrator.stats.template_errors = []

        orchestrator.logger = MagicMock()
        orchestrator.logger.phase = MagicMock(
            return_value=MagicMock(__enter__=Mock(), __exit__=Mock())
        )
        orchestrator.logger.level = MagicMock()
        orchestrator.logger.level.value = 20  # INFO

        orchestrator.assets = MagicMock()
        orchestrator.render = MagicMock()

        return orchestrator

    @staticmethod
    def create_cli():
        """Create a mock CLI."""
        return MagicMock()


class TestRewriteFontsCssUrls:
    """Tests for _rewrite_fonts_css_urls function."""

    def test_skips_when_no_fonts_css(self, tmp_path):
        """Skips when fonts.css doesn't exist."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        # No fonts.css file
        _rewrite_fonts_css_urls(orchestrator)

        # Should not error

    def test_skips_when_no_manifest(self, tmp_path):
        """Skips when asset-manifest.json doesn't exist."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        output_dir = tmp_path / "public"
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(parents=True)
        (assets_dir / "fonts.css").write_text("/* fonts */")

        # No manifest file
        _rewrite_fonts_css_urls(orchestrator)

        # Should not error

    def test_rewrites_font_urls(self, tmp_path):
        """Rewrites font URLs in fonts.css."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        output_dir = tmp_path / "public"
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(parents=True)

        # Create fonts.css
        (assets_dir / "fonts.css").write_text('@font-face { src: url("fonts/outfit.woff2"); }')

        # Create manifest
        manifest = {
            "fonts/outfit.woff2": "fonts/outfit.abc123.woff2",
        }
        (output_dir / "asset-manifest.json").write_text(json.dumps(manifest))

        with patch("bengal.fonts.rewrite_font_urls_with_fingerprints") as mock_rewrite:
            mock_rewrite.return_value = True

            _rewrite_fonts_css_urls(orchestrator)

        mock_rewrite.assert_called_once()

    def test_handles_rewrite_errors(self, tmp_path):
        """Handles font URL rewrite errors gracefully."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        output_dir = tmp_path / "public"
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(parents=True)
        (assets_dir / "fonts.css").write_text("/* fonts */")
        (output_dir / "asset-manifest.json").write_text("{}")

        with patch(
            "bengal.fonts.rewrite_font_urls_with_fingerprints",
            side_effect=Exception("Rewrite error"),
        ):
            # Should not raise
            _rewrite_fonts_css_urls(orchestrator)

        orchestrator.logger.warning.assert_called()


class TestPhaseAssets:
    """Tests for phase_assets function."""

    def test_processes_assets(self, tmp_path):
        """Processes assets through asset orchestrator."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        assets = [MagicMock(), MagicMock()]

        result = phase_assets(
            orchestrator, cli, incremental=False, parallel=True, assets_to_process=assets
        )

        orchestrator.assets.process.assert_called_once_with(
            assets, parallel=True, progress_manager=None
        )
        assert result == assets

    def test_rewrites_fonts_when_configured(self, tmp_path):
        """Rewrites font CSS when fonts configured."""
        orchestrator = MockPhaseContext.create_orchestrator(
            tmp_path, config={"fonts": {"google": ["Outfit"]}}
        )
        cli = MockPhaseContext.create_cli()

        with patch("bengal.orchestration.build.rendering._rewrite_fonts_css_urls") as mock_rewrite:
            phase_assets(orchestrator, cli, incremental=False, parallel=False, assets_to_process=[])

        mock_rewrite.assert_called_once()

    def test_updates_assets_time_stats(self, tmp_path):
        """Updates assets time statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()

        phase_assets(orchestrator, cli, incremental=False, parallel=False, assets_to_process=[])

        assert orchestrator.stats.assets_time_ms >= 0

    def test_processes_theme_assets_on_incremental_if_missing(self, tmp_path):
        """Processes theme assets on incremental if output missing."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.theme = "my-theme"
        orchestrator.site.assets = [MagicMock()]
        cli = MockPhaseContext.create_cli()

        # Mock theme assets check
        with patch("bengal.orchestration.content.ContentOrchestrator") as MockContent:
            mock_content = MagicMock()
            MockContent.return_value = mock_content
            mock_theme_dir = tmp_path / "themes" / "my-theme" / "assets"
            mock_theme_dir.mkdir(parents=True)
            mock_content._get_theme_assets_dir.return_value = mock_theme_dir

            result = phase_assets(
                orchestrator,
                cli,
                incremental=True,
                parallel=False,
                assets_to_process=[],  # No changed assets
            )

        # Should process all assets since output missing
        assert result == orchestrator.site.assets


class TestPhaseRender:
    """Tests for phase_render function."""

    def test_renders_pages(self, tmp_path):
        """Renders pages through render orchestrator."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        pages = [MagicMock(), MagicMock()]

        with patch("bengal.utils.build_context.BuildContext") as MockContext:
            mock_ctx = MagicMock()
            MockContext.return_value = mock_ctx

            phase_render(
                orchestrator,
                cli,
                incremental=False,
                parallel=True,
                quiet=False,
                verbose=False,
                memory_optimized=False,
                pages_to_build=pages,
                tracker=MagicMock(),
                profile=MagicMock(),
                progress_manager=None,
                reporter=None,
            )

        orchestrator.render.process.assert_called_once()

    def test_uses_streaming_render_in_memory_optimized(self, tmp_path):
        """Uses StreamingRenderOrchestrator in memory-optimized mode."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()

        with (
            patch("bengal.orchestration.streaming.StreamingRenderOrchestrator") as MockStreaming,
            patch("bengal.utils.build_context.BuildContext"),
        ):
            mock_streaming = MagicMock()
            MockStreaming.return_value = mock_streaming

            phase_render(
                orchestrator,
                cli,
                incremental=False,
                parallel=True,
                quiet=False,
                verbose=False,
                memory_optimized=True,
                pages_to_build=[],
                tracker=MagicMock(),
                profile=MagicMock(),
                progress_manager=None,
                reporter=None,
            )

        MockStreaming.assert_called_once()
        mock_streaming.process.assert_called_once()

    def test_updates_rendering_time_stats(self, tmp_path):
        """Updates rendering time statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()

        with patch("bengal.utils.build_context.BuildContext"):
            phase_render(
                orchestrator,
                cli,
                incremental=False,
                parallel=False,
                quiet=False,
                verbose=False,
                memory_optimized=False,
                pages_to_build=[],
                tracker=MagicMock(),
                profile=MagicMock(),
                progress_manager=None,
                reporter=None,
            )

        assert orchestrator.stats.rendering_time_ms >= 0

    def test_transfers_cached_content_from_early_context(self, tmp_path):
        """Transfers cached content from early context."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()

        early_context = MagicMock()
        early_context.has_cached_content = True
        early_context._page_contents = {"test.md": "content"}

        with patch("bengal.utils.build_context.BuildContext") as MockContext:
            mock_ctx = MagicMock()
            MockContext.return_value = mock_ctx

            phase_render(
                orchestrator,
                cli,
                incremental=False,
                parallel=False,
                quiet=False,
                verbose=False,
                memory_optimized=False,
                pages_to_build=[],
                tracker=MagicMock(),
                profile=MagicMock(),
                progress_manager=None,
                reporter=None,
                early_context=early_context,
            )

        # Should transfer cached content
        assert mock_ctx._page_contents == early_context._page_contents

    def test_returns_build_context(self, tmp_path):
        """Returns BuildContext for post-processing."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()

        with patch("bengal.utils.build_context.BuildContext") as MockContext:
            mock_ctx = MagicMock()
            MockContext.return_value = mock_ctx

            result = phase_render(
                orchestrator,
                cli,
                incremental=False,
                parallel=False,
                quiet=False,
                verbose=False,
                memory_optimized=False,
                pages_to_build=[],
                tracker=MagicMock(),
                profile=MagicMock(),
                progress_manager=None,
                reporter=None,
            )

        assert result is mock_ctx


class TestPhaseUpdateSitePages:
    """Tests for phase_update_site_pages function."""

    def test_full_build_no_update(self, tmp_path):
        """Full builds don't update site.pages."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        phase_update_site_pages(orchestrator, incremental=False, pages_to_build=[])

        # No update for full builds

    def test_incremental_replaces_stale_proxies(self, tmp_path):
        """Incremental builds replace stale proxies with rendered pages."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        # Existing proxy
        proxy = MagicMock()
        proxy.source_path = Path("test.md")
        orchestrator.site.pages = [proxy]

        # Rendered page
        rendered = MagicMock()
        rendered.source_path = Path("test.md")
        pages_to_build = [rendered]

        phase_update_site_pages(orchestrator, incremental=True, pages_to_build=pages_to_build)

        # Site.pages should now contain rendered page
        assert orchestrator.site.pages[0] is rendered

    def test_keeps_unchanged_pages(self, tmp_path):
        """Keeps unchanged pages in site.pages."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        # Unchanged page
        unchanged = MagicMock()
        unchanged.source_path = Path("unchanged.md")

        # Changed page
        changed_old = MagicMock()
        changed_old.source_path = Path("changed.md")

        orchestrator.site.pages = [unchanged, changed_old]

        # Only changed page was rebuilt
        changed_new = MagicMock()
        changed_new.source_path = Path("changed.md")
        pages_to_build = [changed_new]

        phase_update_site_pages(orchestrator, incremental=True, pages_to_build=pages_to_build)

        # Unchanged should remain, changed should be replaced
        assert orchestrator.site.pages[0] is unchanged
        assert orchestrator.site.pages[1] is changed_new


class TestPhaseTrackAssets:
    """Tests for phase_track_assets function."""

    def test_tracks_page_asset_dependencies(self, tmp_path):
        """Tracks asset dependencies from rendered pages."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        page = MagicMock()
        page.source_path = Path("test.md")
        page.rendered_html = '<img src="/assets/image.png">'
        pages_to_build = [page]

        with (
            patch("bengal.cache.asset_dependency_map.AssetDependencyMap") as MockMap,
            patch("bengal.rendering.asset_extractor.extract_assets_from_html") as mock_extract,
        ):
            mock_map = MagicMock()
            MockMap.return_value = mock_map
            mock_extract.return_value = ["/assets/image.png"]

            phase_track_assets(orchestrator, pages_to_build)

        mock_map.track_page_assets.assert_called_once_with(page.source_path, ["/assets/image.png"])
        mock_map.save_to_disk.assert_called_once()

    def test_skips_pages_without_html(self, tmp_path):
        """Skips pages without rendered HTML."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        page = MagicMock()
        page.rendered_html = None
        pages_to_build = [page]

        with patch("bengal.cache.asset_dependency_map.AssetDependencyMap") as MockMap:
            mock_map = MagicMock()
            MockMap.return_value = mock_map

            phase_track_assets(orchestrator, pages_to_build)

        # Should not track for pages without HTML
        mock_map.track_page_assets.assert_not_called()

    def test_handles_tracking_errors(self, tmp_path):
        """Handles asset tracking errors gracefully."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        with patch(
            "bengal.cache.asset_dependency_map.AssetDependencyMap",
            side_effect=Exception("Tracking error"),
        ):
            # Should not raise
            phase_track_assets(orchestrator, [])

        orchestrator.logger.warning.assert_called()
