"""
Centralized CLI output system for Bengal.

Provides a unified interface for all CLI messaging with:
- Profile-aware formatting (Writer, Theme-Dev, Developer)
- Consistent indentation and spacing
- Automatic TTY detection
- Rich/fallback rendering

Example:
    from bengal.output import CLIOutput, get_cli_output, init_cli_output

    cli = CLIOutput(profile=BuildProfile.WRITER)
    cli.header("Building your site...")
    cli.phase_start("Discovery")
    cli.success("Built 245 pages in 0.8s")
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
