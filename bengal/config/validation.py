"""
Configuration validation for required keys.

This module validates that required configuration keys exist at load time
to fail fast with clear error messages.

See Also:
- :mod:`bengal.config.loader`: Configuration loading.
- :mod:`bengal.config.defaults`: Default configuration values.

"""

from __future__ import annotations

from typing import Any

from bengal.errors import BengalConfigError, ErrorCode

# Required keys by section
REQUIRED_KEYS: dict[str, list[str]] = {
    "site": ["title"],
    "build": ["output_dir", "content_dir"],
}


def validate_config(config: dict[str, Any]) -> None:
    """
    Validate required keys exist. Raises ConfigError if missing.
    
    Args:
        config: Configuration dictionary to validate.
    
    Raises:
        BengalConfigError: If any required keys are missing.
    
    Example:
            >>> validate_config({"site": {"title": "My Site"}})
            >>> validate_config({"site": {}})  # Missing title
        BengalConfigError: Missing required config keys: site.title
        
    """
    missing: list[str] = []
    for section, keys in REQUIRED_KEYS.items():
        section_data = config.get(section, {})
        if not isinstance(section_data, dict):
            missing.append(f"{section} (not a dict)")
            continue
        for key in keys:
            if key not in section_data:
                missing.append(f"{section}.{key}")

    if missing:
        raise BengalConfigError(
            f"Missing required config keys: {', '.join(missing)}. "
            f"Add them to your bengal.yaml or config/_default/*.yaml",
            code=ErrorCode.C003,  # config_invalid_value
            suggestion="Add the missing keys to your configuration file",
        )
