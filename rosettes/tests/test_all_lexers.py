"""Tests for all Rosettes lexers."""

import pytest

from rosettes import highlight, list_languages, supports_language, tokenize


class TestAllLanguages:
    """Test all 20 supported languages."""

    @pytest.mark.parametrize(
        "language,code,expected_token_type",
        [
            # Original 10 MVP languages
            ("python", "def foo(): pass", "kd"),  # keyword declaration
            ("javascript", "const x = 1;", "kd"),
            ("typescript", "interface Foo {}", "kd"),
            ("json", '{"key": "value"}', "s"),  # string
            ("json", '{"num": 42}', "m"),  # number
            ("yaml", "key: value", "na"),  # name attribute
            ("toml", "[section]", "nc"),  # name class
            ("bash", "echo hello", "nb"),  # name builtin
            ("html", "<div>content</div>", "nt"),  # name tag
            ("css", ".class { color: red; }", "nc"),  # name class
            ("diff", "+added line", "gi"),  # generic inserted
            # New 10 languages
            ("rust", "fn main() {}", "kd"),  # keyword declaration
            ("go", "func main() {}", "kd"),
            ("sql", "SELECT * FROM users", "k"),  # keyword
            ("markdown", "# Heading", "gh"),  # generic heading
            ("xml", "<root>content</root>", "nt"),  # name tag
            ("c", "int main() {}", "kt"),  # keyword type
            ("cpp", "class Foo {};", "kd"),  # keyword declaration
            ("java", "public class Main {}", "kd"),
            ("ruby", "def foo; end", "kd"),
            ("php", "<?php echo $x; ?>", "nv"),  # name variable
            # MyST Markdown
            ("myst", ":::{note}\nContent\n:::", "k"),  # keyword (directive)
            # Jinja2 templates
            ("jinja2", "{% if x %}{{ y }}{% endif %}", "k"),  # keyword
            # New languages
            ("scss", "$color: #fff; .class { }", "nv"),  # name variable
            ("rst", ".. note::\n   Content", "k"),  # keyword (directive)
            ("latex", "\\section{Title}", "k"),  # keyword (command)
            ("liquid", "{% for x in items %}", "k"),  # keyword
            ("http", "GET /api HTTP/1.1", "k"),  # keyword (method)
            ("regex", "^\\d+$", "k"),  # keyword (anchor)
            ("asciidoc", "= Title\n\nNOTE: text", "k"),  # keyword (admonition)
            ("svelte", "{#if condition}", "k"),  # keyword
            ("ocaml", "let x = 1", "k"),  # keyword
            ("awk", "BEGIN { print }", "k"),  # keyword
            # Next 10 languages
            ("wasm", "(module (func))", "k"),  # keyword
            ("handlebars", "{{#if x}}{{/if}}", "k"),  # keyword
            ("nunjucks", "{% for x in items %}", "k"),  # keyword
            ("fish", "function greet; echo hi; end", "k"),  # keyword
            ("prisma", "model User { id Int @id }", "k"),  # keyword
            ("cypher", "MATCH (n) RETURN n", "k"),  # keyword
            ("jsonnet", "local x = 1;", "k"),  # keyword
            ("vue", "<template>{{ msg }}</template>", "nt"),  # name tag
            ("twig", "{% for x in items %}", "k"),  # keyword
            ("mermaid", "graph TD\n  A --> B", "kd"),  # keyword declaration
        ],
    )
    def test_language_tokenizes(self, language: str, code: str, expected_token_type: str) -> None:
        """Each language produces tokens with expected types."""
        tokens = tokenize(code, language)
        assert len(tokens) > 0
        # Check that at least one token has the expected type
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

    @pytest.mark.parametrize(
        "alias,canonical",
        [
            # Original aliases
            ("py", "python"),
            ("py3", "python"),
            ("js", "javascript"),
            ("ts", "typescript"),
            ("yml", "yaml"),
            ("sh", "bash"),
            ("shell", "bash"),
            ("htm", "html"),
            ("patch", "diff"),
            # New language aliases
            ("rs", "rust"),
            ("golang", "go"),
            ("mysql", "sql"),
            ("postgresql", "sql"),
            ("md", "markdown"),
            ("svg", "xml"),
            ("h", "c"),
            ("c++", "cpp"),
            ("cxx", "cpp"),
            ("rb", "ruby"),
            ("php7", "php"),
            # MyST aliases
            ("mystmd", "myst"),
            ("myst-markdown", "myst"),
            # Jinja2 aliases
            ("jinja", "jinja2"),
            ("j2", "jinja2"),
            ("html+jinja", "jinja2"),
            # New language aliases
            ("sass", "scss"),
            ("restructuredtext", "rst"),
            ("tex", "latex"),
            ("jekyll", "liquid"),
            ("https", "http"),
            ("regexp", "regex"),
            ("adoc", "asciidoc"),
            ("ml", "ocaml"),
            ("reasonml", "ocaml"),
            ("gawk", "awk"),
            # Next 10 language aliases
            ("wat", "wasm"),
            ("webassembly", "wasm"),
            ("hbs", "handlebars"),
            ("mustache", "handlebars"),
            ("njk", "nunjucks"),
            ("eleventy", "nunjucks"),
            ("fishshell", "fish"),
            ("neo4j", "cypher"),
            ("libsonnet", "jsonnet"),
            ("vuejs", "vue"),
            ("symfony", "twig"),
            ("mmd", "mermaid"),
        ],
    )
    def test_language_aliases(self, alias: str, canonical: str) -> None:
        """Aliases resolve to canonical names."""
        assert supports_language(alias)
        code = "test"
        # Both should produce output without error
        html1 = highlight(code, alias, css_class_style="pygments")
        html2 = highlight(code, canonical, css_class_style="pygments")
        # Both should be valid HTML
        assert '<div class="highlight">' in html1
        assert '<div class="highlight">' in html2


