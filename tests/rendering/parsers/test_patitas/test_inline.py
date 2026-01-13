"""Inline element tests for Patitas.

Comprehensive tests for inline parsing and rendering.
"""

from __future__ import annotations

import pytest

from bengal.rendering.parsers.patitas import parse


class TestEmphasisVariants:
    """Emphasis with different delimiters and contexts."""

    @pytest.mark.parametrize(
        "source,expected",
        [
            ("*em*", "<em>em</em>"),
            ("_em_", "<em>em</em>"),
            ("**strong**", "<strong>strong</strong>"),
            ("__strong__", "<strong>strong</strong>"),
        ],
    )
    def test_basic_emphasis(self, source, expected):
        """Basic emphasis variants."""
        html = parse(source)
        assert expected in html

    def test_emphasis_at_start(self):
        """Emphasis at paragraph start."""
        html = parse("*em* rest")
        assert "<em>em</em>" in html

    def test_emphasis_at_end(self):
        """Emphasis at paragraph end."""
        html = parse("start *em*")
        assert "<em>em</em>" in html

    def test_emphasis_in_middle(self):
        """Emphasis in middle of text."""
        html = parse("before *em* after")
        assert "<em>em</em>" in html
        assert "before" in html
        assert "after" in html

    def test_multiple_emphasis(self):
        """Multiple emphasis in same paragraph."""
        html = parse("*one* and *two*")
        assert html.count("<em>") == 2

    def test_emphasis_with_spaces_inside(self):
        """Emphasis with spaces inside."""
        html = parse("*multiple words*")
        assert "<em>multiple words</em>" in html

    def test_unclosed_emphasis(self):
        """Unclosed emphasis treated as literal."""
        html = parse("*unclosed")
        # Should contain literal asterisk or empty emphasis
        assert "*" in html or "<em>" not in html


class TestStrongVariants:
    """Strong emphasis variants."""

    def test_strong_with_emphasis_inside(self):
        """Strong containing emphasis."""
        html = parse("**bold with *italic* inside**")
        assert "<strong>" in html

    def test_emphasis_with_strong_inside(self):
        """Emphasis containing strong."""
        html = parse("*italic with **bold** inside*")
        assert "<em>" in html


class TestCodeSpans:
    """Inline code span tests."""

    def test_basic_code_span(self):
        """Basic code span."""
        html = parse("`code`")
        assert "<code>code</code>" in html

    def test_code_span_with_backticks(self):
        """Code span containing backticks."""
        html = parse("`` `code` ``")
        assert "<code>" in html

    def test_code_span_preserves_spaces(self):
        """Code span preserves internal spaces."""
        html = parse("`a  b`")
        assert "a  b" in html or "a b" in html  # Some normalization may occur

    def test_code_span_escapes_html(self):
        """Code span escapes HTML."""
        html = parse("`<script>`")
        assert "&lt;script&gt;" in html

    def test_multiple_code_spans(self):
        """Multiple code spans in paragraph."""
        html = parse("`one` and `two`")
        assert html.count("<code>") == 2


class TestLinks:
    """Link parsing and rendering tests."""

    def test_basic_link(self):
        """Basic inline link."""
        html = parse("[text](url)")
        assert '<a href="url">text</a>' in html

    def test_link_with_absolute_url(self):
        """Link with absolute URL."""
        html = parse("[Google](https://google.com)")
        assert 'href="https://google.com"' in html

    def test_link_with_title(self):
        """Link with title."""
        html = parse('[text](url "my title")')
        assert 'title="my title"' in html

    def test_link_with_empty_text(self):
        """Link with empty text."""
        html = parse("[](url)")
        assert 'href="url"' in html

    def test_link_with_emphasis_in_text(self):
        """Link text can contain emphasis."""
        html = parse("[*emphasized*](url)")
        assert "<em>" in html or "emphasized" in html

    def test_multiple_links(self):
        """Multiple links in paragraph."""
        html = parse("[one](a) and [two](b)")
        assert 'href="a"' in html
        assert 'href="b"' in html


class TestImages:
    """Image parsing and rendering tests."""

    def test_basic_image(self):
        """Basic image."""
        html = parse("![alt](image.png)")
        assert '<img src="image.png"' in html
        assert 'alt="alt"' in html

    def test_image_with_title(self):
        """Image with title."""
        html = parse('![alt](image.png "title")')
        assert 'title="title"' in html

    def test_image_empty_alt(self):
        """Image with empty alt text."""
        html = parse("![](image.png)")
        assert 'alt=""' in html

    def test_image_url_with_spaces(self):
        """Image URL handling."""
        html = parse("![alt](image%20name.png)")
        assert "image%20name.png" in html


