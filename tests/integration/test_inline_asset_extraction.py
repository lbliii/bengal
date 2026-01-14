"""Integration tests for inline asset extraction optimization."""

from pathlib import Path
from unittest.mock import MagicMock

from bengal.orchestration.build.rendering import phase_track_assets
from bengal.orchestration.build_context import BuildContext


class TestInlineAssetExtraction:
    """Integration tests for inline asset extraction."""

    def test_phase_track_assets_persists_accumulated_data(self, tmp_path):
        """phase_track_assets persists accumulated assets from rendering."""
        # Create mock orchestrator
        orchestrator = MagicMock()
        orchestrator.site.paths.asset_cache = tmp_path / "asset_cache"
        orchestrator.site.paths.asset_cache.mkdir(parents=True)
        orchestrator.logger.phase.return_value.__enter__ = MagicMock()
        orchestrator.logger.phase.return_value.__exit__ = MagicMock(return_value=False)

        # Create pages with rendered HTML
        page1 = MagicMock()
        page1.source_path = Path("page1.md")
        page1.rendered_html = '<img src="/img/logo.png" />'

        page2 = MagicMock()
        page2.source_path = Path("page2.md")
        page2.rendered_html = '<script src="/js/app.js"></script>'

        pages = [page1, page2]

        # Create build context with accumulated assets (from inline extraction)
        ctx = BuildContext()
        ctx.accumulate_page_assets(Path("page1.md"), {"/img/logo.png"})
        ctx.accumulate_page_assets(Path("page2.md"), {"/js/app.js"})

        # Run phase
        phase_track_assets(orchestrator, pages, cli=None, build_context=ctx)

        # Verify persistence succeeded
        orchestrator.logger.info.assert_called_once()

        # Verify accumulated assets were cleared after persistence
        assert not ctx.has_accumulated_assets

    def test_phase_track_assets_handles_empty_pages(self, tmp_path):
        """phase_track_assets handles empty page list."""
        # Create mock orchestrator
        orchestrator = MagicMock()
        orchestrator.site.paths.asset_cache = tmp_path / "asset_cache"
        orchestrator.site.paths.asset_cache.mkdir(parents=True)
        orchestrator.logger.phase.return_value.__enter__ = MagicMock()
        orchestrator.logger.phase.return_value.__exit__ = MagicMock(return_value=False)

        ctx = BuildContext()

        # Run phase with empty page list
        phase_track_assets(orchestrator, [], cli=None, build_context=ctx)

        # Should complete without error
        orchestrator.logger.info.assert_called_once()

    def test_phase_track_assets_clears_memory_after_persistence(self, tmp_path):
        """phase_track_assets clears accumulated assets to free memory."""
        orchestrator = MagicMock()
        orchestrator.site.paths.asset_cache = tmp_path / "asset_cache"
        orchestrator.site.paths.asset_cache.mkdir(parents=True)
        orchestrator.logger.phase.return_value.__enter__ = MagicMock()
        orchestrator.logger.phase.return_value.__exit__ = MagicMock(return_value=False)

        # Accumulate many assets
        ctx = BuildContext()
        for i in range(100):
            ctx.accumulate_page_assets(Path(f"page{i}.md"), {f"/img/{i}.png"})

        assert ctx.accumulated_asset_count == 100

        pages = [
            MagicMock(source_path=Path(f"page{i}.md"), rendered_html="<html>") for i in range(100)
        ]
        phase_track_assets(orchestrator, pages, cli=None, build_context=ctx)

        # Memory should be freed
        assert ctx.accumulated_asset_count == 0
