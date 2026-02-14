"""Render configuration using ContextVar pattern.

Provides thread-safe configuration for HtmlRenderer instances using ContextVar.
Enables 50% slot reduction (14→7) and ~1.3x instantiation speedup.

Thread Safety:
    ContextVars are thread-local by design (PEP 567).
    Each thread has independent storage - no locks needed.

Usage:
    # Set config for current thread
    with render_config_context(RenderConfig(highlight=True)) as cfg:
        renderer = HtmlRenderer(source)
        # renderer._highlight reads from ContextVar

    # Or manual set/reset with token
    token = set_render_config(RenderConfig(highlight=True))
    try:
        renderer = HtmlRenderer(source)
    finally:
        reset_render_config(token)

RFC: rfc-contextvar-config-implementation.md

"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextvars import Token
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from bengal.parsing.backends.patitas.utils.contextvar import ContextVarManager

if TYPE_CHECKING:
    from bengal.parsing.backends.patitas.directives.registry import DirectiveRegistry
    from bengal.parsing.backends.patitas.roles.registry import RoleRegistry

__all__ = [
    "RenderConfig",
    "get_render_config",
    "render_config_context",
    "reset_render_config",
    "set_render_config",
]


def _check_rosettes_available() -> bool:
    """Check if rosettes syntax highlighter is available (computed once)."""
    try:
        import rosettes

        return True
    except ImportError:
        return False


# Module-level singleton for rosettes availability (computed once at import)
_ROSETTES_AVAILABLE: bool = _check_rosettes_available()


@dataclass(frozen=True, slots=True)
class RenderConfig:
    """Immutable render configuration.

    Set once per render context, read by all renderers.
    Frozen dataclass ensures thread-safety.

    Note: rosettes_available uses a factory default to capture
    module-level import check result.

    Attributes:
        highlight: Enable syntax highlighting for code blocks
        highlight_style: Highlighting style ("semantic" or "pygments")
        directive_registry: Registry for custom directive rendering
        role_registry: Registry for custom role rendering
        text_transformer: Optional callback to transform plain text nodes
        slugify: Optional custom slugify function for heading IDs
        rosettes_available: Whether rosettes highlighter is available (auto-detected)
    """

    highlight: bool = False
    highlight_style: Literal["semantic", "pygments"] = "semantic"
    directive_registry: DirectiveRegistry | None = None
    role_registry: RoleRegistry | None = None
    text_transformer: Callable[[str], str] | None = None
    slugify: Callable[[str], str] | None = None
    rosettes_available: bool = field(default_factory=lambda: _ROSETTES_AVAILABLE)


# Module-level default (singleton)
_DEFAULT_RENDER_CONFIG: RenderConfig = RenderConfig()

# Thread-local configuration using ContextVarManager
_manager: ContextVarManager[RenderConfig] = ContextVarManager(
    "render_config", default=_DEFAULT_RENDER_CONFIG
)


def get_render_config() -> RenderConfig:
    """Get current render configuration (thread-local).

    Returns:
        The RenderConfig for the current thread/context.
    """
    # Manager returns Optional, but we have a default so it's always set
    return _manager.get() or _DEFAULT_RENDER_CONFIG


def set_render_config(config: RenderConfig) -> Token[RenderConfig | None]:
    """Set render configuration for current context.

    Returns a token that can be used to restore the previous value.
    Always use with try/finally or render_config_context() for proper cleanup.

    Args:
        config: The RenderConfig to set for the current context.

    Returns:
        Token that can be passed to reset_render_config() to restore previous value.
    """
    return _manager.set(config)


def reset_render_config(token: Token[RenderConfig | None] | None = None) -> None:
    """Reset render configuration.

    If token is provided, restores to the previous value (proper nesting).
    Otherwise, resets to the default configuration.

    Args:
        token: Optional token from set_render_config() for proper nesting support.
    """
    _manager.reset(token)


def render_config_context(config: RenderConfig) -> Iterator[RenderConfig]:
    """Context manager for scoped render configuration.

    Properly restores previous config on exit (supports nesting).

    Usage:
        with render_config_context(RenderConfig(highlight=True)) as cfg:
            renderer = HtmlRenderer(source)
            # cfg.highlight is True

    Args:
        config: The RenderConfig to use within the context.

    Yields:
        The config that was set (same as input).
    """
    return _manager.context(config)