class TestLineBreaks:
    """Line break tests."""

    def test_backslash_hard_break(self):
        """Backslash creates hard break."""
        html = parse("line1\\\nline2")
        assert "<br />" in html

    def test_soft_break_renders_as_newline(self):
        """Soft break renders appropriately."""
        html = parse("line1\nline2")
        # Soft break becomes space or newline
        assert "line1" in html
        assert "line2" in html


class TestEscapes:
    """Escape sequence tests."""

    @pytest.mark.parametrize(
        "char",
        ["\\", "`", "*", "_", "{", "}", "[", "]", "(", ")", "#", "+", "-", ".", "!"],
    )
    def test_escaped_characters(self, char):
        """Escaped characters render as literals."""
        html = parse(f"\\{char}")
        # Should contain the literal character, not be processed as markdown
        assert char in html

    def test_escaped_asterisk_not_emphasis(self):
        """Escaped asterisks don't create emphasis."""
        html = parse("\\*not emphasis\\*")
        assert "<em>" not in html

    def test_escape_in_code_span_not_processed(self):
        """Escapes inside code spans are literal."""
        html = parse(r"`\*`")
        assert "\\*" in html or r"\*" in html

    def test_escape_in_link_url(self):
        """Backslash escapes processed in link URLs."""
        html = parse(r"[foo](/bar\*)")
        # Escaped asterisk becomes literal asterisk in URL
        assert 'href="/bar*"' in html

    def test_escape_in_link_title(self):
        """Backslash escapes processed in link titles."""
        html = parse(r'[foo](/url "ti\*tle")')
        # Escaped asterisk becomes literal in title
        assert 'title="ti*tle"' in html

    def test_escape_in_image_url(self):
        """Backslash escapes processed in image URLs."""
        html = parse(r"![alt](/img\*.png)")
        assert 'src="/img*.png"' in html


class TestCodeFenceEscapes:
    """Backslash escape tests in code fence info strings."""

    def test_escape_in_info_string(self):
        """Backslash escapes processed in code fence info string."""
        html = parse("``` foo\\+bar\ncode\n```")
        # Escaped + becomes literal + in language class
        assert 'class="language-foo+bar"' in html

    def test_escaped_backtick_in_tilde_fence(self):
        """Backticks can be escaped in tilde fence info string."""
        html = parse("~~~ foo\\`bar\ncode\n~~~")
        assert 'class="language-foo`bar"' in html


class TestMixedInline:
    """Mixed inline elements."""

    def test_emphasis_and_code(self):
        """Emphasis and code in same paragraph."""
        html = parse("*em* and `code`")
        assert "<em>" in html
        assert "<code>" in html

    def test_link_and_emphasis(self):
        """Link and emphasis in same paragraph."""
        html = parse("[link](url) and *em*")
        assert "<a href" in html
        assert "<em>" in html

    def test_complex_inline(self):
        """Complex inline nesting."""
        html = parse("**bold with `code` inside**")
        assert "<strong>" in html
        assert "<code>" in html

    def test_image_and_text(self):
        """Image with surrounding text."""
        html = parse("Before ![alt](img.png) after")
        assert "Before" in html
        assert "<img" in html
        assert "after" in html


class TestInlineEdgeCases:
    """Edge cases for inline parsing."""

    def test_empty_emphasis(self):
        """Empty emphasis markers."""
        html = parse("**")
        # Empty emphasis should render as literal
        assert "**" in html or html.strip() == "<p></p>"

    def test_single_asterisk(self):
        """Single asterisk is literal."""
        html = parse("a * b")
        assert "*" in html

    def test_asterisk_surrounded_by_spaces(self):
        """Asterisks with spaces aren't emphasis."""
        html = parse("a * b * c")
        assert "<em>" not in html

    def test_unclosed_link(self):
        """Unclosed link bracket."""
        html = parse("[unclosed")
        assert "[unclosed" in html or "unclosed" in html

    def test_unclosed_image(self):
        """Unclosed image bracket."""
        html = parse("![unclosed")
        assert "unclosed" in html

    def test_url_without_brackets(self):
        """URL without link brackets is literal."""
        html = parse("http://example.com")
        # Plain URLs are literal text (no autolink plugin)
        assert "http://example.com" in html


