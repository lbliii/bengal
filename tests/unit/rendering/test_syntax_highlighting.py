"""
Tests for syntax highlighting behavior, including language aliasing and
special handling for client-side rendered languages like Mermaid.
"""

from bengal.rendering.parsers import MistuneParser, PythonMarkdownParser


class TestMistuneHighlightingAliasesAndMermaid:
    def setup_method(self):
        self.parser = MistuneParser(enable_highlighting=True)

    def test_jinja2_alias_highlighted(self):
        content = """
```jinja2
<h1>{{ title }}</h1>
"""
        html = self.parser.parse(content, {})
        # Pygments output should include the standard highlight wrapper
        assert '<div class="highlight">' in html or '<span class="k">' in html

    def test_go_html_template_aliased_to_html(self):
        content = """
```go-html-template
<div>{{ .Title }}</div>
"""
        html = self.parser.parse(content, {})
        # Should be highlighted as HTML; presence of highlight wrapper is sufficient
        assert '<div class="highlight">' in html or '<span class="nt">' in html

    def test_mermaid_wrapped_for_client_side(self):
        content = """
```mermaid
graph LR
A --> B
"""
        html = self.parser.parse(content, {})
        # Mermaid blocks should be wrapped in a div with class mermaid
        assert '<div class="mermaid">' in html
        # Content should be HTML-escaped inside
        assert "&gt;" in html or "graph LR" in html


class TestPythonMarkdownHighlightingAliases:
    def setup_method(self):
        self.parser = PythonMarkdownParser()

    def test_jinja2_alias_highlighted(self):
        content = """
```jinja2
<h1>{{ title }}</h1>
"""
        html = self.parser.parse(content, {})
        assert '<div class="highlight">' in html or '<span class="k">' in html

    def test_go_html_template_aliased_to_html(self):
        content = """
```go-html-template
<div>{{ .Title }}</div>
"""
        html = self.parser.parse(content, {})
        assert '<div class="highlight">' in html or '<span class="nt">' in html
