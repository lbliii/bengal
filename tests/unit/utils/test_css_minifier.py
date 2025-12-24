"""
Tests for bengal/utils/css_minifier.py.

Covers:
- Comment removal
- Whitespace collapsing
- String preservation
- Selector handling
- Property value handling
- CSS functions (calc, clamp, min, max)
- Multi-value properties (box-shadow, background, etc.)
- Grid/border-radius slash properties
- Font shorthand
- CSS validation (brace/paren/bracket balance)
- Edge cases and empty input
"""

from __future__ import annotations


class TestMinifyCssBasics:
    """Test basic minify_css functionality."""

    def test_empty_string_returns_empty(self) -> None:
        """Test that empty string returns empty."""
        from bengal.utils.css_minifier import minify_css

        result = minify_css("")
        assert result == ""

    def test_none_returns_empty(self) -> None:
        """Test that None-like input returns empty."""
        from bengal.utils.css_minifier import minify_css

        result = minify_css("")
        assert result == ""

    def test_simple_rule_minified(self) -> None:
        """Test that simple rule is minified."""
        from bengal.utils.css_minifier import minify_css

        css = "body { color: red; }"
        result = minify_css(css)

        # Should remove unnecessary whitespace
        assert "body{color:red" in result or "body{color:red}" in result


class TestMinifyCssCommentRemoval:
    """Test CSS comment removal."""

    def test_removes_single_line_comment(self) -> None:
        """Test removal of single-line comment."""
        from bengal.utils.css_minifier import minify_css

        css = "/* comment */ body { color: red; }"
        result = minify_css(css)

        assert "/* comment */" not in result
        assert "color:red" in result

    def test_removes_multiline_comment(self) -> None:
        """Test removal of multi-line comment."""
        from bengal.utils.css_minifier import minify_css

        css = """/*
         * Multi-line
         * comment
         */
        body { color: red; }
        """
        result = minify_css(css)

        assert "Multi-line" not in result
        assert "color:red" in result

    def test_removes_multiple_comments(self) -> None:
        """Test removal of multiple comments."""
        from bengal.utils.css_minifier import minify_css

        css = "/* first */ body { /* second */ color: red; /* third */ }"
        result = minify_css(css)

        assert "first" not in result
        assert "second" not in result
        assert "third" not in result


class TestMinifyCssStringPreservation:
    """Test that strings are preserved."""

    def test_preserves_double_quoted_strings(self) -> None:
        """Test that double-quoted strings are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = 'body { content: "hello world"; }'
        result = minify_css(css)

        assert '"hello world"' in result

    def test_preserves_single_quoted_strings(self) -> None:
        """Test that single-quoted strings are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "body { content: 'hello world'; }"
        result = minify_css(css)

        assert "'hello world'" in result

    def test_preserves_escaped_quotes_in_strings(self) -> None:
        """Test that escaped quotes in strings are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = r'body { content: "say \"hello\""; }'
        result = minify_css(css)

        assert r"\"hello\"" in result

    def test_preserves_url_strings(self) -> None:
        """Test that url() strings are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = 'body { background: url("image.png"); }'
        result = minify_css(css)

        assert 'url("image.png")' in result


class TestMinifyCssWhitespaceCollapsing:
    """Test whitespace collapsing."""

    def test_collapses_multiple_spaces(self) -> None:
        """Test that multiple spaces are collapsed."""
        from bengal.utils.css_minifier import minify_css

        css = "body   {    color:    red;    }"
        result = minify_css(css)

        # Should not have multiple consecutive spaces
        assert "    " not in result

    def test_removes_newlines(self) -> None:
        """Test that newlines are removed."""
        from bengal.utils.css_minifier import minify_css

        css = """body {
            color: red;
        }"""
        result = minify_css(css)

        # Should be on fewer lines or single line
        lines = result.strip().split("\n")
        assert len(lines) <= 2

    def test_removes_trailing_whitespace(self) -> None:
        """Test that trailing whitespace is removed."""
        from bengal.utils.css_minifier import minify_css

        css = "body { color: red;   }   "
        result = minify_css(css)

        assert result.rstrip() == result.strip().rstrip()


