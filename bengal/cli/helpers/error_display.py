"""
Beautiful error display for CLI.

Provides formatted display of BengalError instances with error codes,
suggestions, file locations, and documentation links.

Functions:
    display_bengal_error: Display a BengalError with beautiful formatting
    beautify_common_exception: Convert common exceptions to user-friendly messages

Example:
    >>> from bengal.errors import BengalRenderingError, ErrorCode
    >>> from bengal.cli.helpers.error_display import display_bengal_error
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
        #   Docs: https://bengal.dev/docs/errors/c001/
    """
    icons = cli.icons

    # Header with code and category
    if error.code:
        code_str = f"[{error.code.name}]"
        category = error.code.category.replace("_", " ").title()

        if cli.use_rich:
            cli.console.print()
            cli.console.print(
                f"  [bold red]{icons.error}[/bold red] [bold]{code_str}[/bold] "
                f"[red]{category} Error[/red]"
            )
            cli.console.print()
        else:
            cli.console.print()
            cli.console.print(f"  {icons.error} {code_str} {category} Error")
            cli.console.print()
    else:
        if cli.use_rich:
            cli.console.print()
            cli.console.print(f"  [bold red]{icons.error} Error[/bold red]")
            cli.console.print()
        else:
            cli.console.print()
            cli.console.print(f"  {icons.error} Error")
            cli.console.print()

    # Main message
    if cli.use_rich:
        cli.console.print(f"  {error.message}")
        cli.console.print()
    else:
        cli.console.print(f"  {error.message}")
        cli.console.print()

    # File location (clickable in most terminals)
    if error.file_path:
        location = f"  File: {error.file_path}"
        if error.line_number:
            location += f":{error.line_number}"
        if cli.use_rich:
            cli.console.print(f"[dim]{location}[/dim]")
            cli.console.print()
        else:
            cli.console.print(location)
            cli.console.print()

    # Related files (for debugging)
    if error.related_files:
        if cli.use_rich:
            cli.console.print("  [dim]Related:[/dim]")
            for rf in error.related_files[:3]:
                cli.console.print(f"    [dim]• {rf}[/dim]")
            if len(error.related_files) > 3:
                cli.console.print(f"    [dim]... and {len(error.related_files) - 3} more[/dim]")
            cli.console.print()
        else:
            cli.console.print("  Related:")
            for rf in error.related_files[:3]:
                cli.console.print(f"    • {rf}")
            if len(error.related_files) > 3:
                cli.console.print(f"    ... and {len(error.related_files) - 3} more")
            cli.console.print()

    # Actionable suggestion
    if error.suggestion:
        if cli.use_rich:
            cli.console.print(f"  [bold cyan]Tip:[/bold cyan] {error.suggestion}")
            cli.console.print()
        else:
            cli.console.print(f"  Tip: {error.suggestion}")
            cli.console.print()

    # Documentation link
    if error.code:
        docs_url = f"https://bengal.dev{error.code.docs_url}"
        if cli.use_rich:
            cli.console.print(f"  [dim]Docs: {docs_url}[/dim]")
            cli.console.print()
        else:
            cli.console.print(f"  Docs: {docs_url}")
            cli.console.print()


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
        filename = getattr(e, "filename", str(e))
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
            if hasattr(e, "problem_mark"):
                mark = e.problem_mark
                return (
                    f"YAML syntax error at line {mark.line + 1}, column {mark.column + 1}",
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

    # Handle Jinja2 template errors
    try:
        import jinja2

        if isinstance(e, jinja2.TemplateSyntaxError):
            location = ""
            if e.lineno:
                location = f" at line {e.lineno}"
            if e.filename:
                location = f" in {e.filename}{location}"
            return (
                f"Template syntax error{location}: {e.message}",
                "Check template syntax - common issues: missing end tags, unclosed braces",
            )
        if isinstance(e, jinja2.UndefinedError):
            return (
                f"Undefined variable in template: {e.message}",
                "Check that the variable is passed to the template context",
            )
        if isinstance(e, jinja2.TemplateNotFound):
            return (
                f"Template not found: {e.name}",
                "Check templates/ directory and theme template inheritance",
            )
        if isinstance(e, jinja2.TemplateError):
            return (
                f"Template error: {e.message}",
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
