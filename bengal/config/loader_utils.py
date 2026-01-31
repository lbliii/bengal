"""
Shared utilities for configuration loaders.

This module provides common functions used by ConfigLoader, ConfigDirectoryLoader,
and UnifiedConfigLoader to avoid code duplication.

Inspired by refactoring work from @detailobsessed (Ismar Slomic).

Functions:
    load_yaml_file: Load a single YAML file with error handling.
    extract_baseurl: Extract baseurl from a config dict.
    flatten_config: Flatten nested configuration for easier access.
    warn_search_ui_without_index: Warn about search UI misconfiguration.
    load_environment_config: Load environment-specific configuration.
    load_profile_config: Load profile-specific configuration.
    get_default_config: Get a deep copy of DEFAULTS.

"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bengal.config.environment import get_environment_file_candidates
from bengal.config.utils import get_default_config
from bengal.errors import BengalConfigError, ErrorCode, record_error
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


def load_yaml_file(path: Path) -> dict[str, Any]:
    """
    Load a single YAML file with comprehensive error handling.

    Parses the YAML file and returns its contents as a dictionary.
    Provides detailed error messages with line numbers for syntax errors.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed YAML content as a dictionary. Returns an empty dict
        if the file is empty or contains only ``null``.

    Raises:
        BengalConfigError: If YAML parsing fails (with line number if available)
            or if the file cannot be read (permissions, encoding, etc.).
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
            return content or {}
    except yaml.YAMLError as e:
        # Extract line number from YAML error if available
        line_number = getattr(e, "problem_mark", None)
        line_num = (
            (line_number.line + 1) if line_number and hasattr(line_number, "line") else None
        )

        error = BengalConfigError(
            f"Invalid YAML in {path}: {e}",
            code=ErrorCode.C001,
            file_path=path,
            line_number=line_num,
            suggestion="Check YAML syntax, indentation, and ensure all quotes are properly closed",
            original_error=e,
        )
        record_error(error, file_path=str(path))
        raise error from e
    except Exception as e:
        error = BengalConfigError(
            f"Failed to load {path}: {e}",
            code=ErrorCode.C003,
            file_path=path,
            suggestion="Check file permissions and encoding (must be UTF-8)",
            original_error=e if isinstance(e, Exception) else None,
        )
        record_error(error, file_path=str(path))
        raise error from e


def extract_baseurl(config: dict[str, Any] | None) -> Any:
    """
    Extract baseurl from a config dict if explicitly provided.

    Checks both nested ``site.baseurl`` and flat ``baseurl`` keys.

    Args:
        config: Configuration dictionary to extract from.

    Returns:
        The baseurl value if present (including empty string), or None if missing.
    """
    if not config or not isinstance(config, dict):
        return None

    # Prefer nested site.baseurl
    site_section = config.get("site")
    if isinstance(site_section, dict) and "baseurl" in site_section:
        return site_section.get("baseurl")

    # Fallback to flat baseurl
    if "baseurl" in config:
        return config.get("baseurl")

    return None


