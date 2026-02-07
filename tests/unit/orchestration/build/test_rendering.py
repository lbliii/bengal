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
    _is_css_output_missing,
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


class TestIsCssOutputMissing:
    """Tests for _is_css_output_missing helper function.

    This helper validates CSS entry points exist in output before skipping
    asset processing during incremental builds. See Issue #130.
    """

    def test_returns_true_when_assets_dir_missing(self, tmp_path):
        """Returns True when output/assets/ directory doesn't exist."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        # Don't create output directory

        assert _is_css_output_missing(orchestrator) is True

    def test_returns_true_when_css_dir_missing(self, tmp_path):
        """Returns True when output/assets/css/ directory doesn't exist."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        output_assets = tmp_path / "public" / "assets"
        output_assets.mkdir(parents=True)
        # Don't create css subdirectory

        assert _is_css_output_missing(orchestrator) is True

    def test_returns_true_when_no_style_css(self, tmp_path):
        """Returns True when no style*.css files exist."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        css_dir = tmp_path / "public" / "assets" / "css"
        css_dir.mkdir(parents=True)
        # Create other CSS files but not style.css
        (css_dir / "fonts.css").write_text("/* fonts */")
        (css_dir / "print.css").write_text("/* print */")

        assert _is_css_output_missing(orchestrator) is True

    def test_returns_false_when_style_css_exists(self, tmp_path):
        """Returns False when style.css exists."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        css_dir = tmp_path / "public" / "assets" / "css"
        css_dir.mkdir(parents=True)
        (css_dir / "style.css").write_text("/* styles */")

        assert _is_css_output_missing(orchestrator) is False

    def test_returns_false_when_fingerprinted_style_exists(self, tmp_path):
        """Returns False when fingerprinted style.{hash}.css exists."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        css_dir = tmp_path / "public" / "assets" / "css"
        css_dir.mkdir(parents=True)
        (css_dir / "style.abc12345.css").write_text("/* fingerprinted */")

        assert _is_css_output_missing(orchestrator) is False

    def test_returns_false_with_multiple_style_files(self, tmp_path):
        """Returns False when multiple style CSS files exist."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        css_dir = tmp_path / "public" / "assets" / "css"
        css_dir.mkdir(parents=True)
        (css_dir / "style.css").write_text("/* original */")
        (css_dir / "style.abc12345.css").write_text("/* fingerprinted */")

        assert _is_css_output_missing(orchestrator) is False

    def test_ignores_non_style_css_files(self, tmp_path):
        """Ignores CSS files that don't match style*.css pattern."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        css_dir = tmp_path / "public" / "assets" / "css"
        css_dir.mkdir(parents=True)
        # Create various CSS files but not style.css
        (css_dir / "mystyle.css").write_text("/* not a match */")
        (css_dir / "custom-style.css").write_text("/* not a match */")
        (css_dir / "main.css").write_text("/* not a match */")

        assert _is_css_output_missing(orchestrator) is True


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
            assets, parallel=True, progress_manager=None, collector=None
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

    def test_processes_all_assets_on_incremental_if_css_missing(self, tmp_path):
        """Processes all assets on incremental build if CSS output is missing.

        This is a safety net that handles race conditions where output is
        corrupted after provenance filtering. The check is unified for both
        themed and non-themed sites - site.assets is the source of truth.
        """
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.assets = [MagicMock(), MagicMock()]
        cli = MockPhaseContext.create_cli()

        # CSS output is missing (no public/assets/css/style*.css)
        # Don't create the CSS directory - this triggers the safety net

        result = phase_assets(
            orchestrator,
            cli,
            incremental=True,
            parallel=False,
            assets_to_process=[],  # No changed assets
        )

        # Should process all assets since CSS output is missing
        assert result == orchestrator.site.assets

    def test_processes_all_assets_for_themed_site_if_css_missing(self, tmp_path):
        """Themed sites also get all assets processed when CSS missing.

        The safety net behavior is unified - no special handling for themes.
        Theme assets are included in site.assets during content discovery.
        """
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.theme = "my-theme"
        orchestrator.site.assets = [MagicMock(), MagicMock(), MagicMock()]
        cli = MockPhaseContext.create_cli()

        # CSS output is missing
        # Don't create the CSS directory - this triggers the safety net

        result = phase_assets(
            orchestrator,
            cli,
            incremental=True,
            parallel=False,
            assets_to_process=[],  # No changed assets
        )

        # Should process all assets (theme assets are already in site.assets)
        assert result == orchestrator.site.assets

    def test_skips_safety_net_when_css_exists(self, tmp_path):
        """Safety net doesn't trigger when CSS output exists."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.assets = [MagicMock()]
        cli = MockPhaseContext.create_cli()

        # Create CSS output so safety net doesn't trigger
        css_dir = tmp_path / "public" / "assets" / "css"
        css_dir.mkdir(parents=True)
        (css_dir / "style.css").write_text("/* styles */")

        result = phase_assets(
            orchestrator,
            cli,
            incremental=True,
            parallel=False,
            assets_to_process=[],  # No changed assets
        )

        # Should NOT process assets - CSS exists, no safety net needed
        assert result == []


