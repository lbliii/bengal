"""Tests for opt-in intra-stylesheet CSS dead-code removal (#512)."""

import pytest

from bengal.css import minify_css
from bengal.css.cascade import surviving_resolve_ok
from bengal.css.dead_code import has_removable_dead_code, remove_dead_code_tree
from bengal.css.parser import parse_stylesheet
from bengal.css.tokenizer import tokenize


class TestDeadCodeRemoval:
    def test_removes_unused_keyframes(self) -> None:
        source = "@keyframes spin{to{transform:rotate(360deg)}}.a{animation:fade 1s}"
        expected = ".a{animation:fade 1s}"
        assert minify_css(source, remove_dead_code=True) == expected

    def test_keeps_used_keyframes(self) -> None:
        source = "@keyframes spin{to{transform:rotate(360deg)}}.a{animation:spin 1s}"
        assert minify_css(source, remove_dead_code=True) == source

    def test_removes_unused_font_face(self) -> None:
        source = "@font-face{font-family:'Unused';src:url(a.woff)}.a{font-family:serif}"
        expected = ".a{font-family:serif}"
        assert minify_css(source, remove_dead_code=True) == expected

    def test_keeps_used_font_face(self) -> None:
        source = "@font-face{font-family:'MyFont';src:url(a.woff)}.a{font-family:'MyFont',serif}"
        assert minify_css(source, remove_dead_code=True) == source

    def test_removes_unused_custom_property(self) -> None:
        source = ":root{--used:red;--unused:blue}.a{color:var(--used)}"
        expected = ":root{--used:red}.a{color:var(--used)}"
        assert minify_css(source, remove_dead_code=True) == expected

    def test_disabled_by_default(self) -> None:
        source = "@keyframes spin{to{}}.a{color:red}"
        assert minify_css(source) == source

    def test_has_removable_detects_dead_definitions(self) -> None:
        tree = parse_stylesheet(tokenize("@keyframes spin{to{}}.a{color:red}"))
        assert has_removable_dead_code(tree)

    def test_surviving_resolve_ok_accepts_pruned_tree(self) -> None:
        source = "@keyframes spin{to{}}.a{color:red}"
        tree = parse_stylesheet(tokenize(source))
        pruned = remove_dead_code_tree(tree)
        assert surviving_resolve_ok(tree, pruned, normalize=True)

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            (
                "@keyframes a{to{}}@keyframes b{to{}}.x{animation-name:a}",
                "@keyframes a{to{}}.x{animation-name:a}",
            ),
            (
                ":root{--a:1;--b:2}.x{color:var(--a)}",
                ":root{--a:1}.x{color:var(--a)}",
            ),
        ],
    )
    def test_partial_removal(self, source: str, expected: str) -> None:
        assert minify_css(source, remove_dead_code=True) == expected
