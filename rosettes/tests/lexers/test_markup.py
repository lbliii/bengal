"""Markup language lexer tests (HTML, CSS, Markdown, XML)."""

from rosettes import tokenize


class TestHtmlLexer:
    """HTML-specific tests."""

    def test_doctype(self) -> None:
        """Tokenizes DOCTYPE."""
        code = "<!DOCTYPE html>"
        tokens = tokenize(code, "html")
        preprocs = [t for t in tokens if t.type.value == "cp"]
        assert len(preprocs) == 1

    def test_comment(self) -> None:
        """Tokenizes HTML comments."""
        code = "<!-- comment -->"
        tokens = tokenize(code, "html")
        comments = [t for t in tokens if t.type.value == "cm"]
        assert len(comments) == 1

    def test_entity(self) -> None:
        """Tokenizes HTML entities."""
        code = "<p>&nbsp;&copy;</p>"
        tokens = tokenize(code, "html")
        entities = [t for t in tokens if t.type.value == "ni"]
        assert len(entities) >= 2

    def test_attribute_names(self) -> None:
        """Tokenizes attribute names correctly."""
        code = '<div class="container" id="main">'
        tokens = tokenize(code, "html")
        attrs = [t for t in tokens if t.type.value == "na"]
        attr_values = {t.value for t in attrs}
        assert "class" in attr_values
        assert "id" in attr_values

    def test_attribute_values_double_quoted(self) -> None:
        """Tokenizes double-quoted attribute values."""
        code = '<a href="/path/to/page">'
        tokens = tokenize(code, "html")
        strings = [t for t in tokens if t.type.value == "s2"]
        assert len(strings) == 1
        assert '"/path/to/page"' in strings[0].value

    def test_attribute_values_single_quoted(self) -> None:
        """Tokenizes single-quoted attribute values."""
        code = "<a href='/path'>"
        tokens = tokenize(code, "html")
        strings = [t for t in tokens if t.type.value == "s1"]
        assert len(strings) == 1

    def test_self_closing_tags(self) -> None:
        """Tokenizes self-closing tags."""
        code = '<img src="photo.jpg" alt="Photo"/>'
        tokens = tokenize(code, "html")
        tags = [t for t in tokens if t.type.value == "nt"]
        assert any("<img" in t.value for t in tags)
        assert any("/>" in t.value for t in tags)

    def test_multiple_attributes(self) -> None:
        """Tokenizes multiple attributes on a tag."""
        code = '<input type="text" name="email" placeholder="Enter email" required>'
        tokens = tokenize(code, "html")
        attrs = [t for t in tokens if t.type.value == "na"]
        strings = [t for t in tokens if t.type.value == "s2"]
        assert len(attrs) >= 4
        assert len(strings) >= 3

    def test_nested_tags(self) -> None:
        """Tokenizes nested HTML structure."""
        code = '<div><span class="inner">Text</span></div>'
        tokens = tokenize(code, "html")
        tags = [t for t in tokens if t.type.value == "nt"]
        assert len(tags) >= 4

    def test_data_attributes(self) -> None:
        """Tokenizes data-* attributes."""
        code = '<div data-id="123" data-name="test">'
        tokens = tokenize(code, "html")
        attrs = [t for t in tokens if t.type.value == "na"]
        attr_values = {t.value for t in attrs}
        assert "data-id" in attr_values
        assert "data-name" in attr_values


