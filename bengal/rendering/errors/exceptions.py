"""
Template rendering exception classes.

This module contains the TemplateRenderError exception which provides rich
error information for template rendering failures, including source context,
suggestions, and IDE-friendly formatting.

Classes:
    TemplateRenderError: Rich exception with template context, line numbers,
        source snippets, and actionable suggestions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import TemplateSyntaxError, UndefinedError
from jinja2.exceptions import TemplateAssertionError, TemplateRuntimeError

from bengal.errors import BengalRenderingError
from bengal.utils.logger import truncate_error

from .context import InclusionChain, TemplateErrorContext


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