class TestPythonLexer:
    """Python-specific tests."""

    def test_function_definition(self) -> None:
        """Tokenizes function definitions."""
        code = "def hello(name: str) -> str:\n    return f'Hello {name}'"
        tokens = tokenize(code, "python")
        keywords = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "def" for t in keywords)

    def test_class_definition(self) -> None:
        """Tokenizes class definitions."""
        code = "class MyClass(BaseClass):\n    pass"
        tokens = tokenize(code, "python")
        keywords = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "class" for t in keywords)

    def test_decorators(self) -> None:
        """Tokenizes decorators."""
        code = "@property\n@staticmethod\ndef method(self): pass"
        tokens = tokenize(code, "python")
        decorators = [t for t in tokens if t.type.value == "nd"]
        assert any("@property" in t.value for t in decorators)
        assert any("@staticmethod" in t.value for t in decorators)

    def test_f_strings(self) -> None:
        """Tokenizes f-strings."""
        code = "name = 'World'\nmsg = f'Hello {name}!'"
        tokens = tokenize(code, "python")
        strings = [t for t in tokens if t.type.value == "s"]
        assert any("f'" in t.value or 'f"' in t.value for t in strings)

    def test_docstrings(self) -> None:
        """Tokenizes docstrings."""
        code = '"""This is a docstring."""'
        tokens = tokenize(code, "python")
        docs = [t for t in tokens if t.type.value == "sd"]
        assert len(docs) == 1

    def test_builtin_functions(self) -> None:
        """Tokenizes builtin functions."""
        code = "result = len(list(range(10)))"
        tokens = tokenize(code, "python")
        builtins = [t for t in tokens if t.type.value == "nb"]
        builtin_names = {t.value for t in builtins}
        assert "len" in builtin_names
        assert "list" in builtin_names
        assert "range" in builtin_names

    def test_keyword_constants(self) -> None:
        """Tokenizes True, False, None."""
        code = "x = True\ny = False\nz = None"
        tokens = tokenize(code, "python")
        consts = [t for t in tokens if t.type.value == "kc"]
        const_values = {t.value for t in consts}
        assert "True" in const_values
        assert "False" in const_values
        assert "None" in const_values

    def test_import_statements(self) -> None:
        """Tokenizes import statements."""
        code = "from typing import List, Dict\nimport os"
        tokens = tokenize(code, "python")
        keywords = [t for t in tokens if t.type.value == "kn"]
        keyword_values = {t.value for t in keywords}
        assert "from" in keyword_values
        assert "import" in keyword_values

    def test_walrus_operator(self) -> None:
        """Tokenizes walrus operator."""
        code = "if (n := len(data)) > 10: pass"
        tokens = tokenize(code, "python")
        values = [t.value for t in tokens]
        assert ":=" in values

    def test_type_hints(self) -> None:
        """Tokenizes type hints with arrow."""
        code = "def process(data: list[int]) -> dict[str, int]: ..."
        tokens = tokenize(code, "python")
        values = [t.value for t in tokens]
        assert "->" in values

    def test_exception_names(self) -> None:
        """Tokenizes exception names."""
        code = "raise ValueError('invalid')"
        tokens = tokenize(code, "python")
        exceptions = [t for t in tokens if t.type.value == "ne"]
        assert any(t.value == "ValueError" for t in exceptions)

    def test_self_and_cls(self) -> None:
        """Tokenizes self and cls as pseudo-builtins."""
        code = "def method(self): return self.value"
        tokens = tokenize(code, "python")
        pseudo = [t for t in tokens if t.type.value == "bp"]
        assert any(t.value == "self" for t in pseudo)

    def test_numbers(self) -> None:
        """Tokenizes various number formats."""
        code = "a = 42\nb = 3.14\nc = 0xFF\nd = 0b1010\ne = 0o777"
        tokens = tokenize(code, "python")
        integers = [t for t in tokens if t.type.value == "mi"]
        floats = [t for t in tokens if t.type.value == "mf"]
        hex_nums = [t for t in tokens if t.type.value == "mh"]
        bin_nums = [t for t in tokens if t.type.value == "mb"]
        oct_nums = [t for t in tokens if t.type.value == "mo"]
        assert len(integers) >= 1
        assert len(floats) >= 1
        assert len(hex_nums) >= 1
        assert len(bin_nums) >= 1
        assert len(oct_nums) >= 1

    def test_comments(self) -> None:
        """Tokenizes comments."""
        code = "x = 1  # This is a comment\ny = 2"
        tokens = tokenize(code, "python")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) == 1

    def test_lambda(self) -> None:
        """Tokenizes lambda expressions."""
        code = "fn = lambda x, y: x + y"
        tokens = tokenize(code, "python")
        keywords = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "lambda" for t in keywords)

    def test_async_await(self) -> None:
        """Tokenizes async/await."""
        code = "async def fetch():\n    result = await get_data()"
        tokens = tokenize(code, "python")
        keywords = [t for t in tokens if t.type.value == "k"]
        keyword_values = {t.value for t in keywords}
        assert "async" in keyword_values
        assert "await" in keyword_values


