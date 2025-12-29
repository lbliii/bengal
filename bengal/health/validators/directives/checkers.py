"""
Directive validation checkers.

Provides validation methods for syntax, completeness, and performance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.health.report import CheckResult
from bengal.utils.logger import get_logger

from .constants import MAX_TABS_PER_BLOCK

logger = get_logger(__name__)


def get_line_with_context(file_path: Path, line_number: int, context_lines: int = 2) -> str:
    """
    Get a line from a file with context (lines before/after).

    Returns formatted string with line numbers and content.
    """
    try:
        if not file_path.exists():
            return f"Line {line_number}: (file not found)"

        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)

        result_lines = []
        for i in range(start, end):
            line_num = i + 1
            marker = ">>>" if line_num == line_number else "   "
            result_lines.append(f"{marker} {line_num:4d} | {lines[i]}")

        return "\n".join(result_lines)
    except Exception as e:
        logger.debug(
            "directive_checker_line_read_failed",
            file_path=str(file_path),
            line_number=line_number,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_fallback_message",
        )
        return f"Line {line_number}: (could not read file)"


def _get_relative_content_path(file_path: Path) -> str:
    """
    Get a user-friendly relative path for display.

    Tries to show path relative to 'content' directory for wayfinding.
    Falls back to showing last 3 path components if content dir not found.
    """
    parts = file_path.parts

    # Try to find 'content' in path and show relative to it
    try:
        content_idx = parts.index("content")
        rel_parts = parts[content_idx + 1 :]  # Parts after 'content/'
        return "/".join(rel_parts)
    except ValueError:
        pass

    # Fallback: show last 3 components for context (e.g., "guides/topics/file.md")
    if len(parts) > 3:
        return "/".join(parts[-3:])

    return str(file_path.name)


def check_directive_syntax(data: dict[str, Any]) -> list[CheckResult]:
    """Check directive syntax is valid."""
    results = []
    errors = data["syntax_errors"]
    fence_warnings = data["fence_nesting_warnings"]

    # Check for syntax errors (only report if there ARE errors)
    if errors:
        details = []
        for e in errors[:5]:
            file_path = e["page"]
            line_num = e["line"]
            error_msg = f"{file_path.name}:{line_num} - {e['type']}: {e['error']}"
            context = get_line_with_context(file_path, line_num)
            details.append(f"{error_msg}\n{context}")

        results.append(
            CheckResult.error(
                f"{len(errors)} directive(s) have syntax errors",
                code="H201",
                recommendation="Fix directive syntax. Check directive names and closing backticks.",
                details=details,
            )
        )
    # No success message - if there are no errors, silence is golden

    # Check for fence nesting warnings
    if fence_warnings:
        file_groups: dict[str, list[dict[str, Any]]] = {}
        metadata_warnings = []

        for w in fence_warnings:
            # Use full path as key to avoid grouping unrelated files with same name
            file_key = str(w["page"])
            if file_key not in file_groups:
                file_groups[file_key] = []
            file_groups[file_key].append(w)

            w_copy = w.copy()
            w_copy["page"] = str(w["page"])
            metadata_warnings.append(w_copy)

        details = []
        for _file_path_str, warnings in list(file_groups.items())[:3]:
            first_warning = warnings[0]
            file_path = first_warning["page"]
            outer_line = first_warning["line"]
            inner_line = first_warning.get("inner_line")

            # Show relative path from content dir for wayfinding
            rel_path = _get_relative_content_path(file_path)

            # Show clear outer vs inner relationship with context at inner line
            if inner_line:
                detail_msg = (
                    f"{rel_path}:{inner_line} - Inner code block conflicts with "
                    f"outer directive at line {outer_line}. Fix: Change outer to 4+ backticks."
                )
                # Show context at the inner (conflicting) line where user needs to look
                context = get_line_with_context(file_path, inner_line)
            else:
                detail_msg = f"{rel_path}:{outer_line} - {first_warning.get('warning', 'fence nesting issue')}"
                context = get_line_with_context(file_path, outer_line)

            details.append(f"{detail_msg}\n{context}")

            if len(warnings) > 1:
                other_lines = sorted(set(w["line"] for w in warnings[1:]))
                details.append(
                    f"  ... and {len(warnings) - 1} more at lines: {', '.join(map(str, other_lines))}"
                )

        if len(fence_warnings) > 3:
            remaining = len(fence_warnings) - sum(len(w) for w in list(file_groups.values())[:3])
            if remaining > 0:
                details.append(f"... and {remaining} more")

        results.append(
            CheckResult.warning(
                f"{len(fence_warnings)} directive(s) have fence nesting issues",
                code="H202",
                recommendation=(
                    "These directives use 3 backticks (```) but contain code blocks with 3 backticks. "
                    "Fix: Change directive opening from ```{name} to ````{name} (use 4+ backticks)."
                ),
                details=details,
                metadata={"fence_warnings": metadata_warnings},
            )
        )

    return results


def check_directive_completeness(data: dict[str, Any]) -> list[CheckResult]:
    """Check directives are complete (have required content, options, etc)."""
    results = []
    errors = data["completeness_errors"]

    if errors:
        warning_keywords = ["only 1 tab", "consider using", "has no tab markers"]
        warnings = [e for e in errors if any(kw in e["error"] for kw in warning_keywords)]
        hard_errors = [e for e in errors if e not in warnings]

        if hard_errors:
            details = []
            for e in hard_errors[:5]:
                file_path = e["page"]
                line_num = e["line"]
                error_msg = f"{file_path.name}:{line_num} - {e['type']}: {e['error']}"
                context = get_line_with_context(file_path, line_num)
                details.append(f"{error_msg}\n{context}")

            results.append(
                CheckResult.error(
                    f"{len(hard_errors)} directive(s) incomplete",
                    code="H203",
                    recommendation="Fix incomplete directives. Add required content and options.",
                    details=details,
                )
            )

        if warnings:
            details = []
            for e in warnings[:5]:
                file_path = e["page"]
                line_num = e["line"]
                error_msg = f"{file_path.name}:{line_num} - {e['type']}: {e['error']}"
                context = get_line_with_context(file_path, line_num)
                details.append(f"{error_msg}\n{context}")

            results.append(
                CheckResult.warning(
                    f"{len(warnings)} directive(s) could be improved",
                    code="H204",
                    recommendation="Review directive usage. Consider simpler alternatives for single-item directives.",
                    details=details,
                )
            )

    # No success message - if directives are complete, silence is golden

    return results


def check_directive_performance(data: dict[str, Any]) -> list[CheckResult]:
    """Check for performance issues with directive usage."""
    results = []
    warnings = data["performance_warnings"]

    if warnings:
        too_many_tabs = [w for w in warnings if w["issue"] == "too_many_tabs"]

        if too_many_tabs:
            results.append(
                CheckResult.warning(
                    f"{len(too_many_tabs)} tabs block(s) have many tabs (>{MAX_TABS_PER_BLOCK})",
                    code="H206",
                    recommendation="Consider splitting into multiple tabs blocks or separate pages. Large tabs blocks slow rendering.",
                    details=[
                        f"{_get_relative_content_path(w['page'])}:{w['line']}: {w['count']} tabs"
                        for w in sorted(too_many_tabs, key=lambda x: x["count"], reverse=True)[:5]
                    ],
                )
            )

    # No stats message - directive usage stats are noise during debugging

    return results


# Note: check_directive_rendering (H207) was removed.
# It parsed all HTML output files (~1.2s) and never caught any issues.
# Syntax validation (H201) catches directive problems at source level.
