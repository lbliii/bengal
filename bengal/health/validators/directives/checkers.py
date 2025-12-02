"""
Directive validation checkers.

Provides validation methods for syntax, completeness, performance, and rendering.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.health.report import CheckResult
from bengal.rendering.parsers.factory import ParserFactory

from .constants import MAX_DIRECTIVES_PER_PAGE, MAX_TABS_PER_BLOCK

if TYPE_CHECKING:
    from bengal.core.site import Site


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
    except Exception:
        return f"Line {line_number}: (could not read file)"


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
                recommendation="Fix directive syntax. Check directive names and closing backticks.",
                details=details,
            )
        )
    # No success message - if there are no errors, silence is golden

    # Check for fence nesting warnings
    if fence_warnings:
        file_groups = {}
        metadata_warnings = []

        for w in fence_warnings:
            file_key = w["page"].name
            if file_key not in file_groups:
                file_groups[file_key] = []
            file_groups[file_key].append(w)

            w_copy = w.copy()
            w_copy["page"] = str(w["page"])
            metadata_warnings.append(w_copy)

        details = []
        for file_name, warnings in list(file_groups.items())[:3]:
            first_warning = warnings[0]
            file_path = first_warning["page"]
            line_num = first_warning["line"]

            detail_msg = (
                f"{file_name}:{line_num} - {first_warning.get('warning', 'fence nesting issue')}"
            )
            context = get_line_with_context(file_path, line_num)
            details.append(f"{detail_msg}\n{context}")

            if len(warnings) > 1:
                other_lines = sorted(set(w["line"] for w in warnings[1:]))
                details.append(
                    f"  ... and {len(warnings) - 1} more issue(s) at lines: {', '.join(map(str, other_lines))}"
                )

        if len(fence_warnings) > 3:
            details.append(
                f"... and {len(fence_warnings) - sum(len(w) for w in list(file_groups.values())[:3])} more"
            )

        results.append(
            CheckResult.warning(
                f"{len(fence_warnings)} directive(s) have fence nesting issues",
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
        heavy_pages = [w for w in warnings if w["issue"] == "heavy_directive_usage"]
        too_many_tabs = [w for w in warnings if w["issue"] == "too_many_tabs"]

        if heavy_pages:
            results.append(
                CheckResult.warning(
                    f"{len(heavy_pages)} page(s) have heavy directive usage (>{MAX_DIRECTIVES_PER_PAGE} directives)",
                    recommendation="Consider splitting large pages or reducing directive nesting. Each directive adds ~20-50ms build time.",
                    details=[
                        f"{w['page'].name}: {w['count']} directives"
                        for w in sorted(heavy_pages, key=lambda x: x["count"], reverse=True)[:5]
                    ],
                )
            )

        if too_many_tabs:
            results.append(
                CheckResult.warning(
                    f"{len(too_many_tabs)} tabs block(s) have many tabs (>{MAX_TABS_PER_BLOCK})",
                    recommendation="Consider splitting into multiple tabs blocks or separate pages. Large tabs blocks slow rendering.",
                    details=[
                        f"{w['page'].name}:{w['line']}: {w['count']} tabs"
                        for w in sorted(too_many_tabs, key=lambda x: x["count"], reverse=True)[:5]
                    ],
                )
            )

    # No stats message - directive usage stats are noise during debugging

    return results


def check_directive_rendering(site: Site, data: dict[str, Any]) -> list[CheckResult]:
    """Check that directives rendered properly in output HTML."""
    results = []
    issues = []

    pages_to_check = [
        p
        for p in site.pages
        if p.output_path and p.output_path.exists() and not p.metadata.get("_generated")
    ]

    for page in pages_to_check:
        try:
            content = page.output_path.read_text(encoding="utf-8")

            if _has_unrendered_directives(content):
                issues.append(
                    f"{page.output_path.name}: Directive syntax error - directive not rendered"
                )

            if 'class="markdown-error"' in content:
                issues.append(f"{page.output_path.name}: Directive parsing error in output")

        except Exception:
            # Gracefully skip pages that can't be read (permissions, encoding issues)
            # This is non-critical validation - we don't want to fail the health check
            pass

    if issues:
        file_counts = {}
        for issue in issues:
            file_name = issue.split(":")[0]
            file_counts[file_name] = file_counts.get(file_name, 0) + 1

        details = []
        for file_name, count in list(file_counts.items())[:3]:
            details.append(f"{file_name}: {count} issue(s)")
        remaining = len(issues) - sum(list(file_counts.values())[:3])
        if remaining > 0:
            details.append(f"... and {remaining} more")

        results.append(
            CheckResult.error(
                f"{len(issues)} page(s) have directive rendering errors",
                recommendation=(
                    "Directives failed to render. Common causes: "
                    "missing closing fence, invalid syntax, or unknown directive type. "
                    "Check the directive syntax in the source markdown files."
                ),
                details=details,
            )
        )
    # No success message - if rendering worked, silence is golden

    return results


def _has_unrendered_directives(html_content: str) -> bool:
    """
    Check if HTML has unrendered directive blocks (outside code blocks).

    Args:
        html_content: HTML content to check

    Returns:
        True if unrendered directives found (not in code blocks)
    """
    try:
        parser = ParserFactory.get_html_parser("native")
        soup = parser(html_content)
        remaining_text = soup.get_text()
        return bool(re.search(r":{3,}\{(\w+)", remaining_text))
    except Exception:
        return re.search(r":{3,}\{(\w+)", html_content) is not None