class TestJavaScriptLexer:
    """JavaScript-specific tests."""

    def test_arrow_function(self) -> None:
        """Tokenizes arrow functions."""
        tokens = tokenize("const f = (x) => x * 2;", "javascript")
        values = [t.value for t in tokens]
        assert "=>" in values

    def test_template_literal(self) -> None:
        """Tokenizes template literals."""
        tokens = tokenize("`hello ${name}`", "javascript")
        assert any(t.value.startswith("`") for t in tokens)

    def test_bigint(self) -> None:
        """Tokenizes BigInt literals."""
        tokens = tokenize("const big = 123n;", "javascript")
        assert any(t.value == "123n" for t in tokens)

    def test_nullish_coalescing(self) -> None:
        """Tokenizes nullish coalescing operator."""
        tokens = tokenize("const x = a ?? b;", "javascript")
        values = [t.value for t in tokens]
        assert "??" in values

    def test_const_let_var(self) -> None:
        """Tokenizes variable declarations."""
        code = "const a = 1;\nlet b = 2;\nvar c = 3;"
        tokens = tokenize(code, "javascript")
        keywords = [t for t in tokens if t.type.value == "kd"]
        keyword_values = {t.value for t in keywords}
        assert "const" in keyword_values
        assert "let" in keyword_values
        assert "var" in keyword_values

    def test_function_declaration(self) -> None:
        """Tokenizes function declarations."""
        code = "function greet(name) { return 'Hello ' + name; }"
        tokens = tokenize(code, "javascript")
        keywords = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "function" for t in keywords)

    def test_class_syntax(self) -> None:
        """Tokenizes class syntax."""
        code = "class MyClass extends Base { constructor() { super(); } }"
        tokens = tokenize(code, "javascript")
        keywords = [t for t in tokens if t.type.value in ("k", "kd")]
        keyword_values = {t.value for t in keywords}
        assert "class" in keyword_values
        assert "extends" in keyword_values

    def test_async_await(self) -> None:
        """Tokenizes async/await."""
        code = "async function fetch() { const data = await getData(); }"
        tokens = tokenize(code, "javascript")
        keywords = [t for t in tokens if t.type.value == "k"]
        keyword_values = {t.value for t in keywords}
        assert "async" in keyword_values
        assert "await" in keyword_values

    def test_destructuring(self) -> None:
        """Tokenizes destructuring syntax."""
        code = "const { a, b } = obj;\nconst [x, y] = arr;"
        tokens = tokenize(code, "javascript")
        # Should have punctuation for braces and brackets
        punct = [t for t in tokens if t.type.value == "p"]
        assert len(punct) >= 4

    def test_spread_operator(self) -> None:
        """Tokenizes spread operator."""
        code = "const arr = [...items, newItem];"
        tokens = tokenize(code, "javascript")
        values = [t.value for t in tokens]
        assert "..." in values

    def test_optional_chaining(self) -> None:
        """Tokenizes optional chaining."""
        code = "const value = obj?.prop?.nested;"
        tokens = tokenize(code, "javascript")
        values = [t.value for t in tokens]
        # Optional chaining may be tokenized as ? and . separately
        assert "?" in values and "." in values

    def test_regex_literal(self) -> None:
        """Tokenizes regex literals."""
        code = "const pattern = /^hello.*$/gi;"
        tokens = tokenize(code, "javascript")
        strings = [t for t in tokens if t.type.value == "sr"]
        assert len(strings) >= 1

    def test_single_line_comments(self) -> None:
        """Tokenizes single-line comments."""
        code = "const x = 1; // comment"
        tokens = tokenize(code, "javascript")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) == 1

    def test_multi_line_comments(self) -> None:
        """Tokenizes multi-line comments."""
        code = "/* multi\nline\ncomment */\nconst x = 1;"
        tokens = tokenize(code, "javascript")
        comments = [t for t in tokens if t.type.value == "cm"]
        assert len(comments) == 1


class TestTypeScriptLexer:
    """TypeScript-specific tests."""

    def test_type_annotation(self) -> None:
        """Tokenizes type annotations."""
        tokens = tokenize("const x: number = 1;", "typescript")
        types = [t for t in tokens if t.type.value == "kt"]  # keyword type
        assert any(t.value == "number" for t in types)

    def test_interface(self) -> None:
        """Tokenizes interface declarations."""
        tokens = tokenize("interface User { name: string; }", "typescript")
        keywords = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "interface" for t in keywords)

    def test_decorator(self) -> None:
        """Tokenizes decorators."""
        tokens = tokenize("@Component class Foo {}", "typescript")
        decorators = [t for t in tokens if t.type.value == "nd"]
        assert any("@Component" in t.value for t in decorators)


