"""Configuration validation helpers for CLI commands."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

import yaml


def check_yaml_syntax(config_dir: Path, errors: list[str], warnings: list[str]) -> None:
    """Check YAML syntax for all config files."""
    yaml_files = list(config_dir.glob("**/*.yaml")) + list(config_dir.glob("**/*.yml"))

    for yaml_file in yaml_files:
        try:
            with yaml_file.open("r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML in {yaml_file.relative_to(config_dir)}: {e}")


def validate_config_types(config: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    """Validate config value types."""
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
    """Validate config values and ranges."""
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
    """Check for unknown/typo keys."""
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
