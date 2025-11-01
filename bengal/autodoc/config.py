"""
Configuration loader for autodoc.

Loads autodoc settings from config/ directory or bengal.toml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import toml


def load_autodoc_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load autodoc configuration from config/ directory or bengal.toml.

    Loading priority:
    1. config/_default/autodoc.yaml (directory-based config)
    2. bengal.toml (backward compatibility)
    3. Default configuration

    Args:
        config_path: Path to config file or directory (default: auto-detect)

    Returns:
        Autodoc configuration dict with defaults
    """
    # Default configuration (all disabled by default - opt-in via config)
    default_config = {
        "python": {
            "enabled": False,  # Disabled by default - enable in config
            "source_dirs": ["."],
            "output_dir": "content/api",
            "exclude": [
                "*/tests/*",
                "*/test_*.py",
                "*/__pycache__/*",
                "*/migrations/*",
            ],
            "docstring_style": "auto",
            "include_private": False,
            "include_special": False,
            # Alias and inherited member features
            "include_inherited": False,
            "include_inherited_by_type": {
                "class": False,
                "exception": False,
            },
            "alias_strategy": "canonical",  # Options: canonical, duplicate, list-only
            # URL grouping configuration
            "strip_prefix": None,  # Optional: prefix to strip from module names
            "grouping": {
                "mode": "off",  # Options: off, auto, explicit
                "prefix_map": {},  # For explicit mode: {"module.path": "group_name"}
            },
        },
        "openapi": {
            "enabled": False,
        },
        "cli": {
            "enabled": False,  # Disabled by default - enable in config
            "app_module": None,  # e.g., 'bengal.cli:main'
            "framework": "click",  # 'click', 'argparse', 'typer'
            "output_dir": "content/cli",
            "include_hidden": False,
        },
    }

    # Try directory-based config first (new system)
    config_dir = Path("config")
    if config_dir.exists() and config_dir.is_dir():
        try:
            from bengal.config.directory_loader import ConfigDirectoryLoader

            loader = ConfigDirectoryLoader()
            full_config = loader.load(config_dir, environment=None, profile=None)

            # Extract autodoc section if present
            if "autodoc" in full_config:
                return _merge_autodoc_config(default_config, full_config["autodoc"])

        except Exception as e:
            print(f"⚠️  Warning: Could not load config from {config_dir}: {e}")
            # Fall through to try bengal.toml

    # Try single-file config (backward compatibility)
    if config_path is None:
        config_path = Path("bengal.toml")

    if config_path.exists():
        try:
            file_config = toml.load(config_path)

            # Merge with defaults
            if "autodoc" in file_config:
                return _merge_autodoc_config(default_config, file_config["autodoc"])

        except Exception as e:
            print(f"⚠️  Warning: Could not load config from {config_path}: {e}")

    # Return defaults if no config found
    return default_config


def _merge_autodoc_config(
    default_config: dict[str, Any], autodoc_config: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge autodoc configuration with defaults.

    Args:
        default_config: Default configuration
        autodoc_config: User autodoc configuration

    Returns:
        Merged configuration
    """
    # Merge top-level settings (like use_html_renderer)
    for key, value in autodoc_config.items():
        if key not in ["python", "openapi", "cli"]:
            default_config[key] = value

    # Merge Python config
    if "python" in autodoc_config:
        python_user_config = autodoc_config["python"]

        # Handle nested include_inherited_by_type dict
        if "include_inherited_by_type" in python_user_config:
            default_config["python"]["include_inherited_by_type"].update(
                python_user_config["include_inherited_by_type"]
            )
            # Remove from user config to avoid overwriting default dict
            python_user_config = dict(python_user_config)
            python_user_config.pop("include_inherited_by_type")

        # Handle nested grouping dict
        if "grouping" in python_user_config:
            grouping_config = python_user_config["grouping"]
            # Validate mode if present
            if "mode" in grouping_config:
                mode = grouping_config["mode"]
                if mode not in ["off", "auto", "explicit"]:
                    print(f"⚠️  Warning: Invalid grouping mode '{mode}', using 'off'")
                    grouping_config["mode"] = "off"
            default_config["python"]["grouping"].update(grouping_config)
            # Remove from user config to avoid overwriting default dict
            python_user_config = dict(python_user_config)
            python_user_config.pop("grouping")

        default_config["python"].update(python_user_config)

    # Merge OpenAPI config
    if "openapi" in autodoc_config:
        default_config["openapi"].update(autodoc_config["openapi"])

    # Merge CLI config
    if "cli" in autodoc_config:
        default_config["cli"].update(autodoc_config["cli"])

    return default_config


def get_python_config(config: dict[str, Any]) -> dict[str, Any]:
    """Get Python autodoc configuration."""
    return config.get("python", {})


def get_openapi_config(config: dict[str, Any]) -> dict[str, Any]:
    """Get OpenAPI autodoc configuration."""
    return config.get("openapi", {})


def get_cli_config(config: dict[str, Any]) -> dict[str, Any]:
    """Get CLI autodoc configuration."""
    return config.get("cli", {})


def get_grouping_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    Get grouping configuration from Python autodoc config.

    Args:
        config: Full autodoc configuration dict

    Returns:
        Grouping configuration with mode and prefix_map

    Example:
        >>> config = load_autodoc_config()
        >>> grouping = get_grouping_config(config)
        >>> grouping["mode"]
        "off"
    """
    python_config = get_python_config(config)
    return python_config.get("grouping", {"mode": "off", "prefix_map": {}})