class TestPhaseRender:
    """Tests for phase_render function."""

    def test_renders_pages(self, tmp_path):
        """Renders pages through render orchestrator."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        pages = [MagicMock(), MagicMock()]

        with patch("bengal.orchestration.build_context.BuildContext") as MockContext:
            mock_ctx = MagicMock()
            MockContext.return_value = mock_ctx

            phase_render(
                orchestrator,
                cli,
                incremental=False,
                force_sequential=False,
                quiet=False,
                verbose=False,
                memory_optimized=False,
                pages_to_build=pages,
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
            patch("bengal.orchestration.build_context.BuildContext"),
        ):
            mock_streaming = MagicMock()
            MockStreaming.return_value = mock_streaming

            phase_render(
                orchestrator,
                cli,
                incremental=False,
                force_sequential=False,
                quiet=False,
                verbose=False,
                memory_optimized=True,
                pages_to_build=[],
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

        with patch("bengal.orchestration.build_context.BuildContext"):
            phase_render(
                orchestrator,
                cli,
                incremental=False,
                force_sequential=True,
                quiet=False,
                verbose=False,
                memory_optimized=False,
                pages_to_build=[],
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

        with patch("bengal.orchestration.build_context.BuildContext") as MockContext:
            mock_ctx = MagicMock()
            MockContext.return_value = mock_ctx

            phase_render(
                orchestrator,
                cli,
                incremental=False,
                force_sequential=True,
                quiet=False,
                verbose=False,
                memory_optimized=False,
                pages_to_build=[],
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

        with patch("bengal.orchestration.build_context.BuildContext") as MockContext:
            mock_ctx = MagicMock()
            MockContext.return_value = mock_ctx

            result = phase_render(
                orchestrator,
                cli,
                incremental=False,
                force_sequential=True,
                quiet=False,
                verbose=False,
                memory_optimized=False,
                pages_to_build=[],
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

    def test_persists_accumulated_assets(self, tmp_path):
        """Persists accumulated assets from BuildContext."""
        from bengal.orchestration.build_context import BuildContext

        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        page = MagicMock()
        page.source_path = Path("test.md")
        page.rendered_html = '<img src="/assets/image.png">'
        pages_to_build = [page]

        # Create build context with accumulated assets
        ctx = BuildContext()
        ctx.accumulate_page_assets(Path("test.md"), {"/assets/image.png"})

        with patch("bengal.cache.asset_dependency_map.AssetDependencyMap") as MockMap:
            mock_map = MagicMock()
            MockMap.return_value = mock_map

            phase_track_assets(orchestrator, pages_to_build, build_context=ctx)

        # Should persist accumulated assets
        mock_map.track_page_assets.assert_called_once()
        mock_map.save_to_disk.assert_called_once()
        # Accumulated assets should be cleared after persistence
        assert not ctx.has_accumulated_assets

    def test_handles_multiple_pages(self, tmp_path):
        """Handles multiple pages with accumulated assets."""
        from bengal.orchestration.build_context import BuildContext

        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        pages = [
            MagicMock(source_path=Path("p1.md"), rendered_html="<html>"),
            MagicMock(source_path=Path("p2.md"), rendered_html="<html>"),
            MagicMock(source_path=Path("p3.md"), rendered_html="<html>"),
        ]

        ctx = BuildContext()
        ctx.accumulate_page_assets(Path("p1.md"), {"/a.png"})
        ctx.accumulate_page_assets(Path("p2.md"), {"/b.png", "/c.js"})
        ctx.accumulate_page_assets(Path("p3.md"), {"/d.css"})

        with patch("bengal.cache.asset_dependency_map.AssetDependencyMap") as MockMap:
            mock_map = MagicMock()
            MockMap.return_value = mock_map

            phase_track_assets(orchestrator, pages, build_context=ctx)

        assert mock_map.track_page_assets.call_count == 3
        mock_map.save_to_disk.assert_called_once()

    def test_handles_empty_accumulated_assets(self, tmp_path):
        """Handles build context with no accumulated assets."""
        from bengal.orchestration.build_context import BuildContext

        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        ctx = BuildContext()  # Empty context

        with patch("bengal.cache.asset_dependency_map.AssetDependencyMap") as MockMap:
            mock_map = MagicMock()
            MockMap.return_value = mock_map

            phase_track_assets(orchestrator, [], build_context=ctx)

        # Should still save (even if empty)
        mock_map.track_page_assets.assert_not_called()
        mock_map.save_to_disk.assert_called_once()

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
