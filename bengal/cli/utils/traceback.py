"""
Traceback configuration helpers for CLI commands.

Provides a unified function for setting up traceback display with
proper precedence handling for CLI flags, environment variables,
and file-based configuration.

Moved from bengal/cli/helpers/traceback.py to consolidate CLI utilities.

Functions:
    configure_traceback: Set up traceback handling with proper precedence

Precedence (highest to lowest):
    1. CLI --traceback flag
    2. CLI --debug flag (maps to full traceback)
    3. File config ([dev.traceback] in site config)
    4. BENGAL_TRACEBACK environment variable
    5. Default (minimal)

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site


def configure_traceback(
    debug: bool = False,
    traceback: str | None = None,
    site: Site | None = None,
) -> None:
    """
    Configure traceback handling with proper precedence.

    This function should typically be called twice in commands that load a site:
    1. Before site loading (without site) - applies CLI flags
    2. After site loading (with site) - applies file-based config

    Precedence order:
    1. CLI --traceback flag (highest)
    2. CLI --debug flag (maps to full traceback)
    3. File-based config ([dev.traceback] in site config)
    4. Environment variable (BENGAL_TRACEBACK)
    5. Default (minimal)

    Args:
        debug: Whether debug mode is enabled (maps to full traceback)
        traceback: Explicit traceback style (full, compact, minimal, off)
        site: Optional Site instance to apply file-based config from

    Example:
        @click.command()
        @click.option("--debug", is_flag=True)
        @click.option("--traceback", type=click.Choice([...]))
        def my_command(debug: bool, traceback: str | None):
            # Before site loading
            configure_traceback(debug, traceback)

            site = load_site_from_cli(...)

            # After site loading (applies file config)
            configure_traceback(debug, traceback, site=site)

    """
    from bengal.errors.traceback import (
        TracebackConfig,
        apply_file_traceback_to_env,
        map_debug_flag_to_traceback,
        set_effective_style_from_cli,
    )
    from bengal.utils.observability.logger import get_logger

    logger = get_logger(__name__)

    # Step 1: Map --debug flag to traceback style if --traceback not explicitly set
    map_debug_flag_to_traceback(debug, traceback)

    # Step 2: Set traceback style from CLI flag
    set_effective_style_from_cli(traceback)

    # Step 3: Install traceback handler
    TracebackConfig.from_environment().install()

    # Step 4: Apply file-based config if site is available (lowest precedence)
    if site:
        try:
            apply_file_traceback_to_env(site.config)
            TracebackConfig.from_environment().install()
        except Exception as e:
            # Silently fail if file config can't be applied
            logger.debug(
                "traceback_file_config_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
