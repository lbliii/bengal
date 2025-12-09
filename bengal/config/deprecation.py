"""
Configuration deprecation handling.

Provides warnings for deprecated config keys with migration guidance.
Follows the principle of graceful degradation - deprecated keys still work,
but users are informed of the preferred alternatives.
"""

from __future__ import annotations

from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# =============================================================================
# Deprecated Key Mappings
# =============================================================================
# Format: "old_key": ("new_section", "new_key", "migration_note")
#
# These keys are deprecated but still functional. Users will see a warning
# suggesting they migrate to the new format.

DEPRECATED_KEYS: dict[str, tuple[str, str, str]] = {
    # Assets - flat keys deprecated in favor of nested assets.* section
    "minify_assets": (
        "assets",
        "minify",
        "Use 'assets.minify: true' instead of 'minify_assets: true'",
    ),
    "optimize_assets": (
        "assets",
        "optimize",
        "Use 'assets.optimize: true' instead of 'optimize_assets: true'",
    ),
    "fingerprint_assets": (
        "assets",
        "fingerprint",
        "Use 'assets.fingerprint: true' instead of 'fingerprint_assets: true'",
    ),
    # Features - flat keys deprecated in favor of nested features.* section
    "generate_sitemap": (
        "features",
        "sitemap",
        "Use 'features.sitemap: true' instead of 'generate_sitemap: true'",
    ),
    "generate_rss": (
        "features",
        "rss",
        "Use 'features.rss: true' instead of 'generate_rss: true'",
    ),
    # Markdown - legacy key names
    "markdown_engine": (
        "markdown",
        "parser",
        "Use 'markdown.parser: mistune' instead of 'markdown_engine: mistune'",
    ),
}

# Keys that have been renamed (not just restructured)
RENAMED_KEYS: dict[str, tuple[str, str]] = {
    # "old_key": ("new_key", "migration_note")
}


def check_deprecated_keys(
    config: dict[str, Any],
    source: str = "configuration",
    warn: bool = True,
) -> list[tuple[str, str, str]]:
    """
    Check for deprecated config keys and optionally warn.

    Args:
        config: Configuration dictionary to check
        source: Source description for log messages (e.g., "bengal.toml")
        warn: Whether to emit warnings (default: True)

    Returns:
        List of (old_key, new_location, migration_note) tuples for deprecated keys found

    Example:
        >>> config = {"minify_assets": True, "title": "My Site"}
        >>> deprecated = check_deprecated_keys(config)
        >>> len(deprecated)
        1
        >>> deprecated[0][0]
        'minify_assets'
    """
    found_deprecated: list[tuple[str, str, str]] = []

    for old_key, (section, new_key, note) in DEPRECATED_KEYS.items():
        if old_key in config:
            new_location = f"{section}.{new_key}"
            found_deprecated.append((old_key, new_location, note))

            if warn:
                logger.warning(
                    "config_key_deprecated",
                    old_key=old_key,
                    new_location=new_location,
                    source=source,
                    migration=note,
                )

    for old_key, (new_key, note) in RENAMED_KEYS.items():
        if old_key in config:
            found_deprecated.append((old_key, new_key, note))

            if warn:
                logger.warning(
                    "config_key_renamed",
                    old_key=old_key,
                    new_key=new_key,
                    source=source,
                    migration=note,
                )

    return found_deprecated


def print_deprecation_warnings(
    deprecated: list[tuple[str, str, str]],
    source: str = "configuration",
) -> None:
    """
    Print user-friendly deprecation warnings.

    Args:
        deprecated: List of (old_key, new_location, note) from check_deprecated_keys()
        source: Source description for context

    Example output:
        ⚠️  Deprecated config keys in bengal.toml:

          • minify_assets → assets.minify
            Use 'assets.minify: true' instead of 'minify_assets: true'

          • generate_sitemap → features.sitemap
            Use 'features.sitemap: true' instead of 'generate_sitemap: true'

        These keys still work but will be removed in a future version.
    """
    if not deprecated:
        return

    print(f"\n⚠️  Deprecated config keys in {source}:\n")

    for old_key, new_location, note in deprecated:
        print(f"  • {old_key} → {new_location}")
        print(f"    {note}\n")

    print("  These keys still work but may be removed in a future version.\n")


def migrate_deprecated_keys(
    config: dict[str, Any],
    in_place: bool = False,
) -> dict[str, Any]:
    """
    Migrate deprecated keys to their new locations.

    This function moves values from deprecated flat keys to their new
    nested locations. The original keys are preserved for backward
    compatibility unless in_place=True.

    Args:
        config: Configuration dictionary
        in_place: If True, remove old keys after migration

    Returns:
        Updated configuration dictionary

    Example:
        >>> config = {"minify_assets": True}
        >>> result = migrate_deprecated_keys(config)
        >>> result["assets"]["minify"]
        True
        >>> "minify_assets" in result  # Preserved by default
        True
    """
    result = dict(config) if not in_place else config

    for old_key, (section, new_key, _) in DEPRECATED_KEYS.items():
        if old_key in config:
            # Ensure section exists
            if section not in result:
                result[section] = {}
            elif not isinstance(result[section], dict):
                # Section exists but isn't a dict - skip migration
                continue

            # Only migrate if new key isn't already set
            if new_key not in result[section]:
                result[section][new_key] = config[old_key]

            # Remove old key if in_place
            if in_place and old_key in result:
                del result[old_key]

    return result


def get_deprecation_summary() -> str:
    """
    Get a summary of all deprecated keys for documentation.

    Returns:
        Markdown-formatted summary of deprecated keys
    """
    lines = ["# Deprecated Configuration Keys\n"]
    lines.append("The following config keys are deprecated:\n")

    lines.append("## Flat Keys → Nested Sections\n")
    lines.append("| Deprecated | Use Instead | Notes |")
    lines.append("|------------|-------------|-------|")

    for old_key, (section, new_key, note) in sorted(DEPRECATED_KEYS.items()):
        new_loc = f"`{section}.{new_key}`"
        lines.append(f"| `{old_key}` | {new_loc} | {note} |")

    if RENAMED_KEYS:
        lines.append("\n## Renamed Keys\n")
        lines.append("| Old Name | New Name | Notes |")
        lines.append("|----------|----------|-------|")

        for old_key, (new_key, note) in sorted(RENAMED_KEYS.items()):
            lines.append(f"| `{old_key}` | `{new_key}` | {note} |")

    return "\n".join(lines)
