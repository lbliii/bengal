"""
Terminal reporter for page explanations.

Formats PageExplanation data for display in terminal using plain text.
Provides visually organized output with boxed sections and indented trees
optimized for readability and quick information scanning.

Key Features:
- Boxed sections for visual organization
- Tree view for template inheritance chains
- Color-coded cache status (HIT/STALE/MISS)
- Truncated lists for long content with "... +N more" indicators
- Issue display with severity indicators and actionable suggestions

Example:
    >>> from bengal.debug import PageExplainer, ExplanationReporter
    >>> explainer = PageExplainer(site)
    >>> explanation = explainer.explain("docs/guide.md")
    >>> reporter = ExplanationReporter()
    >>> reporter.print(explanation)  # Full formatted output
    >>> print(reporter.format_summary(explanation))  # One-line summary

Related Modules:
- bengal.debug.explainer: Produces PageExplanation instances
- bengal.debug.models: Data models being formatted

See Also:
- bengal/cli/commands/explain.py: CLI command using this reporter

"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.debug.models import (
        CacheInfo,
        DependencyInfo,
        Issue,
        OutputInfo,
        PageExplanation,
        PerformanceInfo,
        ShortcodeUsage,
        SourceInfo,
        TemplateInfo,
    )


class ExplanationReporter:
    """
    Format and display page explanations in terminal.

    Uses plain text for well-formatted terminal output.
    Designed for quick scanning and visual clarity.

    Creation:
        Direct instantiation: ExplanationReporter()

    Examples:
        reporter = ExplanationReporter()
        reporter.print(explanation)

    """

    def __init__(self, console: object | None = None) -> None:
        """
        Initialize the reporter.

        Args:
            console: Ignored — kept for backward compatibility.
        """
        self._out = sys.stdout

    def _write(self, text: str = "") -> None:
        print(text, file=self._out)

    def print(self, explanation: PageExplanation, verbose: bool = False) -> None:
        """
        Print formatted explanation to terminal.

        Args:
            explanation: PageExplanation to display
            verbose: Show additional details (template variables, timing)
        """
        self._write()
        self._write(f"  Page Explanation: {explanation.source.path}")
        self._write()

        self._print_source(explanation.source)

        if explanation.frontmatter:
            self._print_frontmatter(explanation.frontmatter)

        if explanation.template_chain:
            self._print_template_chain(explanation.template_chain)

        self._print_dependencies(explanation.dependencies)

        if explanation.shortcodes:
            self._print_shortcodes(explanation.shortcodes)

        self._print_cache(explanation.cache)
        self._print_output(explanation.output)

        if explanation.issues:
            self._print_issues(explanation.issues)

        if verbose and explanation.performance:
            self._print_performance(explanation.performance)

    def _print_box(self, title: str, lines: list[str]) -> None:
        """Print a titled box with content lines."""
        self._write(f"  --- {title} ---")
        for line in lines:
            self._write(f"  {line}")
        self._write()

    def _print_source(self, source: SourceInfo) -> None:
        """Print source file information."""
        lines = [
            f"Path:     {source.path}",
            f"Size:     {source.size_human} ({source.line_count} lines)",
        ]
        if source.modified:
            lines.append(f"Modified: {source.modified.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Encoding: {source.encoding}")
        self._print_box("Source", lines)

    def _print_frontmatter(self, frontmatter: dict[str, Any]) -> None:
        """Print frontmatter metadata."""
        lines = []
        priority_keys = ["title", "description", "date", "tags", "type", "template", "weight"]
        for key in priority_keys:
            if key in frontmatter:
                value = frontmatter[key]
                lines.append(f"{key}: {self._format_value(value)}")

        for key, value in frontmatter.items():
            if key not in priority_keys:
                lines.append(f"{key}: {self._format_value(value)}")

        if lines:
            self._print_box("Frontmatter", lines)

    def _format_value(self, value: object) -> str:
        """Format a frontmatter value for display."""
        if isinstance(value, list):
            if len(value) <= 5:
                return f"[{', '.join(str(v) for v in value)}]"
            return f"[{', '.join(str(v) for v in value[:5])}, ... +{len(value) - 5} more]"
        if isinstance(value, dict):
            return f"{{...}} ({len(value)} keys)"
        if isinstance(value, str) and len(value) > 50:
            return f'"{value[:50]}..."'
        return repr(value)

    def _print_template_chain(self, chain: list[TemplateInfo]) -> None:
        """Print template inheritance chain."""
        lines = []
        for i, tpl in enumerate(chain):
            theme_str = f" ({tpl.theme})" if tpl.theme else ""
            indent = "  " * i
            prefix = "-> extends: " if i > 0 else ""
            lines.append(f"{indent}{prefix}{tpl.name}{theme_str}")

            lines.extend(f"{indent}  includes: {include}" for include in tpl.includes[:5])
            if len(tpl.includes) > 5:
                lines.append(f"{indent}  ... +{len(tpl.includes) - 5} more includes")

        self._print_box("Template Chain", lines)

    def _print_dependencies(self, deps: DependencyInfo) -> None:
        """Print dependencies organized by category."""
        sections = []

        if deps.content:
            sections.append(("Content", deps.content))
        if deps.templates:
            sections.append(("Templates", deps.templates))
        if deps.data:
            sections.append(("Data", deps.data))
        if deps.assets:
            sections.append(("Assets", deps.assets))
        if deps.includes:
            sections.append(("Includes", deps.includes))

        if not sections:
            return

        lines = []
        for section_name, items in sections:
            lines.append(f"{section_name}:")
            lines.extend(f"  * {item}" for item in items[:5])
            if len(items) > 5:
                lines.append(f"  ... +{len(items) - 5} more")

        self._print_box("Dependencies", lines)

    def _print_shortcodes(self, shortcodes: list[ShortcodeUsage]) -> None:
        """Print shortcode/directive usage."""
        lines = [f"{'Directive':<20} {'Uses':>5}  Lines"]
        lines.append("-" * 50)

        for sc in shortcodes[:10]:
            lines_str = ", ".join(str(ln) for ln in sc.lines[:5])
            if len(sc.lines) > 5:
                lines_str += f" +{len(sc.lines) - 5}"
            lines.append(f"{sc.name:<20} {sc.count:>5}  {lines_str}")

        if len(shortcodes) > 10:
            lines.append(f"{'...':<20} +{len(shortcodes) - 10}")

        self._print_box("Directives/Shortcodes", lines)

    def _print_cache(self, cache: CacheInfo) -> None:
        """Print cache status."""
        lines = [f"Status:    {cache.status}"]
        if cache.reason:
            lines.append(f"Reason:    {cache.reason}")
        if cache.cache_key:
            key_display = cache.cache_key
            if len(key_display) > 50:
                key_display = key_display[:50] + "..."
            lines.append(f"Cache key: {key_display}")

        layers = []
        if cache.content_cached:
            layers.append("parsed content")
        if cache.rendered_cached:
            layers.append("rendered HTML")
        if layers:
            lines.append(f"Cached:    {', '.join(layers)}")

        self._print_box("Cache Status", lines)

    def _print_output(self, output: OutputInfo) -> None:
        """Print output information."""
        lines = [f"URL:  {output.url}"]
        if output.path:
            lines.append(f"Path: {output.path}")
        if output.size_human:
            lines.append(f"Size: {output.size_human}")
        self._print_box("Output", lines)

    def _print_issues(self, issues: list[Issue]) -> None:
        """Print diagnosed issues with severity indicators."""
        self._write()
        self._write("  Issues Found:")
        self._write()

        for i, issue in enumerate(issues, 1):
            icon = issue.severity_emoji
            self._write(f"  {i}. {icon} {issue.issue_type.replace('_', ' ').title()}")
            self._write(f"     {issue.message}")

            if issue.details:
                for key, value in issue.details.items():
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value[:3])
                        if len(issue.details[key]) > 3:
                            value += " ..."
                    self._write(f"     {key}: {value}")

            if issue.suggestion:
                self._write(f"     Suggestion: {issue.suggestion}")
            self._write()

    def _print_performance(self, performance: PerformanceInfo) -> None:
        """Print performance timing breakdown."""
        lines = [f"Total: {performance.total_ms:.1f}ms"]
        if performance.breakdown:
            for phase, duration in performance.breakdown.items():
                lines.append(f"  {phase}: {duration:.1f}ms")
        self._print_box("Performance", lines)

    def format_summary(self, explanation: PageExplanation) -> str:
        """
        Format a brief one-line summary.

        Args:
            explanation: PageExplanation to summarize

        Returns:
            Single-line summary string
        """
        title = explanation.frontmatter.get("title", explanation.source.path.name)
        template = explanation.template_chain[0].name if explanation.template_chain else "default"
        cache = explanation.cache.status
        deps = (
            len(explanation.dependencies.templates)
            + len(explanation.dependencies.data)
            + len(explanation.dependencies.assets)
        )

        return f"{title} | template: {template} | cache: {cache} | deps: {deps}"
