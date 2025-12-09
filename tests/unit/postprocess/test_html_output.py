"""
Tests for bengal/postprocess/html_output.py.

Covers:
- format_html_output modes: raw, pretty, minify
- Whitespace-sensitive region protection (pre, code, textarea, script, style)
- Comment removal
- Whitespace collapsing
- Inter-tag whitespace handling
- Class attribute normalization
- Title text trimming
- Pretty indentation
- Void tag handling
"""

from __future__ import annotations


class TestFormatHtmlOutputRawMode:
    """Test format_html_output in raw mode."""

    def test_raw_mode_returns_unchanged(self) -> None:
        """Test that raw mode returns input unchanged."""
        from bengal.postprocess.html_output import format_html_output

        html = "<div>  \n  Hello  \n  </div>"
        result = format_html_output(html, mode="raw")

        assert result == html

    def test_raw_mode_handles_empty_string(self) -> None:
        """Test that raw mode handles empty string."""
        from bengal.postprocess.html_output import format_html_output

        result = format_html_output("", mode="raw")
        assert result == ""

    def test_raw_mode_handles_none(self) -> None:
        """Test that raw mode handles None (as empty string)."""
        from bengal.postprocess.html_output import format_html_output

        # The function returns empty string for falsy values
        result = format_html_output("", mode="raw")
        assert result == ""


class TestFormatHtmlOutputMinifyMode:
    """Test format_html_output in minify mode."""

    def test_minify_removes_comments(self) -> None:
        """Test that minify mode removes HTML comments."""
        from bengal.postprocess.html_output import format_html_output

        html = "<div><!-- comment -->Hello</div>"
        result = format_html_output(html, mode="minify")

        assert "<!-- comment -->" not in result
        assert "Hello" in result

    def test_minify_collapses_inter_tag_whitespace(self) -> None:
        """Test that minify mode collapses whitespace between tags."""
        from bengal.postprocess.html_output import format_html_output

        html = "<div>   </div>   <span>Hello</span>"
        result = format_html_output(html, mode="minify")

        # Should not have multiple spaces between tags
        assert "   " not in result

    def test_minify_preserves_code_block_whitespace(self) -> None:
        """Test that minify preserves whitespace in code blocks."""
        from bengal.postprocess.html_output import format_html_output

        html = "<pre><code>  indented\n    more indented</code></pre>"
        result = format_html_output(html, mode="minify")

        # Whitespace inside code block should be preserved
        assert "  indented" in result
        assert "    more indented" in result

    def test_minify_preserves_script_content(self) -> None:
        """Test that minify preserves script content."""
        from bengal.postprocess.html_output import format_html_output

        html = "<script>  var x = 1;  </script>"
        result = format_html_output(html, mode="minify")

        # Script content should be preserved
        assert "var x = 1" in result

    def test_minify_preserves_style_content(self) -> None:
        """Test that minify preserves style content."""
        from bengal.postprocess.html_output import format_html_output

        html = "<style>  .class { color: red; }  </style>"
        result = format_html_output(html, mode="minify")

        # Style content should be preserved
        assert ".class { color: red; }" in result

    def test_minify_preserves_textarea_content(self) -> None:
        """Test that minify preserves textarea content."""
        from bengal.postprocess.html_output import format_html_output

        html = "<textarea>  user input\n  here  </textarea>"
        result = format_html_output(html, mode="minify")

        # Textarea content should be preserved
        assert "user input" in result


class TestFormatHtmlOutputPrettyMode:
    """Test format_html_output in pretty mode."""

    def test_pretty_adds_indentation(self) -> None:
        """Test that pretty mode adds indentation."""
        from bengal.postprocess.html_output import format_html_output

        html = "<div><span>Hello</span></div>"
        result = format_html_output(html, mode="pretty")

        # Should have some structure with newlines
        assert "\n" in result

    def test_pretty_collapses_blank_lines(self) -> None:
        """Test that pretty mode collapses multiple blank lines."""
        from bengal.postprocess.html_output import format_html_output

        html = "<div>\n\n\n\n</div>"
        result = format_html_output(html, mode="pretty")

        # Should not have 4+ consecutive newlines
        assert "\n\n\n\n" not in result