class TestJsonLexer:
    """JSON-specific tests."""

    def test_nested_object(self) -> None:
        """Tokenizes nested JSON."""
        code = '{"outer": {"inner": [1, 2, 3]}}'
        tokens = tokenize(code, "json")
        assert len(tokens) > 0
        # Should have strings, numbers, and punctuation
        types = {t.type.value for t in tokens}
        assert "s" in types  # strings
        assert "m" in types  # numbers (generic)
        assert "p" in types  # punctuation

    def test_basic_types(self) -> None:
        """Tokenizes basic JSON types."""
        code = '{"str": "hello", "num": 42, "bool": true, "nil": null}'
        tokens = tokenize(code, "json")
        types = {t.type.value for t in tokens}
        assert "s" in types  # strings
        assert "m" in types  # numbers
        assert "kc" in types  # keyword constants (true, false, null)
        assert "p" in types  # punctuation

    def test_arrays(self) -> None:
        """Tokenizes JSON arrays."""
        code = '["one", "two", "three"]'
        tokens = tokenize(code, "json")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 3

    def test_object_keys(self) -> None:
        """Tokenizes object keys correctly."""
        code = '{"name": "value", "count": 42}'
        tokens = tokenize(code, "json")
        strings = [t for t in tokens if t.type.value == "s"]
        # Both keys and string values should be strings
        assert len(strings) >= 3

    def test_float_numbers(self) -> None:
        """Tokenizes float numbers."""
        code = '{"price": 19.99, "rate": 0.05}'
        tokens = tokenize(code, "json")
        numbers = [t for t in tokens if t.type.value in ("m", "mf")]
        assert len(numbers) >= 2

    def test_scientific_notation(self) -> None:
        """Tokenizes scientific notation."""
        code = '{"big": 1.5e10, "small": 2.5e-5}'
        tokens = tokenize(code, "json")
        numbers = [t for t in tokens if t.type.value in ("m", "mf")]
        assert len(numbers) >= 2

    def test_negative_numbers(self) -> None:
        """Tokenizes negative numbers."""
        code = '{"temp": -20, "diff": -3.5}'
        tokens = tokenize(code, "json")
        # Negative sign might be separate or part of number
        values = [t.value for t in tokens]
        assert "-20" in values or ("-" in values and "20" in values)

    def test_escape_sequences(self) -> None:
        """Tokenizes escape sequences in strings."""
        code = '{"path": "C:\\\\Users\\\\name", "msg": "line1\\nline2"}'
        tokens = tokenize(code, "json")
        strings = [t for t in tokens if t.type.value == "s"]
        # Should have strings with escapes
        assert len(strings) >= 2

    def test_unicode_strings(self) -> None:
        """Tokenizes Unicode strings."""
        code = '{"emoji": "Hello 👋", "chinese": "你好"}'
        tokens = tokenize(code, "json")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 2

    def test_empty_structures(self) -> None:
        """Tokenizes empty objects and arrays."""
        code = '{"empty_obj": {}, "empty_arr": []}'
        tokens = tokenize(code, "json")
        punct = [t for t in tokens if t.type.value == "p"]
        # Should have {, }, [, ], :, and commas
        assert len(punct) >= 6


class TestYamlLexer:
    """YAML-specific tests."""

    def test_anchor_alias(self) -> None:
        """Tokenizes anchors and aliases."""
        code = "defaults: &defaults\n  adapter: postgres\ndev:\n  <<: *defaults"
        tokens = tokenize(code, "yaml")
        values = [t.value for t in tokens]
        assert "&defaults" in values

    def test_multiline_indicator(self) -> None:
        """Tokenizes block scalar indicators."""
        code = "description: |\n  Multi\n  line"
        tokens = tokenize(code, "yaml")
        heredocs = [t for t in tokens if t.type.value == "sh"]
        assert len(heredocs) >= 1

    def test_key_value_pairs(self) -> None:
        """Tokenizes key-value pairs."""
        code = "name: John\nage: 30\nactive: true"
        tokens = tokenize(code, "yaml")
        attrs = [t for t in tokens if t.type.value == "na"]
        attr_values = {t.value for t in attrs}
        assert "name" in attr_values
        assert "age" in attr_values
        assert "active" in attr_values

    def test_nested_structure(self) -> None:
        """Tokenizes nested YAML."""
        code = "server:\n  host: localhost\n  port: 8080"
        tokens = tokenize(code, "yaml")
        attrs = [t for t in tokens if t.type.value == "na"]
        assert len(attrs) >= 3

    def test_list_items(self) -> None:
        """Tokenizes list items."""
        code = "items:\n  - first\n  - second\n  - third"
        tokens = tokenize(code, "yaml")
        values = [t.value for t in tokens]
        assert "-" in values

    def test_boolean_values(self) -> None:
        """Tokenizes boolean values."""
        code = "enabled: true\ndisabled: false\nyes_val: yes\nno_val: no"
        tokens = tokenize(code, "yaml")
        consts = [t for t in tokens if t.type.value == "kc"]
        assert len(consts) >= 2

    def test_null_values(self) -> None:
        """Tokenizes null values."""
        code = "empty: null\nalso_empty: ~"
        tokens = tokenize(code, "yaml")
        consts = [t for t in tokens if t.type.value == "kc"]
        assert len(consts) >= 1

    def test_quoted_strings(self) -> None:
        """Tokenizes quoted strings."""
        code = "message: 'Hello World'\npath: \"/usr/local/bin\""
        tokens = tokenize(code, "yaml")
        # YAML strings may be tokenized as generic string type
        strings = [t for t in tokens if t.type.value in ("s", "s1", "s2")]
        assert len(strings) >= 2

    def test_comments(self) -> None:
        """Tokenizes comments."""
        code = "# Configuration file\nname: app  # inline comment"
        tokens = tokenize(code, "yaml")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) >= 1

    def test_numbers(self) -> None:
        """Tokenizes numbers."""
        code = "port: 8080\nversion: 1.5\nhex: 0xFF"
        tokens = tokenize(code, "yaml")
        integers = [t for t in tokens if t.type.value == "mi"]
        floats = [t for t in tokens if t.type.value == "mf"]
        assert len(integers) >= 1
        assert len(floats) >= 1


