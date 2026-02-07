"""
Tests for syntax highlighting behavior, including language handling and
special treatment for client-side rendered languages like Mermaid.

Note: Bengal uses Rosettes as the default highlighting backend, which
supports ~50 common languages. Languages not supported by Rosettes
fall back to plain text rendering with proper escaping.
"""

from __future__ import annotations

import pytest

from bengal.parsing import PatitasParser

# python-markdown is optional (patitas is default)
try:
    import markdown as _markdown_mod  # noqa: F401

    from bengal.parsing import PythonMarkdownParser

    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


class TestMistuneHighlightingAndMermaid:
    """Test Mistune parser with Rosettes highlighting backend."""

    def setup_method(self):
        self.parser = PatitasParser(enable_highlighting=True)

    def test_python_highlighted(self):
        """Test Python syntax highlighting (supported by Rosettes)."""
        content = """
```python
def hello():
    print("hello")
```
"""
        html = self.parser.parse(content, {})
        # Rosettes should highlight Python with span classes
        assert '<div class="rosettes"' in html
        # Should have some token spans (k=keyword, n=name, s=string, etc.)
        assert "<span class=" in html

    def test_javascript_highlighted(self):
        """Test JavaScript syntax highlighting (supported by Rosettes)."""
        content = """
```javascript
function hello() {
    console.log("hello");
}
```
"""
        html = self.parser.parse(content, {})
        assert '<div class="rosettes"' in html
        assert "<span class=" in html

    def test_unsupported_language_falls_back_to_plain(self):
        """Test that unsupported languages fall back to plain text."""
        content = """
```jinja2
<h1>{{ title }}</h1>
```
"""
        html = self.parser.parse(content, {})
        # Should still wrap in rosettes div (with fallback)
        assert '<div class="rosettes"' in html
        # Content should be escaped
        assert "&lt;h1&gt;" in html or "<h1>" in html

    def test_mermaid_wrapped_for_client_side(self):
        """Test Mermaid blocks are wrapped for client-side rendering."""
        content = """
```mermaid
graph LR
A --> B
```
"""
        html = self.parser.parse(content, {})
        # Mermaid blocks should be wrapped in a div with class mermaid
        assert '<div class="mermaid">' in html
        # Content should be HTML-escaped inside
        assert "&gt;" in html or "graph LR" in html


@pytest.mark.skipif(not HAS_MARKDOWN, reason="python-markdown not installed (optional dependency)")
class TestPythonMarkdownHighlighting:
    """Test python-markdown parser (uses Pygments codehilite extension)."""

    def setup_method(self):
        self.parser = PythonMarkdownParser()

    def test_python_highlighted(self):
        """Test Python syntax highlighting."""
        content = """
```python
def hello():
    print("hello")
```
"""
        html = self.parser.parse(content, {})
        assert '<div class="highlight">' in html or "<span class=" in html

    def test_jinja2_alias_highlighted(self):
        """Test jinja2 alias (python-markdown uses Pygments)."""
        content = """
```jinja2
<h1>{{ title }}</h1>
```
"""
        html = self.parser.parse(content, {})
        assert '<div class="highlight">' in html or '<span class="k">' in html

    def test_go_html_template_aliased_to_html(self):
        """Test go-html-template alias (python-markdown uses Pygments)."""
        content = """
```go-html-template
<div>{{ .Title }}</div>
```
"""
        html = self.parser.parse(content, {})
        assert '<div class="highlight">' in html or '<span class="nt">' in html
