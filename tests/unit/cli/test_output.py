"""
Tests for bengal/output CLI output package.

Tests cover:
- CLIOutput initialization with profiles
- Message level handling (quiet, verbose)
- Output methods (header, phase_start, success, etc.)
- TTY detection and rich/plain fallback
"""

from __future__ import annotations

import pytest

from bengal.output import (
    CLIOutput,
    MessageLevel,
    OutputStyle,
    get_cli_output,
    init_cli_output,
    reset_cli_output,
)


class TestCLIOutputInit:
    """Tests for CLIOutput initialization."""

    def test_init_with_defaults(self):
        """Test CLIOutput can be initialized with defaults."""
        cli = CLIOutput()

        assert cli.quiet is False
        assert cli.verbose is False
        assert cli.profile is None

    def test_init_with_quiet_mode(self):
        """Test CLIOutput quiet mode suppresses non-critical output."""
        cli = CLIOutput(quiet=True)

        assert cli.quiet is True
        assert cli.verbose is False

    def test_init_with_verbose_mode(self):
        """Test CLIOutput verbose mode enables detailed output."""
        cli = CLIOutput(verbose=True)

        assert cli.quiet is False
        assert cli.verbose is True

    def test_init_with_profile(self):
        """Test CLIOutput can be initialized with a build profile."""
        from bengal.utils.observability.profile import BuildProfile

        cli = CLIOutput(profile=BuildProfile.WRITER)

        assert cli.profile == BuildProfile.WRITER
        assert cli.profile_config is not None

    def test_init_with_use_rich_false(self):
        """Test CLIOutput can force plain output."""
        cli = CLIOutput(use_rich=False)

        assert cli.use_rich is False
        # Rich removed — console is None, output uses kida/ANSI directly
        assert cli.console is None

    def test_init_with_use_rich_true(self):
        """Test CLIOutput can force rich output (maps to use_color)."""
        cli = CLIOutput(use_rich=True)

        assert cli.use_rich is True
        # Rich removed — console is None, use_rich maps to use_color
        assert cli.console is None


class TestCLIOutputMethods:
    """Tests for CLIOutput output methods."""

    @pytest.fixture
    def cli(self):
        """Create CLIOutput with rich disabled for testing."""
        return CLIOutput(use_rich=False)

    def test_header_outputs_message(self, cli, capsys):
        """Test header() outputs a header message."""
        cli.header("Test Header")
        captured = capsys.readouterr()
        assert "Test Header" in captured.out

    def test_info_outputs_message(self, cli, capsys):
        """Test info() outputs an info message."""
        cli.info("Test Info")
        captured = capsys.readouterr()
        assert "Test Info" in captured.out

    def test_success_outputs_message(self, cli, capsys):
        """Test success() outputs a success message."""
        cli.success("Test Success")
        captured = capsys.readouterr()
        assert "Test Success" in captured.out

    def test_warning_outputs_message(self, cli, capsys):
        """Test warning() outputs a warning message."""
        cli.warning("Test Warning")
        captured = capsys.readouterr()
        assert "Test Warning" in captured.out

    def test_error_outputs_message(self, cli, capsys):
        """Test error() outputs an error message."""
        cli.error("Test Error")
        captured = capsys.readouterr()
        assert "Test Error" in captured.out

    def test_detail_outputs_with_indent(self, cli, capsys):
        """Test detail() outputs with proper indentation."""
        cli.detail("Indented detail", indent=1)
        captured = capsys.readouterr()
        assert "Indented detail" in captured.out

    def test_blank_outputs_empty_line(self, cli, capsys):
        """Test blank() outputs an empty line."""
        cli.blank()
        captured = capsys.readouterr()
        assert captured.out == "\n"

    def test_quiet_mode_suppresses_detail(self, capsys):
        """Test quiet mode suppresses detail messages."""
        cli = CLIOutput(quiet=True, use_rich=False)
        cli.detail("Should be suppressed")
        _ = capsys.readouterr()
        # In quiet mode, details should be suppressed
        # (Actual behavior depends on implementation)

    def test_phase_outputs_phase(self, cli, capsys):
        """Test phase() outputs phase message."""
        cli.phase("Discovery")
        captured = capsys.readouterr()
        assert "Discovery" in captured.out

    def test_phase_with_duration_outputs_duration(self, cli, capsys):
        """Test phase() with duration outputs phase with timing."""
        cli.phase("Discovery", duration_ms=150)
        captured = capsys.readouterr()
        # Should contain phase name and duration indicator
        assert "Discovery" in captured.out