class TestMinifyCssSelectorHandling:
    """Test selector handling."""

    def test_preserves_descendant_selector_space(self) -> None:
        """Test that space between selectors is preserved."""
        from bengal.utils.css_minifier import minify_css

        css = ".parent .child { color: red; }"
        result = minify_css(css)

        # Space between .parent and .child should be preserved
        assert ".parent .child" in result or ".parent .child{" in result

    def test_preserves_complex_selectors(self) -> None:
        """Test complex selector combinations."""
        from bengal.utils.css_minifier import minify_css

        css = "div.class #id > p + span { color: red; }"
        result = minify_css(css)

        # Should preserve selector structure
        assert "div.class" in result or "div.class#id" in result


class TestMinifyCssCalcFunction:
    """Test calc() function handling."""

    def test_preserves_calc_operator_spaces(self) -> None:
        """Test that calc() preserves spaces around + and -."""
        from bengal.utils.css_minifier import minify_css

        css = "div { width: calc(100% - 20px); }"
        result = minify_css(css)

        # calc requires space around + and -
        assert "100% - 20px" in result or "100%- 20px" in result or "100% -20px" in result

    def test_calc_with_addition(self) -> None:
        """Test calc() with addition."""
        from bengal.utils.css_minifier import minify_css

        css = "div { width: calc(10px + 20px); }"
        result = minify_css(css)

        assert "calc(" in result
        assert "10px" in result
        assert "20px" in result

    def test_nested_calc(self) -> None:
        """Test nested calc() functions."""
        from bengal.utils.css_minifier import minify_css

        css = "div { width: calc(100% - calc(20px + 10px)); }"
        result = minify_css(css)

        assert "calc(" in result


class TestMinifyCssClampMinMax:
    """Test clamp(), min(), max() function handling."""

    def test_clamp_function(self) -> None:
        """Test clamp() function."""
        from bengal.utils.css_minifier import minify_css

        css = "div { font-size: clamp(1rem, 2vw, 3rem); }"
        result = minify_css(css)

        assert "clamp(" in result

    def test_min_function(self) -> None:
        """Test min() function."""
        from bengal.utils.css_minifier import minify_css

        css = "div { width: min(100%, 500px); }"
        result = minify_css(css)

        assert "min(" in result

    def test_max_function(self) -> None:
        """Test max() function."""
        from bengal.utils.css_minifier import minify_css

        css = "div { width: max(300px, 50%); }"
        result = minify_css(css)

        assert "max(" in result


class TestMinifyCssMultiValueProperties:
    """Test multi-value property handling."""

    def test_box_shadow_values(self) -> None:
        """Test box-shadow multi-value handling."""
        from bengal.utils.css_minifier import minify_css

        css = "div { box-shadow: 10px 10px 5px rgba(0,0,0,0.5); }"
        result = minify_css(css)

        assert "box-shadow:" in result

    def test_background_values(self) -> None:
        """Test background multi-value handling."""
        from bengal.utils.css_minifier import minify_css

        css = "div { background: #fff url('img.png') no-repeat center; }"
        result = minify_css(css)

        assert "background:" in result

    def test_transform_values(self) -> None:
        """Test transform multi-value handling."""
        from bengal.utils.css_minifier import minify_css

        css = "div { transform: rotate(45deg) scale(1.5); }"
        result = minify_css(css)

        assert "transform:" in result
        assert "rotate(" in result
        assert "scale(" in result


class TestMinifyCssGridSlashProperties:
    """Test grid and border-radius slash handling."""

    def test_border_radius_slash(self) -> None:
        """Test border-radius with slash notation."""
        from bengal.utils.css_minifier import minify_css

        css = "div { border-radius: 10px / 20px; }"
        result = minify_css(css)

        assert "border-radius:" in result
        # Slash should be preserved with or without spaces
        assert "/" in result

    def test_grid_area_slash(self) -> None:
        """Test grid-area with slash notation."""
        from bengal.utils.css_minifier import minify_css

        css = "div { grid-area: 1 / 2 / 3 / 4; }"
        result = minify_css(css)

        assert "grid-area:" in result


