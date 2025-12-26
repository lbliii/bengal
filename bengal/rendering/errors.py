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

    ErrorDeduplicator:
        Tracks and deduplicates similar errors across multiple pages to
        reduce noise in build output. Attached to BuildStats (not global).

Error Types:
    - syntax: Invalid Jinja2 syntax (missing tags, brackets, etc.)
    - filter: Unknown filter name (e.g., ``| nonexistent``)
    - undefined: Undefined variable access (e.g., ``{{ missing_var }}``)
    - callable: NoneType is not callable (e.g., missing filter/function registration)
    - none_access: NoneType is not iterable (e.g., using 'in' on None)
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

    Error deduplication for batch rendering (via BuildStats):

    >>> dedup = build_stats.get_error_deduplicator()
    >>> for page in pages:
    ...     try:
    ...         render(page)
    ...     except Exception as e:
    ...         error = TemplateRenderError.from_jinja2_error(...)
    ...         if dedup.should_display(error):
    ...             display_template_error(error)
    >>> dedup.display_summary()  # Show counts of suppressed errors

Error Message Enhancement:
    The module includes smart suggestion generation:
    - Typo detection for variable/filter names
    - Safe access patterns for undefined errors
    - Callable identification from template source
    - Documentation links for common issues

Related Modules:
    - bengal.rendering.engines.errors: Low-level engine exceptions
    - bengal.errors: Base error classes (BengalRenderingError)
    - bengal.orchestration.stats: BuildStats with error deduplicator
    - bengal.utils.rich_console: Rich terminal output utilities
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class ErrorDeduplicator:
    """
    Tracks and deduplicates similar template errors across multiple pages.

    When the same error (same template, line, error type) occurs on multiple
    pages, only the first occurrence is displayed in full. Subsequent occurrences
    are counted and summarized at the end.

    Usage:
        >>> dedup = get_error_deduplicator()
        >>> if dedup.should_display(error):
        ...     display_template_error(error)
        >>> dedup.display_summary()
    """

    # Key: (template_name, line_number, error_type, message_prefix)
    # Value: list of page sources that had this error
    seen_errors: dict[tuple[str, int | None, str, str], list[str]] = field(default_factory=dict)
    # Maximum errors to show per unique error signature
    max_display_per_error: int = 2

    def _get_error_key(self, error: TemplateRenderError) -> tuple[str, int | None, str, str]:
        """Generate a key for error deduplication."""
        # Use first 50 chars of message to group similar errors
        msg_prefix = str(error.message)[:50] if error.message else ""
        return (
            error.template_context.template_name,
            error.template_context.line_number,
            error.error_type,
            msg_prefix,
        )

    def should_display(self, error: TemplateRenderError) -> bool:
        """
        Check if this error should be displayed or suppressed.

        Returns True for the first N occurrences of each unique error,
        False for subsequent ones.
        """
        key = self._get_error_key(error)
        page_source = str(error.page_source) if error.page_source else "unknown"

        if key not in self.seen_errors:
            self.seen_errors[key] = []

        self.seen_errors[key].append(page_source)

        # Display if we haven't hit the limit yet
        return len(self.seen_errors[key]) <= self.max_display_per_error

    def get_suppressed_count(self) -> int:
        """Get total count of suppressed (not displayed) errors."""
        total = 0
        for pages in self.seen_errors.values():
            if len(pages) > self.max_display_per_error:
                total += len(pages) - self.max_display_per_error
        return total

    def display_summary(self) -> None:
        """Display summary of suppressed errors."""
        suppressed = self.get_suppressed_count()
        if suppressed == 0:
            return

        try:
            from bengal.utils.rich_console import get_console, should_use_rich

            if should_use_rich():
                console = get_console()
                console.print()
                console.print(
                    f"[yellow bold]⚠️  {suppressed} similar error(s) suppressed[/yellow bold]"
                )

                # Show summary of each unique error
                for key, pages in self.seen_errors.items():
                    if len(pages) > self.max_display_per_error:
                        template, line, error_type, msg = key
                        extra = len(pages) - self.max_display_per_error
                        console.print(
                            f"   • [dim]{template}:{line}[/dim] ({error_type}): "
                            f"[yellow]+{extra} more page(s)[/yellow]"
                        )
                console.print()
                return
        except ImportError:
            pass

        # Fallback to click
        import click

        click.echo()
        click.secho(f"⚠️  {suppressed} similar error(s) suppressed", fg="yellow", bold=True)
        for key, pages in self.seen_errors.items():
            if len(pages) > self.max_display_per_error:
                template, line, error_type, msg = key
                extra = len(pages) - self.max_display_per_error
                click.echo(f"   • {template}:{line} ({error_type}): +{extra} more page(s)")
        click.echo()

    def reset(self) -> None:
        """Reset the deduplicator for a new build."""
        self.seen_errors.clear()


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

        # Generate suggestion (pass template path for better callable identification)
        suggestion = cls._generate_suggestion(
            error, error_type, template_engine, context.template_path
        )

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

        # Check for "NoneType is not callable" errors first
        # This happens when a filter/function in the template is None
        if isinstance(error, TypeError) and (
            "'nonetype' object is not callable" in error_str
            or "nonetype object is not callable" in error_str
        ):
            return "callable"

        # Check for "NoneType is not iterable/subscriptable" errors
        # This happens when using 'in' operator or iteration on None
        if isinstance(error, TypeError) and (
            "argument of type 'nonetype' is not" in error_str
            or "'nonetype' object is not iterable" in error_str
            or "'nonetype' object is not subscriptable" in error_str
            or "'nonetype' has no" in error_str
        ):
            return "none_access"

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
        import traceback as tb_module

        # Jinja2 provides: error.lineno, error.filename, error.source
        line_number = getattr(error, "lineno", None)
        filename = getattr(error, "filename", None) or template_name

        # For TypeError (callable/none_access errors), try to extract location from traceback
        if isinstance(error, TypeError) and line_number is None:
            tb = tb_module.extract_tb(error.__traceback__)
            for frame in reversed(tb):
                # Look for template-related frames
                if "templates/" in frame.filename or frame.filename.endswith(".html"):
                    # This is likely the template location
                    line_number = frame.lineno
                    # Try to get the actual template name from the path
                    if "templates/" in frame.filename:
                        parts = frame.filename.split("templates/")
                        if len(parts) > 1:
                            filename = parts[-1]
                    break
                # Also check for Jinja2/Kida internal frames that have template info
                if "jinja2" in frame.filename.lower() or "kida" in frame.filename.lower():
                    # The previous frame might have the actual template line
                    continue

        # Find template path
        template_path = template_engine._find_template_path(filename)

        # Get source lines
        source_line = None
        surrounding_lines = []

        if template_path and template_path.exists():
            try:
                with open(template_path, encoding="utf-8") as f:
                    lines = f.readlines()

                # If line_number is 1 and it's a comment, find first real code line
                # This happens when compiled templates don't preserve line info
                if line_number == 1 and lines:
                    first_line = lines[0].strip()
                    if first_line.startswith("{#") or first_line.startswith("#"):
                        # Find the first non-comment, non-empty line with actual code
                        line_number = TemplateRenderError._find_first_code_line(lines, error)

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
    def _find_first_code_line(lines: list[str], error: Exception) -> int:
        """
        Find the first line with actual template code (not comments).

        For TypeError errors, tries to find lines with function calls or filters
        that might be the source of the error.

        Args:
            lines: Template source lines
            error: The original error

        Returns:
            Best guess line number (1-indexed), defaults to 1 if not found
        """
        import re

        in_comment = False
        first_code_line = 1
        found_first_code = False

        # Patterns that indicate callable usage (likely error source for TypeError)
        callable_patterns = [
            r"\{\{.*\w+\s*\(",  # {{ func(
            r"\{\%.*\w+\s*\(",  # {% func(
            r"\|s*\w+",  # | filter
        ]

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track multi-line comments
            if "{#" in stripped and "#}" not in stripped:
                in_comment = True
                continue
            if "#}" in stripped:
                in_comment = False
                continue
            if in_comment:
                continue

            # Skip empty lines and single-line comments
            if not stripped or stripped.startswith("{#"):
                continue

            # Found first code line
            if not found_first_code:
                first_code_line = i
                found_first_code = True

            # For callable errors, prefer lines with function calls or filters
            if isinstance(error, TypeError):
                for pattern in callable_patterns:
                    if re.search(pattern, line):
                        return i

        return first_code_line

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
    @staticmethod
    def _generate_suggestion(
        error: Exception,
        error_type: str,
        template_engine: Any,
        template_path: Path | None = None,
    ) -> str | None:
        """Generate helpful suggestion based on error."""
        error_str = str(error).lower()

        if error_type == "callable":
            # Try to identify what was None from the traceback and template
            callable_info = TemplateRenderError._identify_none_callable(error, template_path)
            if callable_info:
                return callable_info
            return (
                "A function or filter being called is None. Check that all filters and "
                "template functions are properly registered in the template engine."
            )

        if error_type == "none_access":
            # This is "argument of type 'NoneType' is not iterable/subscriptable"
            return (
                "A variable is None when it should be a list, dict, or string. "
                "Check that all context variables are properly initialized. "
                "Common causes: missing data in page.metadata, section is None, or "
                "element is None. Use {% if var %} guards before accessing."
            )

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
    def _identify_none_callable(error: Exception, template_path: Path | None = None) -> str | None:
        """
        Analyze traceback and template source to identify what None callable was being called.

        Args:
            error: The TypeError exception
            template_path: Path to the template file (for source analysis)

        Returns:
            Descriptive string about likely None callable, or None
        """
        import re
        import traceback as tb_module

        tb = tb_module.extract_tb(error.__traceback__)
        suspects: list[str] = []

        # Look for clues in the traceback
        for frame in reversed(tb):
            # Check if this is a filter call
            if "filters" in frame.filename.lower():
                suspects.append("a filter function")
                continue

            # Check for common patterns in the code line
            if frame.line:
                line = frame.line

                # Pattern: something.call(...) or something(...)
                # Look for {{ ... | filter }} patterns
                filter_match = re.search(r"\|\s*(\w+)", line)
                if filter_match:
                    filter_name = filter_match.group(1)
                    suspects.append(f"filter '{filter_name}'")

                # Pattern: function call like func(...)
                call_match = re.search(r"(\w+)\s*\(", line)
                if call_match:
                    func_name = call_match.group(1)
                    if func_name not in (
                        "if",
                        "for",
                        "while",
                        "with",
                        "set",
                        "print",
                        "range",
                        "len",
                        "dict",
                        "list",
                        "str",
                        "int",
                        "float",
                        "isinstance",
                        "getattr",
                        "hasattr",
                        "type",
                        "exec",
                    ):
                        suspects.append(f"function '{func_name}'")

        # If we have the template path, scan it for likely suspects
        if template_path and template_path.exists():
            try:
                template_suspects = TemplateRenderError._scan_template_for_callables(template_path)
                suspects.extend(template_suspects)
            except Exception:
                pass

        # Deduplicate and format
        unique_suspects = list(dict.fromkeys(suspects))  # Preserve order, remove dupes

        if unique_suspects:
            if len(unique_suspects) == 1:
                return (
                    f"Likely cause: {unique_suspects[0]} is None or not registered. "
                    f"Verify it's defined in template globals or context."
                )
            else:
                formatted = ", ".join(unique_suspects[:3])
                if len(unique_suspects) > 3:
                    formatted += f" (and {len(unique_suspects) - 3} more)"
                return (
                    f"Suspected callables: {formatted}. "
                    f"One of these is likely None or not registered."
                )

        return None

    @staticmethod
    def _scan_template_for_callables(template_path: Path) -> list[str]:
        """
        Scan template source for function calls and filters that might be None.

        Returns list of suspected callable names.
        """
        import re

        suspects: list[str] = []

        try:
            with open(template_path, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return suspects

        # Common global functions that are usually registered
        known_safe = {
            "range",
            "len",
            "dict",
            "list",
            "str",
            "int",
            "float",
            "bool",
            "set",
            "tuple",
            "enumerate",
            "zip",
            "sorted",
            "reversed",
            "min",
            "max",
            "sum",
            "abs",
            "round",
            "type",
            "isinstance",
            "getattr",
            "hasattr",
            "callable",
            "print",
            "super",
            # Common Jinja2/template builtins
            "loop",
            "self",
            "caller",
            # Control flow (not functions)
            "if",
            "else",
            "elif",
            "for",
            "endfor",
            "endif",
            "block",
            "endblock",
            "macro",
            "endmacro",
            "call",
            "endcall",
            "include",
            "import",
            "from",
            "extends",
            "with",
            "endwith",
        }

        # Find function calls: word( that aren't in Jinja tags
        # Pattern: {{ func( or {% func( but not {{ var.method( (those are likely safe)
        func_pattern = r"\{\{[^}]*\b(\w+)\s*\([^}]*\}\}"
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            if func_name.lower() not in known_safe:
                suspects.append(f"function '{func_name}'")

        # Find filters: | filter_name
        filter_pattern = r"\|\s*(\w+)"
        for match in re.finditer(filter_pattern, content):
            filter_name = match.group(1)
            if filter_name.lower() not in known_safe:
                suspects.append(f"filter '{filter_name}'")

        return suspects

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
        "callable": "https://bengal.dev/docs/templates/troubleshooting#none-not-callable",
        "none_access": "https://bengal.dev/docs/templates/troubleshooting#none-not-iterable",
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
    if error.error_type == "callable":
        # This is a "NoneType is not callable" error
        suggestions.append(
            "[red bold]A filter or function is None![/red bold] This means something "
            "expected to be callable wasn't registered properly."
        )

        # Try to find clues from the source line
        if error.template_context.source_line:
            line = error.template_context.source_line
            import re

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

    elif error.error_type == "none_access":
        # This is "argument of type 'NoneType' is not a container or iterable"
        suggestions.append(
            "[red bold]A variable is None![/red bold] This happens when using 'in' operator "
            "or iterating over a variable that doesn't exist or is None."
        )

        # Try to find clues from the source line
        if error.template_context.source_line:
            line = error.template_context.source_line
            import re

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

    elif error.error_type == "undefined":
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
        "callable": "None Is Not Callable",
        "none_access": "None Is Not Iterable",
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
