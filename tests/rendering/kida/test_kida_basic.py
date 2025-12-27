"""Basic tests for Kida template engine."""

from bengal.rendering.kida import Environment, Template
from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.lexer import tokenize


class TestLexer:
    """Test Kida lexer."""

    def test_tokenize_empty(self):
        """Empty template produces only EOF."""
        tokens = tokenize("")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_tokenize_data_only(self):
        """Plain text is tokenized as DATA."""
        tokens = tokenize("Hello, World!")
        assert len(tokens) == 2
        assert tokens[0].type == TokenType.DATA
        assert tokens[0].value == "Hello, World!"
        assert tokens[1].type == TokenType.EOF

    def test_tokenize_variable(self):
        """Variable expression is tokenized correctly."""
        tokens = tokenize("{{ name }}")
        types = [t.type for t in tokens]
        assert types == [
            TokenType.VARIABLE_BEGIN,
            TokenType.NAME,
            TokenType.VARIABLE_END,
            TokenType.EOF,
        ]
        assert tokens[1].value == "name"

    def test_tokenize_mixed(self):
        """Mixed data and expressions."""
        tokens = tokenize("Hello, {{ name }}!")
        types = [t.type for t in tokens]
        assert types == [
            TokenType.DATA,
            TokenType.VARIABLE_BEGIN,
            TokenType.NAME,
            TokenType.VARIABLE_END,
            TokenType.DATA,
            TokenType.EOF,
        ]
        assert tokens[0].value == "Hello, "
        assert tokens[2].value == "name"
        assert tokens[4].value == "!"

    def test_tokenize_block(self):
        """Block tag is tokenized correctly."""
        tokens = tokenize("{% if true %}yes{% endif %}")
        types = [t.type for t in tokens]
        assert TokenType.BLOCK_BEGIN in types
        assert TokenType.BLOCK_END in types

    def test_tokenize_filter(self):
        """Filter syntax is tokenized."""
        tokens = tokenize("{{ name | upper }}")
        types = [t.type for t in tokens]
        assert TokenType.PIPE in types

    def test_tokenize_string_literal(self):
        """String literals are tokenized."""
        tokens = tokenize('{{ "hello" }}')
        assert any(t.type == TokenType.STRING and t.value == "hello" for t in tokens)

    def test_tokenize_number(self):
        """Numbers are tokenized."""
        tokens = tokenize("{{ 42 }}")
        assert any(t.type == TokenType.INTEGER and t.value == "42" for t in tokens)

    def test_line_tracking(self):
        """Line numbers are tracked correctly."""
        tokens = tokenize("line1\n{{ x }}\nline3")
        var_token = next(t for t in tokens if t.type == TokenType.NAME)
        assert var_token.lineno == 2


