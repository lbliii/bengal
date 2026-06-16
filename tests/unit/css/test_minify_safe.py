"""Safe-level minification correctness, including the #510 regression."""

import pytest

from bengal.css import minify_css


class TestIssue510:
    """https://github.com/lbliii/bengal/issues/510 — @scope (...) to (...)."""

    def test_scope_to_not_glued(self) -> None:
        css = "@scope (.surface) to (.surface .surface) { :scope { padding: 1rem; } }"
        out = minify_css(css)
        assert "to (" in out
        assert "to(" not in out
        assert ".surface .surface" in out  # descendant inside scope-end preserved

    def test_scope_inside_layer(self) -> None:
        css = (
            "@layer ui.component {\n"
            "  @scope (.s) to (.s .s) {\n"
            "    :scope { padding: 1rem; }\n"
            "  }\n"
            "}"
        )
        out = minify_css(css)
        assert out == "@layer ui.component{@scope (.s) to (.s .s){:scope{padding:1rem}}}"

    def test_standalone_to_function_unchanged(self) -> None:
        # A genuine function named to() must stay a function.
        out = minify_css("a { background: linear-gradient(to right, red, blue); }")
        assert "to right" in out


class TestPreludeFunctionDistinction:
    """The #510 bug class: an ``ident (`` prelude must keep its space (so the
    ident stays a keyword), while a real functional notation (``ident(``) must
    collapse (so it stays a single function token).

    A space before ``(`` is *only* removable when the preceding ident is a
    function name. Every at-rule prelude keyword below (``to``, ``not``,
    ``and``, ``@supports``, ``@container <name>``) must therefore retain it.
    """

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            # @scope prelude — both the scope-start and the `to` scope-end.
            (
                "@scope (.x) to (.x .x) { :scope { color: red; } }",
                "@scope (.x) to (.x .x){:scope{color:red}}",
            ),
            # @supports prelude keeps the space before its condition group.
            (
                "@supports (display: grid) { a { color: red; } }",
                "@supports (display:grid){a{color:red}}",
            ),
            (
                "@supports not (display: grid) { a { color: red; } }",
                "@supports not (display:grid){a{color:red}}",
            ),
            # @container with a name keeps the space before the query.
            (
                "@container sidebar (min-width: 200px) { a { color: red; } }",
                "@container sidebar (min-width:200px){a{color:red}}",
            ),
            # Media-query combinators: and / or / not all keep the space.
            (
                "@media (min-width: 200px) and (max-width: 400px) { a { color: red; } }",
                "@media (min-width:200px) and (max-width:400px){a{color:red}}",
            ),
            (
                "@media (min-width: 200px) or (orientation: landscape) { a { color: red; } }",
                "@media (min-width:200px) or (orientation:landscape){a{color:red}}",
            ),
            (
                "@media not (min-width: 200px) { a { color: red; } }",
                "@media not (min-width:200px){a{color:red}}",
            ),
        ],
    )
    def test_prelude_keywords_keep_space_before_paren(self, source: str, expected: str) -> None:
        assert minify_css(source) == expected

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            # Real functional notations: the space before `(` must collapse so
            # the ident + `(` stay a single function token.
            ("a { width: clamp( 1rem , 2vw , 3rem ); }", "a{width:clamp(1rem,2vw,3rem)}"),
            ("a { width: calc( 100% - 20px ); }", "a{width:calc(100% - 20px)}"),
            ("a { width: min( 1rem , 2vw ); }", "a{width:min(1rem,2vw)}"),
            ("a { width: max( 1rem , 2vw ); }", "a{width:max(1rem,2vw)}"),
            ("a { color: var( --x , red ); }", "a{color:var(--x,red)}"),
            ("a { color: rgb( 1 , 2 , 3 ); }", "a{color:rgb(1,2,3)}"),
        ],
    )
    def test_function_notation_collapses_paren(self, source: str, expected: str) -> None:
        assert minify_css(source) == expected


class TestSafeCorrectness:
    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            (".a { color: red; }", ".a{color:red}"),
            (".a .b { color: red; }", ".a .b{color:red}"),
            (".a.b { color: red; }", ".a.b{color:red}"),
            (".a > .b { color: red; }", ".a>.b{color:red}"),
            (".a + .b { color: red; }", ".a+.b{color:red}"),
            (".a, .b { color: red; }", ".a,.b{color:red}"),
            ("div { width: calc(100% - 20px); }", "div{width:calc(100% - 20px)}"),
            (
                "@media screen and (min-width: 768px) { a { color: red; } }",
                "@media screen and (min-width:768px){a{color:red}}",
            ),
            ("li:nth-child(2n + 1) { color: red; }", "li:nth-child(2n+ 1){color:red}"),
            (".a { filter: blur(5px) brightness(.5); }", ".a{filter:blur(5px) brightness(.5)}"),
            (".a { margin: 1px 2px 3px 4px; }", ".a{margin:1px 2px 3px 4px}"),
            (".a { grid-area: 1 / 1 / -1 / -1; }", ".a{grid-area:1/1/-1/-1}"),
        ],
    )
    def test_exact(self, source: str, expected: str) -> None:
        assert minify_css(source) == expected

    def test_comments_removed(self) -> None:
        assert minify_css("/* c */ a { color: red; }") == "a{color:red}"

    def test_idempotent(self) -> None:
        css = "@media screen { .a > .b, .c { width: calc(100% - 2px); color: red; } }"
        once = minify_css(css)
        assert minify_css(once) == once


class TestFailSafe:
    def test_empty(self) -> None:
        assert minify_css("") == ""

    def test_already_tight_value_roundtrips(self) -> None:
        # No whitespace -> emitted byte-for-byte inside the value.
        assert "U+0000-00FF" in minify_css("a { unicode-range: U+0000-00FF; }")

    def test_garbage_does_not_crash(self) -> None:
        for junk in ["}}}{{{", "@@@", "a{b", '"unterminated', "/* unclosed"]:
            assert isinstance(minify_css(junk), str)
