"""Tests for opt-in CSS nesting flatten (#516)."""

import pytest

from bengal.css import minify_css
from bengal.css.nesting import flatten_nesting_tree, has_nested_rules
from bengal.css.parser import parse_stylesheet
from bengal.css.tokenizer import tokenize


class TestNestingFlatten:
    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            (
                ".parent{color:blue;.child{color:red}}",
                ".parent{color:blue}.parent .child{color:red}",
            ),
            (
                ".parent{color:blue;&:hover{color:red}}",
                ".parent{color:blue}.parent:hover{color:red}",
            ),
            (
                ".a,.b{color:blue;.c{color:red}}",
                ".a,.b{color:blue}.a .c,.b .c{color:red}",
            ),
        ],
    )
    def test_flatten_nested_rules(self, source: str, expected: str) -> None:
        assert minify_css(source, flatten_nesting=True) == expected

    def test_disabled_by_default(self) -> None:
        source = ".parent{color:blue;.child{color:red}}"
        assert minify_css(source) == source
        assert "&" in minify_css(source) or ".child" in minify_css(source)

    def test_has_nested_rules_detects_nesting(self) -> None:
        tree = parse_stylesheet(tokenize(".a{.b{color:red}}"))
        assert has_nested_rules(tree)
        flat = parse_stylesheet(tokenize(".a .b{color:red}"))
        assert not has_nested_rules(flat)

    def test_flatten_tree_idempotent_on_flat_input(self) -> None:
        tree = parse_stylesheet(tokenize(".a .b{color:red}"))
        assert flatten_nesting_tree(tree) is tree
