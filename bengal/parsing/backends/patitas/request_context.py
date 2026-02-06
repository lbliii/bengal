"""Request-scoped context using ContextVar pattern.

Provides per-request state for parsing and rendering without parameter drilling.
Unifies source file, error handler, page context, and link resolution.

Thread Safety:
    ContextVars are thread-local by design (PEP 567).
    Each thread has independent storage - no locks needed.
    Also async-safe (each task gets its own context).

Usage:
    with request_context(source_file=path, page=page, site=site):
        html = render(page.content)
        # All nested code can access context via get_request_context()

RFC: rfc-contextvar-downstream-patterns.md

"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import Token
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.parsing.backends.patitas.utils.contextvar import ContextVarManager

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

__all__ = [
    "RequestContext",
    "RequestContextError",
    "get_request_context",
    "request_context",
    "reset_request_context",
    "set_request_context",
    "try_get_request_context",
]


class RequestContextError(RuntimeError):
    """Raised when request context is required but not set.

    This is a fail-fast error to catch missing context setup early.
    Use try_get_request_context() for optional access.
    """


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Per-request context for parsing and rendering.

    Provides access to build-wide and page-specific state
    without parameter drilling.

    Thread Safety:
        ContextVar provides automatic thread/async isolation.
        Each thread/task gets its own context stack.

    Attributes:
        source_file: Path to source file being processed
        source_content: Raw source content
        page: Page object being rendered (optional)
        site: Site instance for configuration (optional)
        error_handler: Callback for error reporting
        strict_mode: If True, raise exceptions on errors
        link_resolver: Callback to resolve internal links
        trace_enabled: If True, enable debug tracing
    """

    # Source information
    source_file: Path | None = None
    source_content: str = ""

    # Page context (for rendering)
    page: Page | None = None
    site: Site | None = None

    # Error handling
    error_handler: Callable[[Exception, str], None] | None = None
    strict_mode: bool = False

    # Link resolution
    link_resolver: Callable[[str], str | None] | None = None

    # Debug/profiling
    trace_enabled: bool = False

    def resolve_link(self, target: str) -> str | None:
        """Resolve a link target to URL.

        Args:
            target: Link target to resolve (e.g., "docs/getting-started.md")

        Returns:
            Resolved URL or None if resolver not set or target not found
        """
        if self.link_resolver:
            return self.link_resolver(target)
        return None

    def report_error(self, error: Exception, context: str) -> None:
        """Report an error with context.

        Behavior depends on configuration:
        - If error_handler set: calls handler
        - If strict_mode: re-raises exception
        - Otherwise: silently ignores

        Args:
            error: The exception that occurred
            context: String describing where the error occurred
        """
        if self.error_handler:
            self.error_handler(error, context)
        elif self.strict_mode:
            raise error


# Thread-local request context using ContextVarManager (default None for fail-fast)
_manager: ContextVarManager[RequestContext] = ContextVarManager("request_context")


def get_request_context() -> RequestContext:
    """Get current request context.

    Use this when context is required and absence is a programming error.

    Returns:
        The current RequestContext

    Raises:
        RequestContextError: If no context is set (fail-fast)
    """
    return _manager.get_or_raise(
        RequestContextError,
        "No request context set. Use request_context() context manager "
        "or set_request_context() before parsing/rendering.",
    )


def try_get_request_context() -> RequestContext | None:
    """Get current request context, or None if not set.

    Use this for optional context access where fallback behavior is acceptable.

    Returns:
        The current RequestContext or None if not within a context
    """
    return _manager.get()


def set_request_context(ctx: RequestContext) -> Token[RequestContext | None]:
    """Set request context for current context.

    Returns a token that can be used to restore the previous value.
    Always use with try/finally or request_context() for proper cleanup.

    Args:
        ctx: The RequestContext to set

    Returns:
        Token that can be passed to reset_request_context()
    """
    return _manager.set(ctx)


def reset_request_context(token: Token[RequestContext | None] | None = None) -> None:
    """Reset request context.

    If token is provided, restores to the previous value (proper nesting).
    Otherwise, resets to None.

    Args:
        token: Optional token from set_request_context()
    """
    _manager.reset(token)


@contextmanager
def request_context(
    source_file: Path | None = None,
    source_content: str = "",
    page: Page | None = None,
    site: Site | None = None,
    error_handler: Callable[[Exception, str], None] | None = None,
    strict_mode: bool = False,
    link_resolver: Callable[[str], str | None] | None = None,
    trace_enabled: bool = False,
) -> Iterator[RequestContext]:
    """Context manager for request-scoped state.

    Creates a RequestContext and sets it as current for the duration.
    Properly restores previous context on exit (supports nesting).

    Args:
        source_file: Path to source file being processed
        source_content: Raw source content
        page: Page object being rendered
        site: Site instance for configuration
        error_handler: Callback for error reporting
        strict_mode: If True, raise exceptions on errors
        link_resolver: Callback to resolve internal links
        trace_enabled: If True, enable debug tracing

    Yields:
        The created RequestContext

    Usage:
        with request_context(source_file=path, page=page, site=site):
            html = render(page.content)
            # All nested code can access context via get_request_context()

    Nesting:
        Context managers can be nested. Inner context shadows outer.
        Token-based reset restores previous context on exit.
    """
    ctx = RequestContext(
        source_file=source_file,
        source_content=source_content,
        page=page,
        site=site,
        error_handler=error_handler,
        strict_mode=strict_mode,
        link_resolver=link_resolver,
        trace_enabled=trace_enabled,
    )
    with _manager.context(ctx):
        yield ctx
