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
            result = runner.invoke(main, ['build', '--quiet', '--verbose', '.'])

            assert result.exit_code != 0
            assert "--quiet and --verbose cannot be used together" in result.output

    def test_quiet_and_dev_conflict(self):
        """Test that --quiet and --dev cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ['build', '--quiet', '--dev', '.'])

            assert result.exit_code != 0
            assert "--quiet cannot be used with --dev" in result.output

    def test_quiet_and_theme_dev_conflict(self):
        """Test that --quiet and --theme-dev cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ['build', '--quiet', '--theme-dev', '.'])

            assert result.exit_code != 0
            assert "--quiet cannot be used with --dev or --theme-dev" in result.output

    def test_memory_optimized_and_perf_profile_conflict(self):
        """Test that --memory-optimized and --perf-profile cannot be used together."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, [
                'build',
                '--memory-optimized',
                '--perf-profile', 'test.stats',
                '.'
            ])

            assert result.exit_code != 0
            assert "cannot be used together" in result.output
            assert "profiler doesn't work with streaming" in result.output

    def test_memory_optimized_and_incremental_warning(self):
        """Test that --memory-optimized with --incremental shows warning."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # This will fail at site creation but should show the warning first
            result = runner.invoke(main, ['build', '--memory-optimized', '--incremental', '.'])

            # Warning should appear in output
            assert "Warning:" in result.output or "⚠️" in result.output or "warning" in result.output.lower()


class TestProfilePrecedence:
    """Test build profile precedence and flag interactions."""

    def test_dev_flag_takes_precedence(self):
        """Test that --dev flag takes highest precedence."""
        # Would need to mock BuildProfile.from_cli_args to test this properly
        from bengal.utils.profile import BuildProfile

        profile = BuildProfile.from_cli_args(
            dev=True,
            theme_dev=True,
            profile='writer',
            verbose=True
        )

        assert profile == BuildProfile.DEVELOPER

    def test_theme_dev_precedence_over_profile(self):
        """Test that --theme-dev takes precedence over --profile."""
        from bengal.utils.profile import BuildProfile

        profile = BuildProfile.from_cli_args(
            dev=False,
            theme_dev=True,
            profile='writer',
            verbose=False
        )

        assert profile == BuildProfile.THEME_DEV

    def test_profile_option_precedence(self):
        """Test that --profile option takes precedence over --verbose."""
        from bengal.utils.profile import BuildProfile

        profile = BuildProfile.from_cli_args(
            profile='writer',
            verbose=True,
            dev=False,
            theme_dev=False
        )

        assert profile == BuildProfile.WRITER

    def test_verbose_maps_to_theme_dev(self):
        """Test that --verbose maps to theme-dev profile."""
        from bengal.utils.profile import BuildProfile

        profile = BuildProfile.from_cli_args(
            verbose=True,
            dev=False,
            theme_dev=False,
            profile=None
        )

        assert profile == BuildProfile.THEME_DEV

    def test_default_profile_is_writer(self):
        """Test that default profile is WRITER."""
        from bengal.utils.profile import BuildProfile

        profile = BuildProfile.from_cli_args(
            dev=False,
            theme_dev=False,
            verbose=False,
            profile=None,
            debug=False
        )

        assert profile == BuildProfile.WRITER


class TestFlagPropagation:
    """Test that flags are properly propagated through the build system."""

    def test_quiet_flag_structure(self):
        """Test that quiet parameter exists in build signature."""
        import inspect

        from bengal.orchestration.build import BuildOrchestrator

        # Check method signature
        sig = inspect.signature(BuildOrchestrator.build)
        params = sig.parameters

        assert 'quiet' in params
        assert params['quiet'].default is False  # Should default to False

    def test_strict_flag_structure(self):
        """Test that strict parameter exists in build signature."""
        import inspect

        from bengal.orchestration.build import BuildOrchestrator

        sig = inspect.signature(BuildOrchestrator.build)
        params = sig.parameters

        assert 'strict' in params
        assert params['strict'].default is False  # Should default to False

    def test_render_orchestrator_accepts_quiet(self):
        """Test that RenderOrchestrator.process accepts quiet parameter."""
        import inspect

        from bengal.orchestration.render import RenderOrchestrator

        sig = inspect.signature(RenderOrchestrator.process)
        params = sig.parameters

        assert 'quiet' in params
        assert params['quiet'].default is False

    def test_streaming_orchestrator_accepts_quiet(self):
        """Test that StreamingRenderOrchestrator.process accepts quiet parameter."""
        import inspect

        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        sig = inspect.signature(StreamingRenderOrchestrator.process)
        params = sig.parameters

        assert 'quiet' in params
        assert params['quiet'].default is False


class TestValidateFlag:
    """Test --validate flag functionality."""

    def test_validate_flag_exists(self):
        """Test that --validate flag is recognized."""
        runner = CliRunner()
        result = runner.invoke(main, ['build', '--help'])

        assert '--validate' in result.output
        assert 'Validate templates' in result.output or 'validate' in result.output.lower()

    # Note: Full integration test would require a test site with templates
    # This is covered by integration tests


class TestStrictMode:
    """Test --strict flag functionality."""

    def test_strict_flag_exists(self):
        """Test that --strict flag is recognized."""
        runner = CliRunner()
        result = runner.invoke(main, ['build', '--help'])

        assert '--strict' in result.output
        assert 'strict' in result.output.lower()

    # Note: Full functionality test requires integration with health checks
    # This is covered by integration tests

