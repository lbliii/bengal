"""Frozen configuration dataclasses for Rosettes.

All configuration objects are immutable (frozen) for thread-safety.
"""

from dataclasses import dataclass

__all__ = ["LexerConfig", "FormatConfig", "HighlightConfig"]


@dataclass(frozen=True, slots=True)
class LexerConfig:
    """Configuration for lexer behavior.

    Attributes:
        strip_whitespace: If True, strip trailing whitespace from lines.
        tab_size: Number of spaces per tab for column calculation.
    """

    strip_whitespace: bool = False
    tab_size: int = 4


@dataclass(frozen=True, slots=True)
class FormatConfig:
    """Configuration for output formatting.

    Attributes:
        css_class: Base CSS class for the code container.
        wrap_code: If True, wrap output in <pre><code> tags.
        class_prefix: Prefix for token CSS classes.
        data_language: Language name for data-language attribute (e.g., 'python').
    """

    css_class: str = "highlight"
    wrap_code: bool = True
    class_prefix: str = ""
    data_language: str | None = None


@dataclass(frozen=True, slots=True)
class HighlightConfig:
    """Combined configuration for syntax highlighting.

    Attributes:
        hl_lines: Set of 1-based line numbers to highlight.
        show_linenos: If True, include line numbers in output.
        css_class: Base CSS class for the code container.
        lineno_class: CSS class for line number elements.
        hl_line_class: CSS class for highlighted lines.
    """

    hl_lines: frozenset[int] = frozenset()
    show_linenos: bool = False
    css_class: str = "highlight"
    lineno_class: str = "lineno"
    hl_line_class: str = "hll"
