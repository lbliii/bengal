"""Test set, with, and include statements in Kida template engine.

Based on Jinja2's test_core_tags.py TestSet and TestWith classes.
Tests variable assignment, scoping, and template inclusion.
"""

import pytest

from bengal.rendering.kida import DictLoader, Environment


@pytest.fixture
def env():
    """Create a Kida environment for testing."""
    return Environment()


class TestSetStatement:
    """set statement functionality."""

    def test_simple_set(self, env):
        """Simple set statement."""
        tmpl = env.from_string("{% set x = 42 %}{{ x }}")
        assert tmpl.render() == "42"

    def test_set_string(self, env):
        """Set string value."""
        tmpl = env.from_string("{% set name = 'World' %}Hello {{ name }}")
        assert tmpl.render() == "Hello World"

    def test_set_expression(self, env):
        """Set with expression."""
        tmpl = env.from_string("{% set result = a + b %}{{ result }}")
        assert tmpl.render(a=2, b=3) == "5"

    def test_set_list(self, env):
        """Set list value."""
        tmpl = env.from_string("{% set items = [1, 2, 3] %}{{ items|join(',') }}")
        assert tmpl.render() == "1,2,3"

    def test_set_dict(self, env):
        """Set dict value."""
        tmpl = env.from_string("{% set d = {'a': 1, 'b': 2} %}{{ d.a }}-{{ d.b }}")
        assert tmpl.render() == "1-2"

    def test_set_override(self, env):
        """Set overrides context variable."""
        tmpl = env.from_string("{% set x = 'new' %}{{ x }}")
        assert tmpl.render(x="old") == "new"

    def test_multiple_set(self, env):
        """Multiple set statements."""
        tmpl = env.from_string("{% set a = 1 %}{% set b = 2 %}{% set c = a + b %}{{ c }}")
        assert tmpl.render() == "3"


class TestSetTupleUnpacking:
    """Set with tuple unpacking."""

    def test_tuple_unpacking(self, env):
        """Tuple unpacking in set."""
        tmpl = env.from_string("{% set a, b = 1, 2 %}{{ a }}-{{ b }}")
        assert tmpl.render() == "1-2"

    def test_list_unpacking(self, env):
        """Unpacking from list."""
        tmpl = env.from_string("{% set a, b, c = items %}{{ a }}-{{ b }}-{{ c }}")
        assert tmpl.render(items=[1, 2, 3]) == "1-2-3"


class TestSetBlock:
    """Set block (capture) functionality."""

    @pytest.mark.xfail(reason="set block may not be implemented")
    def test_set_block(self, env):
        """Set block captures content."""
        tmpl = env.from_string("{% set content %}Hello World{% endset %}{{ content }}")
        assert tmpl.render() == "Hello World"

    @pytest.mark.xfail(reason="set block may not be implemented")
    def test_set_block_with_vars(self, env):
        """Set block with variable interpolation."""
        tmpl = env.from_string("{% set greeting %}Hello {{ name }}{% endset %}{{ greeting }}")
        assert tmpl.render(name="World") == "Hello World"


class TestWithStatement:
    """with statement functionality."""

    def test_with_basic(self, env):
        """Basic with statement."""
        tmpl = env.from_string("{% with x = 42 %}{{ x }}{% endwith %}")
        assert tmpl.render() == "42"

    def test_with_multiple_vars(self, env):
        """With multiple variables."""
        tmpl = env.from_string("{% with a = 1, b = 2 %}{{ a }}-{{ b }}{% endwith %}")
        assert tmpl.render() == "1-2"

    def test_with_scoping(self, env):
        """With creates local scope."""
        tmpl = env.from_string(
            "{% set x = 'outer' %}{% with x = 'inner' %}{{ x }}{% endwith %}-{{ x }}"
        )
        result = tmpl.render()
        assert "inner" in result
        assert "outer" in result

    def test_with_expression(self, env):
        """With using expressions."""
        tmpl = env.from_string("{% with total = a + b %}{{ total }}{% endwith %}")
        assert tmpl.render(a=2, b=3) == "5"

    def test_with_reassign_context_var(self, env):
        """With assigns from context variable."""
        tmpl = env.from_string("{% with local = ctx_value %}{{ local }}{% endwith %}")
        assert tmpl.render(ctx_value="hello") == "hello"


