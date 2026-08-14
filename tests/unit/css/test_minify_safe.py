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

    def test_comment_only_is_empty(self) -> None:
        assert minify_css("/* only a comment */") == ""

    def test_whitespace_only_is_empty(self) -> None:
        assert minify_css("   \n\t   ") == ""

    def test_empty_rule_kept_at_safe_level(self) -> None:
        assert minify_css("body { }") == "body{}"

    def test_non_string_input_stringifies(self) -> None:
        assert minify_css(123) == "123"  # type: ignore[arg-type]


class TestCommentRemoval:
    """Moved from the legacy utils twin; single-line comments are in TestSafeCorrectness."""

    def test_multiline_comment_removed(self) -> None:
        css = """/*
         * Multi-line
         * comment
         */
        body { color: red; }
        """
        assert minify_css(css) == "body{color:red}"

    def test_multiple_comments_removed(self) -> None:
        css = "/* first */ body { /* second */ color: red; /* third */ }"
        assert minify_css(css) == "body{color:red}"


class TestStringPreservation:
    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ('body { content: "hello world"; }', 'body{content:"hello world"}'),
            ("body { content: 'hello world'; }", "body{content:'hello world'}"),
            (r'body { content: "say \"hello\""; }', r'body{content:"say \"hello\""}'),
            ('body { background: url("image.png"); }', 'body{background:url("image.png")}'),
        ],
    )
    def test_quoted_values_kept(self, source: str, expected: str) -> None:
        assert minify_css(source) == expected


class TestSelectorCompoundStarts:
    """Descendant space vs same-element compaction (legacy twin)."""

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            (".a :where(h1, h2) { color: red; }", ".a :where(h1,h2){color:red}"),
            (".a :is(h1, h2) { color: red; }", ".a :is(h1,h2){color:red}"),
            (".a :not(pre) > code { color: red; }", ".a :not(pre)>code{color:red}"),
            (".a :has(> img) { color: red; }", ".a :has(>img){color:red}"),
            (".a :hover { color: red; }", ".a :hover{color:red}"),
            (".a ::before { content: ''; }", ".a ::before{content:''}"),
            (".a [data-x] { color: red; }", ".a [data-x]{color:red}"),
            (".a * { color: red; }", ".a *{color:red}"),
            (".a #b { color: red; }", ".a #b{color:red}"),
            (".a button { color: red; }", ".a button{color:red}"),
        ],
    )
    def test_descendant_space_before_compound_start(self, source: str, expected: str) -> None:
        assert minify_css(source) == expected

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            (".a:where(h1, h2) { color: red; }", ".a:where(h1,h2){color:red}"),
            (".a:is(h1, h2) { color: red; }", ".a:is(h1,h2){color:red}"),
            (".a:not(pre) > code { color: red; }", ".a:not(pre)>code{color:red}"),
            (".a:has(> img) { color: red; }", ".a:has(>img){color:red}"),
            (".a:hover { color: red; }", ".a:hover{color:red}"),
            (".a::before { content: ''; }", ".a::before{content:''}"),
            (".a[data-x] { color: red; }", ".a[data-x]{color:red}"),
        ],
    )
    def test_same_element_selectors_stay_compact(self, source: str, expected: str) -> None:
        assert minify_css(source) == expected


class TestCalcVariants:
    def test_addition_keeps_operator_spaces(self) -> None:
        assert minify_css("div { width: calc(10px + 20px); }") == "div{width:calc(10px + 20px)}"

    def test_nested_calc(self) -> None:
        css = "div { width: calc(100% - calc(20px + 10px)); }"
        assert minify_css(css) == "div{width:calc(100% - calc(20px + 10px))}"


class TestMultiValueAndSlash:
    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            (
                "div { box-shadow: 10px 10px 5px rgba(0,0,0,0.5); }",
                "div{box-shadow:10px 10px 5px rgba(0,0,0,0.5)}",
            ),
            (
                "div { background: #fff url('img.png') no-repeat center; }",
                "div{background:#fff url('img.png') no-repeat center}",
            ),
            (
                "div { transform: rotate(45deg) scale(1.5); }",
                "div{transform:rotate(45deg) scale(1.5)}",
            ),
            ("div { border-radius: 10px / 20px; }", "div{border-radius:10px/20px}"),
        ],
    )
    def test_multi_value_and_slash_properties(self, source: str, expected: str) -> None:
        assert minify_css(source) == expected


class TestAtImport:
    def test_import_preserved(self) -> None:
        css = '@import "other.css"; body { color: red; }'
        assert minify_css(css) == '@import "other.css";body{color:red}'


class TestColorFunctions:
    """rgb() is covered by TestPreludeFunctionDistinction; rgba/hsl were twin-only."""

    def test_rgba(self) -> None:
        assert minify_css("div { color: rgba(255, 0, 0, 0.5); }") == "div{color:rgba(255,0,0,0.5)}"

    def test_hsl(self) -> None:
        assert minify_css("div { color: hsl(0, 100%, 50%); }") == "div{color:hsl(0,100%,50%)}"
