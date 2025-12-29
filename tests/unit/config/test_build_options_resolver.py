"""
Unit tests for unified build options resolution.

Tests precedence: CLI > config > DEFAULTS, with defensive path handling
and string boolean coercion.

Note: parallel processing is now auto-detected via should_parallelize().
The force_sequential option is used to explicitly disable parallel processing.
"""

from __future__ import annotations

from bengal.config.build_options_resolver import CLIFlags, resolve_build_options
from bengal.config.defaults import DEFAULTS


class TestCLIFlagsPrecedence:
    """Test that CLI flags take precedence over config and defaults."""

    def test_cli_force_sequential_wins_over_default(self):
        """CLI force_sequential flag takes precedence."""
        config = {}
        cli = CLIFlags(force_sequential=True)

        options = resolve_build_options(config, cli)

        assert options.force_sequential is True

    def test_cli_incremental_wins_over_config(self):
        """CLI flag takes precedence over config."""
        config = {"incremental": False}
        cli = CLIFlags(incremental=True)

        options = resolve_build_options(config, cli)

        assert options.incremental is True

    def test_none_cli_flag_means_not_passed(self):
        """None in CLIFlags means 'use config or default'."""
        config = {"incremental": False}
        cli = CLIFlags(incremental=None)  # Explicitly not passed

        options = resolve_build_options(config, cli)

        assert options.incremental is False  # From config


class TestConfigPrecedence:
    """Test that config takes precedence over DEFAULTS."""

    def test_config_wins_over_defaults(self):
        """Config takes precedence over DEFAULTS."""
        config = {"incremental": False}

        options = resolve_build_options(config)

        assert options.incremental is False  # Config wins

    def test_defaults_used_when_not_set(self):
        """DEFAULTS used when neither CLI nor config sets value."""
        config = {}

        options = resolve_build_options(config)

        assert options.incremental == DEFAULTS["incremental"]

    def test_flattened_config_path(self):
        """Flattened config path (quiet) is checked first."""
        config = {"quiet": True}

        options = resolve_build_options(config)

        assert options.quiet is True

    def test_nested_config_path(self):
        """Nested config path (build.quiet) is checked as fallback."""
        config = {"build": {"quiet": True}}

        options = resolve_build_options(config)

        assert options.quiet is True

    def test_flattened_takes_precedence_over_nested(self):
        """Flattened path takes precedence over nested if both exist."""
        config = {"quiet": True, "build": {"quiet": False}}

        options = resolve_build_options(config)

        assert options.quiet is True  # Flattened wins


class TestStringBooleanCoercion:
    """Test string boolean coercion for config values."""

    def test_string_true_coerced(self):
        """String 'true' is coerced to boolean True."""
        config = {"quiet": "true"}

        options = resolve_build_options(config)

        assert options.quiet is True

    def test_string_false_coerced(self):
        """String 'false' is coerced to boolean False."""
        config = {"quiet": "false"}

        options = resolve_build_options(config)

        assert options.quiet is False

    def test_string_case_insensitive(self):
        """String boolean coercion is case-insensitive."""
        config = {"quiet": "TRUE"}

        options = resolve_build_options(config)

        assert options.quiet is True

    def test_string_variants(self):
        """Various string boolean variants are supported."""
        for true_val in ("true", "1", "yes", "on", "TRUE", "Yes"):
            config = {"quiet": true_val}
            options = resolve_build_options(config)
            assert options.quiet is True, f"Failed for: {true_val}"

        for false_val in ("false", "0", "no", "off", "FALSE", "No"):
            config = {"quiet": false_val}
            options = resolve_build_options(config)
            assert options.quiet is False, f"Failed for: {false_val}"

    def test_nested_string_boolean(self):
        """String booleans in nested paths are also coerced."""
        config = {"build": {"quiet": "false"}}

        options = resolve_build_options(config)

        assert options.quiet is False


class TestFastMode:
    """Test fast mode special handling."""

    def test_fast_mode_forces_quiet(self):
        """Fast mode forces quiet=True."""
        config = {"quiet": False}
        cli = CLIFlags(fast=True)

        options = resolve_build_options(config, cli)

        # Fast mode forces quiet=True
        assert options.quiet is True

    def test_fast_mode_from_config(self):
        """Fast mode from config also forces quiet."""
        config = {"fast_mode": True, "quiet": False}

        options = resolve_build_options(config)

        assert options.quiet is True

    def test_fast_mode_cli_overrides_config(self):
        """CLI fast flag overrides config fast_mode."""
        config = {"fast_mode": False, "quiet": False}
        cli = CLIFlags(fast=True)

        options = resolve_build_options(config, cli)

        assert options.quiet is True  # Fast mode from CLI forces quiet


