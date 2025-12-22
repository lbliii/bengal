"""
Rich template error handling with contextual debugging information.

This module provides structured error objects for template rendering failures,
enabling clear error messages with source context, suggestions, and IDE-friendly
formatting.

Key Classes:
    TemplateRenderError:
        Rich exception with template context, line numbers, source snippets,
        and actionable suggestions. Extends BengalRenderingError for
        consistent error handling across the codebase.

    TemplateErrorContext:
        Captures error location (file, line, column) and surrounding source
        code for display.

    InclusionChain:
        Tracks template include/extend hierarchy to show how the error
        location was reached.

Error Types:
    - syntax: Invalid Jinja2 syntax (missing tags, brackets, etc.)
    - filter: Unknown filter name (e.g., ``| nonexistent``)
    - undefined: Undefined variable access (e.g., ``{{ missing_var }}``)
    - runtime: Runtime errors during template execution
    - other: Unclassified template errors

Display Functions:
    display_template_error():
        Renders error to terminal with syntax highlighting (via Rich if
        available) or plain text fallback. Shows source context, suggestions,
        and documentation links.

Usage:
    Typically created automatically by the rendering pipeline:

    >>> try:
    ...     template.render(context)
    ... except Exception as e:
    ...     error = TemplateRenderError.from_jinja2_error(
    ...         e, template_name, page_source, template_engine
    ...     )
    ...     display_template_error(error)

Error Message Enhancement:
    The module includes smart suggestion generation:
    - Typo detection for variable/filter names
    - Safe access patterns for undefined errors
    - Documentation links for common issues

Related Modules:
    - bengal.rendering.engines.errors: Low-level engine exceptions
    - bengal.errors: Base error classes (BengalRenderingError)
    - bengal.utils.rich_console: Rich terminal output utilities
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import TemplateSyntaxError, UndefinedError
from jinja2.exceptions import TemplateAssertionError, TemplateRuntimeError

from bengal.errors import BengalRenderingError
from bengal.utils.logger import truncate_error


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


class TemplateRenderError(BengalRenderingError):
    """
    Rich template error with all debugging information.

    This replaces the simple string error messages with structured data
    that can be displayed beautifully and used for IDE integration.

    Extends BengalRenderingError to provide consistent error handling
    while maintaining rich context for template debugging.
    """

    def __init__(
        self,
        error_type: str,
        message: str,
        template_context: TemplateErrorContext,
        inclusion_chain: InclusionChain | None = None,
        page_source: Path | None = None,
        suggestion: str | None = None,
        available_alternatives: list[str] | None = None,
        search_paths: list[Path] | None = None,
        *,
        file_path: Path | None = None,
        line_number: int | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize template render error.

        Args:
            error_type: Type of error ('syntax', 'undefined', 'filter', 'runtime')
            message: Error message
            template_context: Template error context
            inclusion_chain: Template inclusion chain (if applicable)
            page_source: Source page path (if applicable)
            suggestion: Helpful suggestion for fixing
            available_alternatives: List of alternative filters/variables
            search_paths: Template search paths
            file_path: File path (defaults to template_context.template_path)
            line_number: Line number (defaults to template_context.line_number)
            original_error: Original exception that caused this error
        """
        # Set base class fields (use template context if not provided)
        super().__init__(
            message=message,
            file_path=file_path or template_context.template_path,
            line_number=line_number or template_context.line_number,
            suggestion=suggestion,
            original_error=original_error,
        )

        # Set rich context fields
        self.error_type = error_type
        self.template_context = template_context
        self.inclusion_chain = inclusion_chain
        self.page_source = page_source
        self.available_alternatives = available_alternatives or []
        self.search_paths = search_paths

    @classmethod
    def from_jinja2_error(
        cls, error: Exception, template_name: str, page_source: Path | None, template_engine: Any
    ) -> TemplateRenderError:
        """
        Extract rich error information from Jinja2 exception.

        Args:
            error: Jinja2 exception
            template_name: Template being rendered
            page_source: Source content file (if applicable)
            template_engine: Template engine instance

        Returns:
            Rich error object
        """
        # Determine error type
        error_type = cls._classify_error(error)

        # Extract context
        context = cls._extract_context(error, template_name, template_engine)

        # Build inclusion chain
        inclusion_chain = cls._build_inclusion_chain(error, template_engine)

        # Generate suggestion
        suggestion = cls._generate_suggestion(error, error_type, template_engine)

        # Find alternatives (for unknown filters/variables)
        alternatives = cls._find_alternatives(error, error_type, template_engine)

        # Extract search paths from template engine
        search_paths: list[Path] | None = None
        if hasattr(template_engine, "template_dirs"):
            try:
                dirs = template_engine.template_dirs
                if dirs and hasattr(dirs, "__iter__"):
                    search_paths = list(dirs)
            except (TypeError, AttributeError):
                # Handle mock objects or other non-iterable cases
                pass

        return cls(
            error_type=error_type,
            message=truncate_error(error),
            template_context=context,
            inclusion_chain=inclusion_chain,
            page_source=page_source,
            suggestion=suggestion,
            available_alternatives=alternatives,
            search_paths=search_paths,
            original_error=error,
        )

    @staticmethod
    def _classify_error(error: Exception) -> str:
        """Classify Jinja2 error type."""
        error_str = str(error).lower()

        # Check for filter errors first (can be TemplateAssertionError or part of other errors)
        if (
            "no filter named" in error_str
            or ("filter" in error_str and ("unknown" in error_str or "not found" in error_str))
            or (isinstance(error, TemplateAssertionError) and "unknown filter" in error_str)
        ):
            return "filter"

        if isinstance(error, TemplateSyntaxError):
            return "syntax"
        elif isinstance(error, TemplateAssertionError):
            # Filter errors during compilation
            if "filter" in error_str or "unknown filter" in error_str:
                return "filter"
            return "syntax"
        elif isinstance(error, UndefinedError):
            return "undefined"
        elif isinstance(error, TemplateRuntimeError):
            return "runtime"
        # Fallback: In Jinja2 <3.0, or in some sandboxed/embedded environments,
        # TemplateAssertionError may not be raised for unknown filters; instead,
        # a generic exception with a message containing "unknown filter" may be raised.
        # See test_classify_unknown_filter_in_assertion in tests/unit/rendering/test_template_error_edge_cases.py
        # for coverage of this behavior.
        if "unknown filter" in error_str:
            return "filter"
        return "other"

    @staticmethod
    def _extract_context(
        error: Exception, template_name: str, template_engine: Any
    ) -> TemplateErrorContext:
        """Extract template context from error."""
        # Jinja2 provides: error.lineno, error.filename, error.source
        line_number = getattr(error, "lineno", None)
        filename = getattr(error, "filename", None) or template_name

        # Find template path
        template_path = template_engine._find_template_path(filename)

        # Get source lines
        source_line = None
        surrounding_lines = []

        if template_path and template_path.exists():
            try:
                with open(template_path, encoding="utf-8") as f:
                    lines = f.readlines()

                if line_number and 1 <= line_number <= len(lines):
                    # Get the error line
                    source_line = lines[line_number - 1].rstrip()

                    # Get surrounding context (3 lines before, 3 after)
                    start = max(0, line_number - 4)
                    end = min(len(lines), line_number + 3)

                    for i in range(start, end):
                        surrounding_lines.append((i + 1, lines[i].rstrip()))
            except (OSError, IndexError):
                pass

        return TemplateErrorContext(
            template_name=filename,
            line_number=line_number,
            column=None,  # Jinja2 doesn't provide column consistently
            source_line=source_line,
            surrounding_lines=surrounding_lines,
            template_path=template_path,
        )

    @staticmethod
    def _build_inclusion_chain(error: Exception, template_engine: Any) -> InclusionChain | None:
        """Build template inclusion chain from traceback."""
        # Parse Python traceback to find template includes
        import traceback

        tb = traceback.extract_tb(error.__traceback__)

        entries = []
        for frame in tb:
            # Look for template file paths
            if "templates/" in frame.filename:
                template_name = Path(frame.filename).name
                entries.append((template_name, frame.lineno))

        return InclusionChain(entries) if entries else None

    @staticmethod
    def _generate_suggestion(error: Exception, error_type: str, template_engine: Any) -> str | None:
        """Generate helpful suggestion based on error."""
        error_str = str(error).lower()

        if error_type == "filter":
            if "in_section" in error_str:
                return "Bengal doesn't have 'in_section' filter. Check if the page is in a section using: {% if page.parent %}"
            elif "is_ancestor" in error_str:
                return "Use page comparison instead: {% if page._path == other_page._path %}"

        elif error_type == "undefined":
            if "metadata.weight" in error_str:
                return "Use safe access: {{ page.metadata.get('weight', 0) }}"

        elif error_type == "syntax":
            if "with" in error_str:
                return (
                    "Jinja2 doesn't support 'with' in include. Use {% set %} before {% include %}"
                )
            elif "default=" in error_str:
                return "The 'default' parameter in sort() is not supported. Remove it or use a custom filter."

        return None

    @staticmethod
    def _find_alternatives(error: Exception, error_type: str, template_engine: Any) -> list[str]:
        """Find alternative filters/variables that might work."""
        if error_type != "filter":
            return []

        # Extract filter name from error
        import re

        match = re.search(r"No filter named ['\"](\w+)['\"]", str(error))
        if not match:
            return []

        unknown_filter = match.group(1)

        # Get all available filters
        available_filters = sorted(template_engine.env.filters.keys())

        # Find similar filters (Levenshtein distance or simple matching)
        from difflib import get_close_matches

        suggestions = get_close_matches(unknown_filter, available_filters, n=3, cutoff=0.6)

        return suggestions