class TestCssLexer:
    """CSS-specific tests."""

    def test_id_selector(self) -> None:
        """Tokenizes ID selectors."""
        code = "#main { color: red; }"
        tokens = tokenize(code, "css")
        vars = [t for t in tokens if t.type.value == "nv"]
        assert any("#main" in t.value for t in vars)

    def test_at_rule(self) -> None:
        """Tokenizes at-rules."""
        code = "@media (min-width: 768px) {}"
        tokens = tokenize(code, "css")
        keywords = [t for t in tokens if t.type.value == "k"]
        assert any("@media" in t.value for t in keywords)

    def test_pseudo_class(self) -> None:
        """Tokenizes pseudo-classes."""
        code = "a:hover { color: blue; }"
        tokens = tokenize(code, "css")
        pseudos = [t for t in tokens if t.type.value == "kp"]
        assert any(":hover" in t.value for t in pseudos)

    def test_class_selector(self) -> None:
        """Tokenizes class selectors."""
        code = ".container { margin: 0 auto; }"
        tokens = tokenize(code, "css")
        classes = [t for t in tokens if t.type.value == "nc"]
        assert any(".container" in t.value for t in classes)

    def test_property_values(self) -> None:
        """Tokenizes property names and values."""
        code = "body { font-size: 16px; color: #333; }"
        tokens = tokenize(code, "css")
        names = [t for t in tokens if t.type.value == "nt"]
        name_values = {t.value for t in names}
        assert "font-size" in name_values
        assert "color" in name_values

    def test_color_values(self) -> None:
        """Tokenizes color values."""
        code = ".box { background: #ff0000; border-color: rgb(0, 128, 255); }"
        tokens = tokenize(code, "css")
        values = [t.value for t in tokens]
        assert any("#ff0000" in v for v in values)

    def test_css_variables(self) -> None:
        """Tokenizes CSS custom properties."""
        code = ":root { --primary-color: blue; }\n.btn { color: var(--primary-color); }"
        tokens = tokenize(code, "css")
        values = [t.value for t in tokens]
        assert any("--primary-color" in v for v in values)

    def test_keyframes(self) -> None:
        """Tokenizes keyframes."""
        code = "@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }"
        tokens = tokenize(code, "css")
        keywords = [t for t in tokens if t.type.value == "k"]
        assert any("@keyframes" in t.value for t in keywords)

    def test_combinators(self) -> None:
        """Tokenizes combinators."""
        code = "div > p { margin: 0; }\ndiv + p { padding: 0; }"
        tokens = tokenize(code, "css")
        values = [t.value for t in tokens]
        assert ">" in values
        assert "+" in values

    def test_important(self) -> None:
        """Tokenizes !important."""
        code = ".override { color: red !important; }"
        tokens = tokenize(code, "css")
        values = [t.value for t in tokens]
        assert any("!important" in v for v in values)


class TestMarkdownLexer:
    """Markdown-specific tests."""

    def test_headings(self) -> None:
        """Tokenizes headings."""
        code = "# Heading 1\n## Heading 2"
        tokens = tokenize(code, "markdown")
        headings = [t for t in tokens if t.type.value == "gh"]
        assert len(headings) >= 2

    def test_code_block(self) -> None:
        """Tokenizes fenced code blocks."""
        code = "```python\nprint('hello')\n```"
        tokens = tokenize(code, "markdown")
        code_blocks = [t for t in tokens if t.type.value == "sb"]
        assert len(code_blocks) >= 1

    def test_emphasis(self) -> None:
        """Tokenizes emphasis."""
        code = "This is **bold** and *italic*"
        tokens = tokenize(code, "markdown")
        strong = [t for t in tokens if t.type.value == "gs"]
        emph = [t for t in tokens if t.type.value == "ge"]
        assert len(strong) >= 1
        assert len(emph) >= 1

    def test_link(self) -> None:
        """Tokenizes links."""
        code = "[text](https://example.com)"
        tokens = tokenize(code, "markdown")
        attrs = [t for t in tokens if t.type.value == "na"]
        assert len(attrs) >= 1


class TestXmlLexer:
    """XML-specific tests."""

    def test_declaration(self) -> None:
        """Tokenizes XML declaration."""
        code = '<?xml version="1.0" encoding="UTF-8"?>'
        tokens = tokenize(code, "xml")
        preprocs = [t for t in tokens if t.type.value == "cp"]
        assert len(preprocs) >= 1

    def test_cdata(self) -> None:
        """Tokenizes CDATA sections."""
        code = "<![CDATA[raw content]]>"
        tokens = tokenize(code, "xml")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 1

    def test_entity(self) -> None:
        """Tokenizes entity references."""
        code = "<text>&lt;&gt;&amp;</text>"
        tokens = tokenize(code, "xml")
        entities = [t for t in tokens if t.type.value == "ni"]
        assert len(entities) >= 3

    def test_attribute(self) -> None:
        """Tokenizes attributes."""
        code = '<element attr="value"/>'
        tokens = tokenize(code, "xml")
        values = [t.value for t in tokens]
        assert "attr" in values or any("attr" in v for v in values)


class TestDiffLexer:
    """Diff-specific tests."""

    def test_added_lines(self) -> None:
        """Tokenizes added lines."""
        code = "+new line\n-old line"
        tokens = tokenize(code, "diff")
        inserted = [t for t in tokens if t.type.value == "gi"]
        assert len(inserted) >= 1

    def test_removed_lines(self) -> None:
        """Tokenizes removed lines."""
        code = "-removed\n+added"
        tokens = tokenize(code, "diff")
        deleted = [t for t in tokens if t.type.value == "gd"]
        assert len(deleted) >= 1

    def test_hunk_header(self) -> None:
        """Tokenizes hunk headers."""
        code = "@@ -1,3 +1,4 @@"
        tokens = tokenize(code, "diff")
        subheadings = [t for t in tokens if t.type.value == "gu"]
        assert len(subheadings) == 1