def flatten_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten nested configuration for easier access.

    Extracts values from common sections to the top level while preserving
    the original section structure. This allows both flat access
    (``config["title"]``) and section access (``config["site"]["title"]``).
    Nested values (site.*, build.*, etc.) take precedence over top-level
    values for consistency with Bengal's nested-first architecture.

    Sections flattened:
        - ``site.*`` → top level (title, baseurl, etc.)
        - ``build.*`` → top level (parallel, incremental, etc.)
        - ``features.*`` → top level (rss, sitemap, etc.)
        - ``assets.*`` → top level (minify, optimize, etc.)

    Note: ``dev.*`` is NOT flattened to preserve environment-specific nesting.

    Args:
        config: Nested configuration dictionary.

    Returns:
        Flattened configuration dictionary. Original sections are preserved
        and values are also accessible at the top level.
    """
    flat = dict(config)

    # Extract values from known sections to top level
    # Specific nested values override general flat values
    # Note: "dev" is excluded from flattening to preserve environment-specific nesting
    for section in ("site", "build", "assets", "features"):
        if section in config and isinstance(config[section], dict):
            flat.update(config[section])

    return flat


def warn_search_ui_without_index(config: dict[str, Any]) -> None:
    """
    Warn if theme.features has search but search index won't be generated.

    This catches a common confusion: users set ``theme.features: [search]``
    (which only enables UI components) but don't realize they also need
    ``features.search: true`` or ``output_formats.site_wide: [index_json]``
    for search to actually work.

    Args:
        config: Configuration dictionary after feature expansion.
    """
    # Get theme.features (UI flags - list of strings)
    theme = config.get("theme", {})
    if not isinstance(theme, dict):
        return

    theme_features = theme.get("features", [])
    if not isinstance(theme_features, list):
        return

    # Check if "search" is in theme.features
    has_search_ui = any(
        f == "search" or (isinstance(f, str) and f.startswith("search."))
        for f in theme_features
    )

    if not has_search_ui:
        return

    # Check if search index will be generated
    output_formats = config.get("output_formats", {})
    if not isinstance(output_formats, dict):
        return

    site_wide = output_formats.get("site_wide", [])
    has_index_json = "index_json" in site_wide if isinstance(site_wide, list) else False

    if has_index_json:
        return

    # Search UI is enabled but no index will be generated - warn user
    logger.warning(
        "search_ui_without_index",
        theme_features=[f for f in theme_features if "search" in str(f)],
        site_wide_formats=site_wide,
        suggestion=(
            "Add 'features.search: true' to config/_default/features.yaml, "
            "or add 'index_json' to output_formats.site_wide"
        ),
    )


def load_environment_config(config_dir: Path, environment: str) -> dict[str, Any] | None:
    """
    Load environment-specific configuration overrides.

    Searches for environment configuration in ``config_dir/environments/``
    using multiple filename candidates (e.g., ``production.yaml``,
    ``prod.yaml``).

    Args:
        config_dir: Root configuration directory.
        environment: Environment name (e.g., ``"production"``, ``"preview"``).

    Returns:
        Environment configuration dictionary, or ``None`` if no matching
        file is found.
    """
    env_dir = config_dir / "environments"
    if not env_dir.exists():
        return None

    # Try candidates (production.yaml, prod.yaml, etc.)
    candidates = get_environment_file_candidates(environment)

    for candidate in candidates:
        env_file = env_dir / candidate
        if env_file.exists():
            logger.debug("environment_config_found", file=str(env_file))
            return load_yaml_file(env_file)

    logger.debug(
        "environment_config_not_found",
        environment=environment,
        tried=candidates,
    )
    return None


def load_profile_config(config_dir: Path, profile: str) -> dict[str, Any] | None:
    """
    Load profile-specific configuration overrides.

    Searches for profile configuration in ``config_dir/profiles/`` with
    both ``.yaml`` and ``.yml`` extensions.

    Args:
        config_dir: Root configuration directory.
        profile: Profile name (e.g., ``"writer"``, ``"developer"``).

    Returns:
        Profile configuration dictionary, or ``None`` if no matching
        file is found.
    """
    profiles_dir = config_dir / "profiles"
    if not profiles_dir.exists():
        return None

    # Try .yaml and .yml
    for ext in [".yaml", ".yml"]:
        profile_file = profiles_dir / f"{profile}{ext}"
        if profile_file.exists():
            logger.debug("profile_config_found", file=str(profile_file))
            return load_yaml_file(profile_file)

    logger.debug("profile_config_not_found", profile=profile)
    return None


__all__ = [
    "extract_baseurl",
    "flatten_config",
    "get_default_config",
    "load_environment_config",
    "load_profile_config",
    "load_yaml_file",
    "warn_search_ui_without_index",
]
