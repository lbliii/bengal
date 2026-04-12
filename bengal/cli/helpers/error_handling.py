"""
Unified error handling for CLI commands.

Provides decorators and context managers for consistent error handling
across all Bengal CLI commands, including formatted error output,
traceback display control, and proper abort handling.

.. note::
    Error handling logic has been consolidated into :mod:`bengal.cli.utils.errors`.
    This module now delegates to those utilities while maintaining the same API.

Functions:
    handle_cli_errors: Decorator for command-level error handling
    cli_error_context: Context manager for operation-level error handling

Example:
    @handle_cli_errors(show_art=True)
    def my_command():
        with cli_error_context("loading configuration"):
            config = load_config()

"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Generator
from functools import wraps
from typing import Any


def handle_cli_errors[F: Callable[..., Any]](
    show_art: bool = False,
    preserve_chain: bool = True,
    show_traceback: bool | None = None,
) -> Callable[[F], F]:
    """
    Decorator for unified CLI error handling.

    Args:
        show_art: Whether to show ASCII art in error messages
        preserve_chain: Whether to preserve exception chain (raise ... from e)
        show_traceback: Whether to show traceback (None = auto-detect from config)

    Example:
        @handle_cli_errors()
        def my_command():
            # ... command logic ...
            pass

    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except SystemExit, KeyboardInterrupt:
                raise
            except Exception as e:
                # Delegate to consolidated error handling
                from bengal.cli.utils.errors import handle_exception
                from bengal.cli.utils.output import get_cli_output

                cli = get_cli_output()
                handle_exception(
                    e,
                    cli,
                    operation=None,
                    show_art=show_art,
                    show_traceback=show_traceback,
                )

                if preserve_chain:
                    raise SystemExit(1) from e
                raise SystemExit(1) from None

        return wrapper  # type: ignore[return-value]

    return decorator


@contextlib.contextmanager
def cli_error_context(
    operation: str,
    show_art: bool = False,
    show_traceback: bool | None = None,
) -> Generator[None]:
    """
    Context manager for error handling within command functions.

    Args:
        operation: Description of the operation being performed
        show_art: Whether to show ASCII art in error messages
        show_traceback: Whether to show traceback (None = auto-detect)

    Example:
        def my_command():
            with cli_error_context("loading site"):
                site = Site.from_config(...)

    """
    try:
        yield
    except SystemExit, KeyboardInterrupt:
        raise
    except Exception as e:
        # Delegate to consolidated error handling
        from bengal.cli.utils.errors import handle_exception
        from bengal.cli.utils.output import get_cli_output

        cli = get_cli_output()
        handle_exception(
            e,
            cli,
            operation=operation,
            show_art=show_art,
            show_traceback=show_traceback,
        )

        raise SystemExit(1) from e
