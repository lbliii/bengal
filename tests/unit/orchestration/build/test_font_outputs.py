"""Focused tests for font output writes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from bengal.core.output import BuildOutputCollector, OutputType
from bengal.orchestration.build.initialization import phase_fonts


def _orchestrator(tmp_path: Path):
    orchestrator = MagicMock()
    orchestrator.site = MagicMock()
    orchestrator.site.root_path = tmp_path
    orchestrator.site.output_dir = tmp_path / "public"
    orchestrator.site.output_dir.mkdir(parents=True)
    orchestrator.site.config = {"fonts": {"google": ["Outfit"]}}
    orchestrator.stats = MagicMock()
    orchestrator.stats.fonts_time_ms = 0
    orchestrator._last_build_options = None
    return orchestrator


def test_fonts_css_copy_is_atomic_and_collector_visible(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    cli = MagicMock()
    collector = BuildOutputCollector(output_dir=orchestrator.site.output_dir)

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    fonts_css = assets_dir / "fonts.css"
    fonts_css.write_text("/* fonts */", encoding="utf-8")

    with patch("bengal.fonts.FontHelper") as MockFontHelper:
        mock_font_helper = MagicMock()
        MockFontHelper.return_value = mock_font_helper
        mock_font_helper.process.return_value = fonts_css

        phase_fonts(orchestrator, cli, collector=collector)

    output_css = orchestrator.site.output_dir / "assets" / "fonts.css"
    assert output_css.read_text(encoding="utf-8") == "/* fonts */"
    outputs = collector.get_outputs()
    assert len(outputs) == 1
    assert outputs[0].path == Path("assets/fonts.css")
    assert outputs[0].output_type == OutputType.CSS


def test_unchanged_fonts_css_is_not_recorded(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    cli = MagicMock()
    collector = BuildOutputCollector(output_dir=orchestrator.site.output_dir)

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    fonts_css = assets_dir / "fonts.css"
    fonts_css.write_text("/* fonts */", encoding="utf-8")
    output_css = orchestrator.site.output_dir / "assets" / "fonts.css"
    output_css.parent.mkdir(parents=True)
    output_css.write_text("/* fonts */", encoding="utf-8")

    with patch("bengal.fonts.FontHelper") as MockFontHelper:
        mock_font_helper = MagicMock()
        MockFontHelper.return_value = mock_font_helper
        mock_font_helper.process.return_value = fonts_css

        phase_fonts(orchestrator, cli, collector=collector)

    assert collector.get_outputs() == []
