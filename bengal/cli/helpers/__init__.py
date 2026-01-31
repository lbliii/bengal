"""
CLI helper functions and utilities.

This package provides common helper functions used throughout the Bengal CLI,
including site loading, error handling, progress display, and configuration
validation.

Modules:
    cli_app_loader: CLI application loading utilities
    cli_output: CLI output instance management
    config_validation: Configuration file validation
    error_display: Beautiful error display for BengalError instances
    error_handling: CLI error handling decorators
    metadata: Command metadata and categorization
    progress: Progress display helpers
    site_loader: Site loading from CLI context
    traceback: Traceback configuration
    validation: Flag and option validation

Example:
    >>> from bengal.cli.helpers import load_site_from_cli, cli_progress
    >>> site = load_site_from_cli(ctx)
    >>> with cli_progress() as progress:
    ...     progress.add_phase('build', 'Building')
"""

from bengal.cli.helpers.cli_app_loader import load_cli_app
from bengal.cli.helpers.cli_output import get_cli_output
from bengal.cli.helpers.config_validation import (
    check_unknown_keys,
    check_yaml_syntax,
    validate_config_types,
    validate_config_values,
)
from bengal.cli.helpers.error_display import (
    beautify_common_exception,
    display_bengal_error,
)
from bengal.cli.helpers.error_handling import cli_error_context, handle_cli_errors
from bengal.cli.helpers.metadata import (
    CommandMetadata,
    command_metadata,
    find_commands_by_tag,
    get_command_metadata,
    list_commands_by_category,
)
from bengal.cli.helpers.progress import cli_progress, simple_progress
from bengal.cli.helpers.site_loader import load_site_from_cli
from bengal.cli.helpers.traceback import configure_traceback
from bengal.cli.helpers.validation import validate_flag_conflicts, validate_mutually_exclusive

__all__ = [
    "CommandMetadata",
    "beautify_common_exception",
    "check_unknown_keys",
    # Config validation
    "check_yaml_syntax",
    "cli_error_context",
    "cli_progress",
    "command_metadata",
    "configure_traceback",
    # Error display
    "display_bengal_error",
    "find_commands_by_tag",
    "get_cli_output",
    "get_command_metadata",
    "handle_cli_errors",
    "list_commands_by_category",
    "load_cli_app",
    "load_site_from_cli",
    "simple_progress",
    "validate_config_types",
    "validate_config_values",
    "validate_flag_conflicts",
    "validate_mutually_exclusive",
]
