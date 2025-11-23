"""
Integration tests for CLI output with actual commands.

These tests verify that CLI commands work with the themed console
and don't crash with style errors.

Uses Phase 1 infrastructure: run_cli() helper for standardized CLI testing.
"""

import pytest

from tests._testing.cli import run_cli


class TestCLICommandOutput:
    """Test CLI commands produce valid output without errors."""

    @pytest.mark.bengal(testroot="test-basic")
    def test_clean_command_works(self, site):
        """Test 'bengal site clean' command doesn't crash with style errors."""
        # Run clean help command (should not crash with style errors)
        result = run_cli(["site", "clean", "--help"], cwd=str(site.root_path))

        # Should not contain style error
        assert "Failed to get style" not in result.stderr
        assert "unable to parse 'header' as color" not in result.stderr

        # Help should succeed
        result.assert_ok()

    def test_build_help_shows_themed_output(self):
        """Test help commands display without style errors."""
        result = run_cli(["site", "build", "--help"])

        # Should not have style errors
        assert "Failed to get style" not in result.stderr

        # Help should succeed
        result.assert_ok()

        # Should show help text
        assert "build" in result.stdout.lower() or "Build" in result.stdout

    def test_version_command_works(self):
        """Test version command displays correctly."""
        result = run_cli(["--version"])

        # Should not have style errors
        assert "Failed to get style" not in result.stderr

        # Should succeed
        result.assert_ok()

        # Should show version
        assert "Bengal" in result.stdout or "bengal" in result.stdout

    @pytest.mark.bengal(testroot="test-assets")
    def test_assets_status_shows_manifest_entries(self, site):
        """`bengal assets status` should report logical-to-fingerprint mappings."""
        # Ensure manifest exists
        result = run_cli(["site", "build", "--clean-output"], cwd=str(site.root_path), timeout=40)
        result.assert_ok()

        status = run_cli(["assets", "status"], cwd=str(site.root_path))
        status.assert_ok()
        assert "css/style.css" in status.stdout
        assert "fingerprint" in status.stdout.lower()


class TestCLIOutputWithRealCommands:
    """Test CLI output system with real command scenarios."""

    @pytest.mark.bengal(testroot="test-basic")
    def test_build_command_uses_themed_header(self, site):
        """Test build command displays themed header without errors."""
        # Run build command on the test site
        result = run_cli(["site", "build"], cwd=str(site.root_path), timeout=30)

        # Build should succeed
        result.assert_ok()

        # Should not have style errors
        assert "Failed to get style" not in result.stderr
        assert "unable to parse" not in result.stderr


class TestCLIOutputInitialization:
    """Test CLIOutput initialization uses themed console."""

    def test_cli_output_has_themed_console(self):
        """Test CLIOutput initializes with bengal_theme."""
        from bengal.utils.cli_output import CLIOutput

        cli = CLIOutput(use_rich=True)

        # Console should be initialized
        assert cli.console is not None

        # Console should be able to render semantic styles without errors
        # Test by checking it can get the 'header' style
        try:
            style = cli.console.get_style("header")
            assert style is not None
        except Exception as e:
            pytest.fail(f"Console doesn't have 'header' style: {e}")

    def test_cli_output_header_doesnt_crash(self):
        """Test header method doesn't crash with style error."""
        from bengal.utils.cli_output import CLIOutput

        cli = CLIOutput(use_rich=True)

        # Should not raise MissingStyle error
        try:
            cli.header("Test Header")
        except Exception as e:
            if "Failed to get style" in str(e):
                pytest.fail(f"Header crashed with style error: {e}")
            # Other exceptions might be OK (like output issues in test env)

    def test_cli_output_all_message_types_work(self):
        """Test all message types work without style errors."""
        from bengal.utils.cli_output import CLIOutput

        cli = CLIOutput(use_rich=True)

        # None of these should raise style errors
        try:
            cli.header("Building site")
            cli.success("Build complete")
            cli.warning("Cache miss")
            cli.error("Test error")
            cli.info("Test info")
            cli.path("/test/path")
            cli.metric("Pages", 100)
            cli.phase("Discovery", duration_ms=50, details="10 pages")
        except Exception as e:
            if "Failed to get style" in str(e) or "unable to parse" in str(e):
                pytest.fail(f"CLI output crashed with style error: {e}")


class TestThemeConsistency:
    """Test theme is consistent across all CLI entry points."""

    def test_get_console_returns_themed_instance(self):
        """Test get_console() returns a themed console."""
        from bengal.utils.rich_console import get_console

        console = get_console()

        assert console is not None

        # Verify it has semantic styles by trying to get them
        try:
            console.get_style("header")
            console.get_style("success")
            console.get_style("error")
        except Exception as e:
            pytest.fail(f"Console missing semantic styles: {e}")

    def test_cli_output_uses_get_console(self):
        """Test CLIOutput uses get_console() not raw Console()."""
        from bengal.utils.cli_output import CLIOutput
        from bengal.utils.rich_console import get_console

        cli = CLIOutput(use_rich=True)
        expected_console = get_console()

        # Should be using the singleton themed console
        assert cli.console is expected_console

    def test_singleton_console_persists_theme(self):
        """Test singleton console maintains theme across calls."""
        from bengal.utils.rich_console import get_console, reset_console

        # Reset to ensure clean state
        reset_console()

        console1 = get_console()
        console2 = get_console()

        # Should be same instance
        assert console1 is console2

        # Both should have semantic styles
        try:
            console1.get_style("header")
            console2.get_style("header")
        except Exception as e:
            pytest.fail(f"Singleton console lost theme: {e}")


@pytest.mark.parametrize(
    "command",
    [
        ["site", "clean", "--help"],
        ["site", "build", "--help"],
        ["--help"],
        ["--version"],
    ],
)
def test_cli_command_no_style_errors(command):
    """Test various CLI commands don't produce style errors."""
    result = run_cli(command, timeout=10)

    # Should never have style errors
    assert "Failed to get style" not in result.stderr
    assert "unable to parse" not in result.stderr.lower()
    assert "is not a valid color" not in result.stderr
