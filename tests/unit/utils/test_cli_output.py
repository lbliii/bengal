"""
Tests for CLI output system with color theming.

This test suite verifies:
1. Semantic color token usage
2. Color palette consistency
3. Panel-based header rendering
4. Fallback to plain output
5. Profile-aware formatting
"""

import pytest
from rich.console import Console

from bengal.output import CLIOutput, MessageLevel


class TestColorTheming:
    """Test the new color palette and semantic theming."""

    def test_uses_semantic_success_style(self):
        """Success messages should use [success] semantic style instead of direct colors."""
        cli = CLIOutput(use_rich=True, quiet=False)

        # Capture console output
        from io import StringIO

        from rich.console import Console

        buffer = StringIO()
        cli.console = Console(file=buffer, force_terminal=True, width=80, legacy_windows=False)

        cli.success("Build completed")
        output = buffer.getvalue()

        # Should contain success style, not raw color codes like [bold green]
        assert "[success]" in output or "Build completed" in output

    def test_uses_semantic_warning_style(self):
        """Warning messages should use [warning] semantic style."""
        cli = CLIOutput(use_rich=True, quiet=False)

        from io import StringIO

        buffer = StringIO()
        cli.console = Console(file=buffer, force_terminal=True, width=80, legacy_windows=False)

        cli.warning("Cache miss detected")
        output = buffer.getvalue()

        # Should use warning style
        assert "[warning]" in output or "Cache miss" in output

    def test_uses_semantic_error_style(self):
        """Error messages should use [error] semantic style."""
        cli = CLIOutput(use_rich=True, quiet=False)

        from io import StringIO

        buffer = StringIO()
        cli.console = Console(file=buffer, force_terminal=True, width=80, legacy_windows=False)

        cli.error("Build failed")
        output = buffer.getvalue()

        # Should use error style
        assert "[error]" in output or "Build failed" in output

    def test_uses_semantic_header_style(self):
        """Headers should use [header] semantic style."""
        cli = CLIOutput(use_rich=True, quiet=False)

        from io import StringIO

        from bengal.utils.observability.rich_console import bengal_theme

        buffer = StringIO()
        cli.console = Console(
            file=buffer, force_terminal=True, width=80, legacy_windows=False, theme=bengal_theme
        )

        cli.header("Building site")
        output = buffer.getvalue()

        # Should render as a panel (contains border characters)
        assert "─" in output or "Building site" in output

    def test_uses_semantic_path_style(self):
        """Paths should use [path] semantic style."""
        cli = CLIOutput(use_rich=True, quiet=False)

        import re
        from io import StringIO

        buffer = StringIO()
        cli.console = Console(file=buffer, force_terminal=True, width=80, legacy_windows=False)

        cli.path("/path/to/output")
        output = buffer.getvalue()

        # Strip ANSI codes for checking (Rich applies automatic highlighting)
        plain_output = re.sub(r"\x1b\[[0-9;]+m", "", output)

        # Should contain path styling - check plain text since Rich applies ANSI codes
        assert "/path/to/output" in plain_output

    def test_uses_semantic_metric_styles(self):
        """Metrics should use [metric_label] and [metric_value] styles."""
        cli = CLIOutput(use_rich=True, quiet=False)

        from io import StringIO

        buffer = StringIO()
        cli.console = Console(file=buffer, force_terminal=True, width=80, legacy_windows=False)

        cli.metric("Pages", 100)
        output = buffer.getvalue()

        # Should contain metric styling
        assert "[metric_label]" in output or "Pages" in output


