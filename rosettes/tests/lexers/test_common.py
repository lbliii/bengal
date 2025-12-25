"""Common tests for all Rosettes lexers.

Tests that all supported languages tokenize correctly and produce valid output.
"""

import pytest

from rosettes import highlight, list_languages, supports_language, tokenize


class TestAllLanguages:
    """Test all supported languages produce valid output."""

    @pytest.mark.parametrize(
        "language,code,expected_token_type",
        [
            # Core languages
            ("python", "def foo(): pass", "kd"),
            ("javascript", "const x = 1;", "kd"),
            ("typescript", "interface Foo {}", "kd"),
            ("json", '{"key": "value"}', "s"),
            ("json", '{"num": 42}', "m"),
            ("yaml", "key: value", "na"),
            ("toml", "[section]", "nc"),
            ("bash", "echo hello", "nb"),
            ("html", "<div>content</div>", "nt"),
            ("css", ".class { color: red; }", "nc"),
            ("diff", "+added line", "gi"),
            # Systems languages
            ("rust", "fn main() {}", "kd"),
            ("go", "func main() {}", "kd"),
            ("c", "int main() {}", "kt"),
            ("cpp", "class Foo {};", "kd"),
            ("java", "public class Main {}", "kd"),
            # Other languages
            ("sql", "SELECT * FROM users", "k"),
            ("markdown", "# Heading", "gh"),
            ("xml", "<root>content</root>", "nt"),
            ("ruby", "def foo; end", "kd"),
            ("php", "<?php echo $x; ?>", "nv"),
            # Template languages
            ("myst", ":::{note}\nContent\n:::", "k"),
            ("jinja2", "{% if x %}{{ y }}{% endif %}", "k"),
            ("liquid", "{% for x in items %}", "k"),
            ("handlebars", "{{#if x}}{{/if}}", "k"),
            ("nunjucks", "{% for x in items %}", "k"),
            ("twig", "{% for x in items %}", "k"),
            # Markup languages
            ("scss", "$color: #fff; .class { }", "nv"),
            ("rst", ".. note::\n   Content", "k"),
            ("latex", "\\section{Title}", "k"),
            ("asciidoc", "= Title\n\nNOTE: text", "k"),
            # Other
            ("http", "GET /api HTTP/1.1", "k"),
            ("regex", "^\\d+$", "k"),
            ("svelte", "{#if condition}", "k"),
            ("ocaml", "let x = 1", "k"),
            ("awk", "BEGIN { print }", "k"),
            ("wasm", "(module (func))", "k"),
            ("fish", "function greet; echo hi; end", "k"),
            ("prisma", "model User { id Int @id }", "k"),
            ("cypher", "MATCH (n) RETURN n", "k"),
            ("jsonnet", "local x = 1;", "k"),
            ("vue", "<template>{{ msg }}</template>", "nt"),
            ("mermaid", "graph TD\n  A --> B", "kd"),
        ],
    )
    def test_language_tokenizes(self, language: str, code: str, expected_token_type: str) -> None:
        """Each language produces tokens with expected types."""
        tokens = tokenize(code, language)
        assert len(tokens) > 0
        token_types = {t.type.value for t in tokens}
        assert expected_token_type in token_types, (
            f"Expected {expected_token_type} in {token_types} for {language}"
        )

    @pytest.mark.parametrize("language", list_languages())
    def test_language_highlights(self, language: str) -> None:
        """Each language produces HTML output."""
        code = "test code"
        html = highlight(code, language, css_class_style="pygments")
        assert '<div class="highlight">' in html
        assert "test" in html or "code" in html


class TestLanguageAliases:
    """Test that language aliases resolve correctly."""

    @pytest.mark.parametrize(
        "alias,canonical",
        [
            # Python
            ("py", "python"),
            ("py3", "python"),
            # JavaScript/TypeScript
            ("js", "javascript"),
            ("ts", "typescript"),
            # Config formats
            ("yml", "yaml"),
            # Shell
            ("sh", "bash"),
            ("shell", "bash"),
            # Markup
            ("htm", "html"),
            ("svg", "xml"),
            ("md", "markdown"),
            # Diff
            ("patch", "diff"),
            # Systems languages
            ("rs", "rust"),
            ("golang", "go"),
            ("h", "c"),
            ("c++", "cpp"),
            ("cxx", "cpp"),
            ("rb", "ruby"),
            ("php7", "php"),
            # SQL
            ("mysql", "sql"),
            ("postgresql", "sql"),
            # Templates
            ("mystmd", "myst"),
            ("myst-markdown", "myst"),
            ("jinja", "jinja2"),
            ("j2", "jinja2"),
            ("html+jinja", "jinja2"),
            ("jekyll", "liquid"),
            ("hbs", "handlebars"),
            ("mustache", "handlebars"),
            ("njk", "nunjucks"),
            ("eleventy", "nunjucks"),
            ("symfony", "twig"),
            # Other
            ("sass", "scss"),
            ("restructuredtext", "rst"),
            ("tex", "latex"),
            ("https", "http"),
            ("regexp", "regex"),
            ("adoc", "asciidoc"),
            ("ml", "ocaml"),
            ("reasonml", "ocaml"),
            ("gawk", "awk"),
            ("wat", "wasm"),
            ("webassembly", "wasm"),
            ("fishshell", "fish"),
            ("neo4j", "cypher"),
            ("libsonnet", "jsonnet"),
            ("vuejs", "vue"),
            ("mmd", "mermaid"),
        ],
    )
    def test_alias_resolves(self, alias: str, canonical: str) -> None:
        """Aliases resolve to canonical names."""
        assert supports_language(alias)
        html1 = highlight("test", alias, css_class_style="pygments")
        html2 = highlight("test", canonical, css_class_style="pygments")
        assert '<div class="highlight">' in html1
        assert '<div class="highlight">' in html2
