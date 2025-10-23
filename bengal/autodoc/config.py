"""
Configuration loader for autodoc.

Loads autodoc settings from bengal.toml or provides sensible defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import toml


def load_autodoc_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load autodoc configuration from bengal.toml.

    Args:
        config_path: Path to config file (default: ./bengal.toml)

    Returns:
        Autodoc configuration dict with defaults
    """
    # Default configuration
    default_config = {
        "python": {
            "enabled": True,
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
        },
        "openapi": {
            "enabled": False,
        },
        "cli": {
            "enabled": False,
            "app_module": None,  # e.g., 'bengal.cli:main'
            "framework": "click",  # 'click', 'argparse', 'typer'
            "output_dir": "content/cli",
            "include_hidden": False,
        },
    }

    # Try to load from file
    if config_path is None:
        config_path = Path("bengal.toml")

    if not config_path.exists():
        return default_config

    try:
        file_config = toml.load(config_path)

        # Merge with defaults
        if "autodoc" in file_config:
            autodoc_config = file_config["autodoc"]

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
                default_config["python"].update(python_user_config)

            # Merge OpenAPI config
            if "openapi" in autodoc_config:
                default_config["openapi"].update(autodoc_config["openapi"])

            # Merge CLI config
            if "cli" in autodoc_config:
                default_config["cli"].update(autodoc_config["cli"])

        return default_config

    except Exception as e:
        print(f"⚠️  Warning: Could not load config from {config_path}: {e}")
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
