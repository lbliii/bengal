"""Validation helpers for CLI commands."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import click

F = TypeVar("F", bound=Callable[..., Any])


def validate_mutually_exclusive(
    *flag_pairs: tuple[str, str],
    error_message: str | None = None,
) -> Callable[[F], F]:
    """
    Decorator to validate mutually exclusive flags.

    Args:
        flag_pairs: Pairs of flag names that cannot be used together
        error_message: Custom error message (default: "{flag1} and {flag2} cannot be used together")

    Example:
        @click.command()
        @click.option("--quiet", is_flag=True)
        @click.option("--verbose", is_flag=True)
        @validate_mutually_exclusive(("quiet", "verbose"))
        def my_command(quiet: bool, verbose: bool):
            # ...
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for flag1, flag2 in flag_pairs:
                if kwargs.get(flag1) and kwargs.get(flag2):
                    if error_message:
                        msg = error_message.format(flag1=flag1, flag2=flag2)
                    else:
                        msg = f"--{flag1} and --{flag2} cannot be used together"
                    raise click.UsageError(msg)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def validate_flag_conflicts(
    conflicts: dict[str, list[str]],
    error_message: str | None = None,
) -> Callable[[F], F]:
    """
    Decorator to validate flag conflicts (one flag conflicts with multiple others).

    Args:
        conflicts: Dict mapping flag name to list of conflicting flag names
        error_message: Custom error message template (default: "{flag} cannot be used with {others}")

    Example:
        @click.command()
        @click.option("--fast", is_flag=True)
        @click.option("--dev", is_flag=True)
        @click.option("--theme-dev", is_flag=True)
        @validate_flag_conflicts({"fast": ["dev", "theme_dev"]})
        def my_command(fast: bool, dev: bool, theme_dev: bool):
            # ...
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for flag, conflicting_flags in conflicts.items():
                if kwargs.get(flag):
                    active_conflicts = [f"--{cf}" for cf in conflicting_flags if kwargs.get(cf)]
                    if active_conflicts:
                        if error_message:
                            msg = error_message.format(
                                flag=flag, others=", ".join(active_conflicts)
                            )
                        else:
                            others_str = " or ".join(active_conflicts)
                            msg = f"--{flag} cannot be used with {others_str}"
                        raise click.UsageError(msg)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
