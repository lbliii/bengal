"""
Validation helpers for CLI commands.

Provides decorators for validating CLI flag combinations, including
mutually exclusive flags and multi-flag conflicts.

Functions:
    validate_mutually_exclusive: Ensure flag pairs aren't used together
    validate_flag_conflicts: Validate one-to-many flag conflicts

Example:
    @click.command()
    @click.option("--quiet", is_flag=True)
    @click.option("--verbose", is_flag=True)
    @validate_mutually_exclusive(("quiet", "verbose"))
    def my_command(quiet, verbose):
        pass
"""

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
            # Map internal flag names to user-facing flag names
            flag_name_map = {
                "use_dev": "dev",
                "use_theme_dev": "theme-dev",
            }

            for flag, conflicting_flags in conflicts.items():
                if kwargs.get(flag):
                    # Get user-facing flag name
                    user_flag = flag_name_map.get(flag, flag)

                    # Check which conflicting flags are actually active
                    active_conflicts = []
                    for cf in conflicting_flags:
                        if kwargs.get(cf):
                            active_conflicts.append(cf)

                    if active_conflicts:
                        # Map all conflicting flags to user-facing names (list all possible conflicts)
                        user_conflicting_flags = [
                            flag_name_map.get(cf, cf) for cf in conflicting_flags
                        ]

                        if error_message:
                            # Format with all possible conflicts
                            if len(user_conflicting_flags) == 1:
                                all_conflicts_str = f"--{user_conflicting_flags[0]}"
                            elif len(user_conflicting_flags) == 2:
                                all_conflicts_str = f"--{user_conflicting_flags[0]} or --{user_conflicting_flags[1]}"
                            else:
                                all_conflicts_str = (
                                    ", ".join(f"--{cf}" for cf in user_conflicting_flags[:-1])
                                    + f", or --{user_conflicting_flags[-1]}"
                                )
                            msg = error_message.format(flag=user_flag, others=all_conflicts_str)
                        else:
                            # Build error message listing all possible conflicts
                            if len(user_conflicting_flags) == 1:
                                others_str = f"--{user_conflicting_flags[0]}"
                            elif len(user_conflicting_flags) == 2:
                                others_str = f"--{user_conflicting_flags[0]} or --{user_conflicting_flags[1]}"
                            else:
                                others_str = (
                                    ", ".join(f"--{cf}" for cf in user_conflicting_flags[:-1])
                                    + f", or --{user_conflicting_flags[-1]}"
                                )
                            msg = f"--{user_flag} cannot be used with {others_str}"
                        raise click.UsageError(msg)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
