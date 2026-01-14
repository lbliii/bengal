"""
Error context dataclasses for template error handling.

This module contains data structures that capture context around template
errors, including location information and template inclusion chains.

Classes:
    TemplateErrorContext: Captures error location (file, line, column) and
        surrounding source code for display.
    InclusionChain: Tracks template include/extend hierarchy to show how
        the error location was reached.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TemplateErrorContext:
    """Context around an error in a template."""

    template_name: str
    line_number: int | None
    column: int | None
    source_line: str | None
    surrounding_lines: list[tuple[int, str]]  # (line_num, line_content)
    template_path: Path | None


@dataclass
class InclusionChain:
    """Represents the template inclusion chain."""

    entries: list[tuple[str, int | None]]  # [(template_name, line_num), ...]

    def __str__(self) -> str:
        """Format as readable chain."""
        chain = []
        for i, (template, line) in enumerate(self.entries):
            indent = "  " * i
            arrow = "└─" if i == len(self.entries) - 1 else "├─"
            if line:
                chain.append(f"{indent}{arrow} {template}:{line}")
            else:
                chain.append(f"{indent}{arrow} {template}")
        return "\n".join(chain)