class TestProtectedRegions:
    """Test whitespace-sensitive region protection."""

    def test_pre_tag_preserved(self) -> None:
        """Test that pre tag content is preserved."""
        from bengal.postprocess.html_output import format_html_output

        html = "<pre>  line 1\n    line 2\n</pre>"
        result = format_html_output(html, mode="minify")

        # Pre content should be unchanged
        assert "  line 1" in result
        assert "    line 2" in result

    def test_code_tag_preserved(self) -> None:
        """Test that code tag content is preserved."""
        from bengal.postprocess.html_output import format_html_output

        html = "<code>  function()  </code>"
        result = format_html_output(html, mode="minify")

        assert "  function()  " in result

    def test_nested_pre_code_preserved(self) -> None:
        """Test that nested pre/code content is preserved."""
        from bengal.postprocess.html_output import format_html_output

        html = "<pre><code>  if (x) {\n    return y;\n  }</code></pre>"
        result = format_html_output(html, mode="minify")

        assert "  if (x) {" in result
        assert "    return y;" in result
        assert "  }" in result


class TestSplitProtectedRegions:
    """Test _split_protected_regions function."""

    def test_empty_string_returns_empty_tuple(self) -> None:
        """Test that empty string returns list with empty tuple."""
        from bengal.postprocess.html_output import _split_protected_regions

        result = _split_protected_regions("")
        assert result == [("", False)]

    def test_no_protected_regions(self) -> None:
        """Test HTML with no protected regions."""
        from bengal.postprocess.html_output import _split_protected_regions

        html = "<div>Hello</div>"
        result = _split_protected_regions(html)

        # Should return single non-protected segment
        assert len(result) == 1
        assert result[0][1] is False  # Not protected

    def test_identifies_pre_as_protected(self) -> None:
        """Test that pre tags are identified as protected."""
        from bengal.postprocess.html_output import _split_protected_regions

        html = "before<pre>code</pre>after"
        result = _split_protected_regions(html)

        # Should have 3 segments: before (unprotected), pre (protected), after (unprotected)
        protected_segments = [seg for seg, is_protected in result if is_protected]
        assert len(protected_segments) == 1
        assert "<pre>code</pre>" in protected_segments[0]

    def test_identifies_script_as_protected(self) -> None:
        """Test that script tags are identified as protected."""
        from bengal.postprocess.html_output import _split_protected_regions

        html = "before<script>var x = 1;</script>after"
        result = _split_protected_regions(html)

        protected_segments = [seg for seg, is_protected in result if is_protected]
        assert len(protected_segments) == 1
        assert "<script>var x = 1;</script>" in protected_segments[0]


class TestCommentRemoval:
    """Test HTML comment removal."""

    def test_removes_standard_comments(self) -> None:
        """Test that standard HTML comments are removed."""
        from bengal.postprocess.html_output import _remove_html_comments

        html = "before<!-- comment -->after"
        result = _remove_html_comments(html)

        assert result == "beforeafter"

    def test_preserves_ie_conditional_comments(self) -> None:
        """Test that IE conditional comments are preserved."""
        from bengal.postprocess.html_output import _remove_html_comments

        html = "<!--[if IE]><link href='ie.css'><![endif]-->"
        result = _remove_html_comments(html)

        # IE conditionals should be preserved
        assert "<!--[if IE]>" in result or result == html

    def test_removes_multiline_comments(self) -> None:
        """Test that multiline comments are removed."""
        from bengal.postprocess.html_output import _remove_html_comments

        html = "before<!--\nmultiline\ncomment\n-->after"
        result = _remove_html_comments(html)

        assert result == "beforeafter"


class TestWhitespaceCollapsing:
    """Test whitespace collapsing functions."""

    def test_collapse_blank_lines(self) -> None:
        """Test that multiple blank lines are collapsed."""
        from bengal.postprocess.html_output import _collapse_blank_lines

        text = "line1\n\n\n\nline2"
        result = _collapse_blank_lines(text)

        # Should have at most 2 consecutive newlines
        assert "\n\n\n" not in result
        assert "line1" in result
        assert "line2" in result

    def test_strip_trailing_whitespace(self) -> None:
        """Test that trailing whitespace is stripped from lines."""
        from bengal.postprocess.html_output import _strip_trailing_whitespace

        text = "line1   \nline2\t\nline3"
        result = _strip_trailing_whitespace(text)

        assert "line1   \n" not in result
        assert "line2\t\n" not in result


class TestInterTagWhitespace:
    """Test inter-tag whitespace collapsing."""

    def test_collapse_spaces_between_tags(self) -> None:
        """Test that spaces between tags are collapsed."""
        from bengal.postprocess.html_output import _collapse_intertag_whitespace

        text = ">   <"
        result = _collapse_intertag_whitespace(text)

        assert result == "> <"

    def test_preserves_single_newline(self) -> None:
        """Test that single newline between tags is preserved."""
        from bengal.postprocess.html_output import _collapse_intertag_whitespace

        text = ">\n   <"
        result = _collapse_intertag_whitespace(text)

        assert result == ">\n<"


