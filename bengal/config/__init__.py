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

from pathlib import Path
from typing import Any

from bengal.config.deprecation import (
    DEPRECATED_KEYS,
    RENAMED_KEYS,
    check_deprecated_keys,
    get_deprecation_summary,
    migrate_deprecated_keys,
    print_deprecation_warnings,
)
from bengal.config.snapshot import (
    AssetsSection,
    BuildSection,
    ConfigSnapshot,
    ContentSection,
    DevSection,
    FeaturesSection,
    SiteSection,
    ThemeSection,
)
from bengal.config.unified_loader import UnifiedConfigLoader


class ConfigLoader(UnifiedConfigLoader):
    """
    Backward-compatible wrapper around UnifiedConfigLoader.

    Legacy ConfigLoader accepted a root path during construction and then
    ``load()`` with no arguments. This wrapper preserves that workflow while
    delegating the real work to UnifiedConfigLoader.

    """

    def __init__(self, root_path: Path, track_origins: bool = False) -> None:
        super().__init__(track_origins=track_origins)
        self._root_path = Path(root_path)

    def load(
        self,
        site_root: Path | None = None,
        environment: str | None = None,
        profile: str | None = None,
    ):
        target_root = Path(site_root) if site_root is not None else self._root_path
        return super().load(target_root, environment=environment, profile=profile)


def pretty_print_config(config: dict[str, Any], title: str = "Configuration") -> None:
    """Pretty print configuration using Rich formatting (pprint fallback)."""
    try:
        from rich.pretty import pprint as rich_pprint

        from bengal.utils.observability.rich_console import get_console, should_use_rich

        if should_use_rich():
            console = get_console()
            console.print()
            console.print(f"[bold cyan]{title}[/bold cyan]")
            console.print()
            rich_pprint(config, console=console, expand_all=True)
            console.print()
        else:
            import pprint

            print(f"\n{title}:\n")
            pprint.pprint(config, width=100, compact=False)
            print()
    except ImportError:
        import pprint

        print(f"\n{title}:\n")
        pprint.pprint(config, width=100, compact=False)
        print()


__all__ = [
    # Deprecation utilities
    "DEPRECATED_KEYS",
    "RENAMED_KEYS",
    "AssetsSection",
    "BuildSection",
    "ConfigLoader",  # Backward compatibility alias
    # Frozen config snapshot types (RFC: Snapshot-Enabled v2)
    "ConfigSnapshot",
    "ContentSection",
    "DevSection",
    "FeaturesSection",
    "SiteSection",
    "ThemeSection",
    "UnifiedConfigLoader",
    "check_deprecated_keys",
    "get_deprecation_summary",
    "migrate_deprecated_keys",
    "print_deprecation_warnings",
]