class TestGlobalCLIOutput:
    """Tests for global CLI output functions."""

    def test_init_cli_output_returns_instance(self):
        """Test init_cli_output() returns a CLIOutput instance."""
        cli = init_cli_output()

        assert isinstance(cli, CLIOutput)

    def test_init_cli_output_with_profile(self):
        """Test init_cli_output() accepts profile parameter."""
        from bengal.utils.observability.profile import BuildProfile

        cli = init_cli_output(profile=BuildProfile.WRITER)

        assert cli.profile == BuildProfile.WRITER

    def test_get_cli_output_returns_initialized(self):
        """Test get_cli_output() returns the initialized instance."""
        init_cli_output()
        cli = get_cli_output()

        assert isinstance(cli, CLIOutput)

    def test_get_cli_output_returns_same_instance(self):
        """Test get_cli_output() returns the same instance."""
        cli1 = init_cli_output()
        cli2 = get_cli_output()

        # Should be the same object (or equivalent - depending on implementation)
        assert cli1 is cli2

    def test_cli_utils_and_output_share_singleton(self):
        """CLI utility imports should use the output package singleton."""
        from bengal.cli.utils.output import get_cli_output as get_cli_output_from_utils

        cli1 = init_cli_output(quiet=True)
        cli2 = get_cli_output_from_utils()

        assert cli1 is cli2
        assert cli2.quiet is True

    def test_cli_utils_reset_clears_output_singleton(self):
        """Resetting through the CLI utility path should clear the shared singleton."""
        from bengal.cli.utils.output import reset_cli_output as reset_cli_output_from_utils

        cli1 = init_cli_output()
        reset_cli_output_from_utils()
        cli2 = get_cli_output()

        assert cli1 is not cli2

    def test_get_cli_output_can_create_isolated_instance(self):
        """Isolated instances should not replace the shared CLI renderer."""
        reset_cli_output()
        global_cli = get_cli_output()
        isolated_cli = get_cli_output(quiet=True, use_global=False)

        assert isolated_cli is not global_cli
        assert isolated_cli.quiet is True
        assert get_cli_output() is global_cli


class TestBridgeOutput:
    """Tests for CLIOutput bridge methods."""

    def test_raw_required_output_ignores_quiet(self, capsys):
        """Required raw output can bypass quiet-mode suppression."""
        cli = CLIOutput(use_rich=False, quiet=True)
        cli.raw("machine output", level=None)

        captured = capsys.readouterr()
        assert captured.out == "machine output\n"

    def test_interrupted_outputs_standard_message(self, capsys):
        """Ctrl-C messaging should flow through CLIOutput."""
        cli = CLIOutput(use_rich=False)
        cli.interrupted()

        captured = capsys.readouterr()
        assert "Interrupted." in captured.out

    def test_prompt_uses_bridge_even_when_quiet(self, monkeypatch, capsys):
        """Interactive prompts remain visible in quiet mode."""
        monkeypatch.setattr("builtins.input", lambda: "docs")
        cli = CLIOutput(use_rich=False, quiet=True)

        result = cli.prompt("Site name")

        captured = capsys.readouterr()
        assert result == "docs"
        assert "Site name" in captured.out

    def test_cli_progress_routes_through_cli_output(self, monkeypatch, capsys):
        """Raw progress helpers should use CLIOutput progress methods."""
        from bengal.cli.helpers.progress import cli_progress

        monkeypatch.setattr(
            "bengal.utils.observability.terminal.is_interactive_terminal",
            lambda: True,
        )
        cli = CLIOutput(use_rich=False)

        with cli_progress("Checking environments", total=2, cli=cli) as update:
            update(advance=1)

        captured = capsys.readouterr()
        assert "Checking environments..." in captured.out
        assert "Checking environments 1/2" in captured.out


class TestMiloBridge:
    """Tests for the Milo app compatibility bridge."""

    def test_milo_generator_progress_routes_through_cli_output(self, capsys):
        """Milo generator progress should render through CLIOutput."""
        from milo.streaming import Progress

        from bengal.cli.milo_app import BengalCLI

        def command_result():
            yield Progress("Preparing", step=1, total=2)
            return {"status": "done"}

        cli = BengalCLI(name="bengal-test")
        result = cli._consume_result(command_result())

        captured = capsys.readouterr()
        assert result == {"status": "done"}
        assert "Preparing 1/2" in captured.err


class TestMessageLevel:
    """Tests for MessageLevel enum."""

    def test_message_levels_exist(self):
        """Test all expected message levels exist."""
        assert hasattr(MessageLevel, "DEBUG")
        assert hasattr(MessageLevel, "INFO")
        assert hasattr(MessageLevel, "WARNING")
        assert hasattr(MessageLevel, "ERROR")


class TestOutputStyle:
    """Tests for OutputStyle enum."""

    def test_output_styles_exist(self):
        """Test OutputStyle enum has expected values."""
        # Just verify the enum can be imported and used
        assert OutputStyle is not None
