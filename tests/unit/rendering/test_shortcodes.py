"""Unit tests for template shortcode expansion."""

from __future__ import annotations

from unittest.mock import MagicMock

from bengal.rendering.shortcodes import (
    _deindent,
    _parse_args,
    expand_shortcodes,
    has_shortcode,
)
from bengal.utils.shortcodes import shortcodes_used_in_content


class TestParseArgs:
    """Tests for shortcode argument parsing."""

    def test_empty_args(self) -> None:
        """Empty args return empty params."""
        p = _parse_args("")
        assert p.named == {}
        assert p.positional == []

    def test_positional_args(self) -> None:
        """Positional args are parsed."""
        p = _parse_args("foo bar baz")
        assert p.positional == ["foo", "bar", "baz"]
        assert p.named == {}

    def test_named_args(self) -> None:
        """Named args are parsed."""
        p = _parse_args('src=/audio/test.mp3 title="My Audio"')
        assert p.named == {"src": "/audio/test.mp3", "title": "My Audio"}
        assert p.positional == []

    def test_get_positional(self) -> None:
        """Get by index returns positional arg."""
        p = _parse_args("a b c")
        assert p.get(0) == "a"
        assert p.get(1) == "b"
        assert p.get(2) == "c"
        assert p.get(3) == ""
        assert p.get(3, "default") == "default"

    def test_get_named(self) -> None:
        """Get by name returns named arg."""
        p = _parse_args('key=value foo="bar baz"')
        assert p.get("key") == "value"
        assert p.get("foo") == "bar baz"
        assert p.get("missing") == ""

    def test_get_int(self) -> None:
        """GetInt coerces to int."""
        p = _parse_args("width=300 count=0")
        assert p.get_int("width") == 300
        assert p.get_int("count") == 0
        assert p.get_int("missing", 42) == 42
        assert p.get_int("bad", 1) == 1

    def test_get_bool(self) -> None:
        """GetBool coerces true/false, 1/0."""
        p = _parse_args("enabled=true disabled=false one=1 zero=0")
        assert p.get_bool("enabled") is True
        assert p.get_bool("disabled") is False
        assert p.get_bool("one") is True
        assert p.get_bool("zero") is False
        assert p.get_bool("missing", True) is True


class TestDeindent:
    """Tests for _deindent helper."""

    def test_no_indent_unchanged(self) -> None:
        """Content without indent is unchanged."""
        assert _deindent("foo\nbar") == "foo\nbar"

    def test_strips_common_indent(self) -> None:
        """Common leading indent is stripped."""
        text = "  line1\n  line2\n  line3"
        assert _deindent(text) == "line1\nline2\nline3"

    def test_empty_lines_preserved(self) -> None:
        """Empty lines don't affect indent calculation."""
        text = "  a\n\n  b"
        assert _deindent(text) == "a\n\nb"