def display_template_error(error: TemplateRenderError, use_color: bool = True) -> None:
    """
    Display a rich template error in the terminal.

    Args:
        error: Rich error object
        use_color: Whether to use terminal colors
    """
    # Try to use rich for enhanced display
    try:
        from bengal.utils.rich_console import should_use_rich

        if should_use_rich():
            _display_template_error_rich(error)
            return
    except ImportError:
        pass  # Fall back to click

    # Fallback to click-based display
    _display_template_error_click(error, use_color)


def _display_template_error_rich(error: TemplateRenderError) -> None:
    """Display template error with rich formatting."""
    from rich.panel import Panel
    from rich.syntax import Syntax

    from bengal.utils.rich_console import get_console

    console = get_console()

    # Error type names
    error_type_names = {
        "syntax": "Template Syntax Error",
        "filter": "Unknown Filter",
        "undefined": "Undefined Variable",
        "runtime": "Template Runtime Error",
        "other": "Template Error",
    }

    header = error_type_names.get(error.error_type, "Template Error")
    ctx = error.template_context

    # Build code context with syntax highlighting
    if ctx.surrounding_lines:
        # Extract code around error
        code_lines = []

        for _line_num, line_content in ctx.surrounding_lines:
            code_lines.append(line_content)

        code_text = "\n".join(code_lines)

        # Create syntax-highlighted code
        start_line = ctx.surrounding_lines[0][0] if ctx.surrounding_lines else 1

        syntax = Syntax(
            code_text,
            "jinja2",
            theme="monokai",
            line_numbers=True,
            start_line=start_line,
            highlight_lines={ctx.line_number} if ctx.line_number else set(),
            word_wrap=False,
            background_color="default",
        )

        # Display in panel
        panel_title = f"[red bold]{header}[/red bold] in [yellow]{ctx.template_name}[/yellow]"
        if ctx.line_number:
            panel_title += f":[yellow]{ctx.line_number}[/yellow]"

        console.print()
        console.print(Panel(syntax, title=panel_title, border_style="red", padding=(1, 2)))
    else:
        # No code context, just show header
        console.print()
        console.print(f"[red bold]⚠️  {header}[/red bold]")
        console.print()
        if ctx.template_path:
            console.print(f"  [cyan]File:[/cyan] {ctx.template_path}")
        else:
            console.print(f"  [cyan]Template:[/cyan] {ctx.template_name}")
        if ctx.line_number:
            console.print(f"  [cyan]Line:[/cyan] {ctx.line_number}")

    # Error message
    console.print()
    console.print(f"[red bold]Error:[/red bold] {error.message}")

    # Generate enhanced suggestions
    suggestions = _generate_enhanced_suggestions(error)

    if suggestions:
        console.print()
        console.print("[yellow bold]💡 Suggestions:[/yellow bold]")
        console.print()
        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"   [yellow]{i}.[/yellow] {suggestion}")

    # Alternatives (for filter/variable errors)
    if error.available_alternatives:
        console.print()
        console.print("[yellow bold]Did you mean:[/yellow bold]")
        for alt in error.available_alternatives:
            console.print(f"   • [cyan]{alt}[/cyan]")

    # Inclusion chain
    if error.inclusion_chain:
        console.print()
        console.print("[cyan bold]Template Chain:[/cyan bold]")
        for line in str(error.inclusion_chain).split("\n"):
            console.print(f"  {line}")

    # Page source
    if error.page_source:
        console.print()
        console.print(f"[cyan]Used by page:[/cyan] {error.page_source}")

    # Template search paths (helpful for debugging template not found errors)
    if error.search_paths:
        console.print()
        console.print("[cyan bold]🔍 Template Search Paths:[/cyan bold]")
        for i, search_path in enumerate(error.search_paths, 1):
            # Mark the path where template was found (if found)
            found_marker = ""
            if ctx.template_path and ctx.template_path.is_relative_to(search_path):
                found_marker = " [green]← found here[/green]"
            console.print(f"   {i}. [dim]{search_path}[/dim]{found_marker}")

    # Documentation link
    doc_links = {
        "filter": "https://bengal.dev/docs/templates/filters",
        "undefined": "https://bengal.dev/docs/templates/variables",
        "syntax": "https://bengal.dev/docs/templates/syntax",
    }

    if error.error_type in doc_links:
        console.print()
        console.print(f"[dim]📚 Learn more: {doc_links[error.error_type]}[/dim]")

    console.print()


