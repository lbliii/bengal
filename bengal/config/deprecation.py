"""
Configuration deprecation handling.

Provides utilities for detecting, warning about, and migrating deprecated
configuration keys to their new locations.
"""

from __future__ import annotations

from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Mapping of deprecated config keys to (section, new_key, note)
DEPRECATED_KEYS: dict[str, tuple[str, str, str]] = {
    "minify_assets": ("assets", "minify", "Use `assets.minify: true` instead."),
    "optimize_assets": ("assets", "optimize", "Use `assets.optimize: true` instead."),
    "fingerprint_assets": ("assets", "fingerprint", "Use `assets.fingerprint: true` instead."),
    "generate_sitemap": ("features", "sitemap", "Use `features.sitemap: true` instead."),
    "generate_rss": ("features", "rss", "Use `features.rss: true` instead."),
    "markdown_engine": ("content", "markdown_parser", "Use `content.markdown_parser` instead."),
    "validate_links": (
        "health.linkcheck",
        "enabled",
        "Use `health.linkcheck.enabled: true` instead.",
    ),
}

# Mapping of renamed config keys to (new_key, note)
RENAMED_KEYS: dict[str, tuple[str, str]] = {
    # "old_key": ("new_key", "Note about the rename.")
}


def check_deprecated_keys(
    config: dict[str, Any], source: str | None = None, warn: bool = True
) -> list[tuple[str, str, str]]:
    """
    Check for deprecated keys in the configuration and return a list of warnings.

    Args:
        config: The configuration dictionary to check.
        source: The source file of the configuration (e.g., "bengal.toml").
        warn: If True, log warnings for deprecated keys.

    Returns:
        A list of tuples, each containing (old_key, new_location, note).
    """
    found_deprecated = []
    for old_key, (section, new_key, note) in DEPRECATED_KEYS.items():
        if old_key in config:
            new_location = f"{section}.{new_key}"
            found_deprecated.append((old_key, new_location, note))
            if warn:
                logger.warning(
                    "config_deprecated_key",
                    old_key=old_key,
                    new_location=new_location,
                    note=note,
                    source=source,
                )
    return found_deprecated


def print_deprecation_warnings(
    deprecated_keys: list[tuple[str, str, str]], source: str | None = None
) -> None:
    """
    Print user-friendly deprecation warnings to the console.

    Args:
        deprecated_keys: A list of tuples, each containing (old_key, new_location, note).
        source: The source file of the configuration (e.g., "bengal.toml").
    """
    if not deprecated_keys:
        return

    source_str = f" in {source}" if source else ""
    print(f"\n⚠️  Deprecated configuration keys found{source_str}:")
    for old_key, new_location, note in deprecated_keys:
        print(f"   - `{old_key}` is deprecated. Use `{new_location}` instead.")
        print(f"     Note: {note}")
    print("\nThese keys may be removed in a future version. Please update your configuration.")
    print("See `bengal config deprecations` for a full list.")


def migrate_deprecated_keys(config: dict[str, Any], in_place: bool = False) -> dict[str, Any]:
    """
    Migrate deprecated configuration keys to their new locations.

    Args:
        config: The configuration dictionary to migrate.
        in_place: If True, modify the config dictionary in place and remove old keys.
                  If False, return a new dictionary with migrations applied.

    Returns:
        The migrated configuration dictionary.
    """
    if not in_place:
        config = config.copy()

    from bengal.config.merge import get_nested_key, set_nested_key

    for old_key, (section, new_key, _) in DEPRECATED_KEYS.items():
        if old_key in config:
            # Only migrate if the new key doesn't already exist
            new_path = f"{section}.{new_key}"
            if get_nested_key(config, new_path) is None:
                set_nested_key(config, new_path, config[old_key])
            if in_place:
                del config[old_key]
    return config


def get_deprecation_summary() -> str:
    """
    Generate a markdown-formatted summary of all deprecated configuration keys.

    Returns:
        A markdown string summarizing deprecated keys.
    """
    summary = ["# Deprecated Configuration Keys", ""]
    summary.append(
        "The following configuration keys are deprecated and will be removed in future versions."
    )
    summary.append("Please update your `bengal.toml` or `bengal.yaml` files accordingly.")
    summary.append("")
    summary.append("| Deprecated | Use Instead | Notes |")
    summary.append("|------------|-------------|-------|")

    for old_key, (section, new_key, note) in DEPRECATED_KEYS.items():
        summary.append(f"| `{old_key}` | `{section}.{new_key}` | {note} |")

    if RENAMED_KEYS:
        summary.append("\n# Renamed Configuration Keys\n")
        summary.append("The following configuration keys have been renamed:")
        summary.append("")
        summary.append("| Old Key | New Key | Notes |")
        summary.append("|---------|---------|-------|")
        for old_key, (new_key, note) in RENAMED_KEYS.items():
            summary.append(f"| `{old_key}` | `{new_key}` | {note} |")

    return "\n".join(summary)
