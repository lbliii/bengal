"""
Unified build options resolution with clear precedence.

This module provides a single source of truth for resolving build options
from CLI flags, config files, and defaults. It eliminates scattered inline
defaults throughout the codebase.

Precedence (highest to lowest):
1. Special Modes (e.g., --fast overrides quiet)
2. CLI flags (explicitly passed)
3. Config file values (flattened or nested)
4. DEFAULTS (single source of truth)

Note: Parallel processing is now auto-detected via should_parallelize().
Use --no-parallel CLI flag to force sequential mode (sets force_sequential=True).

Example:
    >>> from bengal.config.build_options_resolver import resolve_build_options, CLIFlags
    >>>
    >>> # Auto-detection (default)
    >>> config = {}
    >>> options = resolve_build_options(config)
    >>> options.force_sequential
False  # Will use should_parallelize() to decide
    >>>
    >>> # Force sequential via CLI
    >>> cli = CLIFlags(force_sequential=True)
    >>> options = resolve_build_options(config, cli)
    >>> options.force_sequential
True  # Forces sequential, bypasses should_parallelize()

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bengal.config.defaults import DEFAULTS
from bengal.config.utils import coerce_bool, get_config_value
from bengal.orchestration.build.options import BuildOptions


@dataclass
class CLIFlags:
    """
    Flags explicitly passed via CLI (None = not passed).

    All fields default to None, meaning "not explicitly set by user".
    The resolver will fall back to config or DEFAULTS for None values.

    Example:
            >>> # User passed --no-parallel
            >>> cli = CLIFlags(force_sequential=True)
            >>>
            >>> # User didn't pass --no-parallel flag
            >>> cli = CLIFlags(force_sequential=None)

    """

    force_sequential: bool | None = None
    incremental: bool | None = None
    quiet: bool | None = None
    verbose: bool | None = None
    strict: bool | None = None
    fast: bool | None = None
    memory_optimized: bool | None = None
    profile_templates: bool | None = None


def _get_build_config_value(config: dict[str, Any] | Any, key: str) -> Any:
    """
    Get build config value with defensive path handling.

    Uses the shared get_config_value utility to check both flattened
    and nested paths. For boolean build options, coerces string values
    to actual booleans.

    Args:
        config: Configuration dictionary or Config object (may be flattened or nested)
        key: Config key to retrieve

    Returns:
        Config value, or None if not found or invalid

    """
    # Use shared utility for flat/nested access (checks "build" section)
    value = get_config_value(config, key, sections=("build",), default=None)

    # Handle None values (treat as missing)
    if value is None:
        return None

    # Coerce string booleans to actual booleans for known boolean options
    if isinstance(value, str) and key in _BOOLEAN_BUILD_OPTIONS:
        return coerce_bool(value, default=None)

    return value


# Build options that should be coerced from string booleans
_BOOLEAN_BUILD_OPTIONS = frozenset(
    {
        "incremental",
        "quiet",
        "verbose",
        "strict_mode",
        "fast_mode",
        "memory_optimized",
        "profile_templates",
        "strict",
    }
)


def resolve_build_options(
    config: dict[str, Any] | Any,  # Accept Config objects too
    cli_flags: CLIFlags | None = None,
) -> BuildOptions:
    """
    Resolve build options with clear precedence.

    Precedence (highest to lowest):
        1. Special Modes (e.g., --fast overrides quiet/parallel)
        2. CLI flags (explicitly passed)
        3. Config file values (flattened or nested)
        4. DEFAULTS (single source of truth)

    Args:
        config: Site config dictionary (may be flattened or nested)
        cli_flags: CLI flags (None values = not passed)

    Returns:
        Fully resolved BuildOptions

    Example:
            >>> # Config only
            >>> config = {"quiet": True}
            >>> options = resolve_build_options(config)
            >>> options.force_sequential
        False  # Auto-detect via should_parallelize()
            >>> options.quiet
        True
            >>>
            >>> # CLI forces sequential
            >>> cli = CLIFlags(force_sequential=True)
            >>> options = resolve_build_options(config, cli)
            >>> options.force_sequential
        True  # CLI wins - forces sequential
            >>> options.quiet
        True  # Still from config
            >>>
            >>> # Fast mode overrides quiet
            >>> cli = CLIFlags(fast=True)
            >>> options = resolve_build_options(config, cli)
            >>> options.force_sequential
        False  # Fast mode doesn't force sequential (still auto-detect)
            >>> options.quiet
        True  # Fast mode forces quiet

    """
    cli = cli_flags or CLIFlags()
    build_defaults = DEFAULTS.get("build", {})

    def resolve(key: str, cli_value: Any, default_key: str | None = None) -> Any:
        """
        Resolve with CLI > config > DEFAULTS precedence.

        Args:
            key: Config key to look up
            cli_value: CLI flag value (None = not passed)
            default_key: Key in DEFAULTS (if different from config key)
        """
        # CLI flag takes highest precedence
        if cli_value is not None:
            return cli_value

        # Check config (handles both flattened and nested paths)
        config_value = _get_build_config_value(config, key)
        if config_value is not None:
            return config_value

        # Fall back to DEFAULTS
        default_key = default_key or key
        if default_key in build_defaults:
            return build_defaults.get(default_key)
        return DEFAULTS.get(default_key)

    # Handle fast_mode (special mode that overrides quiet)
    fast_mode = resolve("fast_mode", cli.fast)

    # Resolve all options
    # Note: parallel is no longer a config option - always auto-detected via should_parallelize()
    # unless force_sequential=True (set via --no-parallel CLI flag)
    force_sequential = cli.force_sequential if cli.force_sequential is not None else False

    quiet_resolved = resolve("quiet", cli.quiet)
    quiet = (
        True
        if fast_mode
        else (quiet_resolved if quiet_resolved is not None else DEFAULTS.get("quiet", False))
    )

    # Map strict_mode config key to strict option
    strict = resolve("strict_mode", cli.strict, default_key="strict_mode")

    # Resolve other options with proper defaults
    verbose_resolved = resolve("verbose", cli.verbose)
    memory_optimized_resolved = resolve("memory_optimized", cli.memory_optimized)
    profile_templates_resolved = resolve("profile_templates", cli.profile_templates)

    return BuildOptions(
        force_sequential=force_sequential,
        incremental=resolve("incremental", cli.incremental),
        quiet=quiet,
        verbose=verbose_resolved
        if verbose_resolved is not None
        else DEFAULTS.get("verbose", False),
        strict=strict,
        memory_optimized=memory_optimized_resolved
        if memory_optimized_resolved is not None
        else DEFAULTS.get("memory_optimized", False),
        profile_templates=profile_templates_resolved
        if profile_templates_resolved is not None
        else DEFAULTS.get("profile_templates", False),
    )