def _generate_enhanced_suggestions(error: TemplateRenderError) -> list[str]:
    """Generate context-aware suggestions for template errors."""
    suggestions = []

    # Start with existing suggestion
    if error.suggestion:
        suggestions.append(error.suggestion)

    error_str = str(error.message).lower()

    # Enhanced suggestions based on error type
    if error.error_type == "undefined":
        var_name = _extract_variable_name(error.message)

        # ENHANCED: Detect unsafe dict access patterns
        if "'dict object' has no attribute" in error.message:
            # This is THE key pattern we just fixed!
            attr = _extract_dict_attribute(error.message)
            suggestions.append(
                "[red bold]Unsafe dict access detected![/red bold] Dict keys should use .get() method"
            )
            if attr:
                suggestions.append(
                    f"Replace [red]dict.{attr}[/red] with [green]dict.get('{attr}')[/green] or [green]dict.get('{attr}', 'default')[/green]"
                )
            suggestions.append(
                "Common locations: [cyan]page.metadata[/cyan], [cyan]site.config[/cyan], [cyan]section.metadata[/cyan]"
            )
            suggestions.append(
                "[yellow]Note:[/yellow] This error only appears in strict mode (serve). Use [cyan]bengal build --strict[/cyan] to catch in builds."
            )
            return suggestions  # Return early with specific guidance

        if var_name:
            # Common typos
            typo_map = {
                "titel": "title",
                "dat": "date",
                "autor": "author",
                "sumary": "summary",
                "desciption": "description",
                "metdata": "metadata",
                "conent": "content",
            }

            if var_name.lower() in typo_map:
                suggestions.append(
                    f"Common typo: try [cyan]'{typo_map[var_name.lower()]}'[/cyan] instead"
                )

            # Suggest safe access
            suggestions.append(
                f"Use safe access: [cyan]{{{{ {var_name} | default('fallback') }}}}[/cyan]"
            )

            # Check if it looks like metadata access
            if "." in var_name:
                base, attr = var_name.rsplit(".", 1)
                suggestions.append(
                    f"Or use dict access: [cyan]{{{{ {base}.get('{attr}', 'default') }}}}[/cyan]"
                )
            else:
                # Suggest adding to frontmatter
                suggestions.append(f"Add [cyan]'{var_name}'[/cyan] to page frontmatter")

    elif error.error_type == "filter":
        filter_name = _extract_filter_name(error.message)

        if filter_name:
            # Suggest checking documentation
            suggestions.append(
                "Check available filters in [cyan]bengal --help[/cyan] or documentation"
            )

            # Common filter mistakes
            if "date" in filter_name.lower():
                suggestions.append("For dates, use [cyan]{{ date | date('%Y-%m-%d') }}[/cyan]")

    elif error.error_type == "syntax":
        if "unexpected" in error_str:
            suggestions.append("Check for missing [cyan]%}[/cyan] or [cyan]}}[/cyan] tags")

        if "expected token" in error_str:
            suggestions.append("Verify Jinja2 syntax - might be using unsupported features")

        if "endfor" in error_str or "endif" in error_str:
            suggestions.append(
                "Every [cyan]{% for %}[/cyan] needs [cyan]{% endfor %}[/cyan], "
                "every [cyan]{% if %}[/cyan] needs [cyan]{% endif %}[/cyan]"
            )

    return suggestions


