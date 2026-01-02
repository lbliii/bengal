"""Test template inheritance in Kida template engine.

Based on Jinja2's test_inheritance.py.
Tests extends, block, super(), and multi-level inheritance.
"""

import pytest

from bengal.rendering.kida import DictLoader, Environment


@pytest.fixture
def env():
    """Create a Kida environment with test templates."""
    loader = DictLoader(
        {
            "base.html": (
                "<html>"
                "<head>{% block head %}<title>{% block title %}Default{% endblock %}</title>{% endblock %}</head>"
                "<body>{% block body %}Base body{% endblock %}</body>"
                "</html>"
            ),
            "child.html": (
                '{% extends "base.html" %}'
                "{% block title %}Child Title{% endblock %}"
                "{% block body %}Child body{% endblock %}"
            ),
            "grandchild.html": (
                '{% extends "child.html" %}{% block title %}Grandchild Title{% endblock %}'
            ),
            "super_test.html": (
                '{% extends "base.html" %}{% block body %}{{ super() }} + Extended{% endblock %}'
            ),
            "multi_block.html": (
                '{% extends "base.html" %}'
                "{% block head %}{% block title %}Multi{% endblock %} Head{% endblock %}"
            ),
        }
    )
    return Environment(loader=loader)


class TestBasicInheritance:
    """Basic extends and block functionality."""

    def test_base_template(self, env):
        """Base template renders correctly."""
        tmpl = env.get_template("base.html")
        result = tmpl.render()
        assert "<html>" in result
        assert "<title>Default</title>" in result
        assert "Base body" in result

    def test_single_level_inheritance(self, env):
        """Child template overrides blocks."""
        tmpl = env.get_template("child.html")
        result = tmpl.render()
        assert "<html>" in result
        assert "<title>Child Title</title>" in result
        assert "Child body" in result
        assert "Default" not in result
        assert "Base body" not in result

    def test_multi_level_inheritance(self, env):
        """Multi-level inheritance chain."""
        tmpl = env.get_template("grandchild.html")
        result = tmpl.render()
        assert "<title>Grandchild Title</title>" in result
        # Body should be from child (not overridden in grandchild)
        assert "Child body" in result


class TestBlockBehavior:
    """Block behavior and features."""

    @pytest.mark.xfail(reason="super() may not be implemented")
    def test_super(self, env):
        """super() includes parent block content."""
        tmpl = env.get_template("super_test.html")
        result = tmpl.render()
        assert "Base body" in result
        assert "+ Extended" in result

    def test_block_from_string(self):
        """Block in from_string template."""
        env = Environment()
        tmpl = env.from_string("{% block content %}Default{% endblock %}")
        result = tmpl.render()
        assert result == "Default"

    def test_nested_blocks(self, env):
        """Nested blocks in inheritance."""
        tmpl = env.get_template("multi_block.html")
        result = tmpl.render()
        # The block title is inside block head
        assert "Multi" in result