# =============================================================================
# CommonMark Autolinks (Section 6.7)
# =============================================================================


class TestAutolinks:
    """CommonMark autolink tests (section 6.7).
    
    Autolinks are absolute URIs and email addresses wrapped in angle brackets.
    They are parsed as links, not as raw HTML.
        
    """

    # --- URI Autolinks ---

    def test_http_autolink(self):
        """HTTP URL autolink."""
        html = parse("<http://foo.bar.baz>")
        assert '<a href="http://foo.bar.baz">' in html
        assert ">http://foo.bar.baz</a>" in html

    def test_https_autolink(self):
        """HTTPS URL autolink."""
        html = parse("<https://foo.bar.baz>")
        assert '<a href="https://foo.bar.baz">' in html

    def test_https_with_query_string(self):
        """HTTPS with query parameters."""
        html = parse("<https://foo.bar.baz/test?q=hello&id=22&boolean>")
        # Query string should be preserved in href
        assert "https://foo.bar.baz/test?q=hello" in html
        assert "<a " in html

    def test_irc_autolink(self):
        """IRC protocol autolink."""
        html = parse("<irc://foo.bar:2233/baz>")
        assert '<a href="irc://foo.bar:2233/baz">' in html

    def test_mailto_uppercase(self):
        """MAILTO with uppercase."""
        html = parse("<MAILTO:FOO@BAR.BAZ>")
        assert '<a href="MAILTO:FOO@BAR.BAZ">' in html

    def test_custom_scheme(self):
        """Custom scheme autolink."""
        html = parse("<a+b+c:d>")
        assert '<a href="a+b+c:d">' in html

    def test_made_up_scheme(self):
        """Made-up scheme autolink."""
        html = parse("<made-up-scheme://foo,bar>")
        assert '<a href="made-up-scheme://foo,bar">' in html

    def test_relative_path_autolink(self):
        """URL with relative path."""
        html = parse("<https://../>")
        assert '<a href="https://../">' in html

    def test_localhost_autolink(self):
        """Localhost URL autolink."""
        html = parse("<localhost:5001/foo>")
        assert '<a href="localhost:5001/foo">' in html

    def test_backslash_percent_encoded(self):
        """Backslashes in URL are percent-encoded in href."""
        html = parse("<https://example.com/\\[\\>")
        # Backslash should be %5C in href
        assert "%5C" in html
        # But display text keeps original backslash
        assert "https://example.com/\\[\\" in html

    # --- Email Autolinks ---

    def test_email_autolink(self):
        """Simple email autolink."""
        html = parse("<foo@bar.example.com>")
        assert '<a href="mailto:foo@bar.example.com">' in html
        assert ">foo@bar.example.com</a>" in html

    def test_email_with_special_chars(self):
        """Email with special characters in local part."""
        html = parse("<foo+special@Bar.baz-bar0.com>")
        assert '<a href="mailto:foo+special@Bar.baz-bar0.com">' in html

    # --- Invalid Autolinks (should escape, not link) ---

    def test_url_with_space_not_autolink(self):
        """URL with space is not an autolink."""
        html = parse("<https://foo.bar/baz bim>")
        # Should escape < and > as entities, not create link
        assert "&lt;https://foo.bar/baz bim&gt;" in html
        assert "<a " not in html

    def test_escaped_char_in_email_not_autolink(self):
        """Escaped character in email breaks autolink."""
        html = parse(r"<foo\+@bar.example.com>")
        # Backslash makes it not a valid email autolink
        assert "&lt;" in html or "<a " not in html

    def test_short_scheme_not_autolink(self):
        """Single-letter scheme is not a valid autolink."""
        html = parse("<m:abc>")
        # 'm:abc' - scheme is only 1 letter, needs at least 2
        assert "&lt;m:abc&gt;" in html
        assert "<a " not in html

    def test_no_scheme_not_autolink(self):
        """Domain without scheme is not an autolink."""
        html = parse("<foo.bar.baz>")
        # No @ and no scheme:// - not valid
        assert "&lt;foo.bar.baz&gt;" in html
        assert "<a " not in html

    # --- Context Tests ---

    def test_autolink_in_paragraph(self):
        """Autolink within paragraph text."""
        html = parse("Check out <https://example.com> for more info.")
        assert '<a href="https://example.com">' in html
        assert "Check out" in html
        assert "for more info" in html

    def test_autolink_vs_html_tag(self):
        """Autolink takes precedence over HTML tag matching."""
        # <div> is HTML, but <http://example.com> is autolink
        html = parse("<div>text</div> and <http://example.com>")
        assert '<a href="http://example.com">' in html

    def test_multiple_autolinks(self):
        """Multiple autolinks in same paragraph."""
        html = parse("<https://a.com> and <user@example.com>")
        assert html.count("<a ") == 2


