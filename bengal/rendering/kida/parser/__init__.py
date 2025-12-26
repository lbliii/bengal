"""Kida Parser — transforms token stream into immutable AST.

Recursive descent parser that consumes tokens from the Lexer and produces
an immutable Kida AST. All AST nodes are frozen dataclasses for thread-safety.

Architecture:
    The parser uses a mixin-based design for separation of concerns:
    - `TokenNavigationMixin`: Token stream traversal and lookahead
    - `ExpressionParsingMixin`: Expressions, operators, filters, tests
    - `StatementParsingMixin`: Control flow, variables, blocks
    - `BlockParsingMixin`: Template structure, inheritance, includes

Syntax Features:
    - **Unified block endings**: `{% end %}` closes any block (like Go templates)
    - **Pythonic scoping**: `{% let %}` (template), `{% set %}` (block), `{% export %}`
    - **Native async**: `{% async for %}`, `{{ await expr }}`
    - **Pattern matching**: `{% match %}...{% case %}...{% end %}`
    - **Built-in caching**: `{% cache key %}...{% end %}`

Error Handling:
    Parser errors include source location and fix suggestions:
    ```
    ParseError: Expected 'in' after loop variable
      --> template.html:5:12
       |
     5 | {% for item items %}
       |             ^
    Suggestion: Add 'in' keyword: {% for item in items %}
    ```

Example:
    >>> from bengal.rendering.kida.lexer import tokenize
    >>> from bengal.rendering.kida.parser import Parser
    >>> tokens = tokenize("{% for x in items %}{{ x }}{% end %}")
    >>> parser = Parser(tokens, name="template.html", source=source)
    >>> ast = parser.parse()  # Returns Template node

Public API:
    Parser: Main parser class (combines all parsing mixins)
    ParseError: Rich error exception with source context and suggestions
"""

from __future__ import annotations

from bengal.rendering.kida.parser.core import Parser
from bengal.rendering.kida.parser.errors import ParseError

__all__ = [
    "Parser",
    "ParseError",
]