class TestAllBuildOptions:
    """Test resolution of all build options."""

    def test_incremental_resolution(self):
        """Incremental option is resolved correctly."""
        config = {"incremental": False}
        cli = CLIFlags(incremental=True)

        options = resolve_build_options(config, cli)

        assert options.incremental is True  # CLI wins

    def test_quiet_resolution(self):
        """Quiet option is resolved correctly."""
        config = {"quiet": True}

        options = resolve_build_options(config)

        assert options.quiet is True

    def test_verbose_resolution(self):
        """Verbose option is resolved correctly."""
        config = {"verbose": True}
        cli = CLIFlags(verbose=False)

        options = resolve_build_options(config, cli)

        assert options.verbose is False  # CLI wins

    def test_strict_resolution(self):
        """Strict option is resolved correctly (maps to strict_mode in config)."""
        config = {"strict_mode": True}
        cli = CLIFlags(strict=False)

        options = resolve_build_options(config, cli)

        assert options.strict is False  # CLI wins

    def test_memory_optimized_resolution(self):
        """Memory optimized option is resolved correctly."""
        config = {"memory_optimized": True}

        options = resolve_build_options(config)

        assert options.memory_optimized is True

    def test_profile_templates_resolution(self):
        """Profile templates option is resolved correctly."""
        config = {"profile_templates": True}
        cli = CLIFlags(profile_templates=False)

        options = resolve_build_options(config, cli)

        assert options.profile_templates is False  # CLI wins


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_config(self):
        """Empty config falls back to DEFAULTS."""
        config = {}

        options = resolve_build_options(config)

        # force_sequential defaults to False (auto-detect mode)
        assert options.force_sequential is False
        assert options.incremental == DEFAULTS["incremental"]
        assert options.quiet == DEFAULTS.get("quiet", False)

    def test_none_config_values(self):
        """None config values are treated as missing."""
        config = {"incremental": None}

        options = resolve_build_options(config)

        # None should fall back to DEFAULTS
        assert options.incremental == DEFAULTS["incremental"]

    def test_invalid_nested_structure(self):
        """Invalid nested structure (non-dict) is handled gracefully."""
        config = {"build": "not-a-dict"}

        options = resolve_build_options(config)

        # Should fall back to DEFAULTS for values not found
        assert options.incremental == DEFAULTS["incremental"]

    def test_mixed_flattened_and_nested(self):
        """Config with both flattened and nested sections works."""
        config = {
            "quiet": True,  # Flattened
            "build": {"incremental": False},  # Nested
        }

        options = resolve_build_options(config)

        assert options.quiet is True  # From flattened
        assert options.incremental is False  # From nested

    def test_non_boolean_strings_not_coerced(self):
        """Non-boolean strings are not coerced (should use DEFAULTS)."""
        config = {"quiet": "maybe"}  # Not a recognized boolean string

        options = resolve_build_options(config)

        # "maybe" won't match recognized values, falls back to DEFAULTS
        assert options.quiet == DEFAULTS.get("quiet", False)


class TestRealWorldScenarios:
    """Test real-world configuration scenarios."""

    def test_dev_server_config(self):
        """Dev server config (no CLI flags)."""
        config = {"incremental": True, "quiet": False}

        options = resolve_build_options(config)

        # force_sequential defaults to False (auto-detect)
        assert options.force_sequential is False
        assert options.incremental is True

    def test_production_build_config(self):
        """Production build with CLI overrides."""
        config = {"strict_mode": False}
        cli = CLIFlags(strict=True, quiet=True)

        options = resolve_build_options(config, cli)

        # force_sequential defaults to False (auto-detect)
        assert options.force_sequential is False
        assert options.strict is True  # From CLI
        assert options.quiet is True  # From CLI

    def test_fast_mode_ci_build(self):
        """CI build with fast mode enabled."""
        config = {"fast_mode": True}

        options = resolve_build_options(config)

        # force_sequential defaults to False (auto-detect)
        assert options.force_sequential is False
        assert options.quiet is True  # Fast mode forces quiet


class TestForceSequential:
    """Test force_sequential option behavior."""

    def test_force_sequential_default(self):
        """force_sequential defaults to False (auto-detect mode)."""
        options = resolve_build_options({})

        assert options.force_sequential is False

    def test_force_sequential_from_cli(self):
        """force_sequential can be set via CLI."""
        cli = CLIFlags(force_sequential=True)
        options = resolve_build_options({}, cli)

        assert options.force_sequential is True

    def test_force_sequential_not_from_config(self):
        """force_sequential is NOT read from config (CLI only)."""
        # Even if config has force_sequential, it's not read
        config = {"force_sequential": True}
        options = resolve_build_options(config)

        # Should still be False (default) because it's CLI-only
        assert options.force_sequential is False
