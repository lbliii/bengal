"""
Beautiful error display for CLI.

Provides formatted display of BengalError instances with error codes,
suggestions, file locations, and documentation links.

Functions:
    display_bengal_error: Display a BengalError with beautiful formatting
    display_template_render_error: Display a TemplateRenderError with the
        rich source-frame layout (code window, caret, inclusion chain,
        search paths, alternatives) routed through CLIOutput.
    beautify_common_exception: Convert common exceptions to user-friendly messages

Note:
    This module was moved from bengal.cli.helpers.error_display to
    bengal.errors.display to fix layer violations (discovery importing from cli).
    The old import path still works for backward compatibility.

Example:
    >>> from bengal.errors import BengalRenderingError, ErrorCode
    >>> from bengal.errors.display import display_bengal_error
    >>> from bengal.output import CLIOutput
    >>>
    >>> error = BengalRenderingError(
    ...     "Template not found: single.html",
    ...     code=ErrorCode.R001,
    ...     file_path=Path("content/post.md"),
    ...     suggestion="Check templates/ directory",
    ... )
    >>> display_bengal_error(error, CLIOutput())

See Also:
- bengal/errors/exceptions.py: BengalError exception hierarchy
- bengal/errors/codes.py: Error code definitions
- bengal/cli/helpers/error_handling.py: CLI error decorator

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.errors import BengalError
    from bengal.output import CLIOutput
    from bengal.rendering.errors import TemplateRenderError


_ERROR_TYPE_HEADERS: dict[str, str] = {
    "syntax": "Template Syntax Error",
    "filter": "Unknown Filter",
    "undefined": "Undefined Variable",
    "runtime": "Template Runtime Error",
    "callable": "None Is Not Callable",
    "none_access": "None Is Not Iterable",
    "type_comparison": "Type Comparison Error",
    "include_missing": "Include Not Found",
    "circular_include": "Circular Include",
    "other": "Template Error",
}


def display_bengal_error(error: BengalError, cli: CLIOutput) -> None:
    """
    Display a BengalError with beautiful, structured formatting.

    Formats the error with:
    - Error code and category header
    - Main error message
    - File location (clickable in most terminals)
    - Related files for debugging
    - Actionable suggestion
    - Documentation link

    Args:
        error: The BengalError instance to display.
        cli: CLI output helper for formatted printing.

    Example:
            >>> display_bengal_error(error, cli)
        #
        #   ✖ [C001] Config Error
        #
        #   Invalid YAML syntax in bengal.toml
        #
        #   File: bengal.toml:12
        #
        #   Tip: Check for missing colons, incorrect indentation
        #
        #   Docs: https://lbliii.github.io/bengal/docs/reference/errors/#c001

    """
    icons = cli.icons

    # Header with code and category
    cli.blank()
    if error.code:
        code_str = f"[{error.code.name}]"
        category = error.code.category.replace("_", " ").title()
        cli.error(f"{code_str} {category} Error")
    else:
        cli.error("Error")
    cli.blank()

    # Main message
    cli.info(f"  {error.message}")
    cli.blank()

    # File location (clickable in most terminals)
    if error.file_path:
        location = f"  File: {error.file_path}"
        if error.line_number:
            location += f":{error.line_number}"
        cli.info(location)
        cli.blank()

    # Related files (for debugging)
    if error.related_files:
        cli.info("  Related:")
        for rf in error.related_files[:3]:
            cli.info(f"    {icons.dot} {rf}")
        if len(error.related_files) > 3:
            cli.info(f"    ... and {len(error.related_files) - 3} more")
        cli.blank()

    # Actionable suggestion
    if error.suggestion:
        cli.info(f"  Tip: {error.suggestion}")
        cli.blank()

    # Documentation link
    if error.code:
        docs_url = f"https://lbliii.github.io/bengal{error.code.docs_url}"
        cli.info(f"  Docs: {docs_url}")
        cli.blank()


def display_template_render_error(error: TemplateRenderError, cli: CLIOutput) -> None:
    """Display a :class:`TemplateRenderError` with rich formatting via CLIOutput.

    Renders the same structure as the legacy plain-text formatter but
    routes through :class:`CLIOutput` so output respects the active TTY,
    quiet/verbose flags, and Rich styling.

    Layout:
        1. Header — error type or `[R0XX]` code badge.
        2. File / Template name.
        3. Line number.
        4. Code window with `>` marker on the offending line and a
           caret underline.
        5. Error message.
        6. Suggestion (``Tip:``).
        7. Alternative filters/variables (``Did you mean:``).
        8. Inclusion chain (``Template Chain:``).
        9. Source page that triggered the error.
       10. Template search paths (with `<-- found here` marker).
       11. Docs URL (when an ErrorCode is set).
    """
    code_obj = getattr(error, "code", None)
    code_prefix = f"[{code_obj.name}] " if code_obj else ""

    header = _ERROR_TYPE_HEADERS.get(error.error_type, "Template Error")

    cli.blank()
    cli.error(f"{code_prefix}{header}")

    ctx = error.template_context
    if ctx.template_path:
        cli.blank()
        cli.info(f"  File: {ctx.template_path}")
    else:
        cli.blank()
        cli.info(f"  Template: {ctx.template_name}")

    if ctx.line_number:
        cli.info(f"  Line: {ctx.line_number}")

    if ctx.surrounding_lines:
        cli.blank()
        cli.info("  Code:")
        for line_num, line_content in ctx.surrounding_lines:
            is_error_line = line_num == ctx.line_number
            prefix = ">" if is_error_line else " "
            cli.info(f"  {prefix} {line_num:4d} | {line_content}")

            if is_error_line and ctx.source_line:
                pointer = " " * (len(f"  {prefix} {line_num:4d} | ")) + "^" * min(
                    len(ctx.source_line.strip()), 40
                )
                cli.info(pointer)

    cli.blank()
    cli.info(f"  Error: {error.message}")

    suggestion = getattr(error, "suggestion", None)
    if suggestion:
        cli.blank()
        cli.info(f"  Suggestion: {suggestion}")

    available_alternatives = getattr(error, "available_alternatives", None) or []
    if available_alternatives:
        top, *rest = available_alternatives
        cli.blank()
        cli.info(f"  Did you mean: {top!r}?")
        if rest:
            cli.info(f"  Other matches: {', '.join(f'{alt!r}' for alt in rest)}")

    inclusion_chain = getattr(error, "inclusion_chain", None)
    if inclusion_chain:
        cli.blank()
        cli.info("  Template Chain:")
        for line in str(inclusion_chain).split("\n"):
            cli.info(f"  {line}")

    page_source = getattr(error, "page_source", None)
    if page_source:
        cli.blank()
        cli.info(f"  Used by page: {page_source}")

    search_paths = getattr(error, "search_paths", None) or []
    if search_paths:
        cli.blank()
        cli.info("  Template Search Paths:")
        for i, search_path in enumerate(search_paths, 1):
            found_marker = ""
            if ctx.template_path and ctx.template_path.is_relative_to(search_path):
                found_marker = " <-- found here"
            cli.info(f"     {i}. {search_path}{found_marker}")

    if code_obj:
        docs_url = f"https://lbliii.github.io/bengal{code_obj.docs_url}"
        cli.blank()
        cli.info(f"  Docs: {docs_url}")

    cli.blank()


def beautify_common_exception(e: Exception) -> tuple[str, str | None] | None:
    """
    Return (message, suggestion) for common exceptions, or None.

    Handles exceptions from yaml, toml, jinja2, and filesystem operations
    to provide user-friendly error messages.

    Args:
        e: The exception to beautify.

    Returns:
        Tuple of (message, suggestion) if the exception is recognized,
        None otherwise.

    Example:
            >>> result = beautify_common_exception(FileNotFoundError("config.yaml"))
            >>> if result:
            ...     message, suggestion = result
            ...     print(f"Error: {message}")
            ...     if suggestion:
            ...         print(f"Tip: {suggestion}")

    """
    # Handle file not found
    if isinstance(e, FileNotFoundError):
        filename = getattr(e, "filename", None) or str(e)
        return (
            f"File not found: {filename}",
            "Check the path exists and spelling is correct",
        )

    # Handle permission errors
    if isinstance(e, PermissionError):
        filename = getattr(e, "filename", str(e))
        return (
            f"Permission denied: {filename}",
            "Check file permissions or run with appropriate access",
        )

    # Handle YAML errors
    try:
        import yaml

        if isinstance(e, yaml.YAMLError):
            if hasattr(e, "problem_mark") and e.problem_mark is not None:
                mark = e.problem_mark
                # Mark is yaml.Mark which has line and column attributes
                line = getattr(mark, "line", 0)
                column = getattr(mark, "column", 0)
                return (
                    f"YAML syntax error at line {line + 1}, column {column + 1}",
                    "Check for missing colons, incorrect indentation, or unquoted special characters",
                )
            return (
                "Invalid YAML syntax",
                "Validate your YAML at https://yamlvalidator.com",
            )
    except ImportError:
        pass

    # Handle TOML errors
    try:
        import tomllib

        if isinstance(e, tomllib.TOMLDecodeError):
            return (
                f"TOML syntax error: {e}",
                "Check for unquoted strings or missing brackets",
            )
    except ImportError:
        pass

    # Handle Kida template errors
    try:
        from kida import (
            TemplateError as KidaTemplateError,
        )
        from kida import (
            TemplateNotFoundError as KidaTemplateNotFound,
        )
        from kida import (
            TemplateSyntaxError as KidaSyntaxError,
        )
        from kida import (
            UndefinedError as KidaUndefinedError,
        )

        if isinstance(e, KidaSyntaxError):
            location = ""
            if getattr(e, "lineno", None):
                location = f" at line {e.lineno}"
            if getattr(e, "filename", None):
                location = f" in {e.filename}{location}"
            msg = getattr(e, "message", None) or str(e)
            return (
                f"Template syntax error{location}: {msg}",
                "Check template syntax - common issues: missing end tags, unclosed braces",
            )
        if isinstance(e, KidaUndefinedError):
            msg = getattr(e, "message", None) or str(e)
            return (
                f"Undefined variable in template: {msg}",
                "Check that the variable is passed to the template context",
            )
        if isinstance(e, KidaTemplateNotFound):
            name = getattr(e, "name", None) or str(e)
            return (
                f"Template not found: {name}",
                "Check templates/ directory and theme template inheritance",
            )
        if isinstance(e, KidaTemplateError):
            msg = getattr(e, "message", None) or str(e)
            return (
                f"Template error: {msg}",
                "Check template syntax and variable names",
            )
    except ImportError:
        pass

    # Handle encoding errors
    if isinstance(e, UnicodeDecodeError):
        return (
            f"File encoding error: {e.reason}",
            "Ensure the file is saved as UTF-8",
        )

    # Handle JSON errors
    try:
        import json

        if isinstance(e, json.JSONDecodeError):
            return (
                f"JSON syntax error at line {e.lineno}, column {e.colno}: {e.msg}",
                "Check for trailing commas, missing quotes, or unescaped characters",
            )
    except ImportError:
        pass

    return None
