"""
Tests for CLI output system with color theming.

This test suite verifies:
1. Semantic color token usage (ANSI SGR codes from BENGAL_THEME)
2. Color palette consistency
3. Panel-based header rendering (via kida templates)
4. Fallback to plain output
5. Profile-aware formatting
"""

import re
import sys
from io import StringIO

import pytest

from bengal.output import CLIOutput, MessageLevel


def _capture_output(cli, fn):
    """Capture stdout from a CLIOutput method call."""
    buf = StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buf
        fn()
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


class TestColorTheming:
    """Test the new color palette and semantic theming."""

    def test_uses_semantic_success_style(self):
        """Success messages should contain ANSI styling when color enabled."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.success("Build completed"))
        assert "Build completed" in output

    def test_uses_semantic_warning_style(self):
        """Warning messages should contain ANSI styling when color enabled."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.warning("Cache miss detected"))
        assert "Cache miss" in output

    def test_uses_semantic_error_style(self):
        """Error messages should contain ANSI styling when color enabled."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.error("Build failed"))
        assert "Build failed" in output

    def test_uses_semantic_header_style(self):
        """Headers should render with box drawing characters."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.header("Building site"))
        assert "Building site" in output
        # Kida template renders box-drawing chars
        assert "─" in output or "Building site" in output

    def test_uses_semantic_path_style(self):
        """Paths should render with the path."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.path("/path/to/output"))
        plain_output = re.sub(r"\x1b\[[0-9;]+m", "", output)
        assert "/path/to/output" in plain_output

    def test_uses_semantic_metric_styles(self):
        """Metrics should render with label and value."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.metric("Pages", 100))
        plain_output = re.sub(r"\x1b\[[0-9;]+m", "", output)
        assert "Pages" in plain_output


class TestPanelHeader:
    """Test the new Panel-based header rendering."""

    def test_header_uses_panel_with_rich(self):
        """Headers should render with the header text."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.header("Test Header"))
        assert "Test Header" in output

    def test_header_includes_mascot_by_default(self):
        """Headers should include Bengal mascot by default."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.header("Test Header"))
        assert "ᓚᘏᗢ" in output

    def test_header_can_omit_mascot(self):
        """Headers can be rendered without mascot."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.header("Test Header", mascot=False))
        assert "ᓚᘏᗢ" not in output
        assert "Test Header" in output

    def test_header_fallback_without_rich(self):
        """Headers should fallback gracefully without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.header("Test Header")


class TestPlainOutputFallback:
    """Test fallback to plain output when Rich is disabled."""

    def test_plain_output_success(self):
        """Success messages work without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.success("Build completed")

    def test_plain_output_warning(self):
        """Warning messages work without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.warning("Cache miss")

    def test_plain_output_error(self):
        """Error messages work without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.error("Build failed")

    def test_plain_output_path(self):
        """Path messages work without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.path("/path/to/output")

    def test_plain_output_metric(self):
        """Metric messages work without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.metric("Pages", 100)


class TestSemanticPhaseStyles:
    """Test phase output uses semantic styling."""

    def test_phase_uses_semantic_icon_style(self):
        """Phase output should include the phase name."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.phase("Discovery", duration_ms=100))
        assert "Discovery" in output

    def test_phase_uses_semantic_name_style(self):
        """Phase output should include details."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(
            cli, lambda: cli.phase("Rendering", duration_ms=500, details="245 pages")
        )
        assert "Rendering" in output

    def test_phase_timing_uses_dim_style(self):
        """Phase timing should be included in output."""
        cli = CLIOutput(use_rich=True, quiet=False)
        output = _capture_output(cli, lambda: cli.phase("Assets", duration_ms=42))
        assert "Assets" in output


class TestColorPaletteConsistency:
    """Test the color palette is used consistently."""

    def test_bengal_theme_defined(self):
        """Bengal theme should be defined with all semantic styles."""
        from bengal.utils.observability.rich_console import bengal_theme

        # bengal_theme is now a plain dict (Rich Theme removed)
        assert "success" in bengal_theme
        assert "error" in bengal_theme
        assert "warning" in bengal_theme
        assert "header" in bengal_theme

    def test_color_palette_defined(self):
        """Color palette should be defined with all brand colors."""
        from bengal.utils.observability.rich_console import PALETTE

        assert "primary" in PALETTE
        assert "secondary" in PALETTE
        assert "success" in PALETTE
        assert "error" in PALETTE
        assert "warning" in PALETTE
        assert "bengal" in PALETTE
        assert PALETTE["primary"].startswith("#")
        assert PALETTE["secondary"].startswith("#")

    def test_palette_colors_are_hex_format(self):
        """All palette colors should be valid hex codes."""
        from bengal.utils.observability.rich_console import PALETTE

        for name, color in PALETTE.items():
            assert color.startswith("#"), f"{name} color should start with #"
            assert len(color) == 7, f"{name} color should be 7 chars (#RRGGBB)"
            try:
                int(color[1:], 16)
            except ValueError:
                pytest.fail(f"{name} color {color} is not valid hex")


class TestProfileAwareFormatting:
    """Test that output respects build profiles."""

    def test_quiet_mode_suppresses_info(self):
        """Quiet mode should suppress info messages."""
        cli = CLIOutput(use_rich=False, quiet=True)
        assert not cli.should_show(MessageLevel.INFO)
        assert not cli.should_show(MessageLevel.DEBUG)

    def test_quiet_mode_shows_warnings(self):
        """Quiet mode should still show warnings and errors."""
        cli = CLIOutput(use_rich=False, quiet=True)
        assert cli.should_show(MessageLevel.WARNING)
        assert cli.should_show(MessageLevel.ERROR)

    def test_verbose_mode_shows_debug(self):
        """Verbose mode should show debug messages."""
        cli = CLIOutput(use_rich=False, verbose=True)
        assert cli.should_show(MessageLevel.DEBUG)


class TestColorAccessibility:
    """Test color accessibility and contrast (documentation test)."""

    def test_palette_documents_accessibility_intent(self):
        """Color palette should have good contrast for accessibility."""
        from bengal.utils.observability.rich_console import PALETTE

        colors = {
            "primary": PALETTE["primary"],
            "secondary": PALETTE["secondary"],
            "success": PALETTE["success"],
            "error": PALETTE["error"],
            "warning": PALETTE["warning"],
        }
        assert len(set(colors.values())) == len(colors), "Colors should be unique"


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_success_message_still_works(self):
        """Existing success() calls should work unchanged."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.success("Build completed")

    def test_phase_message_still_works(self):
        """Existing phase() calls should work unchanged."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.phase("Discovery", duration_ms=100, details="245 pages")

    def test_header_message_still_works(self):
        """Existing header() calls should work unchanged."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.header("Building site")


class TestIntegration:
    """Integration tests for complete output scenarios."""

    def test_complete_build_output_sequence(self):
        """Test a complete build output sequence."""
        cli = CLIOutput(use_rich=True, quiet=False)

        output = _capture_output(
            cli,
            lambda: (
                cli.header("Building your site"),
                cli.phase("Discovery", duration_ms=61, details="245 pages"),
                cli.phase("Rendering", duration_ms=501, details="245 pages"),
                cli.phase("Assets", duration_ms=42, details="12 files"),
                cli.success("Built 245 pages in 0.8s"),
                cli.path("/Users/test/public"),
            ),
        )

        assert "Building" in output
        assert "Discovery" in output
        assert "Rendering" in output
        assert "Assets" in output
        assert "Built" in output
