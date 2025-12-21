"""
CLI-specific metadata dataclasses for autodoc system.

Provides typed metadata for:
- Commands (CLICommandMetadata)
- Command groups (CLIGroupMetadata)
- Options and arguments (CLIOptionMetadata)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class CLIOptionMetadata:
    """
    Metadata for CLI option or argument.

    Attributes:
        name: Parameter name
        param_type: Type of parameter ("option" or "argument")
        type_name: Type name (e.g., "STRING", "INT", "BOOL")
        required: Whether parameter is required
        default: Default value
        multiple: Whether parameter accepts multiple values
        is_flag: Whether option is a boolean flag
        count: Whether option counts occurrences
        opts: Option flags (e.g., ("-v", "--verbose"))
        envvar: Environment variable name
        help_text: Help text description

    Example:
        >>> meta = CLIOptionMetadata(
        ...     name="verbose",
        ...     param_type="option",
        ...     is_flag=True,
        ...     opts=("-v", "--verbose"),
        ... )
        >>> meta.is_flag
        True
    """

    name: str
    param_type: Literal["option", "argument"]
    type_name: str = "STRING"
    required: bool = False
    default: Any = None
    multiple: bool = False
    is_flag: bool = False
    count: bool = False
    opts: tuple[str, ...] = ()
    envvar: str | None = None
    help_text: str = ""


@dataclass(frozen=True, slots=True)
class CLICommandMetadata:
    """
    Metadata specific to CLI commands.

    Attributes:
        callback: Name of callback function
        option_count: Number of options
        argument_count: Number of arguments
        is_group: Whether this is a command group
        is_hidden: Whether command is hidden

    Example:
        >>> meta = CLICommandMetadata(callback="build_cmd", option_count=3, argument_count=1)
        >>> meta.option_count
        3
    """

    callback: str | None = None
    option_count: int = 0
    argument_count: int = 0
    is_group: bool = False
    is_hidden: bool = False


@dataclass(frozen=True, slots=True)
class CLIGroupMetadata:
    """
    Metadata specific to CLI command groups.

    Attributes:
        callback: Name of callback function
        command_count: Number of subcommands

    Example:
        >>> meta = CLIGroupMetadata(callback="cli_main", command_count=5)
        >>> meta.command_count
        5
    """

    callback: str | None = None
    command_count: int = 0
