"""Tests for conditional {% with %} block.

Conditional with provides nil-resilient template blocks that:
- Skip rendering when expression is falsy (None, empty dict, etc.)
- Bind expression value to 'it' or custom variable name via 'as'
- Coexist with assignment-style {% with x = expr %} syntax
"""

import pytest

from bengal.rendering.kida import Environment
from bengal.rendering.kida.nodes import With, WithConditional


class TestConditionalWithParsing:
    """Test parsing of conditional with syntax."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_parse_conditional_default_binding(self, env):
        """{% with expr %} binds to 'it' by default."""
        from bengal.rendering.kida.lexer import tokenize
        from bengal.rendering.kida.parser import Parser

        source = "{% with page.author %}{{ it.name }}{% end %}"
        tokens = tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()
        node = ast.body[0]

        assert isinstance(node, WithConditional)
        assert node.target.name == "it"

    def test_parse_conditional_as_binding(self, env):
        """{% with expr as name %} binds to custom name."""
        from bengal.rendering.kida.lexer import tokenize
        from bengal.rendering.kida.parser import Parser

        source = "{% with page.author as author %}{{ author.name }}{% end %}"
        tokens = tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()
        node = ast.body[0]

        assert isinstance(node, WithConditional)
        assert node.target.name == "author"

    def test_parse_assignment_style_unchanged(self, env):
        """{% with x = expr %} produces assignment-style With node."""
        from bengal.rendering.kida.lexer import tokenize
        from bengal.rendering.kida.parser import Parser

        source = "{% with x = 1, y = 2 %}{{ x }} {{ y }}{% end %}"
        tokens = tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()
        node = ast.body[0]

        assert isinstance(node, With)
        assert len(node.targets) == 2


class TestConditionalWithRendering:
    """Test rendering behavior of conditional with."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_truthy_value_renders(self, env):
        """Block renders when expression is truthy."""
        template = env.from_string(
            "{% with page.author as author %}Name: {{ author.name }}{% end %}"
        )
        result = template.render(page={"author": {"name": "Alice"}})
        assert result == "Name: Alice"

    def test_none_skips_block(self, env):
        """Block is skipped when expression is None."""
        template = env.from_string(
            "{% with page.author as author %}Name: {{ author.name }}{% end %}"
        )
        result = template.render(page={"author": None})
        assert result == ""

    def test_empty_dict_skips_block(self, env):
        """Block is skipped when expression is empty dict."""
        template = env.from_string(
            "{% with page.author as author %}Name: {{ author.name }}{% end %}"
        )
        result = template.render(page={"author": {}})
        assert result == ""

    def test_empty_list_skips_block(self, env):
        """Block is skipped when expression is empty list."""
        template = env.from_string("{% with items as items %}{{ items | length }}{% end %}")
        result = template.render(items=[])
        assert result == ""

    def test_empty_string_skips_block(self, env):
        """Block is skipped when expression is empty string."""
        template = env.from_string("{% with name as name %}Hello {{ name }}{% end %}")
        result = template.render(name="")
        assert result == ""

    def test_zero_skips_block(self, env):
        """Block is skipped when expression is 0."""
        template = env.from_string("{% with count as count %}Count: {{ count }}{% end %}")
        result = template.render(count=0)
        assert result == ""

    def test_false_skips_block(self, env):
        """Block is skipped when expression is False."""
        template = env.from_string("{% with flag as flag %}Flag: {{ flag }}{% end %}")
        result = template.render(flag=False)
        assert result == ""

    def test_default_it_binding(self, env):
        """Default 'it' binding works."""
        template = env.from_string("{% with page.author %}Name: {{ it.name }}{% end %}")
        result = template.render(page={"author": {"name": "Bob"}})
        assert result == "Name: Bob"


class TestConditionalWithNesting:
    """Test nested conditional with blocks."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_nested_both_truthy(self, env):
        """Nested blocks both render when both truthy."""
        template = env.from_string(
            "{% with data.outer as outer %}O:{{ outer.value }} "
            "{% with outer.inner as inner %}I:{{ inner.value }}{% end %}{% end %}"
        )
        result = template.render(data={"outer": {"value": "A", "inner": {"value": "B"}}})
        assert result == "O:A I:B"

    def test_nested_inner_falsy(self, env):
        """Only inner block skipped when inner is falsy."""
        template = env.from_string(
            "{% with data.outer as outer %}O:{{ outer.value }} "
            "{% with outer.inner as inner %}I:{{ inner.value }}{% end %}{% end %}"
        )
        result = template.render(data={"outer": {"value": "A", "inner": None}})
        assert result == "O:A "

    def test_nested_outer_falsy(self, env):
        """Entire block skipped when outer is falsy."""
        template = env.from_string(
            "{% with data.outer as outer %}O:{{ outer.value }} "
            "{% with outer.inner as inner %}I:{{ inner.value }}{% end %}{% end %}"
        )
        result = template.render(data={"outer": None})
        assert result == ""


class TestConditionalWithScopeRestoration:
    """Test that variable scope is properly restored after with block."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_variable_restored_after_block(self, env):
        """Variable from outer scope is restored after with block."""
        template = env.from_string(
            "{% with other as author %}A:{{ author }}{% end %}B:{{ author }}"
        )
        result = template.render(author="Original", other="Replaced")
        assert result == "A:ReplacedB:Original"

    def test_undefined_variable_not_leaked(self, env):
        """Variable defined in with block doesn't leak."""
        template = env.from_string("before {% with data as x %}{{ x }}{% end %} after")
        result = template.render(data="value")
        assert result == "before value after"


class TestConditionalWithIntegration:
    """Integration tests with other template features."""

    @pytest.fixture
    def env(self):
        return Environment()

    def test_with_in_for_loop(self, env):
        """Conditional with inside for loop."""
        template = env.from_string(
            "{% for item in items %}{% with item.data as data %}{{ data.name }}{% end %}{% end %}"
        )
        result = template.render(
            items=[
                {"data": {"name": "A"}},
                {"data": None},
                {"data": {"name": "C"}},
            ]
        )
        assert result == "AC"

    def test_with_in_if(self, env):
        """Conditional with inside if block."""
        template = env.from_string(
            "{% if show %}{% with data as d %}{{ d.value }}{% end %}{% end %}"
        )
        result = template.render(show=True, data={"value": "X"})
        assert result == "X"

    def test_mixed_styles(self, env):
        """Assignment-style and conditional with coexist."""
        template = env.from_string(
            "{% with x = 10 %}{{ x }}{% end %}-{% with data as d %}{{ d.y }}{% end %}"
        )
        result = template.render(data={"y": 20})
        assert result == "10-20"
