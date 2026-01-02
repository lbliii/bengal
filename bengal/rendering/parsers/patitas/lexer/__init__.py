"""Modular state-machine lexer for Patitas markdown parser.

This package provides a window-based lexer with O(n) guaranteed performance.
The lexer scans entire lines, classifies them, then commits position.

Architecture:
    lexer/
    ├── __init__.py          # Re-exports Lexer, LexerMode
    ├── core.py              # Lexer class (mixin composition + navigation)
    ├── modes.py             # LexerMode enum, HTML tag constants
    ├── classifiers/         # Block-type classification mixins
    │   ├── heading.py       # ATX heading
    │   ├── fence.py         # Fenced code
    │   ├── thematic.py      # Thematic break
    │   ├── quote.py         # Block quote
    │   ├── list.py          # List markers
    │   ├── link_ref.py      # Link reference definitions
    │   ├── footnote.py      # Footnote definitions
    │   ├── html.py          # HTML blocks (types 1-7)
    │   └── directive.py     # MyST directives
    └── scanners/            # Mode-specific scanners
        ├── block.py         # Block mode (main dispatch)
        ├── fence.py         # Code fence mode
        ├── directive.py     # Directive mode
        └── html.py          # HTML block mode

Usage:
    >>> from bengal.rendering.parsers.patitas.lexer import Lexer
    >>> lexer = Lexer("# Hello\\n\\nWorld")
    >>> for token in lexer.tokenize():
    ...     print(token)
    Token(ATX_HEADING, '# Hello', 1:1)
    Token(BLANK_LINE, '', 2:1)
    Token(PARAGRAPH_LINE, 'World', 3:1)
    Token(EOF, '', 3:6)
"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.lexer.core import Lexer
from bengal.rendering.parsers.patitas.lexer.modes import LexerMode

__all__ = ["Lexer", "LexerMode"]