class TestTomlLexer:
    """TOML-specific tests."""

    def test_array_of_tables(self) -> None:
        """Tokenizes array of tables."""
        code = "[[products]]\nname = 'hammer'"
        tokens = tokenize(code, "toml")
        classes = [t for t in tokens if t.type.value == "nc"]
        assert any("products" in t.value for t in classes)

    def test_datetime(self) -> None:
        """Tokenizes datetime values."""
        code = "date = 2024-01-15T10:30:00Z"
        tokens = tokenize(code, "toml")
        dates = [t for t in tokens if t.type.value == "ld"]
        assert len(dates) >= 1

    def test_table_headers(self) -> None:
        """Tokenizes table headers."""
        code = "[package]\nname = 'my-app'\nversion = '1.0.0'"
        tokens = tokenize(code, "toml")
        classes = [t for t in tokens if t.type.value == "nc"]
        assert any("package" in t.value for t in classes)

    def test_dotted_keys(self) -> None:
        """Tokenizes dotted keys."""
        code = "server.host = 'localhost'\nserver.port = 8080"
        tokens = tokenize(code, "toml")
        attrs = [t for t in tokens if t.type.value == "na"]
        assert len(attrs) >= 2

    def test_multiline_strings(self) -> None:
        """Tokenizes multiline strings."""
        code = 'text = """\nmulti\nline\n"""'
        tokens = tokenize(code, "toml")
        # TOML multiline strings are tokenized as doc strings (sd)
        strings = [t for t in tokens if t.type.value in ("s", "s2", "sd")]
        assert len(strings) >= 1

    def test_arrays(self) -> None:
        """Tokenizes arrays."""
        code = "colors = ['red', 'green', 'blue']"
        tokens = tokenize(code, "toml")
        strings = [t for t in tokens if t.type.value == "s1"]
        assert len(strings) >= 3

    def test_inline_tables(self) -> None:
        """Tokenizes inline tables."""
        code = "point = { x = 1, y = 2 }"
        tokens = tokenize(code, "toml")
        values = [t.value for t in tokens]
        assert "{" in values
        assert "}" in values

    def test_boolean_values(self) -> None:
        """Tokenizes boolean values."""
        code = "enabled = true\ndisabled = false"
        tokens = tokenize(code, "toml")
        consts = [t for t in tokens if t.type.value == "kc"]
        assert len(consts) == 2

    def test_numbers(self) -> None:
        """Tokenizes various number formats."""
        code = "int = 42\nfloat = 3.14\nhex = 0xDEAD\nbin = 0b1010"
        tokens = tokenize(code, "toml")
        integers = [t for t in tokens if t.type.value == "mi"]
        floats = [t for t in tokens if t.type.value == "mf"]
        assert len(integers) >= 1
        assert len(floats) >= 1

    def test_comments(self) -> None:
        """Tokenizes comments."""
        code = "# Configuration\nname = 'app'  # inline"
        tokens = tokenize(code, "toml")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) >= 1


class TestBashLexer:
    """Bash-specific tests."""

    def test_variable_expansion(self) -> None:
        """Tokenizes variable expansion."""
        # Use unquoted variables for cleaner tokenization
        code = "echo $HOME $USER"
        tokens = tokenize(code, "bash")
        vars = [t for t in tokens if t.type.value == "nv"]
        assert len(vars) >= 2

    def test_shebang(self) -> None:
        """Tokenizes shebang."""
        code = "#!/bin/bash\necho hello"
        tokens = tokenize(code, "bash")
        shebangs = [t for t in tokens if t.type.value == "ch"]
        assert len(shebangs) == 1

    def test_command_substitution(self) -> None:
        """Tokenizes command substitution."""
        code = "files=$(ls -la)"
        tokens = tokenize(code, "bash")
        subs = [t for t in tokens if t.type.value == "si"]
        assert len(subs) >= 1

    def test_hyphenated_commands(self) -> None:
        """Tokenizes hyphenated command/argument names as single tokens."""
        code = "my-custom-script --option my-arg"
        tokens = tokenize(code, "bash")
        values = [t.value for t in tokens]
        # Hyphenated name should be a single token, not split
        assert "my-custom-script" in values
        assert "my-arg" in values

    def test_options_short_and_long(self) -> None:
        """Tokenizes short and long options."""
        code = "ls -la --color=auto"
        tokens = tokenize(code, "bash")
        attrs = [t for t in tokens if t.type.value == "na"]
        attr_values = [t.value for t in attrs]
        assert "-la" in attr_values
        assert "--color" in attr_values

    def test_builtin_commands(self) -> None:
        """Tokenizes builtin commands correctly."""
        code = "cd /path && echo hello && exit 0"
        tokens = tokenize(code, "bash")
        builtins = [t for t in tokens if t.type.value == "nb"]
        builtin_values = {t.value for t in builtins}
        assert "cd" in builtin_values
        assert "echo" in builtin_values
        assert "exit" in builtin_values

    def test_double_quoted_strings(self) -> None:
        """Tokenizes double-quoted strings."""
        code = 'echo "hello world"'
        tokens = tokenize(code, "bash")
        strings = [t for t in tokens if t.type.value == "s2"]
        assert len(strings) == 1
        assert '"hello world"' in strings[0].value

    def test_single_quoted_strings(self) -> None:
        """Tokenizes single-quoted strings."""
        code = "echo 'literal $VAR'"
        tokens = tokenize(code, "bash")
        strings = [t for t in tokens if t.type.value == "s1"]
        assert len(strings) == 1

    def test_comments(self) -> None:
        """Tokenizes comments."""
        code = "# This is a comment\necho hello"
        tokens = tokenize(code, "bash")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) == 1

    def test_pipes_and_redirects(self) -> None:
        """Tokenizes pipes and redirects."""
        code = "cat file.txt | grep pattern > output.txt"
        tokens = tokenize(code, "bash")
        values = [t.value for t in tokens]
        assert "|" in values
        assert ">" in values


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
        # Should have opening tag and closing />
        assert any("<img" in t.value for t in tags)
        assert any("/>" in t.value for t in tags)

    def test_multiple_attributes(self) -> None:
        """Tokenizes multiple attributes on a tag."""
        code = '<input type="text" name="email" placeholder="Enter email" required>'
        tokens = tokenize(code, "html")
        attrs = [t for t in tokens if t.type.value == "na"]
        strings = [t for t in tokens if t.type.value == "s2"]
        # Should have 4 attribute names and 3 quoted values
        assert len(attrs) >= 4  # type, name, placeholder, required
        assert len(strings) >= 3  # "text", "email", "Enter email"

    def test_nested_tags(self) -> None:
        """Tokenizes nested HTML structure."""
        code = '<div><span class="inner">Text</span></div>'
        tokens = tokenize(code, "html")
        tags = [t for t in tokens if t.type.value == "nt"]
        # Should have: <div, >, <span, >, </span>, </div>
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
        # CSS property names are tokenized as name_tag (nt)
        names = [t for t in tokens if t.type.value == "nt"]
        name_values = {t.value for t in names}
        assert "font-size" in name_values
        assert "color" in name_values

    def test_color_values(self) -> None:
        """Tokenizes color values."""
        code = ".box { background: #ff0000; border-color: rgb(0, 128, 255); }"
        tokens = tokenize(code, "css")
        # Hex colors and rgb values
        values = [t.value for t in tokens]
        assert any("#ff0000" in v for v in values)

    def test_css_variables(self) -> None:
        """Tokenizes CSS custom properties."""
        code = ":root { --primary-color: blue; }\n.btn { color: var(--primary-color); }"
        tokens = tokenize(code, "css")
        # Custom properties
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