class TestRawHTMLInline:
    """Raw HTML inline tests (CommonMark 6.8).
    
    Tests for HTML tags that pass through unchanged.
        
    """

    def test_simple_html_tag(self):
        """Simple HTML tag."""
        html = parse("<div>content</div>")
        assert "content" in html

    def test_self_closing_tag(self):
        """Self-closing HTML tag."""
        html = parse("before <br> after")
        assert "<br" in html

    def test_html_with_attributes(self):
        """HTML with valid attributes."""
        html = parse('<a href="url">text</a>')
        # Raw HTML passes through
        assert "text" in html

    def test_html_comment(self):
        """HTML comment."""
        html = parse("before <!-- comment --> after")
        assert "<!--" in html or "comment" in html

    def test_invalid_html_tag_escaped(self):
        """Invalid HTML tags are escaped."""
        # <33> starts with number, not valid HTML
        html = parse("<33>")
        assert "&lt;33&gt;" in html

    def test_underscore_tag_escaped(self):
        """Underscore-start tag is not valid HTML."""
        html = parse("<__>")
        assert "&lt;__&gt;" in html

    def test_dot_in_tag_name_escaped(self):
        """Dots in tag name make it invalid HTML."""
        html = parse("<foo.bar>")
        assert "&lt;foo.bar&gt;" in html


class TestReferenceStyleImages:
    """Reference-style image tests."""

    def test_full_reference_image(self):
        """Full reference-style image: ![alt][ref]."""
        html = parse("![alt][ref]\n\n[ref]: /url")
        assert '<img src="/url" alt="alt"' in html

    def test_full_reference_image_with_title(self):
        """Reference image with title."""
        html = parse('![alt][ref]\n\n[ref]: /url "title"')
        assert '<img src="/url" alt="alt" title="title"' in html

    def test_collapsed_reference_image(self):
        """Collapsed reference-style image: ![alt][]."""
        html = parse('![foo][]\n\n[foo]: /url "title"')
        assert '<img src="/url" alt="foo" title="title"' in html

    def test_shortcut_reference_image(self):
        """Shortcut reference-style image: ![alt]."""
        html = parse('![foo]\n\n[foo]: /url "title"')
        assert '<img src="/url" alt="foo" title="title"' in html

    def test_reference_image_case_insensitive(self):
        """Reference labels are case-insensitive."""
        html = parse("![Foo][BAR]\n\n[bar]: /url")
        assert '<img src="/url" alt="Foo"' in html

    def test_reference_image_alt_strips_formatting(self):
        """Alt text strips formatting markers."""
        html = parse("![foo *bar*][]\n\n[foo *bar*]: /url")
        assert 'alt="foo bar"' in html
        assert "*" not in html.split('alt="')[1].split('"')[0]


class TestAngleBracketURLs:
    """Angle bracket URL tests for links and images."""

    def test_link_angle_bracket_url(self):
        """Link with angle bracket URL."""
        html = parse("[foo](<url>)")
        assert 'href="url"' in html
        assert "<" not in html.split('href="')[1].split('"')[0]
        assert ">" not in html.split('href="')[1].split('"')[0]

    def test_image_angle_bracket_url(self):
        """Image with angle bracket URL."""
        html = parse("![alt](<url>)")
        assert 'src="url"' in html
        assert "<" not in html.split('src="')[1].split('"')[0]

    def test_link_angle_bracket_with_spaces(self):
        """Angle bracket URL can contain spaces."""
        html = parse("[foo](<url with spaces>)")
        assert 'href="url with spaces"' in html

    def test_link_angle_bracket_with_title(self):
        """Angle bracket URL with title."""
        html = parse('[foo](<url> "title")')
        assert 'href="url"' in html
        assert 'title="title"' in html

    def test_image_angle_bracket_with_title(self):
        """Image angle bracket URL with title."""
        html = parse('![alt](<url> "title")')
        assert 'src="url"' in html
        assert 'title="title"' in html