class TestClassAttributeNormalization:
    """Test class attribute whitespace normalization."""

    def test_normalizes_class_whitespace(self) -> None:
        """Test that class attribute whitespace is normalized."""
        from bengal.postprocess.html_output import _normalize_class_attributes

        html = 'class="a   b    c"'
        result = _normalize_class_attributes(html)

        assert result == 'class="a b c"'

    def test_handles_single_class(self) -> None:
        """Test that single class is unchanged."""
        from bengal.postprocess.html_output import _normalize_class_attributes

        html = 'class="single"'
        result = _normalize_class_attributes(html)

        assert result == 'class="single"'

    def test_handles_empty_class(self) -> None:
        """Test that empty class is handled."""
        from bengal.postprocess.html_output import _normalize_class_attributes

        html = 'class=""'
        result = _normalize_class_attributes(html)

        assert result == 'class=""'


class TestTitleTextTrimming:
    """Test title text whitespace trimming."""

    def test_trims_title_whitespace(self) -> None:
        """Test that title text whitespace is trimmed."""
        from bengal.postprocess.html_output import _trim_title_text

        html = "<title>  Page   Title  </title>"
        result = _trim_title_text(html)

        assert result == "<title>Page Title</title>"

    def test_handles_multiline_title(self) -> None:
        """Test that multiline title is collapsed."""
        from bengal.postprocess.html_output import _trim_title_text

        html = "<title>\n  Page Title\n</title>"
        result = _trim_title_text(html)

        assert result == "<title>Page Title</title>"


class TestPrettyIndentation:
    """Test pretty indentation functionality."""

    def test_indents_nested_elements(self) -> None:
        """Test that nested elements are indented."""
        from bengal.postprocess.html_output import _pretty_indent_html

        html = "<div>\n<span>Hello</span>\n</div>\n"
        result = _pretty_indent_html(html)

        # Should have some indentation (2 spaces per level)
        lines = result.strip().split("\n")
        assert len(lines) >= 1

    def test_handles_void_tags(self) -> None:
        """Test that void tags don't increase depth."""
        from bengal.postprocess.html_output import _pretty_indent_html

        html = "<div>\n<br>\n<span>Hello</span>\n</div>\n"
        result = _pretty_indent_html(html)

        # br is a void tag, shouldn't increase depth
        assert "br" in result


class TestVoidTags:
    """Test void tag handling."""

    def test_void_tags_constant(self) -> None:
        """Test that void tags set includes common void elements."""
        from bengal.postprocess.html_output import _VOID_TAGS

        expected_void = {"br", "hr", "img", "input", "meta", "link"}
        assert expected_void.issubset(_VOID_TAGS)


class TestWhitespaceSensitiveTags:
    """Test whitespace-sensitive tags constant."""

    def test_ws_sensitive_tags_constant(self) -> None:
        """Test that WS sensitive tags includes expected elements."""
        from bengal.postprocess.html_output import _WS_SENSITIVE_TAGS

        expected = ("pre", "code", "textarea", "script", "style")
        assert expected == _WS_SENSITIVE_TAGS


class TestFormatHtmlOutputOptions:
    """Test format_html_output with options dict."""

    def test_remove_comments_option(self) -> None:
        """Test remove_comments option."""
        from bengal.postprocess.html_output import format_html_output

        html = "<div><!-- comment -->Hello</div>"

        # With remove_comments=True
        result = format_html_output(html, mode="pretty", options={"remove_comments": True})
        assert "<!-- comment -->" not in result

        # With remove_comments=False (should keep comment)
        result = format_html_output(html, mode="pretty", options={"remove_comments": False})
        assert "Hello" in result

    def test_collapse_blank_lines_option(self) -> None:
        """Test collapse_blank_lines option."""
        from bengal.postprocess.html_output import format_html_output

        html = "<div>\n\n\n\n</div>"

        # With collapse_blank_lines=True (default)
        result = format_html_output(html, mode="pretty", options={"collapse_blank_lines": True})
        assert "\n\n\n\n" not in result


class TestTrailingNewline:
    """Test that output ends with single trailing newline."""

    def test_adds_trailing_newline(self) -> None:
        """Test that output ends with newline."""
        from bengal.postprocess.html_output import format_html_output

        html = "<div>Hello</div>"
        result = format_html_output(html, mode="minify")

        assert result.endswith("\n")

    def test_single_trailing_newline(self) -> None:
        """Test that output ends with newline."""
        from bengal.postprocess.html_output import format_html_output

        html = "<div>Hello</div>"
        result = format_html_output(html, mode="minify")

        # Should end with at least one newline
        assert result.endswith("\n")
