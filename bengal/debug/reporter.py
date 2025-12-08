"""
Rich terminal reporter for page explanations.

Formats PageExplanation data for display in terminal with Rich panels,
trees, and tables. Optimized for readability and quick scanning.

Key Features:
    - Paneled sections for visual organization
    - Tree view for template chains
    - Color-coded cache status
    - Collapsible details for long lists
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

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

    Uses Rich library for colorful, well-formatted terminal output.
    Designed for quick scanning and visual clarity.

    Creation:
        Direct instantiation: ExplanationReporter(console=None)
            - Uses provided Console or creates new one

    Attributes:
        console: Rich Console instance for output

    Examples:
        reporter = ExplanationReporter()
        reporter.print(explanation)
    """

    def __init__(self, console: Console | None = None) -> None:
        """
        Initialize the reporter.

        Args:
            console: Optional Rich Console. Creates new one if not provided.
        """
        self.console = console or Console()

    def print(self, explanation: PageExplanation, verbose: bool = False) -> None:
        """
        Print formatted explanation to terminal.

        Args:
            explanation: PageExplanation to display
            verbose: Show additional details (template variables, timing)
        """
        # Header
        self.console.print()
        self.console.print(f"📄 [bold]Page Explanation: {explanation.source.path}[/bold]")
        self.console.print()

        # Source panel
        self._print_source(explanation.source)

        # Frontmatter panel
        if explanation.frontmatter:
            self._print_frontmatter(explanation.frontmatter)

        # Template chain
        if explanation.template_chain:
            self._print_template_chain(explanation.template_chain)

        # Dependencies
        self._print_dependencies(explanation.dependencies)

        # Shortcodes
        if explanation.shortcodes:
            self._print_shortcodes(explanation.shortcodes)

        # Cache status
        self._print_cache(explanation.cache)

        # Output
        self._print_output(explanation.output)

        # Issues (if diagnosed)
        if explanation.issues:
            self._print_issues(explanation.issues)

        # Performance (if measured)
        if verbose and explanation.performance:
            self._print_performance(explanation.performance)

    def _print_source(self, source: SourceInfo) -> None:
        """Print source file information panel."""
        lines = [
            f"Path:     {source.path}",
            f"Size:     {source.size_human} ({source.line_count} lines)",
        ]
        if source.modified:
            lines.append(f"Modified: {source.modified.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Encoding: {source.encoding}")

        self.console.print(Panel("\n".join(lines), title="📁 Source", border_style="blue"))

    def _print_frontmatter(self, frontmatter: dict) -> None:
        """Print frontmatter panel."""
        lines = []
        # Show key fields first
        priority_keys = ["title", "description", "date", "tags", "type", "template", "weight"]
        for key in priority_keys:
            if key in frontmatter:
                value = frontmatter[key]
                lines.append(f"{key}: {self._format_value(value)}")

        # Show remaining fields
        for key, value in frontmatter.items():
            if key not in priority_keys:
                lines.append(f"{key}: {self._format_value(value)}")

        if lines:
            self.console.print(Panel("\n".join(lines), title="📝 Frontmatter", border_style="green"))

    def _format_value(self, value: object) -> str:
        """Format a frontmatter value for display."""
        if isinstance(value, list):
            if len(value) <= 5:
                return f"[{', '.join(str(v) for v in value)}]"
            return f"[{', '.join(str(v) for v in value[:5])}, ... +{len(value) - 5} more]"
        elif isinstance(value, dict):
            return f"{{...}} ({len(value)} keys)"
        elif isinstance(value, str) and len(value) > 50:
            return f'"{value[:50]}..."'
        return repr(value)

    def _print_template_chain(self, chain: list[TemplateInfo]) -> None:
        """Print template inheritance chain as tree."""
        tree = Tree("🎨 Template Chain")

        for i, tpl in enumerate(chain):
            # Format template info
            theme_str = f" [dim]({tpl.theme})[/dim]" if tpl.theme else ""
            node_text = f"{tpl.name}{theme_str}"

            if i == 0:
                node = tree.add(node_text)
            else:
                node = node.add(f"↳ extends: {node_text}")

            # Add includes
            for include in tpl.includes[:5]:  # Limit to 5
                node.add(f"[dim]includes: {include}[/dim]")
            if len(tpl.includes) > 5:
                node.add(f"[dim]... +{len(tpl.includes) - 5} more includes[/dim]")

        self.console.print(Panel(tree, border_style="magenta"))

    def _print_dependencies(self, deps: DependencyInfo) -> None:
        """Print dependencies panel."""
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
            lines.append(f"[bold]{section_name}:[/bold]")
            for item in items[:5]:  # Limit to 5 per section
                lines.append(f"  • {item}")
            if len(items) > 5:
                lines.append(f"  [dim]... +{len(items) - 5} more[/dim]")

        self.console.print(Panel("\n".join(lines), title="🔗 Dependencies", border_style="cyan"))

    def _print_shortcodes(self, shortcodes: list[ShortcodeUsage]) -> None:
        """Print shortcode usage panel."""
        table = Table(show_header=True, header_style="bold")
        table.add_column("Directive")
        table.add_column("Uses", justify="right")
        table.add_column("Lines")

        for sc in shortcodes[:10]:  # Limit to 10
            lines_str = ", ".join(str(ln) for ln in sc.lines[:5])
            if len(sc.lines) > 5:
                lines_str += f" +{len(sc.lines) - 5}"
            table.add_row(sc.name, str(sc.count), lines_str)

        if len(shortcodes) > 10:
            table.add_row("[dim]...[/dim]", f"+{len(shortcodes) - 10}", "")

        self.console.print(
            Panel(table, title="🧩 Directives/Shortcodes Used", border_style="yellow")
        )

    def _print_cache(self, cache: CacheInfo) -> None:
        """Print cache status panel."""
        # Status with color
        if cache.status == "HIT":
            status_str = "[green]✅ HIT[/green]"
        elif cache.status == "STALE":
            status_str = "[yellow]⚠️  STALE[/yellow]"
        elif cache.status == "MISS":
            status_str = "[red]❌ MISS[/red]"
        else:
            status_str = f"[dim]❓ {cache.status}[/dim]"

        lines = [f"Status:    {status_str}"]
        if cache.reason:
            lines.append(f"Reason:    {cache.reason}")
        if cache.cache_key:
            # Truncate long cache keys
            key_display = cache.cache_key
            if len(key_display) > 50:
                key_display = key_display[:50] + "..."
            lines.append(f"Cache key: [dim]{key_display}[/dim]")

        # Cache layer status
        layers = []
        if cache.content_cached:
            layers.append("✓ parsed content")
        if cache.rendered_cached:
            layers.append("✓ rendered HTML")
        if layers:
            lines.append(f"Cached:    {', '.join(layers)}")

        self.console.print(Panel("\n".join(lines), title="💾 Cache Status", border_style="blue"))

    def _print_output(self, output: OutputInfo) -> None:
        """Print output information panel."""
        lines = [f"URL:  {output.url}"]
        if output.path:
            lines.append(f"Path: {output.path}")
        if output.size_human:
            lines.append(f"Size: {output.size_human}")

        self.console.print(Panel("\n".join(lines), title="📤 Output", border_style="green"))

    def _print_issues(self, issues: list[Issue]) -> None:
        """Print diagnosed issues."""
        self.console.print()
        self.console.print("[bold]⚠️  Issues Found:[/bold]")
        self.console.print()

        for i, issue in enumerate(issues, 1):
            # Severity icon
            icon = issue.severity_emoji

            # Issue header
            self.console.print(
                f"{i}. {icon} [bold]{issue.issue_type.replace('_', ' ').title()}[/bold]"
            )
            self.console.print(f"   {issue.message}")

            # Details
            if issue.details:
                for key, value in issue.details.items():
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value[:3])
                        if len(issue.details[key]) > 3:
                            value += " ..."
                    self.console.print(f"   ├─ {key}: {value}")

            # Suggestion
            if issue.suggestion:
                self.console.print(f"   └─ [green]Suggestion: {issue.suggestion}[/green]")

            self.console.print()

    def _print_performance(self, performance: PerformanceInfo) -> None:
        """Print performance timing information."""
        lines = [f"Total: {performance.total_ms:.1f}ms"]

        if performance.breakdown:
            for phase, duration in performance.breakdown.items():
                lines.append(f"  {phase}: {duration:.1f}ms")

        self.console.print(Panel("\n".join(lines), title="⏱️  Performance", border_style="red"))

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