class TestExpandShortcodes:
    """Tests for shortcode expansion in content."""

    def test_no_shortcodes_passthrough(self) -> None:
        """Content without shortcodes is unchanged."""
        engine = MagicMock()
        page = MagicMock()
        page.source_path = "test.md"
        site = MagicMock()
        site.config = {}
        site.xref_index = {}
        content = "Plain markdown **bold** text."
        result = expand_shortcodes(content, engine, page, site)
        assert result == content
        engine.template_exists.assert_not_called()

    def test_unknown_shortcode_left_as_is(self) -> None:
        """Unknown shortcode (no template) is left as-is."""
        engine = MagicMock()
        engine.template_exists.return_value = False
        page = MagicMock()
        page.source_path = "test.md"
        site = MagicMock()
        site.config = {}
        site.xref_index = {}
        content = "Before {{< unknown-xyz >}} after"
        result = expand_shortcodes(content, engine, page, site)
        assert result == content
        engine.template_exists.assert_called_with("shortcodes/unknown-xyz.html")

    def test_known_shortcode_expanded(self) -> None:
        """Known shortcode is replaced with template output."""
        engine = MagicMock()
        engine.template_exists.return_value = True
        engine.render_template.return_value = '<audio src="/audio/test.mp3"></audio>'
        page = MagicMock()
        page.source_path = "test.md"
        site = MagicMock()
        site.config = {}
        site.xref_index = {}
        content = "Listen: {{< audio src=/audio/test.mp3 >}}"
        result = expand_shortcodes(content, engine, page, site)
        assert "Listen: " in result
        assert '<audio src="/audio/test.mp3"></audio>' in result
        assert "{{<" not in result
        engine.render_template.assert_called_once()
        call_args = engine.render_template.call_args
        assert call_args[0][0] == "shortcodes/audio.html"
        ctx = call_args[0][1]
        assert "page" in ctx
        assert "site" in ctx
        assert ctx["shortcode"].Get("src") == "/audio/test.mp3"

    def test_paired_shortcode_with_inner(self) -> None:
        """Paired shortcode passes inner content to template."""
        engine = MagicMock()
        engine.template_exists.return_value = True
        engine.render_template.return_value = "<blockquote>Quote text</blockquote>"
        page = MagicMock()
        page.source_path = "test.md"
        site = MagicMock()
        site.config = {}
        site.xref_index = {}
        content = "{{< blockquote author=Jane >}}Quote text{{< /blockquote >}}"
        result = expand_shortcodes(content, engine, page, site)
        assert "<blockquote>Quote text</blockquote>" in result
        call_args = engine.render_template.call_args
        ctx = call_args[0][1]
        assert ctx["Inner"] == "Quote text"
        assert ctx["shortcode"].Get("author") == "Jane"

    def test_markdown_notation_parses_inner(self) -> None:
        """{{% %}} notation parses inner content as Markdown when parse_markdown provided."""
        engine = MagicMock()
        engine.template_exists.return_value = True
        engine.render_template.return_value = "<blockquote>parsed</blockquote>"
        page = MagicMock()
        page.source_path = "test.md"
        site = MagicMock()
        site.config = {}
        site.xref_index = {}
        content = "{{% blockquote author=Jane %}}**Bold** text{{% /blockquote %}}"

        def parse_markdown(s: str) -> str:
            return s.replace("**Bold**", "<strong>Bold</strong>")

        expand_shortcodes(content, engine, page, site, parse_markdown=parse_markdown)
        call_args = engine.render_template.call_args
        ctx = call_args[0][1]
        assert ctx["Inner"] == "<strong>Bold</strong> text"

    def test_standard_notation_passes_inner_raw(self) -> None:
        """{{< >}} notation passes inner content raw (no Markdown parsing)."""
        engine = MagicMock()
        engine.template_exists.return_value = True
        engine.render_template.return_value = "<blockquote>raw</blockquote>"
        page = MagicMock()
        page.source_path = "test.md"
        site = MagicMock()
        site.config = {}
        site.xref_index = {}
        content = "{{< blockquote >}}**Bold** raw{{< /blockquote >}}"

        def parse_markdown(s: str) -> str:
            return s.replace("**", "<b>")  # Would change if parsed

        expand_shortcodes(content, engine, page, site, parse_markdown=parse_markdown)
        call_args = engine.render_template.call_args
        ctx = call_args[0][1]
        assert ctx["Inner"] == "**Bold** raw"

    def test_nested_shortcode_has_parent(self) -> None:
        """Nested shortcode receives Parent context from outer shortcode."""
        engine = MagicMock()
        engine.template_exists.return_value = True

        def render_shortcode(template_name: str, context: dict) -> str:
            shortcode = context["shortcode"]
            if "gallery" in template_name:
                return shortcode.Inner
            if "img" in template_name:
                parent = shortcode.Parent
                cls = parent.Get("class") if parent else ""
                return f'<img src="{shortcode.Get("src")}" class="{cls}">'
            return ""

        engine.render_template.side_effect = render_shortcode
        page = MagicMock()
        page.source_path = "test.md"
        site = MagicMock()
        site.config = {}
        site.xref_index = {}
        content = "{{< gallery class=thumbnails >}}{{< img src=cat.jpg >}}{{< /gallery >}}"
        result = expand_shortcodes(content, engine, page, site)
        assert '<img src="cat.jpg" class="thumbnails">' in result

    def test_shortcodes_used_in_content(self) -> None:
        """shortcodes_used_in_content extracts shortcode names."""
        content = "{{< audio src=x >}} {{% blockquote %}}x{{% /blockquote %}}"
        names = shortcodes_used_in_content(content)
        assert "audio" in names
        assert "blockquote" in names

    def test_has_shortcode(self) -> None:
        """has_shortcode returns True when page uses the shortcode."""
        page = MagicMock()
        page._source = "Text {{< tip >}}Hint{{< /tip >}} more"
        assert has_shortcode(page, "tip") is True
        assert has_shortcode(page, "audio") is False
