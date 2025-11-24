"""Helper for configuring traceback behavior in CLI commands."""

from __future__ import annotations

from bengal.core.site import Site
from bengal.utils.traceback_config import (
    TracebackConfig,
    apply_file_traceback_to_env,
    map_debug_flag_to_traceback,
    set_effective_style_from_cli,
)


def configure_traceback(
    debug: bool = False,
    traceback: str | None = None,
    site: Site | None = None,
) -> None:
    """
    Configure traceback handling with proper precedence.

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
            configure_traceback(debug, traceback)
            # ... rest of command ...
    """
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
        except Exception:
            # Silently fail if file config can't be applied
            pass
