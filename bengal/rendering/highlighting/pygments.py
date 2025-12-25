"""
Pygments-based syntax highlighting backend.

This is the default highlighting backend for Bengal, providing wide
language support via Pygments' extensive lexer library.

Features:
    - 500+ languages supported
    - Caching via bengal.rendering.pygments_cache
    - Line highlighting
    - Line numbers
    - Compatible with all Pygments CSS themes

Performance:
    - Cached lexer lookup: ~0.001ms
    - Uncached lookup: ~30ms (plugin discovery)
    - Cache hit rate: >95% after first few pages

See Also:
    - bengal.rendering.pygments_cache: Lexer caching implementation
    - bengal.rendering.highlighting.protocol: Backend protocol
"""

from __future__ import annotations

from bengal.rendering.highlighting.protocol import HighlightBackend
from bengal.rendering.pygments_cache import get_lexer_cached
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class PygmentsBackend(HighlightBackend):
    """
    Pygments-based syntax highlighting backend.

    This is the default backend, providing wide language support
    via Pygments' extensive lexer library (~500 languages).

    The implementation uses cached lexer lookup to avoid the
    expensive plugin discovery that Pygments performs on each
    lexer request.
    """

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "pygments"

    def supports_language(self, language: str) -> bool:
        """
        Check if Pygments supports the given language.

        Pygments supports nearly all languages via fallback to text lexer,
        so this always returns True. The actual lexer resolution happens
        in highlight().
        """
        # Pygments has extensive language support and falls back to text
        return True

    def highlight(
        self,
        code: str,
        language: str,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        """
        Highlight code using Pygments.

        Args:
            code: Source code to highlight
            language: Programming language identifier
            hl_lines: Line numbers to highlight (1-indexed)
            show_linenos: Whether to include line numbers

        Returns:
            HTML string with highlighted code
        """
        from pygments import highlight
        from pygments.formatters.html import HtmlFormatter

        try:
            # Get cached lexer (fast path for known languages)
            lexer = get_lexer_cached(language=language)

            # Format with Pygments using 'highlight' CSS class
            formatter = HtmlFormatter(
                cssclass="highlight",
                wrapcode=True,
                noclasses=False,  # Use CSS classes instead of inline styles
                linenos="table" if show_linenos else False,
                linenostart=1,
                hl_lines=hl_lines or [],
            )

            highlighted = highlight(code, lexer, formatter)

            # Fix Pygments .hll output: remove newlines from inside the span
            # Pygments outputs: <span class="hll">content\n</span>
            # We need: <span class="hll">content</span>
            # Since .hll uses display:block (for full-width background), the
            # block element already creates a line break. Keeping the newline
            # after </span> would create double spacing in <pre> elements.
            if hl_lines:
                highlighted = highlighted.replace("\n</span>", "</span>")

            return highlighted

        except Exception as e:
            # If highlighting fails, return plain code block
            logger.warning(
                "pygments_highlight_failed",
                language=language,
                error=str(e),
            )
            return self._fallback_render(code, language)

    def _fallback_render(self, code: str, language: str) -> str:
        """
        Render code as plain text when highlighting fails.

        Args:
            code: Source code
            language: Language identifier

        Returns:
            Escaped HTML code block
        """
        import html

        escaped = html.escape(code)
        lang_class = html.escape(language) if language else "text"
        return (
            f'<pre class="highlight"><code class="language-{lang_class}">{escaped}</code></pre>\n'
        )
