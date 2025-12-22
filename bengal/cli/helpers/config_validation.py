"""
Configuration validation helpers for CLI commands.

Provides utilities for validating Bengal configuration files, including
YAML syntax checking, type validation, value range checking, and
detection of unknown/misspelled configuration keys.

Functions:
    check_yaml_syntax: Validate YAML syntax for all config files
    validate_config_types: Check that config values have expected types
    validate_config_values: Validate value ranges and production requirements
    check_unknown_keys: Detect typos/unknown keys with fuzzy suggestions

Usage:
    >>> errors, warnings = [], []
    >>> check_yaml_syntax(config_dir, errors, warnings)
    >>> validate_config_types(config, errors, warnings)
    >>> if errors:
    ...     for e in errors: print(f"Error: {e}")
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

import yaml


def check_yaml_syntax(config_dir: Path, errors: list[str], warnings: list[str]) -> None:
    """
    Check YAML syntax for all config files in a directory.

    Recursively finds and parses all .yaml and .yml files, appending
    any syntax errors to the errors list.

    Args:
        config_dir: Root directory to scan for YAML files
        errors: List to append error messages to (modified in place)
        warnings: List to append warning messages to (modified in place)
    """
    yaml_files = list(config_dir.glob("**/*.yaml")) + list(config_dir.glob("**/*.yml"))

    for yaml_file in yaml_files:
        try:
            with yaml_file.open("r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML in {yaml_file.relative_to(config_dir)}: {e}")


def validate_config_types(config: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    """
    Validate that configuration values have the expected types.

    Checks known boolean fields like 'parallel', 'incremental', 'minify_html',
    etc. to ensure they are actually boolean values.

    Args:
        config: Parsed configuration dictionary
        errors: List to append error messages to (modified in place)
        warnings: List to append warning messages to (modified in place)
    """
    # Known boolean fields
    boolean_fields = [
        "parallel",
        "incremental",
        "minify_html",
        "generate_rss",
        "generate_sitemap",
        "validate_links",
    ]

    for field in boolean_fields:
        if field in config and not isinstance(config[field], bool):
            errors.append(f"'{field}' must be boolean, got {type(config[field]).__name__}")


def validate_config_values(
    config: dict[str, Any], environment: str, errors: list[str], warnings: list[str]
) -> None:
    """
    Validate configuration values and check for reasonable ranges.

    Performs environment-specific validation (e.g., production requires
    site.title) and checks that numeric values are within acceptable ranges.

    Args:
        config: Parsed configuration dictionary
        environment: Target environment ("local", "preview", "production")
        errors: List to append error messages to (modified in place)
        warnings: List to append warning messages to (modified in place)
    """
    # Check required fields for production
    if environment == "production" and "site" in config:
        if not config["site"].get("title"):
            warnings.append("'site.title' is recommended for production")
        if not config["site"].get("baseurl"):
            warnings.append("'site.baseurl' is recommended for production")

    # Check value ranges
    if "build" in config:
        max_workers = config["build"].get("max_workers")
        if max_workers is not None:
            if not isinstance(max_workers, int):
                errors.append(
                    f"'build.max_workers' must be integer, got {type(max_workers).__name__}"
                )
            elif max_workers < 0:
                errors.append("'build.max_workers' must be >= 0")
            elif max_workers > 100:
                warnings.append("'build.max_workers' > 100 seems excessive")


def check_unknown_keys(config: dict[str, Any], warnings: list[str]) -> None:
    """
    Check for unknown or misspelled configuration keys.

    Compares top-level keys against known sections and suggests corrections
    using fuzzy matching when possible typos are detected.

    Args:
        config: Parsed configuration dictionary
        warnings: List to append warning messages to (modified in place)
    """
    known_sections = {
        "site",
        "build",
        "features",
        "theme",
        "markdown",
        "assets",
        "pagination",
        "health",
        "dev",
        "output_formats",
    }

    for key in config:
        if key not in known_sections:
            # Check for typos
            suggestions = difflib.get_close_matches(key, known_sections, n=1, cutoff=0.6)
            if suggestions:
                warnings.append(f"Unknown section '{key}'. Did you mean '{suggestions[0]}'?")
