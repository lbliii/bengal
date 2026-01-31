"""
CLI helper functions and utilities.

This package provides helper functions used throughout the Bengal CLI,
including error handling, progress display, configuration validation,
and command metadata.

Core utilities (output, site loading, validation decorators, traceback config)
are now in :mod:`bengal.cli.utils` - this module re-exports them for convenience.

Modules:
    cli_app_loader: CLI application loading utilities
    config_validation: Configuration file validation
    error_handling: CLI error handling decorators
    metadata: Command metadata and categorization
    progress: Progress display helpers

Example:
    >>> from bengal.cli.helpers import load_site_from_cli, cli_progress
    >>> site = load_site_from_cli(source=".")
    >>> with cli_progress("Processing...", total=10) as update:
    ...     for i in range(10):
    ...         update(advance=1)

"""

from bengal.cli.helpers.cli_app_loader import load_cli_app
from bengal.cli.helpers.config_validation import (
    check_unknown_keys,
    check_yaml_syntax,
    validate_config_types,
    validate_config_values,
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
from bengal.cli.utils import (
    configure_traceback,
    get_cli_output,
    load_site_from_cli,
    validate_flag_conflicts,
    validate_mutually_exclusive,
)
from bengal.errors.display import (
    beautify_common_exception,
    display_bengal_error,
)

__all__ = [
    "CommandMetadata",
    "beautify_common_exception",
    "check_unknown_keys",
    "check_yaml_syntax",
    "cli_error_context",
    "cli_progress",
    "command_metadata",
    "configure_traceback",
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
