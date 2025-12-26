"""Kida Parser — transforms tokens into AST.

Recursive descent parser that builds an immutable AST
from the token stream produced by the lexer.

Features:
    - Pythonic scoping with let/set/export
    - Native async for loops
    - Rich error messages with suggestions

Public API:
    Parser: Main parser class
    ParseError: Parser error exception
"""

from __future__ import annotations

from bengal.rendering.kida.parser.core import Parser
from bengal.rendering.kida.parser.errors import ParseError

__all__ = [
    "Parser",
    "ParseError",
]