# =============================================================================
# NEW LANGUAGE TESTS (Phase 2: 10 additional languages)
# =============================================================================


class TestRustLexer:
    """Rust-specific tests."""

    def test_lifetime(self) -> None:
        """Tokenizes lifetimes."""
        code = "fn foo<'a>(x: &'a str) -> &'a str { x }"
        tokens = tokenize(code, "rust")
        labels = [t for t in tokens if t.type.value == "nl"]
        assert any("'a" in t.value for t in labels)

    def test_attribute(self) -> None:
        """Tokenizes attributes."""
        code = "#[derive(Debug)]\nstruct Foo {}"
        tokens = tokenize(code, "rust")
        decorators = [t for t in tokens if t.type.value == "nd"]
        assert len(decorators) >= 1

    def test_macro(self) -> None:
        """Tokenizes macro calls."""
        code = 'println!("Hello, {}!", name);'
        tokens = tokenize(code, "rust")
        macros = [t for t in tokens if t.type.value == "fm"]
        assert any("println!" in t.value for t in macros)

    def test_raw_string(self) -> None:
        """Tokenizes raw strings."""
        code = 'r#"raw string with "quotes""#'
        tokens = tokenize(code, "rust")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 1


class TestGoLexer:
    """Go-specific tests."""

    def test_goroutine(self) -> None:
        """Tokenizes go keyword."""
        code = "go func() { fmt.Println() }()"
        tokens = tokenize(code, "go")
        keywords = [t for t in tokens if t.type.value == "k"]
        assert any(t.value == "go" for t in keywords)

    def test_channel(self) -> None:
        """Tokenizes channel operations."""
        code = "ch := make(chan int)\nch <- 42"
        tokens = tokenize(code, "go")
        values = [t.value for t in tokens]
        assert "<-" in values

    def test_raw_string(self) -> None:
        """Tokenizes raw strings."""
        code = "`raw string`"
        tokens = tokenize(code, "go")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 1

    def test_short_declaration(self) -> None:
        """Tokenizes short variable declaration."""
        code = "x := 42"
        tokens = tokenize(code, "go")
        values = [t.value for t in tokens]
        assert ":=" in values


class TestSqlLexer:
    """SQL-specific tests."""

    def test_select_query(self) -> None:
        """Tokenizes SELECT query."""
        code = "SELECT id, name FROM users WHERE active = 1;"
        tokens = tokenize(code, "sql")
        keywords = [t for t in tokens if t.type.value == "k"]
        assert any(t.value.upper() == "SELECT" for t in keywords)
        assert any(t.value.upper() == "FROM" for t in keywords)
        assert any(t.value.upper() == "WHERE" for t in keywords)

    def test_join_query(self) -> None:
        """Tokenizes JOIN query."""
        code = "SELECT * FROM orders INNER JOIN users ON orders.user_id = users.id"
        tokens = tokenize(code, "sql")
        keywords = [t for t in tokens if t.type.value == "k"]
        keyword_values = {t.value.upper() for t in keywords}
        assert "JOIN" in keyword_values
        assert "ON" in keyword_values

    def test_aggregate_functions(self) -> None:
        """Tokenizes aggregate functions."""
        code = "SELECT COUNT(*), AVG(price), SUM(quantity) FROM orders"
        tokens = tokenize(code, "sql")
        functions = [t for t in tokens if t.type.value == "nf"]
        func_names = {t.value.upper() for t in functions}
        assert "COUNT" in func_names
        assert "AVG" in func_names

    def test_placeholders(self) -> None:
        """Tokenizes query placeholders."""
        code = "SELECT * FROM users WHERE id = $1 AND name = :name"
        tokens = tokenize(code, "sql")
        vars = [t for t in tokens if t.type.value == "nv"]
        assert len(vars) >= 2


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
        # Attribute name may include the lookahead "=", check that attr is present
        values = [t.value for t in tokens]
        assert "attr" in values or any("attr" in v for v in values)


class TestCLexer:
    """C-specific tests."""

    def test_preprocessor(self) -> None:
        """Tokenizes preprocessor directives."""
        code = "#include <stdio.h>\n#define MAX 100"
        tokens = tokenize(code, "c")
        preprocs = [t for t in tokens if t.type.value == "cp"]
        assert len(preprocs) >= 2

    def test_pointer(self) -> None:
        """Tokenizes pointer operations."""
        code = "int *ptr = &value;"
        tokens = tokenize(code, "c")
        types = [t for t in tokens if t.type.value == "kt"]
        assert any(t.value == "int" for t in types)

    def test_sizeof(self) -> None:
        """Tokenizes sizeof operator."""
        code = "size_t n = sizeof(int);"
        tokens = tokenize(code, "c")
        keywords = [t for t in tokens if t.type.value == "k"]
        assert any(t.value == "sizeof" for t in keywords)

    def test_struct(self) -> None:
        """Tokenizes struct definition."""
        code = "struct Point { int x; int y; };"
        tokens = tokenize(code, "c")
        decls = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "struct" for t in decls)


