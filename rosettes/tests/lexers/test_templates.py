"""Template language lexer tests (Jinja2, MyST, Liquid, etc.)."""

from rosettes import tokenize


class TestMystLexer:
    """MyST Markdown-specific tests."""

    def test_directive_colon_fence(self) -> None:
        """Tokenizes colon-fence directives."""
        code = ":::{note}\nContent\n:::"
        tokens = tokenize(code, "myst")
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
        decl_tokens = [t for t in tokens if t.type.value == "kd"]
        assert any("cards" in t.value for t in decl_tokens)

    def test_option_lines(self) -> None:
        """Option lines are name attributes."""
        code = ":::{note}\n:class: fancy\n:width: 100%\n:::"
        tokens = tokenize(code, "myst")
        attr_tokens = [t for t in tokens if t.type.value == "na"]
        assert len(attr_tokens) >= 2

    def test_nested_fences(self) -> None:
        """Nested fences with more colons."""
        code = "::::{cards}\n:::{card}\nContent\n:::\n::::"
        tokens = tokenize(code, "myst")
        assert len(tokens) > 0
        punct_tokens = [t for t in tokens if t.type.value == "p"]
        assert len(punct_tokens) >= 2

    def test_unknown_directive(self) -> None:
        """Unknown directives are name functions."""
        code = ":::{my-custom-directive}\nContent\n:::"
        tokens = tokenize(code, "myst")
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
        punct_tokens = [t for t in tokens if t.type.value == "p"]
        assert len(punct_tokens) >= 2

    def test_statement(self) -> None:
        """Tokenizes statement tags."""
        code = "{% if condition %}{% endif %}"
        tokens = tokenize(code, "jinja2")
        keyword_tokens = [t for t in tokens if t.type.value == "k"]
        assert any("if" in t.value for t in keyword_tokens)
        assert any("endif" in t.value for t in keyword_tokens)

    def test_filter(self) -> None:
        """Tokenizes filters."""
        code = "{{ name | upper | escape }}"
        tokens = tokenize(code, "jinja2")
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
        op_word_tokens = [t for t in tokens if t.type.value == "ow"]
        assert any("and" in t.value for t in op_word_tokens)