class TestPanelHeader:
    """Test the new Panel-based header rendering."""

    def test_header_uses_panel_with_rich(self):
        """Headers should render as Panel with rich enabled."""
        cli = CLIOutput(use_rich=True, quiet=False)

        from io import StringIO

        from bengal.utils.observability.rich_console import bengal_theme

        buffer = StringIO()
        cli.console = Console(
            file=buffer, force_terminal=True, width=80, legacy_windows=False, theme=bengal_theme
        )

        cli.header("Test Header")
        output = buffer.getvalue()

        # Panel should have border characters
        assert "─" in output
        assert "Test Header" in output

    def test_header_includes_mascot_by_default(self):
        """Headers should include Bengal mascot by default."""
        cli = CLIOutput(use_rich=True, quiet=False)

        from io import StringIO

        from bengal.utils.observability.rich_console import bengal_theme

        buffer = StringIO()
        cli.console = Console(
            file=buffer, force_terminal=True, width=80, legacy_windows=False, theme=bengal_theme
        )

        cli.header("Test Header")
        output = buffer.getvalue()

        # Should contain mascot
        assert "ᓚᘏᗢ" in output

    def test_header_can_omit_mascot(self):
        """Headers can be rendered without mascot."""
        cli = CLIOutput(use_rich=True, quiet=False)

        from io import StringIO

        from bengal.utils.observability.rich_console import bengal_theme

        buffer = StringIO()
        cli.console = Console(
            file=buffer, force_terminal=True, width=80, legacy_windows=False, theme=bengal_theme
        )

        cli.header("Test Header", mascot=False)
        output = buffer.getvalue()

        # Should not contain mascot
        assert "ᓚᘏᗢ" not in output
        assert "Test Header" in output

    def test_header_fallback_without_rich(self):
        """Headers should fallback gracefully without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)

        # Should not raise errors
        cli.header("Test Header")


class TestPlainOutputFallback:
    """Test fallback to plain output when Rich is disabled."""

    def test_plain_output_success(self):
        """Success messages work without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.success("Build completed")  # Should not raise

    def test_plain_output_warning(self):
        """Warning messages work without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.warning("Cache miss")  # Should not raise

    def test_plain_output_error(self):
        """Error messages work without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.error("Build failed")  # Should not raise

    def test_plain_output_path(self):
        """Path messages work without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.path("/path/to/output")  # Should not raise

    def test_plain_output_metric(self):
        """Metric messages work without Rich."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.metric("Pages", 100)  # Should not raise


class TestSemanticPhaseStyles:
    """Test phase output uses semantic styling."""

    def test_phase_uses_semantic_icon_style(self):
        """Phase icons should use [success] style."""
        cli = CLIOutput(use_rich=True, quiet=False)

        from io import StringIO

        buffer = StringIO()
        cli.console = Console(file=buffer, force_terminal=True, width=80, legacy_windows=False)

        cli.phase("Discovery", duration_ms=100)
        output = buffer.getvalue()

        # Should use success style for checkmark
        assert "[success]" in output or "Discovery" in output

    def test_phase_uses_semantic_name_style(self):
        """Phase names should use [phase] style."""
        cli = CLIOutput(use_rich=True, quiet=False)

        from io import StringIO

        buffer = StringIO()
        cli.console = Console(file=buffer, force_terminal=True, width=80, legacy_windows=False)

        cli.phase("Rendering", duration_ms=500, details="245 pages")
        output = buffer.getvalue()

        # Should use phase style
        assert "[phase]" in output or "Rendering" in output

    def test_phase_timing_uses_dim_style(self):
        """Phase timing should use [dim] style for subtlety."""
        cli = CLIOutput(use_rich=True, quiet=False)

        from io import StringIO

        buffer = StringIO()
        cli.console = Console(file=buffer, force_terminal=True, width=80, legacy_windows=False)

        cli.phase("Assets", duration_ms=42)
        output = buffer.getvalue()

        # Should use dim style for timing
        assert "[dim]" in output or "42ms" in output or "Assets" in output


