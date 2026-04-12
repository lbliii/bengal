"""
Beautiful error display for CLI.

Provides formatted display of BengalError instances with error codes,
suggestions, file locations, and documentation links.

Functions:
    display_bengal_error: Display a BengalError with beautiful formatting
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