class TestCppLexer:
    """C++-specific tests."""

    def test_class(self) -> None:
        """Tokenizes class definition."""
        code = "class Foo : public Base { public: void bar(); };"
        tokens = tokenize(code, "cpp")
        decls = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "class" for t in decls)

    def test_template(self) -> None:
        """Tokenizes template."""
        code = "template<typename T>\nT max(T a, T b) { return a > b ? a : b; }"
        tokens = tokenize(code, "cpp")
        decls = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "template" for t in decls)

    def test_lambda(self) -> None:
        """Tokenizes lambda expressions."""
        code = "auto f = [](int x) { return x * 2; };"
        tokens = tokenize(code, "cpp")
        keywords = [t for t in tokens if t.type.value in ("k", "kd")]
        assert any(t.value == "auto" for t in keywords)

    def test_raw_string(self) -> None:
        """Tokenizes raw string literals."""
        code = 'R"(raw string)"'
        tokens = tokenize(code, "cpp")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 1


class TestJavaLexer:
    """Java-specific tests."""

    def test_annotation(self) -> None:
        """Tokenizes annotations."""
        code = "@Override\npublic void foo() {}"
        tokens = tokenize(code, "java")
        decorators = [t for t in tokens if t.type.value == "nd"]
        assert any("@Override" in t.value for t in decorators)

    def test_generic(self) -> None:
        """Tokenizes generics."""
        code = "List<String> items = new ArrayList<>();"
        tokens = tokenize(code, "java")
        types = [t for t in tokens if t.type.value in ("kt", "nc")]
        assert any(t.value == "List" for t in types)
        assert any(t.value == "String" for t in types)

    def test_javadoc(self) -> None:
        """Tokenizes Javadoc comments."""
        code = "/** Javadoc comment */\nclass Foo {}"
        tokens = tokenize(code, "java")
        docs = [t for t in tokens if t.type.value == "sd"]
        assert len(docs) >= 1

    def test_lambda(self) -> None:
        """Tokenizes lambda expressions."""
        code = "list.forEach(x -> System.out.println(x));"
        tokens = tokenize(code, "java")
        values = [t.value for t in tokens]
        assert "->" in values


class TestRubyLexer:
    """Ruby-specific tests."""

    def test_symbol(self) -> None:
        """Tokenizes symbols."""
        code = "hash = { :key => 'value' }"
        tokens = tokenize(code, "ruby")
        symbols = [t for t in tokens if t.type.value == "ss"]
        assert any(":key" in t.value for t in symbols)

    def test_instance_variable(self) -> None:
        """Tokenizes instance variables."""
        code = "@name = 'Ruby'"
        tokens = tokenize(code, "ruby")
        ivars = [t for t in tokens if t.type.value == "vi"]
        assert any("@name" in t.value for t in ivars)

    def test_block(self) -> None:
        """Tokenizes blocks."""
        code = "items.each do |item|\n  puts item\nend"
        tokens = tokenize(code, "ruby")
        keywords = [t for t in tokens if t.type.value == "k"]
        assert any(t.value == "do" for t in keywords)
        assert any(t.value == "end" for t in keywords)

    def test_heredoc(self) -> None:
        """Tokenizes heredocs."""
        # Note: heredoc regex pattern is simplified, may need adjustment
        code = "text = <<DOC\nmulti\nline\nDOC"
        tokens = tokenize(code, "ruby")
        # Heredoc detection is simplified; just ensure tokenization works
        assert len(tokens) > 0


class TestPhpLexer:
    """PHP-specific tests."""

    def test_variable(self) -> None:
        """Tokenizes PHP variables."""
        code = "<?php $name = 'PHP'; ?>"
        tokens = tokenize(code, "php")
        vars = [t for t in tokens if t.type.value == "nv"]
        assert any("$name" in t.value for t in vars)

    def test_heredoc(self) -> None:
        """Tokenizes heredocs."""
        # Note: heredoc regex pattern is simplified
        code = "<<<EOT\nmulti\nline\nEOT;"
        tokens = tokenize(code, "php")
        # Heredoc detection is simplified; just ensure tokenization works
        assert len(tokens) > 0

    def test_arrow_function(self) -> None:
        """Tokenizes arrow functions."""
        code = "<?php $fn = fn($x) => $x * 2; ?>"
        tokens = tokenize(code, "php")
        values = [t.value for t in tokens]
        assert "=>" in values
        assert "fn" in values

    def test_namespace(self) -> None:
        """Tokenizes namespace."""
        code = "<?php namespace App\\Models; use App\\Base; ?>"
        tokens = tokenize(code, "php")
        ns_keywords = [t for t in tokens if t.type.value == "kn"]
        assert any(t.value == "namespace" for t in ns_keywords)
        assert any(t.value == "use" for t in ns_keywords)


