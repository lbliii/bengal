"""
Display functions for template errors.

This module provides functions to display template errors in the terminal
with syntax highlighting (via Rich if available) or plain text fallback.

Functions:
    display_template_error: Main entry point for displaying errors
    _display_template_error_rich: Rich-based display with syntax highlighting
    _display_template_error_plain: Plain text fallback display

Helper Functions:
    _generate_enhanced_suggestions: Context-aware suggestion generation
    _extract_variable_name: Extract variable name from undefined error
    _extract_filter_name: Extract filter name from filter error
    _extract_dict_attribute: Extract attribute from dict access error
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .exceptions import TemplateRenderError


def display_template_error(error: TemplateRenderError, use_color: bool = True) -> None:
    """
    Display a rich template error in the terminal.

    Args:
        error: Rich error object
        use_color: Whether to use terminal colors

    """
    # Try to use rich for enhanced display
    try:
        from bengal.utils.observability.rich_console import should_use_rich

        if should_use_rich():
            _display_template_error_rich(error)
            return
    except ImportError:
        pass  # Fall back to plain text

    # Fallback to plain text display
    _display_template_error_plain(error)


def _display_template_error_rich(error: TemplateRenderError) -> None:
    """Display template error with rich formatting."""
    from rich.panel import Panel
    from rich.syntax import Syntax

    from bengal.utils.observability.rich_console import get_console

    console = get_console()

    # Error type names
    error_type_names = {
        "syntax": "Template Syntax Error",
        "filter": "Unknown Filter",
        "undefined": "Undefined Variable",
        "runtime": "Template Runtime Error",
        "callable": "None Is Not Callable",
        "none_access": "None Is Not Iterable",
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

    # Generate enhanced suggestions (handles both TemplateRenderError and engine TemplateError)
    suggestions = _generate_enhanced_suggestions(error)

    if suggestions:
        console.print()
        console.print("[yellow bold]💡 Suggestions:[/yellow bold]")
        console.print()
        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"   [yellow]{i}.[/yellow] {suggestion}")

    # Alternatives (for filter/variable errors)
    available_alternatives = getattr(error, "available_alternatives", None) or []
    if available_alternatives:
        console.print()
        console.print("[yellow bold]Did you mean:[/yellow bold]")
        for alt in available_alternatives:
            console.print(f"   • [cyan]{alt}[/cyan]")

    # Inclusion chain
    inclusion_chain = getattr(error, "inclusion_chain", None)
    if inclusion_chain:
        console.print()
        console.print("[cyan bold]Template Chain:[/cyan bold]")
        for line in str(inclusion_chain).split("\n"):
            console.print(f"  {line}")

    # Page source
    page_source = getattr(error, "page_source", None)
    if page_source:
        console.print()
        console.print(f"[cyan]Used by page:[/cyan] {page_source}")

    # Template search paths (helpful for debugging template not found errors)
    search_paths = getattr(error, "search_paths", None) or []
    if search_paths:
        console.print()
        console.print("[cyan bold]🔍 Template Search Paths:[/cyan bold]")
        for i, search_path in enumerate(search_paths, 1):
            # Mark the path where template was found (if found)
            found_marker = ""
            if ctx.template_path and ctx.template_path.is_relative_to(search_path):
                found_marker = " [green]← found here[/green]"
            console.print(f"   {i}. [dim]{search_path}[/dim]{found_marker}")

    # Documentation link
    doc_links = {
        "filter": "https://lbliii.github.io/bengal/docs/templates/filters",
        "undefined": "https://lbliii.github.io/bengal/docs/templates/variables",
        "syntax": "https://lbliii.github.io/bengal/docs/templates/syntax",
        "callable": "https://lbliii.github.io/bengal/docs/templates/troubleshooting#none-not-callable",
        "none_access": "https://lbliii.github.io/bengal/docs/templates/troubleshooting#none-not-iterable",
    }

    if error.error_type in doc_links:
        console.print()
        console.print(f"[dim]📚 Learn more: {doc_links[error.error_type]}[/dim]")

    console.print()


def _generate_enhanced_suggestions(error: TemplateRenderError) -> list[str]:
    """Generate context-aware suggestions for template errors."""
    suggestions = []

    # Start with existing suggestion (TemplateRenderError has it; engine TemplateError does not)
    suggestion = getattr(error, "suggestion", None)
    if suggestion:
        suggestions.append(suggestion)

    error_str = str(error.message).lower()

    # Enhanced suggestions based on error type
    if error.error_type == "callable":
        # This is a "NoneType is not callable" error
        suggestions.append(
            "[red bold]A filter or function is None![/red bold] This means something "
            "expected to be callable wasn't registered properly."
        )

        # Try to find clues from the source line
        if error.template_context.source_line:
            line = error.template_context.source_line

            # Look for filter patterns: | filter_name
            filter_matches = re.findall(r"\|\s*(\w+)", line)
            if filter_matches:
                suggestions.append(
                    f"Suspected filters: [cyan]{', '.join(filter_matches)}[/cyan] - "
                    f"verify these are registered in the template engine."
                )

            # Look for function calls: func_name(
            func_matches = re.findall(r"(\w+)\s*\(", line)
            func_matches = [
                f
                for f in func_matches
                if f not in ("if", "for", "while", "with", "set", "range", "len", "dict", "list")
            ]
            if func_matches:
                suggestions.append(
                    f"Suspected functions: [cyan]{', '.join(func_matches)}[/cyan] - "
                    f"verify these are defined in template globals or context."
                )

        suggestions.append(
            "Common causes: missing filter registration, context variable is None when "
            "a method is called on it, or a global function wasn't added to the engine."
        )
        suggestions.append(
            "Debug tip: Add [cyan]{% if debug %}{{ element | pprint }}{% endif %}[/cyan] "
            "to inspect what's being passed to the template."
        )
        return suggestions

    if error.error_type == "none_access":
        # This is "argument of type 'NoneType' is not a container or iterable"
        suggestions.append(
            "[red bold]A variable is None![/red bold] This happens when using 'in' operator "
            "or iterating over a variable that doesn't exist or is None."
        )

        # Try to find clues from the source line
        if error.template_context.source_line:
            line = error.template_context.source_line

            # Look for 'in' patterns: if x in y
            in_match = re.search(r"in\s+(\w+(?:\.\w+)*)", line)
            if in_match:
                var_name = in_match.group(1)
                suggestions.append(
                    f"Variable [cyan]{var_name}[/cyan] is likely None. "
                    f"Add a guard: [green]{{% if {var_name} and x in {var_name} %}}[/green]"
                )

            # Look for for loops: for x in y
            for_match = re.search(r"for\s+\w+\s+in\s+(\w+(?:\.\w+)*)", line)
            if for_match:
                var_name = for_match.group(1)
                suggestions.append(
                    f"Variable [cyan]{var_name}[/cyan] is likely None. "
                    f"Add a guard: [green]{{% if {var_name} %}}{{% for x in {var_name} %}}...{{% endif %}}[/green]"
                )

        suggestions.append(
            "Common causes: missing context variable, accessing .children or .pages on None, "
            "or optional metadata that wasn't provided."
        )
        suggestions.append(
            "Debug tip: Add [cyan]{{ var | pprint }}[/cyan] before the error line to see what's None."
        )
        return suggestions

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
    match = re.search(r"no filter named ['\"]([^'\"]+)['\"]", error_message, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def _extract_dict_attribute(error_message: str) -> str | None:
    """Extract attribute name from dict access error."""
    # Pattern: 'dict object' has no attribute 'attr_name'
    match = re.search(r"'dict object' has no attribute '([^']+)'", error_message)
    if match:
        return match.group(1)

    return None


def _display_template_error_plain(error: TemplateRenderError) -> None:
    """Plain-text fallback display (no Rich)."""
    import sys

    out = sys.stdout

    error_type_names = {
        "syntax": "Template Syntax Error",
        "filter": "Unknown Filter",
        "undefined": "Undefined Variable",
        "runtime": "Template Runtime Error",
        "callable": "None Is Not Callable",
        "none_access": "None Is Not Iterable",
        "other": "Template Error",
    }

    header = error_type_names.get(error.error_type, "Template Error")
    print(f"\n  {header}", file=out)

    ctx = error.template_context
    if ctx.template_path:
        print(f"\n  File: {ctx.template_path}", file=out)
    else:
        print(f"\n  Template: {ctx.template_name}", file=out)

    if ctx.line_number:
        print(f"  Line: {ctx.line_number}", file=out)

    if ctx.surrounding_lines:
        print("\n  Code:", file=out)
        for line_num, line_content in ctx.surrounding_lines:
            is_error_line = line_num == ctx.line_number
            prefix = ">" if is_error_line else " "
            print(f"  {prefix} {line_num:4d} | {line_content}", file=out)

            if is_error_line and ctx.source_line:
                pointer = " " * (len(f"  {prefix} {line_num:4d} | ")) + "^" * min(
                    len(ctx.source_line.strip()), 40
                )
                print(pointer, file=out)

    print(f"\n  Error: {error.message}", file=out)

    suggestion = getattr(error, "suggestion", None)
    if suggestion:
        print(f"\n  Suggestion: {suggestion}", file=out)

    available_alternatives = getattr(error, "available_alternatives", None) or []
    if available_alternatives:
        print(
            f"\n  Did you mean: {', '.join(f'{alt!r}' for alt in available_alternatives)}", file=out
        )

    inclusion_chain = getattr(error, "inclusion_chain", None)
    if inclusion_chain:
        print("\n  Template Chain:", file=out)
        for line in str(inclusion_chain).split("\n"):
            print(f"  {line}", file=out)

    page_source = getattr(error, "page_source", None)
    if page_source:
        print(f"\n  Used by page: {page_source}", file=out)

    search_paths = getattr(error, "search_paths", None) or []
    if search_paths:
        print("\n  Template Search Paths:", file=out)
        for i, search_path in enumerate(search_paths, 1):
            found_marker = ""
            if ctx.template_path and ctx.template_path.is_relative_to(search_path):
                found_marker = " <-- found here"
            print(f"     {i}. {search_path}{found_marker}", file=out)

    print(file=out)
