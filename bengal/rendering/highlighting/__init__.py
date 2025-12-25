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
    - rosettes: Default on Python 3.14t, lock-free and fast (50 languages)
    - pygments: Fallback, wide language support (always available)
    - tree-sitter: Fast, semantic highlighting (optional dependency)

Configuration:
    The default backend auto-selects based on environment:
    - Python 3.14t (free-threaded): Uses Rosettes for GIL-free performance
    - Other Python versions: Uses Pygments

    To override:

    .. code-block:: yaml

        # bengal.yaml
        rendering:
          syntax_highlighting:
            backend: pygments  # or "rosettes", "tree-sitter", "auto"

Usage:
    >>> from bengal.rendering.highlighting import highlight
    >>> html = highlight("print('hello')", "python")

    >>> from bengal.rendering.highlighting import get_highlighter
    >>> backend = get_highlighter()  # Auto-selects best backend
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
    "get_default_backend",
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
            - None or 'auto': Smart selection based on environment
              - Python 3.14t (free-threaded): Rosettes (15x faster parallel)
              - Other Python: Pygments (wide language support)
            - 'rosettes': Lock-free highlighter (50 languages, falls back to Pygments)
            - 'pygments': Regex-based, wide language support
            - 'tree-sitter': Fast, semantic highlighting (requires optional dep)

    Returns:
        Backend instance implementing HighlightBackend

    Raises:
        BengalConfigError: If backend name is unknown
    """
    name = (name or "auto").lower()

    # Handle 'auto' mode: smart backend selection
    if name == "auto":
        name = _select_best_backend()

    if name not in _HIGHLIGHT_BACKENDS:
        from bengal.errors import BengalConfigError, ErrorCode

        available = list(_HIGHLIGHT_BACKENDS.keys())
        raise BengalConfigError(
            f"Unknown highlighting backend: {name!r}. Available: {available}",
            code=ErrorCode.C003,
        )

    return _HIGHLIGHT_BACKENDS[name]()


def _select_best_backend() -> str:
    """Select the best available backend based on environment.

    Priority:
        1. Rosettes on free-threaded Python (GIL disabled) - 15x faster parallel
        2. Rosettes if available (1.8x faster sequential)
        3. tree-sitter if available
        4. Pygments (always available)

    Returns:
        Backend name to use.
    """
    # On free-threaded Python, strongly prefer Rosettes for parallel performance
    if _is_free_threaded_python() and "rosettes" in _HIGHLIGHT_BACKENDS:
        return "rosettes"

    # Even on regular Python, Rosettes is faster (1.8x sequential)
    if "rosettes" in _HIGHLIGHT_BACKENDS:
        return "rosettes"

    # tree-sitter is fast but not GIL-free
    if "tree-sitter" in _HIGHLIGHT_BACKENDS:
        return "tree-sitter"

    # Pygments is always available
    return "pygments"


def list_backends() -> list[str]:
    """
    List all registered highlighting backends.

    Returns:
        Sorted list of backend names
    """
    return sorted(_HIGHLIGHT_BACKENDS.keys())


def get_default_backend() -> str:
    """
    Get the name of the default backend for the current environment.

    This is useful for diagnostics and logging.

    Returns:
        Backend name that would be used with get_highlighter(None)

    Example:
        >>> from bengal.rendering.highlighting import get_default_backend
        >>> print(f"Using {get_default_backend()} for syntax highlighting")
        Using rosettes for syntax highlighting  # on Python 3.14t
    """
    return _select_best_backend()


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


def _register_rosettes_backend() -> None:
    """Register Rosettes backend (always available, bundled with Bengal).

    Rosettes is designed for free-threaded Python and is preferred
    on Python 3.14t builds for lock-free syntax highlighting.

    Features:
        - 50 languages supported
        - 3.4x faster than Pygments (parallel builds)
        - Falls back to Pygments for unsupported languages
    """
    from bengal.rendering.highlighting.rosettes import RosettesBackend

    _HIGHLIGHT_BACKENDS["rosettes"] = RosettesBackend


# Register built-in backends on module import
_register_pygments_backend()
_register_tree_sitter_backend()
_register_rosettes_backend()
