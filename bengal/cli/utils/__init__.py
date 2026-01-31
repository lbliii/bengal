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

from bengal.cli.utils.errors import (
    display_traceback,
    handle_exception,
    should_show_traceback,
)
from bengal.cli.utils.logging import configure_cli_logging, get_log_level_for_profile
from bengal.cli.utils.output import get_cli_output, init_cli_output, reset_cli_output
from bengal.cli.utils.paths import format_display_path, resolve_source_path, truncate_path
from bengal.cli.utils.site import load_site_from_cli
from bengal.cli.utils.traceback import configure_traceback
from bengal.cli.utils.validation import validate_flag_conflicts, validate_mutually_exclusive

__all__ = [
    "configure_cli_logging",
    "configure_traceback",
    "display_traceback",
    "format_display_path",
    "get_cli_output",
    "get_log_level_for_profile",
    "handle_exception",
    "init_cli_output",
    "load_site_from_cli",
    "reset_cli_output",
    "resolve_source_path",
    "should_show_traceback",
    "truncate_path",
    "validate_flag_conflicts",
    "validate_mutually_exclusive",
]