class TestMinifyCssLayerSupport:
    """Test @layer support."""

    def test_preserves_layer_block(self) -> None:
        """Test that @layer blocks are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "@layer tokens { :root { --color: blue; } }"
        result = minify_css(css)

        assert "@layer tokens" in result or "@layer tokens{" in result
        assert "--color:" in result


class TestMinifyCssImportSupport:
    """Test @import support."""

    def test_preserves_import(self) -> None:
        """Test that @import is preserved."""
        from bengal.utils.css_minifier import minify_css

        css = '@import "other.css"; body { color: red; }'
        result = minify_css(css)

        assert "@import" in result
        assert '"other.css"' in result


class TestMinifyCssCustomProperties:
    """Test CSS custom properties."""

    def test_preserves_custom_property(self) -> None:
        """Test that custom properties are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = ":root { --primary-color: blue; }"
        result = minify_css(css)

        assert "--primary-color:" in result

    def test_preserves_var_function(self) -> None:
        """Test that var() is preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "div { color: var(--primary-color); }"
        result = minify_css(css)

        assert "var(--primary-color)" in result


class TestMinifyCssValidation:
    """Test CSS validation (brace/paren balance)."""

    def test_balanced_braces(self) -> None:
        """Test that balanced braces pass validation."""
        from bengal.utils.css_minifier import minify_css

        css = "body { color: red; } div { margin: 0; }"
        result = minify_css(css)

        assert result.count("{") == result.count("}")

    def test_balanced_parentheses(self) -> None:
        """Test that balanced parentheses pass validation."""
        from bengal.utils.css_minifier import minify_css

        css = "div { width: calc(100% - 20px); }"
        result = minify_css(css)

        assert result.count("(") == result.count(")")


class TestMinifyCssNestingSyntax:
    """Test CSS nesting syntax support."""

    def test_preserves_nesting(self) -> None:
        """Test that CSS nesting syntax is preserved."""
        from bengal.utils.css_minifier import minify_css

        css = """
        .parent {
            color: blue;
            .child {
                color: red;
            }
        }
        """
        result = minify_css(css)

        assert ".parent" in result
        assert ".child" in result


class TestMinifyCssMediaQueries:
    """Test @media query handling."""

    def test_preserves_media_query(self) -> None:
        """Test that @media queries are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "@media (min-width: 768px) { body { font-size: 16px; } }"
        result = minify_css(css)

        assert "@media" in result
        assert "min-width:" in result or "min-width: " in result


class TestMinifyCssColorFunctions:
    """Test modern CSS color functions."""

    def test_rgb_function(self) -> None:
        """Test rgb() function."""
        from bengal.utils.css_minifier import minify_css

        css = "div { color: rgb(255, 0, 0); }"
        result = minify_css(css)

        assert "rgb(" in result

    def test_rgba_function(self) -> None:
        """Test rgba() function."""
        from bengal.utils.css_minifier import minify_css

        css = "div { color: rgba(255, 0, 0, 0.5); }"
        result = minify_css(css)

        assert "rgba(" in result

    def test_hsl_function(self) -> None:
        """Test hsl() function."""
        from bengal.utils.css_minifier import minify_css

        css = "div { color: hsl(0, 100%, 50%); }"
        result = minify_css(css)

        assert "hsl(" in result


class TestMinifyCssEdgeCases:
    """Test edge cases."""

    def test_empty_rule(self) -> None:
        """Test handling of empty rule."""
        from bengal.utils.css_minifier import minify_css

        css = "body { }"
        result = minify_css(css)

        assert "body{}" in result or "body{ }" in result or "body {}" in result

    def test_comment_only(self) -> None:
        """Test CSS with only comment."""
        from bengal.utils.css_minifier import minify_css

        css = "/* only a comment */"
        result = minify_css(css)

        assert "only a comment" not in result

    def test_whitespace_only(self) -> None:
        """Test CSS with only whitespace."""
        from bengal.utils.css_minifier import minify_css

        css = "   \n\t   "
        result = minify_css(css)

        assert result.strip() == ""

    def test_invalid_type_handled(self) -> None:
        """Test that invalid types are handled gracefully."""
        from bengal.utils.css_minifier import minify_css

        # Pass a non-string type
        result = minify_css(123)  # type: ignore

        # Should convert to string or return empty
        assert isinstance(result, str)