class TestIncludeStatement:
    """include statement functionality."""

    def test_simple_include(self):
        """Simple include."""
        loader = DictLoader(
            {
                "partial.html": "Hello World",
                "main.html": '{% include "partial.html" %}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        assert tmpl.render() == "Hello World"

    def test_include_with_context(self):
        """Include receives context."""
        loader = DictLoader(
            {
                "partial.html": "Hello {{ name }}",
                "main.html": '{% include "partial.html" %}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        assert tmpl.render(name="World") == "Hello World"

    def test_include_multiple(self):
        """Multiple includes."""
        loader = DictLoader(
            {
                "header.html": "<header>Header</header>",
                "footer.html": "<footer>Footer</footer>",
                "main.html": '{% include "header.html" %}Content{% include "footer.html" %}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        result = tmpl.render()
        assert "<header>Header</header>" in result
        assert "Content" in result
        assert "<footer>Footer</footer>" in result

    def test_include_nested(self):
        """Nested includes."""
        loader = DictLoader(
            {
                "deep.html": "Deep",
                "middle.html": 'Middle{% include "deep.html" %}',
                "main.html": 'Main{% include "middle.html" %}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        result = tmpl.render()
        assert "Main" in result
        assert "Middle" in result
        assert "Deep" in result

    def test_include_with_vars(self):
        """Include with variable in path."""
        loader = DictLoader(
            {
                "en.html": "English",
                "es.html": "Spanish",
            }
        )
        env = Environment(loader=loader)
        # Using variable path requires include to accept variables
        # This may or may not be supported
        tmpl = env.from_string('{% include lang ~ ".html" %}')
        result = tmpl.render(lang="en")
        assert result == "English"

    def test_include_recursion_limit_circular(self):
        """Circular includes raise TemplateRuntimeError."""
        from bengal.rendering.kida.environment.exceptions import TemplateRuntimeError

        loader = DictLoader(
            {
                "a.html": 'A{% include "b.html" %}',
                "b.html": 'B{% include "a.html" %}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("a.html")

        with pytest.raises(TemplateRuntimeError) as exc_info:
            tmpl.render()

        error_msg = str(exc_info.value)
        assert "Maximum include depth exceeded" in error_msg
        assert "Check for circular includes" in error_msg

    def test_include_recursion_limit_deep(self):
        """Deep but legitimate includes work up to limit."""
        # Create 50 levels of includes (just under the limit)
        templates = {}
        for i in range(50):
            if i == 49:
                templates[f"level{i}.html"] = f"Level {i}"
            else:
                templates[f"level{i}.html"] = f"Level {i}{{% include 'level{i+1}.html' %}}"

        loader = DictLoader(templates)
        env = Environment(loader=loader)
        tmpl = env.get_template("level0.html")
        result = tmpl.render()
        # Should render successfully
        assert "Level 0" in result
        assert "Level 49" in result

    def test_include_recursion_limit_exceeded(self):
        """Includes exceeding limit raise TemplateRuntimeError."""
        from bengal.rendering.kida.environment.exceptions import TemplateRuntimeError

        # Create 52 levels (exceeds limit of 50)
        # level0 includes level1 at depth 1, ... level50 includes level51 at depth 51 (> 50)
        templates = {}
        for i in range(52):
            if i == 51:
                templates[f"level{i}.html"] = f"Level {i}"
            else:
                templates[f"level{i}.html"] = f"Level {i}{{% include 'level{i+1}.html' %}}"

        loader = DictLoader(templates)
        env = Environment(loader=loader)
        tmpl = env.get_template("level0.html")

        with pytest.raises(TemplateRuntimeError) as exc_info:
            tmpl.render()

        error_msg = str(exc_info.value)
        assert "Maximum include depth exceeded" in error_msg
        assert "50" in error_msg


class TestIncludeIgnoreMissing:
    """include with ignore missing."""

    @pytest.mark.xfail(reason="ignore missing may not be implemented")
    def test_ignore_missing(self):
        """Include with ignore missing."""
        loader = DictLoader(
            {
                "main.html": '{% include "nonexistent.html" ignore missing %}Fallback',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        result = tmpl.render()
        assert result == "Fallback"


class TestComments:
    """Comment syntax."""

    def test_simple_comment(self, env):
        """Simple comment."""
        tmpl = env.from_string("Hello{# this is a comment #} World")
        assert tmpl.render() == "Hello World"

    def test_multiline_comment(self, env):
        """Multiline comment."""
        tmpl = env.from_string("Hello{# this is\na multiline\ncomment #} World")
        assert tmpl.render() == "Hello World"

    def test_comment_with_code(self, env):
        """Comment containing template code."""
        tmpl = env.from_string("Hello{# {% if true %}hidden{% endif %} #} World")
        assert tmpl.render() == "Hello World"


class TestRawBlock:
    """raw block functionality."""

    def test_raw_basic(self, env):
        """Raw block prevents processing."""
        tmpl = env.from_string("{% raw %}{{ not_a_var }}{% endraw %}")
        assert tmpl.render() == "{{ not_a_var }}"

    def test_raw_with_tags(self, env):
        """Raw with template tags."""
        tmpl = env.from_string("{% raw %}{% if true %}show{% endif %}{% endraw %}")
        assert tmpl.render() == "{% if true %}show{% endif %}"

    def test_raw_multiline(self, env):
        """Multiline raw block."""
        tmpl = env.from_string(
            "{% raw %}\n{{ var }}\n{% for x in y %}{{ x }}{% endfor %}\n{% endraw %}"
        )
        result = tmpl.render()
        assert "{{ var }}" in result
        assert "{% for" in result


class TestExpressionStatements:
    """Expression and output statements."""

    def test_simple_output(self, env):
        """Simple output."""
        tmpl = env.from_string("{{ x }}")
        assert tmpl.render(x=42) == "42"

    def test_output_with_filter(self, env):
        """Output with filter."""
        tmpl = env.from_string("{{ name|upper }}")
        assert tmpl.render(name="hello") == "HELLO"

    def test_complex_expression(self, env):
        """Complex expression output."""
        tmpl = env.from_string("{{ (a + b) * c }}")
        assert tmpl.render(a=2, b=3, c=4) == "20"

    def test_method_call(self, env):
        """Method call in output."""
        tmpl = env.from_string("{{ text.upper() }}")
        assert tmpl.render(text="hello") == "HELLO"

    def test_subscript(self, env):
        """Subscript access."""
        tmpl = env.from_string("{{ items[0] }}-{{ items[1] }}")
        assert tmpl.render(items=["a", "b"]) == "a-b"

    def test_attribute(self, env):
        """Attribute access."""

        class Obj:
            name = "test"

        tmpl = env.from_string("{{ obj.name }}")
        assert tmpl.render(obj=Obj()) == "test"

    def test_negative_subscript(self, env):
        """Negative subscript."""
        tmpl = env.from_string("{{ items[-1] }}")
        assert tmpl.render(items=[1, 2, 3]) == "3"
