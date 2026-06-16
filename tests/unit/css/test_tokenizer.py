"""Tokenizer correctness tests for the Bengal CSS engine."""

from bengal.css.tokenizer import tokenize
from bengal.css.tokens import TokenType


def reconstruct(css: str) -> str:
    """Rebuild source text from tokens (FUNCTION drops its trailing '(')."""
    out: list[str] = []
    for tok in tokenize(css):
        out.append(tok.value)
        if tok.type is TokenType.FUNCTION:
            out.append("(")
    return "".join(out)


class TestLosslessTokenization:
    def test_reconstructs_simple_rule(self) -> None:
        css = ".a { color: red; }"
        assert reconstruct(css) == css

    def test_reconstructs_complex(self) -> None:
        css = '@media (min-width: 768px) { .a::before { content: "x"; } }'
        assert reconstruct(css) == css

    def test_reconstructs_calc_and_urls(self) -> None:
        css = ".a { width: calc(100% - 20px); background: url(img.png); }"
        assert reconstruct(css) == css


class TestFunctionVsIdent:
    def test_ident_space_paren_is_not_function(self) -> None:
        # The #510 root cause: "to (" must tokenize as IDENT, WHITESPACE, LPAREN.
        toks = [t for t in tokenize("to (") if t.type is not TokenType.WHITESPACE]
        assert toks[0].type is TokenType.IDENT
        assert toks[0].value == "to"
        assert toks[1].type is TokenType.LPAREN

    def test_ident_paren_is_function(self) -> None:
        toks = tokenize("to(")
        assert toks[0].type is TokenType.FUNCTION
        assert toks[0].value == "to"

    def test_calc_is_function(self) -> None:
        toks = tokenize("calc(1px)")
        assert toks[0].type is TokenType.FUNCTION


class TestTokenKinds:
    def test_hash(self) -> None:
        assert tokenize("#fff")[0].type is TokenType.HASH

    def test_at_keyword(self) -> None:
        assert tokenize("@media")[0].type is TokenType.AT_KEYWORD

    def test_dimension_number_percentage(self) -> None:
        assert tokenize("10px")[0].type is TokenType.DIMENSION
        assert tokenize("10px")[0].unit == "px"
        assert tokenize("10")[0].type is TokenType.NUMBER
        assert tokenize("10%")[0].type is TokenType.PERCENTAGE

    def test_string_and_bad_string(self) -> None:
        assert tokenize('"hi"')[0].type is TokenType.STRING
        assert tokenize('"hi')[0].type is TokenType.BAD_STRING

    def test_url_unquoted_vs_function(self) -> None:
        assert tokenize("url(x.png)")[0].type is TokenType.URL
        assert tokenize('url("x.png")')[0].type is TokenType.FUNCTION

    def test_comment(self) -> None:
        assert tokenize("/* x */")[0].type is TokenType.COMMENT

    def test_negative_number(self) -> None:
        toks = tokenize("-5px")
        assert toks[0].type is TokenType.DIMENSION
        assert toks[0].value == "-5px"

    def test_custom_property_ident(self) -> None:
        assert tokenize("--my-var")[0].type is TokenType.IDENT
