"""
Tests for the build profile system.
"""

from bengal.utils.profile import (
    BuildProfile,
    get_current_profile,
    get_enabled_health_checks,
    is_validator_enabled,
    set_current_profile,
    should_collect_metrics,
    should_show_debug,
    should_track_memory,
)


class TestBuildProfile:
    """Test BuildProfile enum and configuration."""

    def test_from_string_valid(self):
        """Test parsing valid profile strings."""
        assert BuildProfile.from_string("writer") == BuildProfile.WRITER
        assert BuildProfile.from_string("theme-dev") == BuildProfile.THEME_DEV
        assert BuildProfile.from_string("theme_dev") == BuildProfile.THEME_DEV
        assert BuildProfile.from_string("dev") == BuildProfile.DEVELOPER
        assert BuildProfile.from_string("developer") == BuildProfile.DEVELOPER
        assert BuildProfile.from_string("debug") == BuildProfile.DEVELOPER

    def test_from_string_case_insensitive(self):
        """Test case-insensitive parsing."""
        assert BuildProfile.from_string("WRITER") == BuildProfile.WRITER
        assert BuildProfile.from_string("Theme-Dev") == BuildProfile.THEME_DEV
        assert BuildProfile.from_string("DEV") == BuildProfile.DEVELOPER

    def test_from_string_invalid(self):
        """Test invalid strings default to WRITER."""
        assert BuildProfile.from_string("invalid") == BuildProfile.WRITER
        assert BuildProfile.from_string("") == BuildProfile.WRITER
        assert BuildProfile.from_string(None) == BuildProfile.WRITER

    def test_from_cli_args_precedence(self):
        """Test CLI argument precedence."""
        # dev flag takes priority
        assert BuildProfile.from_cli_args(dev=True, theme_dev=True) == BuildProfile.DEVELOPER
        assert BuildProfile.from_cli_args(dev=True, debug=True) == BuildProfile.DEVELOPER

        # theme_dev flag is second priority
        assert BuildProfile.from_cli_args(theme_dev=True, debug=True) == BuildProfile.THEME_DEV

        # profile option is third
        assert BuildProfile.from_cli_args(profile="writer") == BuildProfile.WRITER

        # debug flag is fourth (maps to DEVELOPER)
        assert BuildProfile.from_cli_args(debug=True) == BuildProfile.DEVELOPER

        # default is writer
        assert BuildProfile.from_cli_args() == BuildProfile.WRITER

    def test_writer_config(self):
        """Test writer profile configuration."""
        config = BuildProfile.WRITER.get_config()

        assert config["show_phase_timing"] is False
        assert config["track_memory"] is False
        assert config["enable_debug_output"] is False
        assert config["collect_metrics"] is False
        assert config["verbose_build_stats"] is False

        # Only critical health checks
        health_checks = config["health_checks"]["enabled"]
        assert "config" in health_checks
        assert "output" in health_checks
        assert "links" in health_checks
        assert "performance" not in health_checks

    def test_theme_dev_config(self):
        """Test theme-dev profile configuration."""
        config = BuildProfile.THEME_DEV.get_config()

        assert config["show_phase_timing"] is True
        assert config["track_memory"] is False
        assert config["enable_debug_output"] is False
        assert config["collect_metrics"] is True
        assert config["verbose_build_stats"] is True

        # Theme-focused health checks
        health_checks = config["health_checks"]["enabled"]
        assert "rendering" in health_checks
        assert "directives" in health_checks
        assert "navigation" in health_checks
        assert "performance" not in health_checks
        assert "cache" not in health_checks

    def test_developer_config(self):
        """Test developer profile configuration."""
        config = BuildProfile.DEVELOPER.get_config()

        assert config["show_phase_timing"] is True
        assert config["track_memory"] is True
        assert config["enable_debug_output"] is True
        assert config["collect_metrics"] is True
        assert config["verbose_build_stats"] is True

        # All health checks
        assert config["health_checks"]["enabled"] == "all"


class TestProfileHelpers:
    """Test profile helper functions."""

    def test_set_get_current_profile(self):
        """Test setting and getting current profile."""
        set_current_profile(BuildProfile.DEVELOPER)
        assert get_current_profile() == BuildProfile.DEVELOPER

        set_current_profile(BuildProfile.WRITER)
        assert get_current_profile() == BuildProfile.WRITER

    def test_should_show_debug(self):
        """Test debug output check."""
        set_current_profile(BuildProfile.WRITER)
        assert should_show_debug() is False

        set_current_profile(BuildProfile.THEME_DEV)
        assert should_show_debug() is False

        set_current_profile(BuildProfile.DEVELOPER)
        assert should_show_debug() is True

    def test_should_track_memory(self):
        """Test memory tracking check."""
        set_current_profile(BuildProfile.WRITER)
        assert should_track_memory() is False

        set_current_profile(BuildProfile.THEME_DEV)
        assert should_track_memory() is False

        set_current_profile(BuildProfile.DEVELOPER)
        assert should_track_memory() is True

    def test_should_collect_metrics(self):
        """Test metrics collection check."""
        set_current_profile(BuildProfile.WRITER)
        assert should_collect_metrics() is False

        set_current_profile(BuildProfile.THEME_DEV)
        assert should_collect_metrics() is True

        set_current_profile(BuildProfile.DEVELOPER)
        assert should_collect_metrics() is True

    def test_get_enabled_health_checks(self):
        """Test getting enabled health checks."""
        set_current_profile(BuildProfile.WRITER)
        enabled = get_enabled_health_checks()
        assert "config" in enabled or "all" not in enabled

        set_current_profile(BuildProfile.DEVELOPER)
        enabled = get_enabled_health_checks()
        assert enabled == ["all"]

    def test_is_validator_enabled(self):
        """Test validator enabled check."""
        set_current_profile(BuildProfile.WRITER)
        assert is_validator_enabled("config") is True
        assert is_validator_enabled("links") is True
        assert is_validator_enabled("performance") is False
        assert is_validator_enabled("cache") is False

        set_current_profile(BuildProfile.THEME_DEV)
        assert is_validator_enabled("rendering") is True
        assert is_validator_enabled("directives") is True
        assert is_validator_enabled("performance") is False

        set_current_profile(BuildProfile.DEVELOPER)
        assert is_validator_enabled("performance") is True
        assert is_validator_enabled("cache") is True
        assert is_validator_enabled("anything") is True  # 'all' enables everything

    def test_validator_name_normalization(self):
        """Test validator name normalization (spaces and case)."""
        set_current_profile(BuildProfile.WRITER)

        # These should all work
        assert is_validator_enabled("config") is True
        assert is_validator_enabled("Config") is True
        assert is_validator_enabled("output") is True
        assert is_validator_enabled("Output") is True
