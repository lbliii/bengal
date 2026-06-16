"""Property-based invariants for the CSS engine (Hypothesis).

These are the safety net the RFC calls for: instead of enumerating cases, assert
the laws the engine must always obey.
"""

from concurrent.futures import ThreadPoolExecutor

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bengal.css import minify_css
from bengal.css.cascade import tree_sig
from bengal.css.parser import parse_stylesheet
from bengal.css.tokenizer import tokenize
from bengal.css.tokens import TokenType


def _reconstruct(css: str) -> str:
    out: list[str] = []
    for tok in tokenize(css):
        out.append(tok.value)
        if tok.type is TokenType.FUNCTION:
            out.append("(")
    return "".join(out)


# Building blocks for plausible CSS.
_idents = st.sampled_from(["a", "div", "foo", "bar", "x-y", "--var", "h1", "to"])
_props = st.sampled_from(["color", "margin", "width", "padding", "border"])
_values = st.sampled_from(
    ["red", "10px", "1px 2px", "calc(100% - 2px)", "#fff", "0", "1.5em", "url(x.png)"]
)
_combinators = st.sampled_from([" ", ">", "+", "~", ", "])


@st.composite
def _selector(draw: st.DrawFn) -> str:
    parts = draw(st.lists(_idents, min_size=1, max_size=3))
    sep = draw(_combinators)
    prefix = draw(st.sampled_from([".", "#", "", ":"]))
    return sep.join(prefix + p for p in parts)


@st.composite
def _rule(draw: st.DrawFn) -> str:
    sel = draw(_selector())
    decls = draw(st.lists(st.tuples(_props, _values), min_size=1, max_size=4))
    body = ";".join(f"{p}: {v}" for p, v in decls)
    return f"{sel} {{ {body} }}"


@st.composite
def _stylesheet(draw: st.DrawFn) -> str:
    return "\n".join(draw(st.lists(_rule(), min_size=1, max_size=5)))


class TestTokenizerInvariants:
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    @given(st.text())
    def test_tokenization_is_lossless_for_any_text(self, text: str) -> None:
        # Every code point is consumed into exactly one token (FUNCTION drops '(').
        assert _reconstruct(text) == text


class TestMinifyInvariants:
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    @given(_stylesheet())
    def test_idempotent(self, css: str) -> None:
        once = minify_css(css)
        assert minify_css(once) == once

    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    @given(_stylesheet())
    def test_meaning_preserved_or_unchanged(self, css: str) -> None:
        # The core safety guarantee: minified output has the same meaning
        # signature as the input, or the input was returned verbatim (guard).
        out = minify_css(css)
        if out == css:
            return
        in_sig = tree_sig(parse_stylesheet(tokenize(css)), normalize=False)
        out_sig = tree_sig(parse_stylesheet(tokenize(out)), normalize=False)
        assert in_sig == out_sig

    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    @given(_stylesheet(), st.sampled_from(["safe", "optimize", "aggressive"]))
    def test_never_raises(self, css: str, level: str) -> None:
        assert isinstance(minify_css(css, level=level), str)


@pytest.mark.parallel_unsafe
def test_thread_safe_parallel_minify() -> None:
    """The engine is stateless; concurrent minification must be deterministic."""
    css = "@media x{.a>.b,.c{width:calc(100% - 2px);color:#FFF}}"
    expected = minify_css(css, level="aggressive")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: minify_css(css, level="aggressive"), range(64)))
    assert all(r == expected for r in results)
