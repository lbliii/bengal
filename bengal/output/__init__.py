"""
Centralized CLI output system for Bengal.

This package provides a unified interface for all CLI messaging with
profile-aware formatting, consistent spacing, and automatic terminal detection.

Features:
    - Profile-aware formatting (Writer, Theme-Dev, Developer)
    - Consistent indentation and spacing rules
    - Automatic TTY detection for Rich vs plain text
    - ASCII-first icons with optional emoji support
    - Dev server integration for request logging

Components:
    - CLIOutput: Main output manager class
    - MessageLevel: Enum for message importance levels
    - OutputStyle: Enum for visual styling
    - IconSet: Icon definitions for status indicators

Architecture:
    The output system separates concerns across modules:
    - core.py: Main CLIOutput class implementation
    - enums.py: Message levels and output styles
    - icons.py: ASCII and emoji icon sets
    - colors.py: HTTP status code and method colorization
    - dev_server.py: Mixin for development server output
    - globals.py: Singleton pattern for global CLI instance

Related:
    - bengal/utils/rich_console.py: Console configuration
    - bengal/cli/: CLI commands that consume this output system

Example:
    >>> from bengal.output import CLIOutput, get_cli_output, init_cli_output
    >>> cli = CLIOutput(profile=BuildProfile.WRITER)
    >>> cli.header("Building your site...")
    >>> cli.phase("Discovery", duration_ms=61)
    >>> cli.success("Built 245 pages in 0.8s")
"""

from __future__ import annotations

from bengal.output.core import CLIOutput
from bengal.output.enums import MessageLevel, OutputStyle
from bengal.output.globals import get_cli_output, init_cli_output

__all__ = [
    "CLIOutput",
    "MessageLevel",
    "OutputStyle",
    "get_cli_output",
    "init_cli_output",
]
