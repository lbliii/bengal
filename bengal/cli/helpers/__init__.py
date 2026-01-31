"""
CLI helper functions and utilities.

This package provides common helper functions used throughout the Bengal CLI,
including site loading, error handling, progress display, and configuration
validation.

.. note::
    Many utilities have been consolidated into :mod:`bengal.cli.utils`.
    This module re-exports them for backward compatibility.
    New code should import from :mod:`bengal.cli.utils` directly.

Modules:
    cli_app_loader: CLI application loading utilities
    cli_output: CLI output instance management (deprecated, use bengal.cli.utils.output)
    config_validation: Configuration file validation
    error_display: Beautiful error display (deprecated, use bengal.errors.display)
    error_handling: CLI error handling decorators
    metadata: Command metadata and categorization
    progress: Progress display helpers
    site_loader: Site loading (deprecated, use bengal.cli.utils.site)
    traceback: Traceback configuration (deprecated, use bengal.cli.utils.traceback)
    validation: Flag validation (deprecated, use bengal.cli.utils.validation)

Example:
    >>> from bengal.cli.helpers import load_site_from_cli, cli_progress
    >>> site = load_site_from_cli(ctx)
    >>> with cli_progress() as progress:
    ...     progress.add_phase('build', 'Building')
"""

# Re-export from consolidated utils for backward compatibility
from bengal.cli.utils import (
    configure_traceback,
    get_cli_output,
    load_site_from_cli,
    validate_flag_conflicts,
    validate_mutually_exclusive,
)

# CLI app loader (still in helpers)
from bengal.cli.helpers.cli_app_loader import load_cli_app

# Config validation (still in helpers)
from bengal.cli.helpers.config_validation import (
    check_unknown_keys,
    check_yaml_syntax,
    validate_config_types,
    validate_config_values,
)

# Error display - re-export from canonical location
from bengal.errors.display import (
    beautify_common_exception,
    display_bengal_error,
)

# Error handling (updated to use utils.errors internally)
from bengal.cli.helpers.error_handling import cli_error_context, handle_cli_errors

# Metadata (still in helpers)
from bengal.cli.helpers.metadata import (
    CommandMetadata,
    command_metadata,
    find_commands_by_tag,
    get_command_metadata,
    list_commands_by_category,
)

# Progress (still in helpers)
from bengal.cli.helpers.progress import cli_progress, simple_progress

__all__ = [
    # Metadata
    "CommandMetadata",
    "command_metadata",
    "find_commands_by_tag",
    "get_command_metadata",
    "list_commands_by_category",
    # Error display (from bengal.errors.display)
    "beautify_common_exception",
    "display_bengal_error",
    # Config validation
    "check_unknown_keys",
    "check_yaml_syntax",
    "validate_config_types",
    "validate_config_values",
    # Error handling
    "cli_error_context",
    "handle_cli_errors",
    # Traceback (from utils)
    "configure_traceback",
    # Output (from utils)
    "get_cli_output",
    # Site loading (from utils)
    "load_site_from_cli",
    # CLI app loader
    "load_cli_app",
    # Progress
    "cli_progress",
    "simple_progress",
    # Validation (from utils)
    "validate_flag_conflicts",
    "validate_mutually_exclusive",
]