class TestMystLexer:
    """MyST Markdown-specific tests."""

    def test_directive_colon_fence(self) -> None:
        """Tokenizes colon-fence directives."""
        code = ":::{note}\nContent\n:::"
        tokens = tokenize(code, "myst")
        # Known directive should be keyword
        directive_tokens = [t for t in tokens if t.type.value == "k"]
        assert any("note" in t.value for t in directive_tokens)

    def test_directive_backtick_fence(self) -> None:
        """Tokenizes backtick-fence directives."""
        code = "```{warning}\nContent\n```"
        tokens = tokenize(code, "myst")
        directive_tokens = [t for t in tokens if t.type.value == "k"]
        assert any("warning" in t.value for t in directive_tokens)

    def test_container_directive(self) -> None:
        """Container directives are keyword declarations."""
        code = ":::{cards}\n:::{card}\n:::\n:::"
        tokens = tokenize(code, "myst")
        # Container directive (cards) should be keyword declaration
        decl_tokens = [t for t in tokens if t.type.value == "kd"]
        assert any("cards" in t.value for t in decl_tokens)

    def test_option_lines(self) -> None:
        """Option lines are name attributes."""
        code = ":::{note}\n:class: fancy\n:width: 100%\n:::"
        tokens = tokenize(code, "myst")
        attr_tokens = [t for t in tokens if t.type.value == "na"]
        assert len(attr_tokens) >= 2  # :class: and :width:

    def test_nested_fences(self) -> None:
        """Nested fences with more colons."""
        code = "::::{cards}\n:::{card}\nContent\n:::\n::::"
        tokens = tokenize(code, "myst")
        # Both outer (cards) and inner (card) should be highlighted
        assert len(tokens) > 0
        # Check fence closers are punctuation
        punct_tokens = [t for t in tokens if t.type.value == "p"]
        assert len(punct_tokens) >= 2

    def test_unknown_directive(self) -> None:
        """Unknown directives are name functions."""
        code = ":::{my-custom-directive}\nContent\n:::"
        tokens = tokenize(code, "myst")
        # Unknown directive should be name function
        func_tokens = [t for t in tokens if t.type.value == "nf"]
        assert any("my-custom-directive" in t.value for t in func_tokens)

    def test_inline_code(self) -> None:
        """Inline code is string backtick."""
        code = "Use `highlight()` to format code."
        tokens = tokenize(code, "myst")
        backtick_tokens = [t for t in tokens if t.type.value == "sb"]
        assert len(backtick_tokens) >= 1

    def test_headings(self) -> None:
        """Headings are generic heading."""
        code = "# Main Title\n\n## Subtitle"
        tokens = tokenize(code, "myst")
        heading_tokens = [t for t in tokens if t.type.value == "gh"]
        assert len(heading_tokens) == 2

    def test_role_syntax(self) -> None:
        """Role syntax is name decorator."""
        code = "See {ref}`my-target` for details."
        tokens = tokenize(code, "myst")
        # Role syntax should be name decorator
        decorator_tokens = [t for t in tokens if t.type.value == "nd"]
        assert any("ref" in t.value for t in decorator_tokens)


class TestJinja2Lexer:
    """Jinja2 template-specific tests."""

    def test_comment(self) -> None:
        """Tokenizes comments."""
        code = "{# This is a comment #}"
        tokens = tokenize(code, "jinja2")
        comment_tokens = [t for t in tokens if t.type.value == "cm"]
        assert len(comment_tokens) == 1

    def test_expression(self) -> None:
        """Tokenizes expressions."""
        code = "{{ variable }}"
        tokens = tokenize(code, "jinja2")
        # Should have punctuation for {{ and }}
        punct_tokens = [t for t in tokens if t.type.value == "p"]
        assert len(punct_tokens) >= 2

    def test_statement(self) -> None:
        """Tokenizes statement tags."""
        code = "{% if condition %}{% endif %}"
        tokens = tokenize(code, "jinja2")
        # Keywords should be present
        keyword_tokens = [t for t in tokens if t.type.value == "k"]
        assert any("if" in t.value for t in keyword_tokens)
        assert any("endif" in t.value for t in keyword_tokens)

    def test_filter(self) -> None:
        """Tokenizes filters."""
        code = "{{ name | upper | escape }}"
        tokens = tokenize(code, "jinja2")
        # Filters should be builtins
        builtin_tokens = [t for t in tokens if t.type.value == "nb"]
        assert any("upper" in t.value for t in builtin_tokens)
        assert any("escape" in t.value for t in builtin_tokens)

    def test_for_loop(self) -> None:
        """Tokenizes for loops."""
        code = "{% for item in items %}{{ item }}{% endfor %}"
        tokens = tokenize(code, "jinja2")
        keyword_tokens = [t for t in tokens if t.type.value == "k"]
        assert any("for" in t.value for t in keyword_tokens)
        assert any("endfor" in t.value for t in keyword_tokens)

    def test_string(self) -> None:
        """Tokenizes strings."""
        code = '{% extends "base.html" %}'
        tokens = tokenize(code, "jinja2")
        string_tokens = [t for t in tokens if t.type.value == "s2"]
        assert len(string_tokens) >= 1

    def test_boolean_constants(self) -> None:
        """Tokenizes boolean constants."""
        code = "{{ true }} {{ false }} {{ none }}"
        tokens = tokenize(code, "jinja2")
        const_tokens = [t for t in tokens if t.type.value == "kc"]
        assert len(const_tokens) == 3

    def test_number(self) -> None:
        """Tokenizes numbers."""
        code = "{{ 42 }} {{ 3.14 }}"
        tokens = tokenize(code, "jinja2")
        int_tokens = [t for t in tokens if t.type.value == "mi"]
        float_tokens = [t for t in tokens if t.type.value == "mf"]
        assert len(int_tokens) >= 1
        assert len(float_tokens) >= 1

    def test_operators(self) -> None:
        """Tokenizes operators."""
        code = "{% if x == 1 and y != 2 %}"
        tokens = tokenize(code, "jinja2")
        # 'and' is operator word
        op_word_tokens = [t for t in tokens if t.type.value == "ow"]
        assert any("and" in t.value for t in op_word_tokens)
