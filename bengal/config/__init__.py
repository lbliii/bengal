"""
Configuration management for Bengal SSG.

This package provides comprehensive configuration loading, validation, and
management for Bengal static sites. It supports multiple configuration formats
(TOML, YAML), environment-based overrides, deprecated key migration, and
directory-based configuration structures.

Modules:
    loader: Primary configuration loader for bengal.toml/bengal.yaml files.
    defaults: Centralized default values for all configuration options.
    deprecation: Detection and migration of deprecated configuration keys.
    directory_loader: Multi-file configuration loading from directory structures.
    env_overrides: Automatic baseurl detection from deployment platforms.
    environment: Deployment environment detection (local, preview, production).
    feature_mappings: Feature toggle expansion to detailed configuration.
    hash: Deterministic configuration hashing for cache invalidation.
    merge: Deep merge utilities for configuration dictionaries.
    origin_tracker: Track which file contributed each configuration key.
    url_policy: Reserved URL namespaces and ownership rules.
    validators: Type-safe configuration validation with helpful error messages.

Example:
    Load configuration from the default file::

        from bengal.config import ConfigLoader

        loader = ConfigLoader(root_path)
        config = loader.load()

    Check for deprecated keys::

        from bengal.config import check_deprecated_keys

        deprecated = check_deprecated_keys(config, source="bengal.toml")
        if deprecated:
            print_deprecation_warnings(deprecated)

See Also:
    - ``bengal.config.defaults``: Default values and helper functions.
    - ``bengal.config.directory_loader``: Advanced directory-based configuration.
"""

from __future__ import annotations

from bengal.config.deprecation import (
    DEPRECATED_KEYS,
    RENAMED_KEYS,
    check_deprecated_keys,
    get_deprecation_summary,
    migrate_deprecated_keys,
    print_deprecation_warnings,
)
from bengal.config.loader import ConfigLoader

__all__ = [
    "ConfigLoader",
    "DEPRECATED_KEYS",
    "RENAMED_KEYS",
    "check_deprecated_keys",
    "get_deprecation_summary",
    "migrate_deprecated_keys",
    "print_deprecation_warnings",
]
