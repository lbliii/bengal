"""
Rosettes-based syntax highlighting backend.

This backend uses Rosettes, Bengal's built-in lock-free syntax highlighter
designed for Python 3.14t free-threading.

Advantages:
    - Zero global mutable state (GIL-free)
    - Immutable configuration (thread-safe by design)
    - Lazy loading (fast cold start)
    - Pygments CSS compatible (drop-in themes)
    - 50 languages supported, 3.4x faster than Pygments (parallel)

Fallback Strategy:
    For unsupported languages, this backend falls back to Pygments
    to ensure broad language coverage while maintaining thread-safety
    for common languages.

Usage:
    Configure in bengal.yaml:

    .. code-block:: yaml

        rendering:
          syntax_highlighting:
            backend: rosettes

    Or use directly:

    >>> from bengal.rendering.highlighting import get_highlighter
    >>> backend = get_highlighter("rosettes")
    >>> html = backend.highlight("def foo(): pass", "python")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# Import bundled rosettes
from bengal.rendering import rosettes

if TYPE_CHECKING:
    pass

__all__ = ["RosettesBackend"]

_logger = logging.getLogger(__name__)


class RosettesBackend:
    """Rosettes-based syntax highlighting backend.

    Thread-safe by design: Rosettes uses immutable state and
    functools.cache for memoization.

    Falls back to Pygments for unsupported languages.
    """

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "rosettes"

    def supports_language(self, language: str) -> bool:
        """Check if Rosettes supports the given language.

        Args:
            language: Language name or alias.

        Returns:
            True if Rosettes has a lexer for this language.
        """
        try:
            return rosettes.supports_language(language)
        except Exception:
            return False

    def highlight(
        self,
        code: str,
        language: str,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        """Render code with syntax highlighting.

        Uses Rosettes for supported languages, falls back to Pygments otherwise.

        Args:
            code: Source code to highlight.
            language: Programming language identifier.
            hl_lines: Line numbers to highlight (1-indexed).
            show_linenos: Whether to include line numbers.

        Returns:
            HTML string with highlighted code.
        """
        # Check if Rosettes supports this language
        if not rosettes.supports_language(language):
            _logger.debug(
                "Rosettes doesn't support language %r, using Pygments fallback",
                language,
            )
            return self._pygments_fallback(code, language, hl_lines, show_linenos)

        try:
            # Convert hl_lines to set for Rosettes API
            hl_set = set(hl_lines) if hl_lines else None

            return rosettes.highlight(
                code,
                language,
                hl_lines=hl_set,
                show_linenos=show_linenos,
            )
        except Exception as e:
            _logger.warning("Rosettes highlighting failed: %s, using fallback", e)
            return self._pygments_fallback(code, language, hl_lines, show_linenos)

    def _pygments_fallback(
        self,
        code: str,
        language: str,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        """Fall back to Pygments for unsupported languages.

        Args:
            code: Source code to highlight.
            language: Programming language identifier.
            hl_lines: Line numbers to highlight.
            show_linenos: Whether to include line numbers.

        Returns:
            HTML string with highlighted code.
        """
        from bengal.rendering.highlighting.pygments import PygmentsBackend

        return PygmentsBackend().highlight(code, language, hl_lines, show_linenos)
