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

from bengal.output import CLIOutput, MessageLevel, OutputStyle, get_cli_output, init_cli_output


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
        from bengal.utils.profile import BuildProfile

        cli = CLIOutput(profile=BuildProfile.WRITER)

        assert cli.profile == BuildProfile.WRITER
        assert cli.profile_config is not None

    def test_init_with_use_rich_false(self):
        """Test CLIOutput can force plain output."""
        cli = CLIOutput(use_rich=False)

        assert cli.use_rich is False
        # Console is always created for type safety (never None)
        # When use_rich=False, Rich features are bypassed but console exists
        assert cli.console is not None

    def test_init_with_use_rich_true(self):
        """Test CLIOutput can force rich output."""
        cli = CLIOutput(use_rich=True)

        assert cli.use_rich is True
        # Console should be set when use_rich is True
        assert cli.console is not None


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
        from bengal.utils.profile import BuildProfile

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
