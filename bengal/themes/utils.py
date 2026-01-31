"""
Shared utilities for theme configuration and validation.

This module centralizes common patterns used across the themes package:

Path Constants:
    THEMES_ROOT: Root directory of the themes package
    DEFAULT_THEME_PATH: Path to the bundled default theme
    DEFAULT_CSS_TOKENS_PATH: Path to generated CSS tokens directory

Validation Utilities:
    validate_enum_field: Validate config fields against allowed values

Config Helpers:
    extract_with_defaults: Extract fields from dict with default values

Example:
    >>> from bengal.themes.utils import validate_enum_field, THEMES_ROOT
    >>> validate_enum_field("mode", "dark", {"light", "dark", "system"})
    >>> print(THEMES_ROOT)
    PosixPath('.../bengal/themes')

Related:
    bengal/themes/config.py: Uses validation utilities
    bengal/themes/generate.py: Uses path constants
    bengal/core/theme/config.py: Uses validation utilities

"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.errors import BengalConfigError, ErrorCode, record_error

# ============================================================================
# Path Constants
# ============================================================================

#: Root directory of the themes package
THEMES_ROOT: Path = Path(__file__).parent

#: Path to the bundled default theme
DEFAULT_THEME_PATH: Path = THEMES_ROOT / "default"

#: Path to generated CSS tokens directory
DEFAULT_CSS_TOKENS_PATH: Path = DEFAULT_THEME_PATH / "assets" / "css" / "tokens"

#: Path to CLI dashboard TCSS file (for token validation)
CLI_DASHBOARD_TCSS_PATH: Path = THEMES_ROOT.parent / "cli" / "dashboard" / "bengal.tcss"


# ============================================================================
# Validation Utilities
# ============================================================================


def validate_enum_field(
    field_name: str,
    value: str,
    valid_values: set[str],
    *,
    do_record_error: bool = True,
) -> None:
    """
    Validate a config field against allowed enum values.

    Provides consistent error messages and handling for configuration fields
    that must be one of a predefined set of values. Used across theme config
    classes to reduce boilerplate validation code.

    Args:
        field_name: Name of the field being validated (for error messages).
            Use the config key name (e.g., "default_mode", "nav_position").
        value: The value to validate.
        valid_values: Set of allowed values. Values are sorted in error messages.
        do_record_error: Whether to call record_error() before raising.
            Set to False if the caller handles error recording separately.
            Defaults to True.

    Raises:
        BengalConfigError: If value is not in valid_values (code=C003).
            Error includes suggestion listing all valid values.

    Example:
        >>> validate_enum_field("default_mode", "dark", {"light", "dark", "system"})
        # No error - valid value

        >>> validate_enum_field("default_mode", "invalid", {"light", "dark", "system"})
        BengalConfigError: Invalid default_mode 'invalid'. Must be one of: dark, light, system

    """
    if value in valid_values:
        return

    sorted_values = ", ".join(sorted(valid_values))
    error = BengalConfigError(
        f"Invalid {field_name} '{value}'. Must be one of: {sorted_values}",
        code=ErrorCode.C003,
        suggestion=f"Set {field_name} to one of: {sorted_values}",
    )
    if do_record_error:
        record_error(error)
    raise error


# ============================================================================
# Config Dict Helpers
# ============================================================================


def extract_with_defaults(data: dict[str, Any], fields: dict[str, Any]) -> dict[str, Any]:
    """
    Extract fields from dict with defaults.

    Simplifies the common pattern of extracting multiple fields from a
    configuration dictionary while providing default values for missing keys.

    Args:
        data: Source dictionary to extract from.
        fields: Mapping of field_name -> default_value.
            Each key defines a field to extract, with its value as the default.

    Returns:
        Dictionary with extracted values. Keys match the fields argument,
        values come from data if present, otherwise from defaults.

    Example:
        >>> data = {"name": "custom", "version": "2.0"}
        >>> fields = {"name": "default", "version": "1.0", "parent": None}
        >>> extract_with_defaults(data, fields)
        {'name': 'custom', 'version': '2.0', 'parent': None}

    Note:
        This is a convenience wrapper around multiple dict.get() calls.
        For simple cases with 1-2 fields, direct .get() may be clearer.

    """
    return {name: data.get(name, default) for name, default in fields.items()}
