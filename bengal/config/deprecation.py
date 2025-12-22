"""
Configuration deprecation handling.

This module provides utilities for detecting, warning about, and migrating
deprecated configuration keys to their new locations. It helps maintain
backward compatibility while guiding users to update their configurations.

The deprecation system supports two types of key changes:
    - **Deprecated keys**: Keys that have moved to a new section or been
      renamed with a different structure (e.g., ``minify_assets`` →
      ``assets.minify``).
    - **Renamed keys**: Simple key name changes within the same structure.

Module Attributes:
    DEPRECATED_KEYS: Mapping of deprecated keys to (section, new_key, note).
    RENAMED_KEYS: Mapping of renamed keys to (new_key, note).

Key Functions:
    check_deprecated_keys: Scan config for deprecated keys and optionally warn.
    print_deprecation_warnings: Print user-friendly deprecation messages.
    migrate_deprecated_keys: Automatically migrate deprecated keys to new locations.
    get_deprecation_summary: Generate markdown summary of all deprecations.

Example:
    >>> from bengal.config.deprecation import check_deprecated_keys
    >>> config = {"minify_assets": True}
    >>> deprecated = check_deprecated_keys(config, source="bengal.toml")
    >>> deprecated
    [('minify_assets', 'assets.minify', 'Use `assets.minify: true` instead.')]

See Also:
    - :mod:`bengal.config.loader`: Uses deprecation checking during config load.
    - CLI command ``bengal config deprecations``: Shows deprecation summary.
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
    Check for deprecated keys in the configuration.

    Scans the provided configuration dictionary for any keys listed in
    ``DEPRECATED_KEYS`` and returns information about their replacements.

    Args:
        config: The configuration dictionary to check.
        source: The source file of the configuration (e.g., ``"bengal.toml"``).
            Used for logging context.
        warn: If ``True``, log warnings for each deprecated key found.

    Returns:
        A list of tuples, each containing ``(old_key, new_location, note)``.
        Returns an empty list if no deprecated keys are found.

    Example:
        >>> config = {"minify_assets": True, "title": "My Site"}
        >>> deprecated = check_deprecated_keys(config, warn=False)
        >>> len(deprecated)
        1
        >>> deprecated[0][0]
        'minify_assets'
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

    Formats and displays deprecation information in a human-readable format,
    suitable for CLI output. Does nothing if the list is empty.

    Args:
        deprecated_keys: A list of tuples from :func:`check_deprecated_keys`,
            each containing ``(old_key, new_location, note)``.
        source: The source file of the configuration (e.g., ``"bengal.toml"``).
            Included in the output header if provided.

    Example:
        Output format::

            ⚠️  Deprecated configuration keys found in bengal.toml:
               - `minify_assets` is deprecated. Use `assets.minify` instead.
                 Note: Use `assets.minify: true` instead.

            These keys may be removed in a future version. Please update your configuration.
            See `bengal config deprecations` for a full list.
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

    Automatically moves deprecated keys to their new locations as defined
    in ``DEPRECATED_KEYS``. Only migrates if the new key doesn't already
    exist, preserving explicit user configuration.

    Args:
        config: The configuration dictionary to migrate.
        in_place: If ``True``, modify the config dictionary in place and
            remove old keys. If ``False``, return a new dictionary with
            migrations applied (original unchanged).

    Returns:
        The migrated configuration dictionary. If ``in_place=False``,
        this is a new dictionary; otherwise, it's the same object.

    Example:
        >>> config = {"minify_assets": True}
        >>> migrated = migrate_deprecated_keys(config)
        >>> "assets" in migrated
        True
        >>> migrated["assets"]["minify"]
        True
        >>> "minify_assets" in migrated  # Old key preserved (in_place=False)
        True
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

    Creates a documentation-ready markdown string listing all deprecated
    and renamed keys with their replacements and notes. Used by the
    ``bengal config deprecations`` CLI command.

    Returns:
        A markdown string with tables of deprecated and renamed keys.
        Includes headings, explanatory text, and properly formatted tables.

    Example:
        >>> summary = get_deprecation_summary()
        >>> "# Deprecated Configuration Keys" in summary
        True
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
