"""
Syntax highlighting backend registry and public API.

This module provides the central registry for highlighting backends,
following Bengal's "bring your own X" pattern.

Public API:
    - highlight(): Highlight code using configured backend
    - get_highlighter(): Get a backend instance by name
    - register_backend(): Register a custom backend
    - list_backends(): List available backends

Default Backends:
    - pygments: Default, wide language support (always available)
    - tree-sitter: Fast, semantic highlighting (optional dependency)

Configuration:
    The default backend is "pygments". To use tree-sitter:

    .. code-block:: yaml

        # bengal.yaml
        rendering:
          syntax_highlighting:
            backend: tree-sitter  # or "auto" for smart selection

Usage:
    >>> from bengal.rendering.highlighting import highlight
    >>> html = highlight("print('hello')", "python")

    >>> from bengal.rendering.highlighting import get_highlighter
    >>> backend = get_highlighter("pygments")
    >>> html = backend.highlight("fn main() {}", "rust")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.highlighting.protocol import HighlightBackend

if TYPE_CHECKING:
    pass

__all__ = [
    "HighlightBackend",
    "highlight",
    "get_highlighter",
    "register_backend",
    "list_backends",
]


# Registry pattern matching other Bengal systems
_HIGHLIGHT_BACKENDS: dict[str, type[HighlightBackend]] = {}


def register_backend(name: str, backend_class: type[HighlightBackend]) -> None:
    """
    Register a syntax highlighting backend.

    Args:
        name: Backend identifier (used in config, e.g., "pygments", "tree-sitter")
        backend_class: Class implementing HighlightBackend protocol

    Raises:
        TypeError: If backend_class doesn't implement HighlightBackend

    Example:
        >>> from bengal.rendering.highlighting import register_backend
        >>> from my_package import MyBackend
        >>> register_backend("my-backend", MyBackend)
    """
    # Validate that it implements the protocol (structural typing check)
    if not isinstance(backend_class, type):
        msg = f"backend_class must be a class, got {type(backend_class).__name__}"
        raise TypeError(msg)

    _HIGHLIGHT_BACKENDS[name.lower()] = backend_class


def get_highlighter(name: str | None = None) -> HighlightBackend:
    """
    Get a highlighting backend instance.

    Args:
        name: Backend name. Options:
            - 'pygments' (default): Regex-based, wide language support
            - 'tree-sitter': Fast, semantic highlighting (requires optional dep)
            - 'auto': Use tree-sitter where available, fallback to pygments
            - None: Same as 'pygments'

    Returns:
        Backend instance implementing HighlightBackend

    Raises:
        BengalConfigError: If backend name is unknown
    """
    name = (name or "pygments").lower()

    # Handle 'auto' mode: prefer tree-sitter if available
    if name == "auto":
        name = "tree-sitter" if "tree-sitter" in _HIGHLIGHT_BACKENDS else "pygments"

    if name not in _HIGHLIGHT_BACKENDS:
        from bengal.errors import BengalConfigError, ErrorCode

        available = list(_HIGHLIGHT_BACKENDS.keys())
        raise BengalConfigError(
            f"Unknown highlighting backend: {name!r}. Available: {available}",
            code=ErrorCode.C003,
        )

    return _HIGHLIGHT_BACKENDS[name]()


def list_backends() -> list[str]:
    """
    List all registered highlighting backends.

    Returns:
        Sorted list of backend names
    """
    return sorted(_HIGHLIGHT_BACKENDS.keys())


def highlight(
    code: str,
    language: str,
    hl_lines: list[int] | None = None,
    show_linenos: bool = False,
    backend: str | None = None,
) -> str:
    """
    Highlight code using the configured backend.

    This is the primary public API for syntax highlighting.

    Args:
        code: Source code to highlight
        language: Programming language (e.g., "python", "rust")
        hl_lines: Lines to highlight (1-indexed)
        show_linenos: Include line numbers
        backend: Override default backend (None uses "pygments")

    Returns:
        HTML string with highlighted code

    Example:
        >>> from bengal.rendering.highlighting import highlight
        >>> html = highlight("def hello(): pass", "python")
        >>> html = highlight("fn main() {}", "rust", show_linenos=True)
        >>> html = highlight("print(1)", "python", hl_lines=[1])
    """
    highlighter = get_highlighter(backend)
    return highlighter.highlight(code, language, hl_lines, show_linenos)


# =============================================================================
# Backend Registration
# =============================================================================


def _register_pygments_backend() -> None:
    """Register Pygments backend (always available)."""
    from bengal.rendering.highlighting.pygments import PygmentsBackend

    _HIGHLIGHT_BACKENDS["pygments"] = PygmentsBackend


def _is_free_threaded_python() -> bool:
    """Check if running on Python 3.13+ free-threaded build."""
    import sys
    import sysconfig

    # Check if this is a free-threaded build (Py_GIL_DISABLED=1)
    gil_disabled = sysconfig.get_config_var("Py_GIL_DISABLED")
    if not gil_disabled:
        return False

    # Check if GIL is currently disabled (Python 3.13+)
    # If GIL is already enabled, no harm in importing tree-sitter
    if hasattr(sys, "_is_gil_enabled"):
        return not sys._is_gil_enabled()

    # Free-threaded build but no runtime check available
    return True


def _register_tree_sitter_backend() -> None:
    """Register tree-sitter backend if available and safe.

    Skips registration on Python 3.13+ free-threaded builds because
    tree-sitter's C bindings re-enable the GIL, defeating free-threading.
    """
    # Skip on free-threaded Python to avoid GIL re-enablement
    if _is_free_threaded_python():
        return

    try:
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        _HIGHLIGHT_BACKENDS["tree-sitter"] = TreeSitterBackend
    except ImportError:
        pass  # tree-sitter not installed


# Register built-in backends on module import
_register_pygments_backend()
_register_tree_sitter_backend()
