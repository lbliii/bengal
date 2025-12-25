"""
Rosettes-based syntax highlighting backend.

This is Bengal's built-in syntax highlighter, designed for Python 3.14t
free-threading with zero global mutable state.

Features:
    - 50 languages supported
    - 3.4x faster than Pygments (parallel builds)
    - Lock-free, thread-safe by design
    - Pygments CSS compatible (drop-in themes)

Unsupported Languages:
    For languages not in the 50 supported, code is rendered as plain
    preformatted text with proper HTML escaping.

Usage:
    >>> from bengal.rendering.highlighting import get_highlighter
    >>> backend = get_highlighter()
    >>> html = backend.highlight("def foo(): pass", "python")
"""

from __future__ import annotations

import html
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
                "Rosettes doesn't support language %r, using plain text",
                language,
            )
            return self._plain_text_fallback(code, language)

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
            _logger.warning("Rosettes highlighting failed: %s, using plain text", e)
            return self._plain_text_fallback(code, language)

    def _plain_text_fallback(self, code: str, language: str) -> str:
        """Render code as plain preformatted text.

        Used for unsupported languages. Properly escapes HTML.

        Args:
            code: Source code to render.
            language: Language identifier (for data attribute).

        Returns:
            HTML string with escaped code.
        """
        escaped = html.escape(code)
        return f'<div class="highlight" data-language="{language}"><pre><code>{escaped}</code></pre></div>'
