"""Tests for config validation.

Tests config/validators.py:
- ConfigValidationError: custom exception
- ConfigValidator: validation with type checking and coercion
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from bengal.config.validators import ConfigValidationError, ConfigValidator


class TestConfigValidationError:
    """Tests for ConfigValidationError exception."""

    def test_is_value_error(self):
        """ConfigValidationError is a ValueError subclass."""
        assert issubclass(ConfigValidationError, ValueError)

    def test_can_be_raised_with_message(self):
        """Can be raised with a message."""
        with pytest.raises(ConfigValidationError) as exc_info:
            raise ConfigValidationError("Test error")
        assert "Test error" in str(exc_info.value)


class TestConfigValidatorFields:
    """Tests for ConfigValidator field definitions."""

    def test_boolean_fields_defined(self):
        """Boolean fields are defined."""
        validator = ConfigValidator()
        assert "parallel" in validator.BOOLEAN_FIELDS
        assert "incremental" in validator.BOOLEAN_FIELDS
        assert "debug" in validator.BOOLEAN_FIELDS

    def test_integer_fields_defined(self):
        """Integer fields are defined."""
        validator = ConfigValidator()
        assert "max_workers" in validator.INTEGER_FIELDS
        assert "port" in validator.INTEGER_FIELDS

    def test_string_fields_defined(self):
        """String fields are defined."""
        validator = ConfigValidator()
        assert "title" in validator.STRING_FIELDS
        assert "baseurl" in validator.STRING_FIELDS


class TestConfigValidatorValidate:
    """Tests for ConfigValidator.validate method."""

    def test_valid_config_passes(self):
        """Valid config passes validation."""
        validator = ConfigValidator()
        config = {"title": "My Site", "parallel": True, "max_workers": 4}
        result = validator.validate(config)
        assert result["title"] == "My Site"
        assert result["parallel"] is True

    def test_empty_config_passes(self):
        """Empty config passes validation."""
        validator = ConfigValidator()
        result = validator.validate({})
        assert result == {}

    def test_invalid_boolean_raises_error(self):
        """Invalid boolean value raises ConfigValidationError."""
        validator = ConfigValidator()
        config = {"parallel": "invalid_string"}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)

    def test_invalid_integer_raises_error(self):
        """Invalid integer value raises ConfigValidationError."""
        validator = ConfigValidator()
        config = {"max_workers": "not_a_number"}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)

    def test_negative_max_workers_raises_error(self):
        """Negative max_workers raises ConfigValidationError."""
        validator = ConfigValidator()
        config = {"max_workers": -1}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)


class TestConfigValidatorTypeCoercion:
    """Tests for ConfigValidator type coercion."""

    def test_coerces_string_true_to_bool(self):
        """Coerces string 'true' to boolean True."""
        validator = ConfigValidator()
        config = {"parallel": "true"}
        result = validator.validate(config)
        assert result["parallel"] is True

    def test_coerces_string_false_to_bool(self):
        """Coerces string 'false' to boolean False."""
        validator = ConfigValidator()
        config = {"parallel": "false"}
        result = validator.validate(config)
        assert result["parallel"] is False

    def test_coerces_string_yes_to_bool(self):
        """Coerces string 'yes' to boolean True."""
        validator = ConfigValidator()
        config = {"debug": "yes"}
        result = validator.validate(config)
        assert result["debug"] is True

    def test_coerces_string_no_to_bool(self):
        """Coerces string 'no' to boolean False."""
        validator = ConfigValidator()
        config = {"debug": "no"}
        result = validator.validate(config)
        assert result["debug"] is False

    def test_coerces_int_to_bool(self):
        """Coerces integer to boolean."""
        validator = ConfigValidator()
        config = {"parallel": 1}
        result = validator.validate(config)
        assert result["parallel"] is True

    def test_coerces_zero_to_false(self):
        """Coerces zero to False."""
        validator = ConfigValidator()
        config = {"parallel": 0}
        result = validator.validate(config)
        assert result["parallel"] is False

    def test_coerces_string_to_int(self):
        """Coerces numeric string to integer."""
        validator = ConfigValidator()
        config = {"max_workers": "8"}
        result = validator.validate(config)
        assert result["max_workers"] == 8

    def test_coerces_non_string_to_string(self):
        """Coerces non-string values to string for string fields."""
        validator = ConfigValidator()
        config = {"title": 123}
        result = validator.validate(config)
        assert result["title"] == "123"


class TestConfigValidatorRanges:
    """Tests for ConfigValidator range validation."""

    def test_max_workers_zero_is_valid(self):
        """Zero max_workers is valid (means auto-detect)."""
        validator = ConfigValidator()
        config = {"max_workers": 0}
        result = validator.validate(config)
        assert result["max_workers"] == 0

    def test_max_workers_over_100_raises_warning(self):
        """max_workers over 100 raises validation error."""
        validator = ConfigValidator()
        config = {"max_workers": 101}
        # Should raise because > 100 is flagged as excessive
        with pytest.raises(ConfigValidationError):
            validator.validate(config)

    def test_negative_min_page_size_raises_error(self):
        """Negative min_page_size raises error."""
        validator = ConfigValidator()
        config = {"min_page_size": -1}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)

    def test_pagination_per_page_zero_raises_error(self):
        """pagination.per_page of zero raises error."""
        validator = ConfigValidator()
        config = {"pagination": {"per_page": 0}}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)

    def test_pagination_per_page_over_1000_raises_error(self):
        """pagination.per_page over 1000 raises error."""
        validator = ConfigValidator()
        config = {"pagination": {"per_page": 1001}}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)

    def test_port_below_1_raises_error(self):
        """Port below 1 raises error."""
        validator = ConfigValidator()
        config = {"port": 0}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)

    def test_port_above_65535_raises_error(self):
        """Port above 65535 raises error."""
        validator = ConfigValidator()
        config = {"port": 65536}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)


class TestConfigValidatorFlattenConfig:
    """Tests for ConfigValidator config flattening."""

    def test_flattens_site_section(self):
        """Flattens 'site' section to root."""
        validator = ConfigValidator()
        config = {"site": {"title": "My Site", "language": "en"}}
        result = validator._flatten_config(config)
        assert result["title"] == "My Site"
        assert result["language"] == "en"

    def test_flattens_build_section(self):
        """Flattens 'build' section to root."""
        validator = ConfigValidator()
        config = {"build": {"parallel": True, "incremental": True}}
        result = validator._flatten_config(config)
        assert result["parallel"] is True
        assert result["incremental"] is True

    def test_handles_assets_section(self):
        """Handles 'assets' section with suffix mapping."""
        validator = ConfigValidator()
        config = {"assets": {"minify": True, "optimize": False}}
        result = validator._flatten_config(config)
        assert result["minify_assets"] is True
        assert result["optimize_assets"] is False

    def test_preserves_flat_keys(self):
        """Preserves already-flat keys."""
        validator = ConfigValidator()
        config = {"title": "My Site", "parallel": True}
        result = validator._flatten_config(config)
        assert result["title"] == "My Site"
        assert result["parallel"] is True

    def test_preserves_pagination_section(self):
        """Preserves pagination section as-is."""
        validator = ConfigValidator()
        config = {"pagination": {"per_page": 20}}
        result = validator._flatten_config(config)
        assert result["pagination"] == {"per_page": 20}


class TestConfigValidatorErrorPrinting:
    """Tests for ConfigValidator error printing."""

    def test_prints_errors_with_count(self):
        """Prints error count in output."""
        validator = ConfigValidator()
        errors = ["Error 1", "Error 2"]
        output = StringIO()

        def capture_print(*args):
            if args:
                output.write(str(args[0]) + "\n")

        with patch("builtins.print", capture_print):
            validator._print_errors(errors)
        result = output.getvalue()
        assert "❌" in result
        assert "1." in result
        assert "2." in result

    def test_prints_source_file_if_provided(self):
        """Prints source file in error output."""
        validator = ConfigValidator()
        errors = ["Error 1"]
        output = StringIO()

        def capture_print(*args):
            if args:
                output.write(str(args[0]) + "\n")

        with patch("builtins.print", capture_print):
            validator._print_errors(errors, source_file=Path("bengal.toml"))
        result = output.getvalue()
        assert "bengal.toml" in result

    def test_logs_errors(self):
        """Logs errors with structured logging."""
        validator = ConfigValidator()
        errors = ["Error 1"]
        with patch("bengal.config.validators.logger") as mock_logger:
            with patch("builtins.print"):  # Suppress print
                validator._print_errors(errors)
            mock_logger.error.assert_called()


class TestConfigValidatorCaseSensitivity:
    """Tests for case-insensitive boolean coercion."""

    def test_uppercase_true(self):
        """Handles uppercase TRUE."""
        validator = ConfigValidator()
        config = {"parallel": "TRUE"}
        result = validator.validate(config)
        assert result["parallel"] is True

    def test_mixed_case_false(self):
        """Handles mixed case False."""
        validator = ConfigValidator()
        config = {"parallel": "False"}
        result = validator.validate(config)
        assert result["parallel"] is False

    def test_uppercase_yes(self):
        """Handles uppercase YES."""
        validator = ConfigValidator()
        config = {"debug": "YES"}
        result = validator.validate(config)
        assert result["debug"] is True

    def test_on_off_strings(self):
        """Handles on/off strings."""
        validator = ConfigValidator()
        config = {"parallel": "on", "debug": "off"}
        result = validator.validate(config)
        assert result["parallel"] is True
        assert result["debug"] is False

    def test_string_one_zero(self):
        """Handles '1' and '0' strings."""
        validator = ConfigValidator()
        config = {"parallel": "1", "debug": "0"}
        result = validator.validate(config)
        assert result["parallel"] is True
        assert result["debug"] is False

