"""
Terminal reporter for page explanations.

Formats PageExplanation data for display in terminal using kida templates
rendered through CLIOutput. Converts PageExplanation dataclasses into
template context dicts for structured, themed output.

Key Features:
- Template-based rendering via CLIOutput.render_write()
- Structured context dict for page_explanation.kida template
- Truncated lists for long content with "... +N more" indicators
- Verbose mode for performance breakdown

Example:
    >>> from bengal.debug import PageExplainer, ExplanationReporter
    >>> explainer = PageExplainer(site)
    >>> explanation = explainer.explain("docs/guide.md")
    >>> reporter = ExplanationReporter(cli=cli)
    >>> reporter.print(explanation)  # Full formatted output
    >>> print(reporter.format_summary(explanation))  # One-line summary

Related Modules:
- bengal.debug.explainer: Produces PageExplanation instances
- bengal.debug.models: Data models being formatted
- bengal.output.core: CLIOutput rendering engine

See Also:
- bengal/cli/milo_commands/inspect.py: CLI command using this reporter
- bengal/output/templates/page_explanation.kida: Template for output

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.debug.models import PageExplanation


class ExplanationReporter:
    """
    Format and display page explanations in terminal.

    Uses kida template rendering via CLIOutput for structured,
    themed terminal output.

    Creation:
        Direct instantiation: ExplanationReporter(cli=cli)

    Examples:
        reporter = ExplanationReporter(cli=cli)
        reporter.print(explanation)

    """

    def __init__(self, cli: object | None = None) -> None:
        """
        Initialize the reporter.

        Args:
            cli: CLIOutput instance for template rendering.
                 If None, a default CLIOutput is created.
        """
        if cli is None:
            from bengal.output.core import CLIOutput

            cli = CLIOutput()
        self._cli = cli

    def print(self, explanation: PageExplanation, verbose: bool = False) -> None:
        """
        Print formatted explanation to terminal.

        Args:
            explanation: PageExplanation to display
            verbose: Show additional details (template variables, timing)
        """
        context = self._build_context(explanation, verbose)
        self._cli.render_write("page_explanation.kida", **context)

    def _build_context(self, explanation: PageExplanation, verbose: bool) -> dict[str, Any]:
        """
        Convert a PageExplanation to a template context dict.

        Args:
            explanation: PageExplanation to convert
            verbose: Whether to include performance data

        Returns:
            Dict matching page_explanation.kida expected context.
        """
        ctx: dict[str, Any] = {}

        # Source
        src = explanation.source
        ctx["source"] = {
            "path": str(src.path),
            "size": src.size_human,
            "lines": src.line_count,
            "modified": src.modified.strftime("%Y-%m-%d %H:%M:%S") if src.modified else None,
            "encoding": src.encoding,
        }

        # Frontmatter
        if explanation.frontmatter:
            priority_keys = ["title", "description", "date", "tags", "type", "template", "weight"]
            items: list[dict[str, str]] = [
                {"label": key, "value": self._format_value(explanation.frontmatter[key])}
                for key in priority_keys
                if key in explanation.frontmatter
            ]
            for key, value in explanation.frontmatter.items():
                if key not in priority_keys:
                    items.append({"label": key, "value": self._format_value(value)})
            ctx["frontmatter"] = items if items else None

        # Template chain
        if explanation.template_chain:
            chain = []
            for i, tpl in enumerate(explanation.template_chain):
                chain.append(
                    {
                        "name": tpl.name,
                        "theme": tpl.theme or "",
                        "depth": i,
                        "includes": list(tpl.includes[:5]),
                    }
                )
            ctx["template_chain"] = chain

        # Dependencies
        deps = explanation.dependencies
        groups: list[dict[str, Any]] = []
        for section, items_list in [
            ("Content", deps.content),
            ("Templates", deps.templates),
            ("Data", deps.data),
            ("Assets", deps.assets),
            ("Includes", deps.includes),
        ]:
            if items_list:
                dep_items = [str(item) for item in items_list[:5]]
                if len(items_list) > 5:
                    dep_items.append(f"... +{len(items_list) - 5} more")
                groups.append({"section": section, "items": dep_items})
        ctx["deps"] = groups if groups else None

        # Shortcodes
        if explanation.shortcodes:
            ctx["shortcodes"] = [
                {
                    "name": sc.name,
                    "count": sc.count,
                    "lines_str": ", ".join(str(ln) for ln in sc.lines[:5])
                    + (f" +{len(sc.lines) - 5}" if len(sc.lines) > 5 else ""),
                }
                for sc in explanation.shortcodes[:10]
            ]

        # Cache
        cache = explanation.cache
        layers = []
        if cache.content_cached:
            layers.append("parsed content")
        if cache.rendered_cached:
            layers.append("rendered HTML")
        ctx["cache"] = {
            "status": cache.status,
            "reason": cache.reason or "",
            "key": (cache.cache_key[:50] + "...")
            if cache.cache_key and len(cache.cache_key) > 50
            else (cache.cache_key or ""),
            "layers": layers,
        }

        # Output
        ctx["output"] = {
            "url": str(explanation.output.url),
            "path": str(explanation.output.path) if explanation.output.path else "",
            "size": explanation.output.size_human or "",
        }

        # Issues
        if explanation.issues:
            ctx["issues"] = [
                {
                    "level": "warning"
                    if "warning" in issue.issue_type.lower()
                    else ("error" if "error" in issue.issue_type.lower() else "info"),
                    "message": f"{issue.issue_type.replace('_', ' ').title()}: {issue.message}",
                    "detail": issue.suggestion or "",
                }
                for issue in explanation.issues
            ]

        # Performance (verbose only)
        if verbose and explanation.performance:
            perf = explanation.performance
            ctx["performance"] = {
                "total_ms": perf.total_ms,
                "breakdown": [
                    {"label": phase, "value": f"{duration:.1f}ms"}
                    for phase, duration in perf.breakdown.items()
                ]
                if perf.breakdown
                else [],
            }

        return ctx

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
