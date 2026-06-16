"""Bengal CSS engine.

A self-contained, zero-dependency, free-threading-safe CSS tokenizer, parser,
and minifier. Correctness is structural: a proper CSS Syntax Level 3 tokenizer
makes the ``<ident-token>`` vs ``<function-token>`` distinction at tokenize time,
so collapsing whitespace can never turn ``to (`` into a ``to(`` function token
(the #510 bug class). A runtime round-trip guard backs every transform.

Designed to mirror the patitas (parser) and rosettes (lexer) architectures so it
can be extracted into a standalone package later by swapping :mod:`bengal.css.errors`.

Public API:
    minify_css(css, *, level="safe" | "optimize" | "aggressive") -> str
    MinifyLevel
    tokenize(css) -> list[Token]
"""

from bengal.css.config import MinifyLevel
from bengal.css.minify import minify_css
from bengal.css.tokenizer import tokenize
from bengal.css.tokens import Token, TokenType

__all__ = ["MinifyLevel", "Token", "TokenType", "minify_css", "tokenize"]
