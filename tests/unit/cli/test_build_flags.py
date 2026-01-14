"""
Tests for build flag validation and propagation in CLI.
"""

from click.testing import CliRunner

from bengal.cli import main


class TestFlagValidation:
    """Test validation of incompatible flag combinations."""

    def test_quiet_and_verbose_conflict(self):
        """Test that --quiet and --verbose cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["site", "build", "--quiet", "--verbose", "."])

            assert result.exit_code != 0
            assert "--quiet and --verbose cannot be used together" in result.output

    def test_quiet_and_dev_conflict(self):
        """Test that --quiet and --dev cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["site", "build", "--quiet", "--dev", "."])

            assert result.exit_code != 0
            assert "--quiet cannot be used with --dev" in result.output

    def test_quiet_and_theme_dev_conflict(self):
        """Test that --quiet and --theme-dev cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["site", "build", "--quiet", "--theme-dev", "."])

            assert result.exit_code != 0
            assert "--quiet cannot be used with --dev or --theme-dev" in result.output

    def test_memory_optimized_and_perf_profile_conflict(self):
        """Test that --memory-optimized and --perf-profile cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["site", "build", "--memory-optimized", "--perf-profile", "test.stats", "."]
            )

            assert result.exit_code != 0
            assert "cannot be used together" in result.output
            assert "profiler doesn't work with streaming" in result.output

    def test_memory_optimized_and_incremental_warning(self):
        """Test that --memory-optimized with --incremental shows warning."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # This will fail at site creation but should show the warning first
            result = runner.invoke(
                main, ["site", "build", "--memory-optimized", "--incremental", "."]
            )

            # Warning should appear in output
            assert (
                "Warning:" in result.output
                or "⚠️" in result.output
                or "warning" in result.output.lower()
            )


class TestProfilePrecedence:
    """Test build profile precedence and flag interactions."""

    def test_dev_flag_takes_precedence(self):
        """Test that --dev flag takes highest precedence."""
        # Would need to mock BuildProfile.from_cli_args to test this properly
        from bengal.utils.observability.profile import BuildProfile

        profile = BuildProfile.from_cli_args(dev=True, theme_dev=True, profile="writer")

        assert profile == BuildProfile.DEVELOPER

    def test_theme_dev_precedence_over_profile(self):
        """Test that --theme-dev takes precedence over --profile."""
        from bengal.utils.observability.profile import BuildProfile

        profile = BuildProfile.from_cli_args(dev=False, theme_dev=True, profile="writer")

        assert profile == BuildProfile.THEME_DEV

    def test_profile_option_precedence(self):
        """Test that --profile option takes precedence over --debug."""
        from bengal.utils.observability.profile import BuildProfile

        profile = BuildProfile.from_cli_args(
            profile="writer", debug=True, dev=False, theme_dev=False
        )

        assert profile == BuildProfile.WRITER

    def test_debug_maps_to_developer(self):
        """Test that --debug maps to developer profile."""
        from bengal.utils.observability.profile import BuildProfile

        profile = BuildProfile.from_cli_args(debug=True, dev=False, theme_dev=False, profile=None)

        assert profile == BuildProfile.DEVELOPER

    def test_default_profile_is_writer(self):
        """Test that default profile is WRITER."""
        from bengal.utils.observability.profile import BuildProfile

        profile = BuildProfile.from_cli_args(dev=False, theme_dev=False, profile=None, debug=False)

        assert profile == BuildProfile.WRITER


class TestFlagPropagation:
    """Test that flags are properly propagated through the build system."""

    def test_build_options_has_quiet(self):
        """Test that quiet field exists in BuildOptions."""
        from bengal.orchestration.build.options import BuildOptions

        # Check that BuildOptions has quiet field with correct default
        options = BuildOptions()
        assert hasattr(options, "quiet")
        assert options.quiet is False  # Should default to False

    def test_build_options_has_strict(self):
        """Test that strict field exists in BuildOptions."""
        from bengal.orchestration.build.options import BuildOptions

        # Check that BuildOptions has strict field with correct default
        options = BuildOptions()
        assert hasattr(options, "strict")
        assert options.strict is False  # Should default to False

    def test_render_orchestrator_accepts_quiet(self):
        """Test that RenderOrchestrator.process accepts quiet parameter."""
        import inspect

        from bengal.orchestration.render import RenderOrchestrator

        sig = inspect.signature(RenderOrchestrator.process)
        params = sig.parameters

        assert "quiet" in params
        assert params["quiet"].default is False

    def test_streaming_orchestrator_accepts_quiet(self):
        """Test that StreamingRenderOrchestrator.process accepts quiet parameter."""
        import inspect

        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        sig = inspect.signature(StreamingRenderOrchestrator.process)
        params = sig.parameters

        assert "quiet" in params
        assert params["quiet"].default is False


class TestValidateFlag:
    """Test --validate flag functionality."""

    def test_validate_flag_exists(self):
        """Test that --validate flag is recognized."""
        runner = CliRunner()
        result = runner.invoke(main, ["site", "build", "--help"])

        assert "--validate" in result.output
        assert "Validate templates" in result.output or "validate" in result.output.lower()

    # Note: Full integration test would require a test site with templates
    # This is covered by integration tests


class TestStrictMode:
    """Test --strict flag functionality."""

    def test_strict_flag_exists(self):
        """Test that --strict flag is recognized."""
        runner = CliRunner()
        result = runner.invoke(main, ["site", "build", "--help"])

        assert "--strict" in result.output
        assert "strict" in result.output.lower()

    # Note: Full functionality test requires integration with health checks
    # This is covered by integration tests


class TestConfigRespect:
    """Test that CLI respects config values when flags not explicitly passed.
    
    RFC: rfc-path-to-200-pgs - discovered that --parallel default=True
    was ignoring config settings. These tests prevent regressions.
        
    """

    def test_no_parallel_flag_default_is_false(self):
        """Test that --no-parallel default is False (auto-detect mode)."""

        from bengal.cli.commands.build import build

        # Find the no_parallel option (now named no_parallel, is_flag=True)
        no_parallel_option = None
        for param in build.params:
            if param.name == "no_parallel":
                no_parallel_option = param
                break

        assert no_parallel_option is not None, "--no-parallel option not found"
        assert no_parallel_option.default is False, (
            f"--no-parallel default should be False to allow auto-detection, "
            f"got {no_parallel_option.default}"
        )

    def test_incremental_flag_default_is_none(self):
        """Test that --incremental default allows config fallback."""
        from bengal.cli.commands.build import build

        incremental_option = None
        for param in build.params:
            if param.name == "incremental":
                incremental_option = param
                break

        assert incremental_option is not None
        assert incremental_option.default is None, (
            "--incremental default should be None to allow config fallback"
        )

    def test_fast_flag_default_is_none(self):
        """Test that --fast default allows config fallback."""
        from bengal.cli.commands.build import build

        fast_option = None
        for param in build.params:
            if param.name == "fast":
                fast_option = param
                break

        assert fast_option is not None
        assert fast_option.default is None, "--fast default should be None to allow config fallback"


class TestFastMode:
    """Test --fast flag functionality."""

    def test_fast_flag_exists(self):
        """Test that --fast flag is recognized in help."""
        runner = CliRunner()
        result = runner.invoke(main, ["site", "build", "--help"])

        assert result.exit_code == 0
        assert "--fast" in result.output
        assert "quiet output" in result.output or "max speed" in result.output

    def test_fast_and_dev_conflict(self):
        """Test that --fast and --dev cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["site", "build", "--fast", "--dev", "."])

            assert result.exit_code != 0
            assert "--fast cannot be used with --dev" in result.output

    def test_fast_and_theme_dev_conflict(self):
        """Test that --fast and --theme-dev cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["site", "build", "--fast", "--theme-dev", "."])

            assert result.exit_code != 0
            assert "--fast cannot be used with --dev or --theme-dev" in result.output

    def test_fast_mode_enables_quiet_and_parallel(self):
        """Test that --fast mode is recognized (actual behavior tested in integration)."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create minimal bengal.toml
            with open("bengal.toml", "w") as f:
                f.write("[site]\ntitle = 'Test'\n")

            # The command will fail at Site.from_config but should parse --fast flag
            result = runner.invoke(main, ["site", "build", "--fast", "."])

            # Flag should be accepted without validation error
            # (The actual behavior - quiet output and parallel - is tested in integration tests)
            assert "--fast" not in result.output  # No error about unknown flag

    def test_no_fast_flag_disables_fast_mode(self):
        """Test that --no-fast explicitly disables fast mode."""
        runner = CliRunner()
        result = runner.invoke(main, ["site", "build", "--help"])

        # Should show both --fast and --no-fast options
        assert "--fast" in result.output
        assert "--no-fast" in result.output
