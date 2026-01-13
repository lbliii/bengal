"""
Syntax highlighting backend registry and public API.

This module provides the central registry for highlighting backends,
following Bengal's "bring your own X" pattern.

Public API:
- highlight(): Highlight code using configured backend
- get_highlighter(): Get a backend instance by name
- register_backend(): Register a custom backend
- list_backends(): List available backends

Default Backend:
- rosettes: External package, lock-free, 55 languages, 3.4x faster than Pygments
  Package: https://pypi.org/project/rosettes/
  Source: https://github.com/lbliii/rosettes

Optional Backends:
- tree-sitter: Fast, semantic highlighting (optional dependency)

Usage:
    >>> from bengal.rendering.highlighting import highlight
    >>> html = highlight("print('hello')", "python")

    >>> from bengal.rendering.highlighting import get_highlighter
    >>> backend = get_highlighter()
    >>> html = backend.highlight("fn main() {}", "rust")

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.highlighting.protocol import HighlightBackend
from bengal.rendering.highlighting.theme_resolver import (
    PALETTE_INHERITANCE,
    resolve_css_class_style,
    resolve_syntax_theme,
)

if TYPE_CHECKING:
    pass

__all__ = [
    "HighlightBackend",
    "highlight",
    "highlight_many",
    "get_highlighter",
    "get_default_backend",
    "register_backend",
    "list_backends",
    # Theme resolution (RFC-0003)
    "resolve_syntax_theme",
    "resolve_css_class_style",
    "PALETTE_INHERITANCE",
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
            - None or 'auto': Uses Rosettes (default)
            - 'rosettes': Built-in, lock-free, 50 languages
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
    """Select the best available backend.
    
    Priority:
        1. Rosettes (default, always available)
        2. tree-sitter if available
    
    Returns:
        Backend name to use.
        
    """
    # Rosettes is the default (bundled with Bengal)
    if "rosettes" in _HIGHLIGHT_BACKENDS:
        return "rosettes"

    # tree-sitter as fallback if available
    if "tree-sitter" in _HIGHLIGHT_BACKENDS:
        return "tree-sitter"

    # Should never reach here - rosettes is always available
    msg = "No highlighting backend available"
    raise RuntimeError(msg)


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
        backend: Override default backend (None uses "rosettes" via "auto")
    
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


def highlight_many(
    items: list[tuple[str, str]],
    backend: str | None = None,
    css_class_style: str = "semantic",
) -> list[str]:
    """
    Highlight multiple code blocks in parallel.
    
    On Python 3.14t free-threaded, this provides significant speedups
    (1.5-2x) for pages with many code blocks.
    
    Args:
        items: List of (code, language) tuples
        backend: Override default backend (None uses rosettes)
        css_class_style: Class naming style (HTML only):
            - "semantic" (default): Uses readable classes like .syntax-function
            - "pygments": Uses Pygments-compatible classes like .nf
    
    Returns:
        List of highlighted HTML strings in the same order
    
    Example:
            >>> from bengal.rendering.highlighting import highlight_many
            >>> blocks = [
            ...     ("def hello(): pass", "python"),
            ...     ("fn main() {}", "rust"),
            ... ]
            >>> results = highlight_many(blocks)
            >>> len(results)
        2
        
    """
    # Rosettes has native parallel support
    backend_name = (backend or "auto").lower()
    if backend_name == "auto":
        backend_name = _select_best_backend()

    if backend_name == "rosettes":
        # Use Rosettes' native parallel implementation
        import rosettes

        return rosettes.highlight_many(items, css_class_style=css_class_style)

    # Fallback: sequential for other backends
    highlighter = get_highlighter(backend)
    return [highlighter.highlight(code, lang) for code, lang in items]


# =============================================================================
# Backend Registration
# =============================================================================


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
    """Register Rosettes backend (external dependency, always available).
    
    Package: https://pypi.org/project/rosettes/
    
    Features:
        - 55 languages supported
        - 3.4x faster than Pygments (parallel builds)
        - Lock-free, designed for free-threaded Python
        
    """
    from bengal.rendering.highlighting.rosettes import RosettesBackend

    _HIGHLIGHT_BACKENDS["rosettes"] = RosettesBackend


# Register built-in backends on module import
_register_rosettes_backend()
_register_tree_sitter_backend()
