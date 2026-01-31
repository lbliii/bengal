"""
CLI utility functions and helpers.

This package consolidates CLI utilities that were previously scattered across
helpers/, output/, and various command files. It provides a single import point
for common CLI patterns.

Modules:
    output: Unified CLIOutput management (get_cli_output, init_cli_output)
    paths: Path formatting and truncation utilities
    logging: Logging configuration helpers
    errors: Unified error handling utilities
    traceback: Traceback configuration
    validation: Flag validation decorators
    site: Site loading utilities

Example:
    from bengal.cli.utils import (
        get_cli_output,
        configure_cli_logging,
        configure_traceback,
        load_site_from_cli,
        validate_mutually_exclusive,
        truncate_path,
    )

"""

# Output management
from bengal.cli.utils.output import get_cli_output, init_cli_output, reset_cli_output

# Path utilities
from bengal.cli.utils.paths import format_display_path, resolve_source_path, truncate_path

# Logging configuration
from bengal.cli.utils.logging import configure_cli_logging, get_log_level_for_profile

# Error handling
from bengal.cli.utils.errors import (
    display_traceback,
    handle_exception,
    should_show_traceback,
)

# Traceback configuration
from bengal.cli.utils.traceback import configure_traceback

# Validation decorators
from bengal.cli.utils.validation import validate_flag_conflicts, validate_mutually_exclusive

# Site loading
from bengal.cli.utils.site import load_site_from_cli

__all__ = [
    # Output
    "get_cli_output",
    "init_cli_output",
    "reset_cli_output",
    # Paths
    "truncate_path",
    "format_display_path",
    "resolve_source_path",
    # Logging
    "configure_cli_logging",
    "get_log_level_for_profile",
    # Errors
    "handle_exception",
    "should_show_traceback",
    "display_traceback",
    # Traceback
    "configure_traceback",
    # Validation
    "validate_mutually_exclusive",
    "validate_flag_conflicts",
    # Site
    "load_site_from_cli",
]