def _extract_variable_name(error_message: str) -> str | None:
    """Extract variable name from undefined variable error."""
    import re

    # Try different patterns
    patterns = [
        r"'([^']+)' is undefined",
        r"undefined variable: ([^\s]+)",
        r"no such element: ([^\s]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, error_message)
        if match:
            return match.group(1)

    return None


def _extract_filter_name(error_message: str) -> str | None:
    """Extract filter name from filter error."""
    import re

    match = re.search(r"no filter named ['\"]([^'\"]+)['\"]", error_message, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def _extract_dict_attribute(error_message: str) -> str | None:
    """Extract attribute name from dict access error."""
    import re

    # Pattern: 'dict object' has no attribute 'attr_name'
    match = re.search(r"'dict object' has no attribute '([^']+)'", error_message)
    if match:
        return match.group(1)

    return None


def _display_template_error_click(error: TemplateRenderError, use_color: bool = True) -> None:
    """Fallback display using click (original implementation)."""
    import click

    # Header
    error_type_names = {
        "syntax": "Template Syntax Error",
        "filter": "Unknown Filter",
        "undefined": "Undefined Variable",
        "runtime": "Template Runtime Error",
        "other": "Template Error",
    }

    header = error_type_names.get(error.error_type, "Template Error")
    click.echo(click.style(f"\n⚠️  {header}", fg="red", bold=True))

    # File and line
    ctx = error.template_context
    if ctx.template_path:
        click.echo(click.style("\n  File: ", fg="cyan") + str(ctx.template_path))
    else:
        click.echo(click.style("\n  Template: ", fg="cyan") + ctx.template_name)

    if ctx.line_number:
        click.echo(click.style("  Line: ", fg="cyan") + str(ctx.line_number))

    # Source code context
    if ctx.surrounding_lines:
        click.echo(click.style("\n  Code:", fg="cyan"))
        for line_num, line_content in ctx.surrounding_lines:
            is_error_line = line_num == ctx.line_number
            prefix = ">" if is_error_line else " "
            if is_error_line:
                styled_line = click.style(line_content, fg="red", bold=True)
            else:
                styled_line = click.style(line_content, fg="white")

            click.echo(click.style(f"  {prefix} {line_num:4d} | ", fg="cyan") + styled_line)

            # Add pointer to error location
            if is_error_line and ctx.source_line:
                # Simple pointer (could be enhanced with column info)
                pointer = " " * (len(f"  {prefix} {line_num:4d} | ")) + "^" * min(
                    len(ctx.source_line.strip()), 40
                )
                click.echo(click.style(pointer, fg="red", bold=True))

    # Error message
    click.echo(click.style("\n  Error: ", fg="red", bold=True) + error.message)

    # Suggestion
    if error.suggestion:
        click.echo(click.style("\n  Suggestion: ", fg="yellow", bold=True) + error.suggestion)

    # Alternatives
    if error.available_alternatives:
        click.echo(
            click.style("\n  Did you mean: ", fg="yellow", bold=True)
            + ", ".join(f"'{alt}'" for alt in error.available_alternatives)
        )

    # Inclusion chain
    if error.inclusion_chain:
        click.echo(click.style("\n  Template Chain:", fg="cyan"))
        for line in str(error.inclusion_chain).split("\n"):
            click.echo(f"  {line}")

    # Page source
    if error.page_source:
        click.echo(click.style("\n  Used by page: ", fg="cyan") + str(error.page_source))

    # Template search paths
    if error.search_paths:
        click.echo(click.style("\n  🔍 Template Search Paths:", fg="cyan", bold=True))
        for i, search_path in enumerate(error.search_paths, 1):
            found_marker = ""
            if ctx.template_path and ctx.template_path.is_relative_to(search_path):
                found_marker = click.style(" ← found here", fg="green")
            click.echo(f"     {i}. {search_path}{found_marker}")

    click.echo()
