"""Parse configuration using ContextVar pattern.

Provides thread-safe configuration for Parser instances using ContextVar.
Enables 50% slot reduction (18→9) and ~2x instantiation speedup.

Thread Safety:
    ContextVars are thread-local by design (PEP 567).
    Each thread has independent storage - no locks needed.

Usage:
    # Set config for current thread
    with parse_config_context(ParseConfig(tables_enabled=True)) as cfg:
        parser = Parser(source)
        # parser._tables_enabled reads from ContextVar

    # Or manual set/reset with token
    token = set_parse_config(ParseConfig(math_enabled=True))
    try:
        parser = Parser(source)
    finally:
        reset_parse_config(token)

RFC: rfc-contextvar-config-implementation.md

"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextvars import Token
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.parsing.backends.patitas.utils.contextvar import ContextVarManager

if TYPE_CHECKING:
    from bengal.parsing.backends.patitas.directives.registry import DirectiveRegistry

__all__ = [
    "ParseConfig",
    "get_parse_config",
    "parse_config_context",
    "reset_parse_config",
    "set_parse_config",
]


@dataclass(frozen=True, slots=True)
class ParseConfig:
    """Immutable parse configuration.

    Set once per Markdown instance, read by all parsers in the context.
    Frozen dataclass ensures thread-safety (immutable after creation).

    Attributes:
        tables_enabled: Enable GFM table parsing
        strikethrough_enabled: Enable ~~strikethrough~~ syntax
        task_lists_enabled: Enable [x] task list items
        footnotes_enabled: Enable [^footnote] syntax
        math_enabled: Enable $math$ and $$math$$ syntax
        autolinks_enabled: Enable URL/email autolink detection
        directive_registry: Registry for custom directive handlers
        strict_contracts: Raise errors on contract violations
        text_transformer: Optional callback to transform plain text lines
    """

    tables_enabled: bool = False
    strikethrough_enabled: bool = False
    task_lists_enabled: bool = False
    footnotes_enabled: bool = False
    math_enabled: bool = False
    autolinks_enabled: bool = False
    directive_registry: DirectiveRegistry | None = None
    strict_contracts: bool = False
    text_transformer: Callable[[str], str] | None = None


# Module-level default (singleton, never recreated)
_DEFAULT_PARSE_CONFIG: ParseConfig = ParseConfig()

# Thread-local configuration using ContextVarManager
_manager: ContextVarManager[ParseConfig] = ContextVarManager(
    "parse_config", default=_DEFAULT_PARSE_CONFIG
)


def get_parse_config() -> ParseConfig:
    """Get current parse configuration (thread-local).

    Returns:
        The ParseConfig for the current thread/context.
    """
    # Manager returns Optional, but we have a default so it's always set
    return _manager.get() or _DEFAULT_PARSE_CONFIG


def set_parse_config(config: ParseConfig) -> Token[ParseConfig | None]:
    """Set parse configuration for current context.

    Returns a token that can be used to restore the previous value.
    Always use with try/finally or parse_config_context() for proper cleanup.

    Args:
        config: The ParseConfig to set for the current context.

    Returns:
        Token that can be passed to reset_parse_config() to restore previous value.
    """
    return _manager.set(config)


def reset_parse_config(token: Token[ParseConfig | None] | None = None) -> None:
    """Reset parse configuration.

    If token is provided, restores to the previous value (proper nesting).
    Otherwise, resets to the default configuration.

    Args:
        token: Optional token from set_parse_config() for proper nesting support.
    """
    _manager.reset(token)


def parse_config_context(config: ParseConfig) -> Iterator[ParseConfig]:
    """Context manager for scoped parse configuration.

    Properly restores previous config on exit (supports nesting).

    Usage:
        with parse_config_context(ParseConfig(tables_enabled=True)) as cfg:
            parser = Parser(source)
            # cfg.tables_enabled is True

    Args:
        config: The ParseConfig to use within the context.

    Yields:
        The config that was set (same as input).
    """
    return _manager.context(config)