class TestInheritanceWithContext:
    """Inheritance with context variables."""

    def test_context_in_child(self):
        """Context variables available in child blocks."""
        loader = DictLoader(
            {
                "base.html": "<h1>{% block title %}{% endblock %}</h1>",
                "child.html": '{% extends "base.html" %}{% block title %}{{ name }}{% endblock %}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render(name="Test")
        assert "<h1>Test</h1>" in result

    def test_set_in_child_block(self):
        """Set statement in child block."""
        loader = DictLoader(
            {
                "base.html": "{% block content %}{% endblock %}",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}{% set x = 42 %}{{ x }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        assert tmpl.render() == "42"


class TestInheritanceWithLoops:
    """Inheritance with loops in blocks."""

    def test_loop_in_block(self):
        """Loop inside a block."""
        loader = DictLoader(
            {
                "base.html": "<ul>{% block items %}{% endblock %}</ul>",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block items %}{% for item in items %}<li>{{ item }}</li>{% endfor %}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render(items=["a", "b", "c"])
        assert "<li>a</li>" in result
        assert "<li>b</li>" in result
        assert "<li>c</li>" in result


class TestInheritanceWithMacros:
    """Inheritance with macros."""

    def test_function_in_base(self):
        """Function defined in base, used in child."""
        loader = DictLoader(
            {
                "base.html": (
                    "{% def greet(name) %}Hello {{ name }}{% end %}"
                    "{% block content %}{% endblock %}"
                ),
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}{{ greet('World') }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render()
        assert "Hello World" in result

    def test_function_in_child(self):
        """Function defined in child block."""
        loader = DictLoader(
            {
                "base.html": "{% block content %}{% endblock %}",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}"
                    "{% def item(x) %}[{{ x }}]{% end %}"
                    "{{ item(1) }}{{ item(2) }}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render()
        assert "[1]" in result
        assert "[2]" in result


class TestInheritanceWithInclude:
    """Inheritance combined with include."""

    def test_include_in_block(self):
        """Include inside a block."""
        loader = DictLoader(
            {
                "base.html": "{% block content %}{% endblock %}",
                "partial.html": "<p>Partial content</p>",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% block content %}{% include "partial.html" %}{% endblock %}'
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render()
        assert "<p>Partial content</p>" in result


class TestInheritanceEdgeCases:
    """Edge cases in inheritance."""

    def test_empty_block(self):
        """Empty block in child."""
        loader = DictLoader(
            {
                "base.html": "{% block content %}Default{% endblock %}",
                "child.html": '{% extends "base.html" %}{% block content %}{% endblock %}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render()
        assert result == ""

    def test_block_with_whitespace(self):
        """Block with only whitespace."""
        loader = DictLoader(
            {
                "base.html": "[{% block content %}{% endblock %}]",
                "child.html": '{% extends "base.html" %}{% block content %}   {% endblock %}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render()
        assert "[" in result and "]" in result

    def test_multiple_extends_same_base(self):
        """Multiple children extending same base."""
        loader = DictLoader(
            {
                "base.html": "{% block content %}Base{% endblock %}",
                "child1.html": '{% extends "base.html" %}{% block content %}Child1{% endblock %}',
                "child2.html": '{% extends "base.html" %}{% block content %}Child2{% endblock %}',
            }
        )
        env = Environment(loader=loader)
        assert env.get_template("child1.html").render() == "Child1"
        assert env.get_template("child2.html").render() == "Child2"

    def test_block_in_conditional(self):
        """Block inside conditional (if allowed)."""
        loader = DictLoader(
            {
                "base.html": "{% block content %}{% endblock %}",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}"
                    "{% if show %}<p>Shown</p>{% endif %}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        assert "<p>Shown</p>" in tmpl.render(show=True)
        assert "<p>Shown</p>" not in tmpl.render(show=False)


class TestInheritanceFromString:
    """Inheritance with from_string templates."""

    def test_extends_loaded_template(self):
        """from_string extends a loaded template."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
            }
        )
        env = Environment(loader=loader)
        tmpl = env.from_string('{% extends "base.html" %}{% block content %}Hello{% endblock %}')
        result = tmpl.render()
        assert "<html>Hello</html>" in result


class TestInheritanceWithFromImport:
    """Inheritance combined with {% from %} imports."""

    def test_from_import_in_child_block(self):
        """{% from %} import in child template available in block."""
        loader = DictLoader(
            {
                "macros.html": "{% def greet(name) %}Hello, {{ name }}!{% end %}",
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% from "macros.html" import greet %}'
                    "{% block content %}{{ greet('World') }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render()
        assert "Hello, World!" in result

    def test_from_import_with_alias_in_child(self):
        """{% from %} import with alias works in child block."""
        loader = DictLoader(
            {
                "macros.html": "{% def greet(name) %}Hi, {{ name }}!{% end %}",
                "base.html": "{% block content %}{% endblock %}",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% from "macros.html" import greet as say_hi %}'
                    "{% block content %}{{ say_hi('Test') }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "Hi, Test!" in result

    def test_multiple_from_imports_in_child(self):
        """Multiple {% from %} imports in child template."""
        loader = DictLoader(
            {
                "utils.html": (
                    "{% def bold(text) %}<b>{{ text }}</b>{% end %}"
                    "{% def italic(text) %}<i>{{ text }}</i>{% end %}"
                ),
                "base.html": "{% block content %}{% endblock %}",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% from "utils.html" import bold, italic %}'
                    "{% block content %}{{ bold('A') }} {{ italic('B') }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<b>A</b>" in result
        assert "<i>B</i>" in result

    def test_from_import_with_context_in_child(self):
        """{% from %} import with context passes context to macro."""
        loader = DictLoader(
            {
                "macros.html": "{% def show_name() %}Name: {{ name }}{% end %}",
                "base.html": "{% block content %}{% endblock %}",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% from "macros.html" import show_name with context %}'
                    "{% block content %}{{ show_name() }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render(name="Alice")
        assert "Name: Alice" in result


class TestInheritanceWithScoping:
    """Tests for top-level statements (let, import, etc.) in child templates."""

    def test_let_in_child_available_in_block(self):
        """{% let %} in child template should be available in blocks."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% let my_var = "test_value" %}'
                    "{% block content %}{{ my_var }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        assert env.get_template("child.html").render() == "<html>test_value</html>"

    def test_import_as_in_child_available_in_block(self):
        """{% import ... as ... %} in child template should be available in blocks."""
        loader = DictLoader(
            {
                "macros.html": "{% def greet(name) %}Hello, {{ name }}!{% end %}",
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% import "macros.html" as m %}'
                    '{% block content %}{{ m.greet("World") }}{% endblock %}'
                ),
            }
        )
        env = Environment(loader=loader)
        assert env.get_template("child.html").render() == "<html>Hello, World!</html>"

    def test_export_in_child_available_in_block(self):
        """{% export %} in child template should be available in blocks."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% export exported_var = "exported" %}'
                    "{% block content %}{{ exported_var }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        assert env.get_template("child.html").render() == "<html>exported</html>"

    def test_do_in_child_executes(self):
        """{% do %} in child template should execute before blocks."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% do my_dict.update({"a": 1}) %}'
                    "{% block content %}{{ my_dict.a }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        my_dict = {}
        assert env.get_template("child.html").render(my_dict=my_dict) == "<html>1</html>"