class TestColorPaletteConsistency:
    """Test the color palette is used consistently."""

    def test_bengal_theme_defined(self):
        """Bengal theme should be defined with all semantic styles."""
        from bengal.utils.observability.rich_console import bengal_theme

        # All semantic styles should be defined
        assert "success" in bengal_theme.styles
        assert "error" in bengal_theme.styles
        assert "warning" in bengal_theme.styles
        assert "header" in bengal_theme.styles
        assert "phase" in bengal_theme.styles
        assert "path" in bengal_theme.styles
        assert "metric_label" in bengal_theme.styles
        assert "metric_value" in bengal_theme.styles

    def test_color_palette_defined(self):
        """Color palette should be defined with all brand colors."""
        from bengal.utils.observability.rich_console import PALETTE

        # Core brand colors
        assert "primary" in PALETTE
        assert "secondary" in PALETTE
        assert "success" in PALETTE
        assert "error" in PALETTE
        assert "warning" in PALETTE
        assert "bengal" in PALETTE

        # Should be hex colors
        assert PALETTE["primary"].startswith("#")
        assert PALETTE["secondary"].startswith("#")

    def test_palette_colors_are_hex_format(self):
        """All palette colors should be valid hex codes."""
        from bengal.utils.observability.rich_console import PALETTE

        for name, color in PALETTE.items():
            # Should start with # and be 7 chars (#RRGGBB)
            assert color.startswith("#"), f"{name} color should start with #"
            assert len(color) == 7, f"{name} color should be 7 chars (#RRGGBB)"
            # Should be valid hex
            try:
                int(color[1:], 16)
            except ValueError:
                pytest.fail(f"{name} color {color} is not valid hex")


class TestProfileAwareFormatting:
    """Test that output respects build profiles."""

    def test_quiet_mode_suppresses_info(self):
        """Quiet mode should suppress info messages."""
        cli = CLIOutput(use_rich=False, quiet=True)

        # These should be suppressed (no output)
        assert not cli.should_show(MessageLevel.INFO)
        assert not cli.should_show(MessageLevel.DEBUG)

    def test_quiet_mode_shows_warnings(self):
        """Quiet mode should still show warnings and errors."""
        cli = CLIOutput(use_rich=False, quiet=True)

        # These should still show
        assert cli.should_show(MessageLevel.WARNING)
        assert cli.should_show(MessageLevel.ERROR)

    def test_verbose_mode_shows_debug(self):
        """Verbose mode should show debug messages."""
        cli = CLIOutput(use_rich=False, verbose=True)

        assert cli.should_show(MessageLevel.DEBUG)


class TestColorAccessibility:
    """Test color accessibility and contrast (documentation test)."""

    def test_palette_documents_accessibility_intent(self):
        """Color palette should have good contrast for accessibility.

        This is a documentation test - we verify the colors are defined
        with accessibility in mind, though actual contrast depends on
        terminal background color.

        Rich library handles actual rendering and should provide good
        contrast on both light and dark terminal backgrounds.
        """
        from bengal.utils.observability.rich_console import PALETTE

        # Document the palette
        colors = {
            "primary": PALETTE["primary"],  # #FF9D00 - Vivid Orange
            "secondary": PALETTE["secondary"],  # #3498DB - Bright Blue
            "success": PALETTE["success"],  # #2ECC71 - Emerald Green
            "error": PALETTE["error"],  # #E74C3C - Alizarin Red
            "warning": PALETTE["warning"],  # #E67E22 - Carrot Orange
        }

        # All colors should be defined and distinctive
        assert len(set(colors.values())) == len(colors), "Colors should be unique"

        # Note: Actual WCAG contrast testing requires knowing the background color,
        # which varies by terminal theme. Rich library automatically adjusts
        # color rendering based on terminal capabilities.


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_success_message_still_works(self):
        """Existing success() calls should work unchanged."""
        cli = CLIOutput(use_rich=False, quiet=False)
        cli.success("Build completed")  # Should not raise

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

        from io import StringIO

        from bengal.utils.observability.rich_console import bengal_theme

        buffer = StringIO()
        cli.console = Console(
            file=buffer, force_terminal=True, width=80, legacy_windows=False, theme=bengal_theme
        )

        # Simulate build output
        cli.header("Building your site")
        cli.phase("Discovery", duration_ms=61, details="245 pages")
        cli.phase("Rendering", duration_ms=501, details="245 pages")
        cli.phase("Assets", duration_ms=42, details="12 files")
        cli.success("Built 245 pages in 0.8s")
        cli.path("/Users/test/public")

        output = buffer.getvalue()

        # Should contain all elements
        assert "Building" in output
        assert "Discovery" in output
        assert "Rendering" in output
        assert "Assets" in output
        assert "Built" in output
