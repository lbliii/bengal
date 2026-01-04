"""
Configuration management for Bengal SSG.

This package provides comprehensive configuration loading, validation, and
management for Bengal static sites. It supports multiple configuration formats
(TOML, YAML), environment-based overrides, deprecated key migration, and
directory-based configuration structures.

Architecture:
    - Config V2: Canonical nested structure (site.*, build.*, dev.*, etc.)
    - UnifiedConfigLoader: Single loader for all modes (file or directory)
    - Config/ConfigSection: Type-safe accessors with IDE autocomplete

Modules:
    unified_loader: Single loader for all config modes (replaces old loaders).
    accessor: Config and ConfigSection classes for structured access.
    defaults: Centralized default values (fully nested structure).
    deprecation: Detection and migration of deprecated configuration keys.
    env_overrides: Automatic baseurl detection from deployment platforms.
    environment: Deployment environment detection (local, preview, production).
    feature_mappings: Feature toggle expansion to detailed configuration.
    hash: Deterministic configuration hashing for cache invalidation.
    merge: Deep merge utilities for configuration dictionaries.
    origin_tracker: Track which file contributed each configuration key.
    url_policy: Reserved URL namespaces and ownership rules.
    validators: Type-safe configuration validation with helpful error messages.

Example:
    Load configuration::

        from bengal.config import UnifiedConfigLoader

        loader = UnifiedConfigLoader()
        config = loader.load(site_root)

        # Access with structured API
        title = config.site.title
        parallel = config.build.parallel

        # Dict access for dynamic keys
        raw = config.raw  # Get underlying dict

    Check for deprecated keys::

        from bengal.config import check_deprecated_keys

        deprecated = check_deprecated_keys(config.raw, source="bengal.toml")
        if deprecated:
            print_deprecation_warnings(deprecated)

See Also:
    - ``bengal.config.accessor``: Config and ConfigSection classes.
    - ``bengal.config.defaults``: Default values (all nested).
    - ``plan/rfc-config-architecture-v2.md``: Architecture RFC.
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
from bengal.config.unified_loader import UnifiedConfigLoader

# Backward compatibility: ConfigLoader alias points to UnifiedConfigLoader
ConfigLoader = UnifiedConfigLoader

__all__ = [
    "ConfigLoader",  # Backward compatibility alias
    "UnifiedConfigLoader",
    "DEPRECATED_KEYS",
    "RENAMED_KEYS",
    "check_deprecated_keys",
    "get_deprecation_summary",
    "migrate_deprecated_keys",
    "print_deprecation_warnings",
]