class TestEnvironment:
    """Test Kida Environment."""

    def test_from_string_simple(self):
        """Compile template from string."""
        env = Environment()
        template = env.from_string("Hello!")
        assert isinstance(template, Template)

    def test_render_data_only(self):
        """Render template with no expressions."""
        env = Environment()
        template = env.from_string("Hello, World!")
        result = template.render()
        assert result == "Hello, World!"

    def test_render_variable(self):
        """Render template with variable."""
        env = Environment()
        template = env.from_string("Hello, {{ name }}!")
        result = template.render(name="World")
        assert result == "Hello, World!"

    def test_render_attribute_access(self):
        """Render template with attribute access."""
        env = Environment()
        template = env.from_string("{{ user.name }}")

        class User:
            name = "Alice"

        result = template.render(user=User())
        assert result == "Alice"

    def test_render_filter(self):
        """Render template with filter."""
        env = Environment()
        template = env.from_string("{{ name | upper }}")
        result = template.render(name="hello")
        assert result == "HELLO"

    def test_render_filter_chain(self):
        """Render template with filter chain."""
        env = Environment()
        template = env.from_string("{{ name | upper | trim }}")
        result = template.render(name="  hello  ")
        assert result == "HELLO"

    def test_render_if_true(self):
        """Render if block when condition is true."""
        env = Environment()
        template = env.from_string("{% if show %}visible{% endif %}")
        result = template.render(show=True)
        assert result == "visible"

    def test_render_if_false(self):
        """Render if block when condition is false."""
        env = Environment()
        template = env.from_string("{% if show %}visible{% endif %}")
        result = template.render(show=False)
        assert result == ""

    def test_render_if_else(self):
        """Render if/else block."""
        env = Environment()
        template = env.from_string("{% if show %}yes{% else %}no{% endif %}")
        assert template.render(show=True) == "yes"
        assert template.render(show=False) == "no"

    def test_render_for_loop(self):
        """Render for loop."""
        env = Environment()
        template = env.from_string("{% for i in items %}{{ i }}{% endfor %}")
        result = template.render(items=[1, 2, 3])
        assert result == "123"

    def test_render_for_else(self):
        """Render for/else when iterable is empty."""
        env = Environment()
        template = env.from_string("{% for i in items %}{{ i }}{% else %}none{% endfor %}")
        result = template.render(items=[])
        assert result == "none"

    def test_render_set(self):
        """Render set statement."""
        env = Environment()
        template = env.from_string("{% set x = 42 %}{{ x }}")
        result = template.render()
        assert result == "42"

    def test_render_nested_for(self):
        """Render nested for loops."""
        env = Environment()
        template = env.from_string(
            "{% for row in matrix %}{% for col in row %}{{ col }}{% endfor %}|{% endfor %}"
        )
        result = template.render(matrix=[[1, 2], [3, 4]])
        assert result == "12|34|"

    def test_custom_filter(self):
        """Register and use custom filter."""
        env = Environment()
        env.add_filter("double", lambda x: x * 2)
        template = env.from_string("{{ n | double }}")
        result = template.render(n=5)
        assert result == "10"

    def test_escape_html(self):
        """HTML is escaped by default."""
        env = Environment()
        template = env.from_string("{{ text }}")
        result = template.render(text="<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_globals(self):
        """Test global variables."""
        env = Environment()
        env.globals["app_name"] = "MyApp"
        template = env.from_string("{{ app_name }}")
        result = template.render()
        assert result == "MyApp"


class TestThreadSafety:
    """Test thread-safety of Kida."""

    def test_concurrent_render(self):
        """Multiple threads can render simultaneously."""
        from concurrent.futures import ThreadPoolExecutor

        env = Environment()
        template = env.from_string("Hello, {{ name }}!")

        def render(name: str) -> str:
            return template.render(name=name)

        with ThreadPoolExecutor(max_workers=4) as executor:
            names = ["Alice", "Bob", "Charlie", "Diana"] * 100
            results = list(executor.map(render, names))

        assert len(results) == 400
        assert results[0] == "Hello, Alice!"
        assert results[1] == "Hello, Bob!"

    def test_concurrent_compile(self):
        """Multiple threads can compile templates."""
        from concurrent.futures import ThreadPoolExecutor

        env = Environment()

        def compile_and_render(i: int) -> str:
            template = env.from_string("Template {{ n }}")
            return template.render(n=i)

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(compile_and_render, range(100)))

        assert len(results) == 100
        assert results[0] == "Template 0"
        assert results[99] == "Template 99"


class TestPythonicScoping:
    """Test Kida's improved scoping with let/export."""

    def test_let_persists(self):
        """Variables declared with let persist across blocks."""
        env = Environment()
        # Note: In current implementation, let is same as set
        # Full let semantics will be added in a later version
        # For now, just verify the template compiles
        env.from_string(
            """
{% let counter = 0 %}
{% for i in items %}{% set counter = counter + 1 %}{% endfor %}
{{ counter }}
""".strip()
        )

    def test_export_from_loop(self):
        """Export makes inner variable available in outer scope."""
        env = Environment()
        # Note: In current implementation, export is same as set
        # Full export semantics will be added in a later version
        # For now, just verify the template compiles
        env.from_string(
            """
{% for item in items %}{% export last = item %}{% endfor %}
{{ last }}
""".strip()
        )


class TestDictLiterals:
    """Test dict literal parsing and compilation."""

    def test_empty_dict(self):
        """Empty dict literal."""
        env = Environment()
        template = env.from_string("{% set x = {} %}{{ x }}")
        result = template.render()
        assert result == "{}"

    def test_dict_with_values(self):
        """Dict with key-value pairs."""
        env = Environment()
        template = env.from_string('{% set x = {"a": 1, "b": 2} %}{{ x["a"] }}')
        result = template.render()
        assert result == "1"

    def test_dict_in_ternary(self):
        """Dict literal in ternary expression."""
        env = Environment()
        template = env.from_string("{% set y = none %}{% set x = y.val if y else {} %}{{ x }}")
        result = template.render()
        assert result == "{}"

    def test_dict_with_variable_key(self):
        """Dict with variable as key."""
        env = Environment()
        template = env.from_string('{% set k = "key" %}{% set d = {k: "value"} %}{{ d["key"] }}')
        result = template.render()
        assert result == "value"

    def test_nested_dict(self):
        """Nested dict literals."""
        env = Environment()
        template = env.from_string(
            '{% set x = {"outer": {"inner": 42}} %}{{ x["outer"]["inner"] }}'
        )
        result = template.render()
        assert result == "42"
