"""Optimize and aggressive level tests."""

import pytest

from bengal.css import MinifyLevel, minify_css


class TestOptimize:
    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("a{color:#FFFFFF}", "a{color:#fff}"),
            ("a{color:#AABBCC}", "a{color:#abc}"),
            ("a{color:#11223344}", "a{color:#1234}"),
            ("a{color:#abcdef}", "a{color:#abcdef}"),
            ("a{opacity:0.50}", "a{opacity:.5}"),
            ("a{margin:1.0px}", "a{margin:1px}"),
            ("a{margin:0.0px}", "a{margin:0px}"),
            ("a{z-index:010}", "a{z-index:10}"),
            ("a{width:50.00%}", "a{width:50%}"),
        ],
    )
    def test_value_normalization(self, source: str, expected: str) -> None:
        assert minify_css(source, level="optimize") == expected

    def test_custom_property_untouched(self) -> None:
        # Custom property values are an arbitrary token stream; do not normalize.
        out = minify_css(":root{--x:0.50}", level="optimize")
        assert "0.50" in out


class TestAggressive:
    def test_removes_empty_rule(self) -> None:
        assert minify_css(".a{}.b{color:red}", level="aggressive") == ".b{color:red}"

    def test_exact_duplicate_dedup(self) -> None:
        assert minify_css("a{color:red;color:red}", level="aggressive") == "a{color:red}"

    def test_fallback_preserved(self) -> None:
        # display:flex is a fallback for display:grid; it must NOT be removed.
        out = minify_css("a{display:flex;display:grid}", level="aggressive")
        assert "flex" in out
        assert "grid" in out

    def test_merge_identical_blocks(self) -> None:
        assert minify_css(".a{color:red}.b{color:red}", level="aggressive") == ".a,.b{color:red}"

    def test_merge_identical_preludes(self) -> None:
        assert (
            minify_css(".a{color:red}.a{margin:0}", level="aggressive") == ".a{color:red;margin:0}"
        )

    def test_merge_adjacent_media(self) -> None:
        css = "@media x{.a{color:red}}@media x{.b{color:blue}}"
        assert minify_css(css, level="aggressive") == "@media x{.a{color:red}.b{color:blue}}"

    def test_non_adjacent_rules_not_merged(self) -> None:
        # An intervening different rule blocks merging (cascade safety).
        css = ".a{color:red}.b{color:blue}.a{margin:0}"
        out = minify_css(css, level="aggressive")
        assert out.count(".a") == 2


class TestLevelCoercion:
    def test_string_and_enum_equivalent(self) -> None:
        css = "a{color:#FFF}"
        assert minify_css(css, level="optimize") == minify_css(css, level=MinifyLevel.OPTIMIZE)

    def test_unknown_level_falls_back_to_safe(self) -> None:
        assert minify_css("a{color:#FFFFFF}", level="bogus") == "a{color:#FFFFFF}"
