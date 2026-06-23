"""
Tests for code processing utilities.
"""

from bengal.utils.primitives.code import (
    HL_LINES_PATTERN,
    CodeFenceAttrs,
    parse_code_info,
    parse_fence_attrs,
    parse_hl_lines,
)


class TestParseHlLines:
    """Tests for parse_hl_lines function."""

    def test_single_line(self):
        """Test single line specification."""
        assert parse_hl_lines("5") == [5]
        assert parse_hl_lines("1") == [1]
        assert parse_hl_lines("100") == [100]

    def test_multiple_lines(self):
        """Test comma-separated lines."""
        assert parse_hl_lines("1,3,5") == [1, 3, 5]
        assert parse_hl_lines("1, 3, 5") == [1, 3, 5]  # With spaces
        assert parse_hl_lines("10,20,30") == [10, 20, 30]

    def test_range(self):
        """Test range specification."""
        assert parse_hl_lines("1-3") == [1, 2, 3]
        assert parse_hl_lines("5-7") == [5, 6, 7]
        assert parse_hl_lines("1-1") == [1]  # Single element range

    def test_mixed(self):
        """Test mixed single lines and ranges."""
        assert parse_hl_lines("1,3-5,7") == [1, 3, 4, 5, 7]
        assert parse_hl_lines("1-3,5,7-9") == [1, 2, 3, 5, 7, 8, 9]

    def test_deduplication(self):
        """Test that duplicates are removed."""
        assert parse_hl_lines("1,1,2,2") == [1, 2]
        assert parse_hl_lines("1-3,2-4") == [1, 2, 3, 4]  # Overlapping ranges

    def test_sorted_output(self):
        """Test that output is sorted."""
        assert parse_hl_lines("5,1,3") == [1, 3, 5]
        assert parse_hl_lines("10,1,5") == [1, 5, 10]

    def test_empty_string(self):
        """Test empty string."""
        assert parse_hl_lines("") == []

    def test_invalid_input(self):
        """Test invalid input is gracefully handled."""
        assert parse_hl_lines("invalid") == []
        assert parse_hl_lines("abc") == []
        assert parse_hl_lines("1,abc,3") == [1, 3]  # Invalid parts skipped

    def test_invalid_range(self):
        """Test invalid range format."""
        assert parse_hl_lines("a-b") == []
        assert parse_hl_lines("1-") == []  # Incomplete range
        assert parse_hl_lines("-3") == []  # Incomplete range

    def test_whitespace_handling(self):
        """Test whitespace in specification."""
        assert parse_hl_lines(" 1 , 2 , 3 ") == [1, 2, 3]
        assert parse_hl_lines("1 - 3") == [1, 2, 3]


class TestParseCodeInfo:
    """Tests for parse_code_info function."""

    def test_language_only(self):
        """Test language-only info string."""
        assert parse_code_info("python") == ("python", [])
        assert parse_code_info("javascript") == ("javascript", [])
        assert parse_code_info("rust") == ("rust", [])

    def test_language_with_highlights(self):
        """Test language with line highlights."""
        assert parse_code_info("python {1,3}") == ("python", [1, 3])
        assert parse_code_info("javascript {1-3,5}") == ("javascript", [1, 2, 3, 5])

    def test_empty_string(self):
        """Test empty string."""
        assert parse_code_info("") == ("", [])

    def test_whitespace_handling(self):
        """Test whitespace handling."""
        assert parse_code_info("  python  ") == ("python", [])
        assert parse_code_info("python  {1,2}") == ("python", [1, 2])

    def test_no_highlights_in_braces(self):
        """Test empty braces."""
        assert parse_code_info("python {}") == ("python", [])

    def test_language_with_special_chars(self):
        """Test language names with special characters."""
        assert parse_code_info("c++") == ("c++", [])
        assert parse_code_info("c#") == ("c#", [])


class TestParseFenceAttrs:
    """Tests for parse_fence_attrs."""

    def test_title_and_highlights(self):
        attrs = parse_fence_attrs('python title="app.py" {1,3}')
        assert attrs == CodeFenceAttrs(
            language="python",
            hl_lines=(1, 3),
            title="app.py",
            diff=False,
            show_linenos=False,
            frame="editor",
        )
        assert attrs.highlight_language == "python"

    def test_diff_flag(self):
        attrs = parse_fence_attrs("python diff")
        assert attrs.diff is True
        assert attrs.highlight_language == "diff"

    def test_diff_language(self):
        attrs = parse_fence_attrs("diff")
        assert attrs.language == "diff"
        assert attrs.highlight_language == "diff"

    def test_linenos(self):
        attrs = parse_fence_attrs("python linenos")
        assert attrs.show_linenos is True

    def test_title_after_braces(self):
        attrs = parse_fence_attrs('python {2} title="late-title.py"')
        assert attrs.title == "late-title.py"
        assert attrs.hl_lines == (2,)

    def test_frame_terminal(self):
        attrs = parse_fence_attrs('bash frame=terminal title="deploy.sh"')
        assert attrs.frame == "terminal"
        assert attrs.language == "bash"

    def test_implicit_terminal_frame_for_shell(self):
        attrs = parse_fence_attrs("bash")
        assert attrs.frame == "terminal"

    def test_implicit_editor_frame_for_code(self):
        attrs = parse_fence_attrs("python")
        assert attrs.frame == "editor"

    def test_implicit_editor_frame_for_html(self):
        attrs = parse_fence_attrs("html")
        assert attrs.frame == "editor"

    def test_editor_frame(self):
        attrs = parse_fence_attrs('python frame=editor title="app.py"')
        assert attrs.frame == "editor"

    def test_collapsible_open(self):
        attrs = parse_fence_attrs("python collapse")
        assert attrs.collapsible is True
        assert attrs.collapsed is False

    def test_collapsible_closed(self):
        attrs = parse_fence_attrs("python collapse=closed")
        assert attrs.collapsible is True
        assert attrs.collapsed is True

    def test_annotations(self):
        attrs = parse_fence_attrs('python annotate="1:Setup,3:Run"')
        assert attrs.annotations == ((1, "Setup"), (3, "Run"))


class TestHlLinesPattern:
    """Tests for the HL_LINES_PATTERN regex."""

    def test_pattern_matches_language_only(self):
        """Test pattern matches language-only strings."""
        match = HL_LINES_PATTERN.match("python")
        assert match is not None
        assert match.group(1) == "python"
        assert match.group(2) is None

    def test_pattern_matches_with_highlights(self):
        """Test pattern matches language with highlights."""
        match = HL_LINES_PATTERN.match("python {1,3-5}")
        assert match is not None
        assert match.group(1) == "python"
        assert match.group(2) == "1,3-5"

    def test_pattern_no_match_empty(self):
        """Test pattern doesn't match empty string."""
        match = HL_LINES_PATTERN.match("")
        assert match is None
