"""
Logging configuration helpers for CLI commands.

Provides unified logging setup that consolidates the repeated patterns
found across build.py, serve.py, and other command files.

Functions:
    configure_cli_logging: Set up logging based on profile and flags
    get_log_level_for_profile: Determine log level from build profile

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.utils.observability.profile import BuildProfile


def get_log_level_for_profile(
    profile: BuildProfile | None,
    debug: bool = False,
    verbose: bool = False,
) -> str:
    """
    Determine appropriate log level based on profile and flags.

    Precedence (highest to lowest):
    1. debug flag → DEBUG
    2. verbose flag → INFO
    3. Profile-based:
       - DEVELOPER → DEBUG
       - THEME_DEV → INFO
       - WRITER → WARNING

    Args:
        profile: Build profile (determines base verbosity)
        debug: Whether debug mode is enabled
        verbose: Whether verbose mode is enabled

    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR)

    """
    from bengal.utils.observability.logger import LogLevel
    from bengal.utils.observability.profile import BuildProfile

    # Explicit flags take precedence
    if debug:
        return LogLevel.DEBUG

    if verbose:
        return LogLevel.INFO

    # Profile-based defaults
    if profile == BuildProfile.DEVELOPER:
        return LogLevel.DEBUG
    elif profile == BuildProfile.THEME_DEV:
        return LogLevel.INFO
    else:
        # WRITER or no profile
        return LogLevel.WARNING


def configure_cli_logging(
    source: str | Path,
    profile: BuildProfile | None = None,
    log_file: str | Path | None = None,
    debug: bool = False,
    verbose: bool = False,
    track_memory: bool = False,
    log_type: str = "build",
) -> Path:
    """
    Configure logging for a CLI command with sensible defaults.

    Handles the common pattern of:
    1. Determining log level from profile/flags
    2. Creating log directory if needed
    3. Determining log file path (explicit or default)
    4. Configuring the logging system

    Args:
        source: Source directory path (for determining log location)
        profile: Build profile (determines default log level)
        log_file: Explicit log file path (overrides default)
        debug: Enable debug logging
        verbose: Enable verbose logging
        track_memory: Enable memory tracking in logs
        log_type: Type of log file ("build", "serve", etc.)

    Returns:
        Path to the log file being used.

    Example:
        # In build command
        log_path = configure_cli_logging(
            source=source,
            profile=build_profile,
            log_file=log_file,
            debug=debug,
            verbose=verbose,
        )

        # In serve command
        log_path = configure_cli_logging(
            source=source,
            debug=debug,
            verbose=verbose,
            log_type="serve",
        )

    """
    from bengal.cache.paths import BengalPaths
    from bengal.utils.observability.logger import configure_logging

    # Resolve source path
    root_path = Path(source).resolve()

    # Get BengalPaths for canonical log location
    paths = BengalPaths(root_path)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)

    # Determine log file path
    if log_file:
        actual_log_path = Path(log_file)
    elif log_type == "serve":
        actual_log_path = paths.serve_log
    else:
        actual_log_path = paths.build_log

    # Get profile config for additional settings
    profile_config: dict[str, bool] = {}
    if profile:
        profile_config = profile.get_config()

    # Determine log level
    log_level = get_log_level_for_profile(profile, debug, verbose)

    # Configure logging
    configure_logging(
        level=log_level,
        log_file=actual_log_path,
        verbose=profile_config.get("verbose_build_stats", False) or verbose or debug,
        track_memory=profile_config.get("track_memory", False) or track_memory,
    )

    return actual_log_path
