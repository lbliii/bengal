"""
Unit tests for unified build options resolution.

Tests precedence: CLI > config > DEFAULTS, with defensive path handling
and string boolean coercion.
"""

from __future__ import annotations

from bengal.config.build_options_resolver import CLIFlags, resolve_build_options
from bengal.config.defaults import DEFAULTS


class TestCLIFlagsPrecedence:
    """Test that CLI flags take precedence over config and defaults."""

    def test_cli_wins_over_config(self):
        """CLI flag takes precedence over config."""
        config = {"parallel": True}
        cli = CLIFlags(parallel=False)

        options = resolve_build_options(config, cli)

        assert options.parallel is False

    def test_cli_wins_over_defaults(self):
        """CLI flag takes precedence over DEFAULTS."""
        config = {}  # No config value

        cli = CLIFlags(parallel=False)
        options = resolve_build_options(config, cli)

        assert options.parallel is False  # CLI wins over DEFAULTS

    def test_none_cli_flag_means_not_passed(self):
        """None in CLIFlags means 'use config or default'."""
        config = {"parallel": False}
        cli = CLIFlags(parallel=None)  # Explicitly not passed

        options = resolve_build_options(config, cli)

        assert options.parallel is False  # From config


class TestConfigPrecedence:
    """Test that config takes precedence over DEFAULTS."""

    def test_config_wins_over_defaults(self):
        """Config takes precedence over DEFAULTS."""
        config = {"parallel": False}

        options = resolve_build_options(config)

        assert options.parallel is False  # Config wins

    def test_defaults_used_when_not_set(self):
        """DEFAULTS used when neither CLI nor config sets value."""
        config = {}

        options = resolve_build_options(config)

        assert options.parallel == DEFAULTS["parallel"]

    def test_flattened_config_path(self):
        """Flattened config path (parallel) is checked first."""
        config = {"parallel": False}

        options = resolve_build_options(config)

        assert options.parallel is False

    def test_nested_config_path(self):
        """Nested config path (build.parallel) is checked as fallback."""
        config = {"build": {"parallel": False}}

        options = resolve_build_options(config)

        assert options.parallel is False

    def test_flattened_takes_precedence_over_nested(self):
        """Flattened path takes precedence over nested if both exist."""
        config = {"parallel": True, "build": {"parallel": False}}

        options = resolve_build_options(config)

        assert options.parallel is True  # Flattened wins


class TestStringBooleanCoercion:
    """Test string boolean coercion for config values."""

    def test_string_true_coerced(self):
        """String 'true' is coerced to boolean True."""
        config = {"parallel": "true"}

        options = resolve_build_options(config)

        assert options.parallel is True

    def test_string_false_coerced(self):
        """String 'false' is coerced to boolean False."""
        config = {"parallel": "false"}

        options = resolve_build_options(config)

        assert options.parallel is False

    def test_string_case_insensitive(self):
        """String boolean coercion is case-insensitive."""
        config = {"parallel": "TRUE"}

        options = resolve_build_options(config)

        assert options.parallel is True

    def test_string_variants(self):
        """Various string boolean variants are supported."""
        for true_val in ("true", "1", "yes", "on", "TRUE", "Yes"):
            config = {"parallel": true_val}
            options = resolve_build_options(config)
            assert options.parallel is True, f"Failed for: {true_val}"

        for false_val in ("false", "0", "no", "off", "FALSE", "No"):
            config = {"parallel": false_val}
            options = resolve_build_options(config)
            assert options.parallel is False, f"Failed for: {false_val}"

    def test_nested_string_boolean(self):
        """String booleans in nested paths are also coerced."""
        config = {"build": {"parallel": "false"}}

        options = resolve_build_options(config)

        assert options.parallel is False


class TestFastMode:
    """Test fast mode special handling."""

    def test_fast_mode_forces_parallel_and_quiet(self):
        """Fast mode forces parallel=True and quiet=True."""
        config = {"parallel": False, "quiet": False}
        cli = CLIFlags(fast=True)

        options = resolve_build_options(config, cli)

        assert options.parallel is True  # Fast mode overrides
        assert options.quiet is True  # Fast mode overrides

    def test_fast_mode_from_config(self):
        """Fast mode from config also forces parallel and quiet."""
        config = {"fast_mode": True, "parallel": False, "quiet": False}

        options = resolve_build_options(config)

        assert options.parallel is True
        assert options.quiet is True

    def test_fast_mode_cli_overrides_config(self):
        """CLI fast flag overrides config fast_mode."""
        config = {"fast_mode": False, "parallel": False}
        cli = CLIFlags(fast=True)

        options = resolve_build_options(config, cli)

        assert options.parallel is True  # Fast mode from CLI


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

        assert options.parallel == DEFAULTS["parallel"]
        assert options.incremental == DEFAULTS["incremental"]
        assert options.quiet == DEFAULTS.get("quiet", False)

    def test_none_config_values(self):
        """None config values are treated as missing."""
        config = {"parallel": None}

        options = resolve_build_options(config)

        # None should fall back to DEFAULTS
        assert options.parallel == DEFAULTS["parallel"]

    def test_invalid_nested_structure(self):
        """Invalid nested structure (non-dict) is handled gracefully."""
        config = {"build": "not-a-dict"}

        options = resolve_build_options(config)

        # Should fall back to DEFAULTS
        assert options.parallel == DEFAULTS["parallel"]

    def test_mixed_flattened_and_nested(self):
        """Config with both flattened and nested sections works."""
        config = {
            "parallel": True,  # Flattened
            "build": {"incremental": False},  # Nested
        }

        options = resolve_build_options(config)

        assert options.parallel is True  # From flattened
        assert options.incremental is False  # From nested

    def test_non_boolean_strings_not_coerced(self):
        """Non-boolean strings are not coerced (should use DEFAULTS)."""
        config = {"parallel": "maybe"}  # Not a recognized boolean string

        options = resolve_build_options(config)

        # Should treat as truthy string, which bool() converts to True
        # But our coercion only handles recognized values, so "maybe" -> True via bool()
        # Actually, wait - our code checks if it's in the recognized list first
        # So "maybe" won't match, and we return None, falling back to DEFAULTS
        assert options.parallel == DEFAULTS["parallel"]


class TestRealWorldScenarios:
    """Test real-world configuration scenarios."""

    def test_dev_server_config(self):
        """Dev server config (no CLI flags)."""
        config = {"parallel": False, "incremental": True}

        options = resolve_build_options(config)

        assert options.parallel is False
        assert options.incremental is True

    def test_production_build_config(self):
        """Production build with CLI overrides."""
        config = {"parallel": True, "strict_mode": False}
        cli = CLIFlags(strict=True, quiet=True)

        options = resolve_build_options(config, cli)

        assert options.parallel is True  # From config
        assert options.strict is True  # From CLI
        assert options.quiet is True  # From CLI

    def test_fast_mode_ci_build(self):
        """CI build with fast mode enabled."""
        config = {"fast_mode": True}

        options = resolve_build_options(config)

        assert options.parallel is True  # Fast mode forces
        assert options.quiet is True  # Fast mode forces
