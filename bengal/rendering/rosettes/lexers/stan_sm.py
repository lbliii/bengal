"""Hand-written Stan lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
Stan is a probabilistic programming language.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    CStyleCommentsMixin,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["StanStateMachineLexer"]


_BLOCKS: frozenset[str] = frozenset(
    {
        "functions",
        "data",
        "transformed",
        "parameters",
        "model",
        "generated",
        "quantities",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "int",
        "real",
        "vector",
        "row_vector",
        "matrix",
        "ordered",
        "positive_ordered",
        "simplex",
        "unit_vector",
        "cholesky_factor_corr",
        "cholesky_factor_cov",
        "corr_matrix",
        "cov_matrix",
        "complex",
        "complex_vector",
        "complex_row_vector",
        "complex_matrix",
        "array",
        "tuple",
    }
)

_KEYWORDS: frozenset[str] = frozenset(
    {
        "for",
        "in",
        "while",
        "if",
        "else",
        "return",
        "break",
        "continue",
        "lower",
        "upper",
        "offset",
        "multiplier",
        "print",
        "reject",
        "target",
        "profile",
    }
)

_DISTRIBUTIONS: frozenset[str] = frozenset(
    {
        "normal",
        "bernoulli",
        "binomial",
        "beta",
        "gamma",
        "exponential",
        "poisson",
        "uniform",
        "cauchy",
        "student_t",
        "multi_normal",
        "lognormal",
        "chi_square",
        "inv_chi_square",
        "scaled_inv_chi_square",
        "inv_gamma",
        "weibull",
        "pareto",
        "beta_binomial",
        "neg_binomial",
        "hypergeometric",
        "categorical",
        "dirichlet",
        "multinomial",
        "wishart",
        "inv_wishart",
        "lkj_corr",
        "lkj_corr_cholesky",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "abs",
        "acos",
        "acosh",
        "asin",
        "asinh",
        "atan",
        "atan2",
        "atanh",
        "cbrt",
        "ceil",
        "cos",
        "cosh",
        "erf",
        "erfc",
        "exp",
        "exp2",
        "expm1",
        "fabs",
        "floor",
        "lgamma",
        "log",
        "log10",
        "log1p",
        "log2",
        "pow",
        "round",
        "sin",
        "sinh",
        "sqrt",
        "tan",
        "tanh",
        "tgamma",
        "trunc",
        "sum",
        "prod",
        "mean",
        "variance",
        "sd",
        "min",
        "max",
        "size",
        "rows",
        "cols",
        "rep_vector",
        "rep_matrix",
        "diag_matrix",
        "identity_matrix",
        "dot_product",
        "quad_form",
        "trace",
        "determinant",
        "inverse",
        "eigenvalues",
        "to_vector",
        "to_matrix",
        "to_array_1d",
        "to_array_2d",
    }
)


class StanStateMachineLexer(
    CStyleCommentsMixin,
    StateMachineLexer,
):
    """Stan lexer."""

    name = "stan"
    aliases = ()
    filenames = ("*.stan",)
    mimetypes = ("text/x-stan",)

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = start

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace
            if char in self.WHITESPACE:
                start = pos
                start_line = line
                while pos < length and code[pos] in self.WHITESPACE:
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], start_line, col)
                continue

            # Preprocessor #include
            if char == "#":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_PREPROC, code[start:pos], line, col)
                continue

            # Comments
            token, new_pos = self._try_comment(code, pos, line, col)
            if token:
                if token.type == TokenType.COMMENT_MULTILINE:
                    newlines = token.value.count("\n")
                    if newlines:
                        line += newlines
                        line_start = pos + token.value.rfind("\n") + 1
                yield token
                pos = new_pos
                continue

            # Strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS or (char == "." and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if char == ".":
                    pos += 1
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                if pos < length and code[pos] == ".":
                    pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                if pos < length and code[pos] in "eE":
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                value = code[start:pos]
                token_type = (
                    TokenType.NUMBER_FLOAT
                    if "." in value or "e" in value.lower()
                    else TokenType.NUMBER_INTEGER
                )
                yield Token(token_type, value, line, col)
                continue

            # Keywords and identifiers
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                if word in _BLOCKS:
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in _TYPES:
                    yield Token(TokenType.KEYWORD_TYPE, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _DISTRIBUTIONS:
                    yield Token(TokenType.NAME_FUNCTION, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Target increment +=
            if char == "~":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Operators
            if char in "=<>!&|+-*/%^":
                start = pos
                if pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "+=",
                    "-=",
                    "*=",
                    "/=",
                    ".*",
                    "./",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Range ..
            if char == "." and pos + 1 < length and code[pos + 1] == ".":
                yield Token(TokenType.OPERATOR, "..", line, col)
                pos += 2
                continue

            # Transpose '
            if char == "'":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Punctuation
            if char in "()[]{},.;:":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
