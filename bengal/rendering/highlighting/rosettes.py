"""
Rosettes-based syntax highlighting backend.

Rosettes is an external syntax highlighting package designed for Python 3.14t
free-threading with zero global mutable state.

Package: https://pypi.org/project/rosettes/
Source: https://github.com/lbliii/rosettes
Docs: https://lbliii.github.io/rosettes/

Features:
    - 55 languages supported (hand-written state machine lexers)
    - O(n) guaranteed performance, zero ReDoS vulnerability
    - 3.4x faster than Pygments (parallel builds)
    - Lock-free, thread-safe by design
    - Semantic class output (default) or Pygments-compatible
    - Config-based theme selection (RFC-0003)

Unsupported Languages:
    For languages not in the 55 supported, code is rendered as plain
    preformatted text with proper HTML escaping.

Usage:
    >>> from bengal.rendering.highlighting import get_highlighter
    >>> backend = get_highlighter()
    >>> html = backend.highlight("def foo(): pass", "python")

Direct Usage (without Bengal):
    >>> from rosettes import highlight
    >>> html = highlight("def foo(): pass", "python")
"""

from __future__ import annotations

import html
import logging
from typing import TYPE_CHECKING

# Import rosettes (external package)
import rosettes
from rosettes.themes import get_palette

from bengal.rendering.highlighting.theme_resolver import (
    CssClassStyle,
    resolve_css_class_style,
    resolve_syntax_theme,
)

if TYPE_CHECKING:
    from typing import Any

__all__ = ["RosettesBackend"]

_logger = logging.getLogger(__name__)


class RosettesBackend:
    """Rosettes-based syntax highlighting backend.

    Uses the external rosettes package (https://pypi.org/project/rosettes/).

    Thread-safe by design: Rosettes uses immutable state and
    functools.cache for memoization.

    Supports theming via site configuration (RFC-0003):
        - css_class_style: "semantic" (default) or "pygments"
        - theme: auto-inherited from site palette
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the backend with optional site configuration.

        Args:
            config: Site configuration dictionary. If provided, theming
                   will be resolved from theme.syntax_highlighting.
        """
        self._config = config or {}

        # Resolve theming from config
        self._css_class_style: CssClassStyle = resolve_css_class_style(self._config)
        self._theme_name = resolve_syntax_theme(self._config)

        # Load palette (lazy, cached)
        try:
            self._palette = get_palette(self._theme_name)
        except KeyError:
            _logger.warning(
                "Unknown syntax theme %r, falling back to bengal-tiger",
                self._theme_name,
            )
            self._palette = get_palette("bengal-tiger")

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "rosettes"

    @property
    def css_class_style(self) -> CssClassStyle:
        """CSS class output style: 'semantic' or 'pygments'."""
        return self._css_class_style

    @property
    def theme_name(self) -> str:
        """Name of the active syntax theme."""
        return self._theme_name

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

            # Determine container class based on style
            css_class = "rosettes" if self._css_class_style == "semantic" else "highlight"

            return rosettes.highlight(
                code,
                language,
                hl_lines=hl_set,
                show_linenos=show_linenos,
                css_class=css_class,
                css_class_style=self._css_class_style,
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
        container_class = "rosettes" if self._css_class_style == "semantic" else "highlight"
        return f'<div class="{container_class}" data-language="{language}"><pre><code>{escaped}</code></pre></div>'
