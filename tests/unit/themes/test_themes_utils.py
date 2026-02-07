"""Tests for bengal.themes.utils module."""

from __future__ import annotations

import pytest

from bengal.errors import BengalConfigError, ErrorCode
from bengal.themes.utils import (
    CLI_DASHBOARD_TCSS_PATH,
    DEFAULT_CSS_TOKENS_PATH,
    DEFAULT_THEME_PATH,
    THEMES_ROOT,
    extract_with_defaults,
    validate_enum_field,
)


class TestPathConstants:
    """Tests for path constant definitions."""

    def test_themes_root_exists(self) -> None:
        """Verify THEMES_ROOT points to valid directory."""
        assert THEMES_ROOT.exists()
        assert THEMES_ROOT.is_dir()
        assert THEMES_ROOT.name == "themes"

    def test_default_theme_path_exists(self) -> None:
        """Verify DEFAULT_THEME_PATH points to default theme directory."""
        assert DEFAULT_THEME_PATH.exists()
        assert DEFAULT_THEME_PATH.is_dir()
        assert DEFAULT_THEME_PATH.name == "default"
        assert DEFAULT_THEME_PATH.parent == THEMES_ROOT

    def test_default_css_tokens_path_structure(self) -> None:
        """Verify DEFAULT_CSS_TOKENS_PATH has correct structure."""
        assert DEFAULT_CSS_TOKENS_PATH.parent.name == "css"
        assert DEFAULT_CSS_TOKENS_PATH.name == "tokens"
        # Path should be under default theme
        assert DEFAULT_THEME_PATH in DEFAULT_CSS_TOKENS_PATH.parents

    def test_cli_dashboard_tcss_path_structure(self) -> None:
        """Verify CLI_DASHBOARD_TCSS_PATH points to correct location."""
        assert CLI_DASHBOARD_TCSS_PATH.name == "bengal.tcss"
        assert CLI_DASHBOARD_TCSS_PATH.parent.name == "dashboard"


class TestValidateEnumField:
    """Tests for validate_enum_field utility."""

    def test_valid_value_passes(self) -> None:
        """Verify valid values pass without raising."""
        # Should not raise
        validate_enum_field("mode", "dark", {"light", "dark", "system"})
        validate_enum_field("mode", "light", {"light", "dark", "system"})
        validate_enum_field("mode", "system", {"light", "dark", "system"})

    def test_invalid_value_raises_bengal_config_error(self) -> None:
        """Verify invalid values raise BengalConfigError."""
        with pytest.raises(BengalConfigError) as exc_info:
            validate_enum_field("mode", "invalid", {"light", "dark", "system"})

        assert exc_info.value.code == ErrorCode.C003

    def test_error_message_includes_field_name(self) -> None:
        """Verify error message includes the field name."""
        with pytest.raises(BengalConfigError) as exc_info:
            validate_enum_field("default_mode", "invalid", {"light", "dark"})

        assert "default_mode" in str(exc_info.value)

    def test_error_message_includes_invalid_value(self) -> None:
        """Verify error message includes the invalid value."""
        with pytest.raises(BengalConfigError) as exc_info:
            validate_enum_field("mode", "bad_value", {"light", "dark"})

        assert "bad_value" in str(exc_info.value)

    def test_error_message_lists_valid_values_sorted(self) -> None:
        """Verify error message lists valid values in sorted order."""
        with pytest.raises(BengalConfigError) as exc_info:
            validate_enum_field("mode", "invalid", {"system", "light", "dark"})

        message = str(exc_info.value)
        # Values should appear sorted
        assert "dark, light, system" in message

    def test_suggestion_includes_valid_values(self) -> None:
        """Verify suggestion includes all valid values."""
        with pytest.raises(BengalConfigError) as exc_info:
            validate_enum_field("mode", "invalid", {"light", "dark"})

        assert exc_info.value.suggestion is not None
        assert "dark" in exc_info.value.suggestion
        assert "light" in exc_info.value.suggestion

    def test_do_record_error_false_still_raises(self) -> None:
        """Verify do_record_error=False still raises, just doesn't record."""
        with pytest.raises(BengalConfigError):
            validate_enum_field(
                "mode",
                "invalid",
                {"light", "dark"},
                do_record_error=False,
            )

    def test_empty_string_in_valid_values(self) -> None:
        """Verify empty string can be a valid value."""
        # Should not raise - empty string is valid
        validate_enum_field("palette", "", {"", "blue", "red"})

    def test_case_sensitive_validation(self) -> None:
        """Verify validation is case-sensitive."""
        with pytest.raises(BengalConfigError):
            validate_enum_field("mode", "DARK", {"light", "dark"})

        with pytest.raises(BengalConfigError):
            validate_enum_field("mode", "Dark", {"light", "dark"})


class TestExtractWithDefaults:
    """Tests for extract_with_defaults utility."""

    def test_extracts_existing_values(self) -> None:
        """Verify existing values are extracted from data."""
        data = {"name": "test", "version": "2.0"}
        fields = {"name": "default", "version": "1.0"}

        result = extract_with_defaults(data, fields)

        assert result == {"name": "test", "version": "2.0"}

    def test_uses_defaults_for_missing_values(self) -> None:
        """Verify defaults are used for missing keys."""
        data = {"name": "test"}
        fields = {"name": "default", "version": "1.0", "parent": None}

        result = extract_with_defaults(data, fields)

        assert result == {"name": "test", "version": "1.0", "parent": None}

    def test_empty_data_returns_all_defaults(self) -> None:
        """Verify empty data returns all default values."""
        data: dict[str, str] = {}
        fields = {"a": "default_a", "b": "default_b"}

        result = extract_with_defaults(data, fields)

        assert result == {"a": "default_a", "b": "default_b"}

    def test_empty_fields_returns_empty_dict(self) -> None:
        """Verify empty fields returns empty dict."""
        data = {"name": "test"}
        fields: dict[str, str] = {}

        result = extract_with_defaults(data, fields)

        assert result == {}

    def test_preserves_none_defaults(self) -> None:
        """Verify None defaults are preserved."""
        data = {"a": "value"}
        fields = {"a": None, "b": None}

        result = extract_with_defaults(data, fields)

        assert result == {"a": "value", "b": None}

    def test_preserves_complex_default_types(self) -> None:
        """Verify complex types (lists, dicts) work as defaults."""
        data = {"name": "test"}
        fields = {"name": "default", "items": [], "config": {}}

        result = extract_with_defaults(data, fields)

        assert result == {"name": "test", "items": [], "config": {}}

    def test_data_value_overrides_default_even_if_falsy(self) -> None:
        """Verify falsy data values (empty string, 0, False) override defaults."""
        data = {"empty": "", "zero": 0, "false": False}
        fields = {"empty": "default", "zero": 1, "false": True}

        result = extract_with_defaults(data, fields)

        assert result == {"empty": "", "zero": 0, "false": False}
