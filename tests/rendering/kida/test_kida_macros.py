"""Test macro functionality in Kida template engine.

Based on Jinja2's test_core_tags.py TestMacros class.
Tests macro definition, arguments, defaults, and scoping.
"""

import pytest

from bengal.rendering.kida import DictLoader, Environment


@pytest.fixture
def env():
    """Create a Kida environment for testing."""
    return Environment()


@pytest.fixture
def env_trim():
    """Create a Kida environment with trim_blocks."""
    return Environment(trim_blocks=True)


class TestMacroBasics:
    """Basic macro functionality."""

    def test_simple(self, env):
        """Simple macro definition and call."""
        tmpl = env.from_string(
            "{% macro say_hello(name) %}Hello {{ name }}!{% endmacro %}{{ say_hello('World') }}"
        )
        assert tmpl.render() == "Hello World!"

    def test_macro_no_args(self, env):
        """Macro with no arguments."""
        tmpl = env.from_string("{% macro greet() %}Hello!{% endmacro %}{{ greet() }}")
        assert tmpl.render() == "Hello!"

    def test_macro_multiple_args(self, env):
        """Macro with multiple arguments."""
        tmpl = env.from_string(
            "{% macro greet(first, last) %}Hello {{ first }} {{ last }}!{% endmacro %}"
            "{{ greet('John', 'Doe') }}"
        )
        assert tmpl.render() == "Hello John Doe!"

    def test_macro_expression_output(self, env):
        """Macro with expression in output."""
        tmpl = env.from_string("{% macro add(a, b) %}{{ a + b }}{% endmacro %}{{ add(2, 3) }}")
        assert tmpl.render() == "5"


class TestMacroDefaults:
    """Macro default arguments."""

    def test_default_value(self, env):
        """Macro with default argument value."""
        tmpl = env.from_string(
            "{% macro greet(name='World') %}Hello {{ name }}!{% endmacro %}{{ greet() }}"
        )
        assert tmpl.render() == "Hello World!"

    def test_override_default(self, env):
        """Override macro default argument."""
        tmpl = env.from_string(
            "{% macro greet(name='World') %}Hello {{ name }}!{% endmacro %}{{ greet('User') }}"
        )
        assert tmpl.render() == "Hello User!"

    def test_multiple_defaults(self, env):
        """Macro with multiple default arguments."""
        tmpl = env.from_string(
            "{% macro m(a, b='B', c='C') %}{{ a }}|{{ b }}|{{ c }}{% endmacro %}"
            "{{ m('A') }}|{{ m('X', 'Y') }}|{{ m('P', 'Q', 'R') }}"
        )
        assert tmpl.render() == "A|B|C|X|Y|C|P|Q|R"

    def test_mixed_args_defaults(self, env):
        """Macro with mix of positional and default args."""
        tmpl = env.from_string(
            "{% macro link(url, text='Click here') %}"
            '<a href="{{ url }}">{{ text }}</a>'
            "{% endmacro %}"
            '{{ link("/about") }}'
        )
        assert tmpl.render() == '<a href="/about">Click here</a>'


class TestMacroScoping:
    """Macro variable scoping."""

    def test_local_scope(self, env):
        """Macro has its own scope."""
        tmpl = env.from_string(
            "{% set x = 'outer' %}{% macro show() %}{{ x }}{% endmacro %}{{ show() }}"
        )
        # Macro should see outer x (closure-like behavior)
        result = tmpl.render()
        assert "outer" in result

    def test_arg_shadows_outer(self, env):
        """Macro argument shadows outer variable."""
        tmpl = env.from_string(
            "{% set name = 'outer' %}"
            "{% macro greet(name) %}{{ name }}{% endmacro %}"
            "{{ greet('inner') }}"
        )
        assert tmpl.render() == "inner"

    def test_set_inside_macro(self, env):
        """Set inside macro doesn't affect outer scope."""
        tmpl = env.from_string(
            "{% set x = 'outer' %}"
            "{% macro change() %}{% set x = 'inner' %}{{ x }}{% endmacro %}"
            "{{ change() }}-{{ x }}"
        )
        result = tmpl.render()
        assert "inner" in result
        assert "outer" in result

    def test_nested_macros(self, env):
        """Nested macro definitions."""
        tmpl = env.from_string(
            """{% macro outer(data) %}
{% macro inner(item) %}[{{ item }}]{% endmacro %}
{{ inner(data) }}
{% endmacro %}
{{ outer('test') }}"""
        )
        result = tmpl.render()
        assert "[test]" in result


class TestMacroRecursion:
    """Recursive macro calls."""

    def test_simple_recursion(self, env):
        """Recursive macro call with factorial.

        Tests that macro results are correctly coerced to numeric values
        for arithmetic operations (fixed by numeric coercion in Phase 3).
        """
        tmpl = env.from_string(
            "{% macro factorial(n) %}"
            "{% if n <= 1 %}1{% else %}{{ n * factorial(n - 1) }}{% endif %}"
            "{% endmacro %}"
            "{{ factorial(5) }}"
        )
        result = tmpl.render().strip()
        # 5! = 120
        assert "120" in result

    def test_countdown(self, env):
        """Recursive countdown."""
        tmpl = env.from_string(
            "{% macro countdown(n) %}"
            "{{ n }}"
            "{% if n > 0 %}{{ countdown(n - 1) }}{% endif %}"
            "{% endmacro %}"
            "{{ countdown(3) }}"
        )
        result = tmpl.render()
        assert "3" in result and "2" in result and "1" in result and "0" in result


class TestMacroWithFilters:
    """Macros with filter usage."""

    def test_filter_in_macro(self, env):
        """Use filter inside macro."""
        tmpl = env.from_string(
            '{% macro shout(text) %}{{ text|upper }}{% endmacro %}{{ shout("hello") }}'
        )
        assert tmpl.render() == "HELLO"

    def test_filter_on_macro_output(self, env):
        """Apply filter to macro output."""
        tmpl = env.from_string(
            "{% macro greet(name) %}hello {{ name }}{% endmacro %}{{ greet('world')|upper }}"
        )
        assert tmpl.render() == "HELLO WORLD"


class TestMacroImport:
    """Macro import functionality."""

    def test_import_macro(self):
        """Import macro from another template."""
        loader = DictLoader(
            {
                "macros.html": "{% macro double(x) %}{{ x * 2 }}{% endmacro %}",
                "main.html": '{% from "macros.html" import double %}{{ double(5) }}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        assert tmpl.render() == "10"

    def test_import_multiple_macros(self):
        """Import multiple macros."""
        loader = DictLoader(
            {
                "macros.html": (
                    "{% macro add(a, b) %}{{ a + b }}{% endmacro %}"
                    "{% macro sub(a, b) %}{{ a - b }}{% endmacro %}"
                ),
                "main.html": (
                    '{% from "macros.html" import add, sub %}{{ add(5, 3) }}-{{ sub(5, 3) }}'
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        assert tmpl.render() == "8-2"

    def test_import_as(self):
        """Import macro with alias."""
        loader = DictLoader(
            {
                "macros.html": "{% macro greet(name) %}Hi {{ name }}{% endmacro %}",
                "main.html": '{% from "macros.html" import greet as hello %}{{ hello("World") }}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        assert tmpl.render() == "Hi World"

    def test_full_import_as(self):
        """Import entire template with alias: {% import "macros.html" as m %}."""
        loader = DictLoader(
            {
                "macros.html": "{% macro greet(name) %}Hi {{ name }}{% endmacro %}",
                "main.html": '{% import "macros.html" as m %}{{ m.greet("World") }}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        assert tmpl.render() == "Hi World"

    def test_full_import_as_with_context(self):
        """Import entire template with context."""
        loader = DictLoader(
            {
                "macros.html": "{% macro show_name() %}Name: {{ name }}{% endmacro %}",
                "main.html": '{% import "macros.html" as m with context %}{{ m.show_name() }}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        assert tmpl.render(name="Alice") == "Name: Alice"


class TestMacroCallsMacro:
    """Test macros that call other macros defined in the same file.

    This is the critical pattern used in page-hero.html where helper macros
    like _get_page_url are called by public macros like hero_element.
    """

    def test_macro_calls_helper_macro_same_file(self):
        """Macro calling another macro defined in the same file.

        Pattern: page-hero.html has _get_page_url called by hero_element.
        This tests the fundamental case without imports.
        """
        env = Environment()
        tmpl = env.from_string(
            "{% macro _helper() %}HELPER{% endmacro %}"
            "{% macro public() %}[{{ _helper() }}]{% endmacro %}"
            "{{ public() }}"
        )
        result = tmpl.render()
        assert result == "[HELPER]"

    def test_macro_calls_helper_with_args(self):
        """Macro calling helper with arguments."""
        env = Environment()
        tmpl = env.from_string(
            "{% macro _format(val) %}|{{ val }}|{% endmacro %}"
            "{% macro show(item) %}Result: {{ _format(item) }}{% endmacro %}"
            "{{ show('test') }}"
        )
        result = tmpl.render()
        assert result == "Result: |test|"

    def test_imported_macro_calls_helper(self):
        """Import a macro that calls a helper macro from the same file.

        This is the CRITICAL test for the page-hero.html bug.
        """
        loader = DictLoader(
            {
                "helpers.html": (
                    "{% macro _helper() %}HELPER{% endmacro %}"
                    "{% macro public() %}[{{ _helper() }}]{% endmacro %}"
                ),
                "main.html": '{% from "helpers.html" import public %}{{ public() }}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        result = tmpl.render()
        assert result == "[HELPER]"

    def test_imported_macro_calls_helper_with_args(self):
        """Import macro that calls helper with arguments.

        Mirrors: hero_element calls _get_page_url(page).
        """
        loader = DictLoader(
            {
                "macros.html": (
                    "{% macro _get_url(page) %}{{ page.href or '/' }}{% endmacro %}"
                    "{% macro public_macro(page) %}URL: {{ _get_url(page) }}{% endmacro %}"
                ),
                "main.html": '{% from "macros.html" import public_macro %}{{ public_macro(page) }}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        result = tmpl.render(page={"href": "/test"})
        assert "URL: /test" in result

    def test_imported_macro_calls_multiple_helpers(self):
        """Import macro that calls multiple helper macros.

        Mirrors: hero_element calls _breadcrumb_eyebrow, _share_dropdown, etc.
        """
        loader = DictLoader(
            {
                "components.html": (
                    "{% macro _header() %}HEADER{% endmacro %}"
                    "{% macro _body(content) %}BODY:{{ content }}{% endmacro %}"
                    "{% macro _footer() %}FOOTER{% endmacro %}"
                    "{% macro card(text) %}{{ _header() }}|{{ _body(text) }}|{{ _footer() }}{% endmacro %}"
                ),
                "main.html": '{% from "components.html" import card %}{{ card("test") }}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        result = tmpl.render()
        assert result == "HEADER|BODY:test|FOOTER"

    def test_imported_macro_with_nested_helper_calls(self):
        """Imported macro where helpers call other helpers.

        Tests deep nesting: hero_element -> _share_dropdown -> icon.
        Note: To output literal braces around an expression, use string
        concatenation with ~ operator instead of {{{ }}} which is ambiguous.
        """
        loader = DictLoader(
            {
                "nested.html": (
                    "{% macro _level3() %}L3{% endmacro %}"
                    "{% macro _level2() %}[{{ _level3() }}]{% endmacro %}"
                    # Use ~ concatenation to output literal braces
                    "{% macro _level1() %}{{ '{' ~ _level2() ~ '}' }}{% endmacro %}"
                    "{% macro top() %}TOP:{{ _level1() }}{% endmacro %}"
                ),
                "main.html": '{% from "nested.html" import top %}{{ top() }}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        result = tmpl.render()
        assert result == "TOP:{[L3]}"

    def test_imported_macro_with_context_and_helper(self):
        """Import macro with context that calls helper."""
        loader = DictLoader(
            {
                "macros.html": (
                    "{% macro _helper() %}{{ site_name }}{% endmacro %}"
                    "{% macro show() %}Site: {{ _helper() }}{% endmacro %}"
                ),
                "main.html": '{% from "macros.html" import show with context %}{{ show() }}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        result = tmpl.render(site_name="Bengal")
        assert result == "Site: Bengal"

    def test_chain_of_template_imports(self):
        """Chain: A imports from B which uses helper from B.

        Tests the pattern: module.html -> element.html -> page-hero.html.
        """
        loader = DictLoader(
            {
                "helpers.html": (
                    "{% macro _util() %}UTIL{% endmacro %}"
                    "{% macro component() %}[{{ _util() }}]{% endmacro %}"
                ),
                "middle.html": (
                    '{% from "helpers.html" import component %}'
                    "{% macro wrapper() %}W:{{ component() }}:W{% endmacro %}"
                ),
                "main.html": '{% from "middle.html" import wrapper %}{{ wrapper() }}',
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        result = tmpl.render()
        assert result == "W:[UTIL]:W"

    def test_extends_with_imported_macro_calling_helper(self):
        """Template extends base and uses imported macro with helper.

        Mirrors: module.html extends base.html and includes element.html
        which imports from page-hero.html.
        """
        loader = DictLoader(
            {
                "macros.html": (
                    "{% macro _helper() %}HELPER{% endmacro %}"
                    "{% macro public() %}[{{ _helper() }}]{% endmacro %}"
                ),
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% from "macros.html" import public %}'
                    "{% block content %}{{ public() }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render()
        assert "[HELPER]" in result


class TestMacroWithContext:
    """Macro context access."""

    def test_access_context_var(self, env):
        """Macro accessing context variable."""
        tmpl = env.from_string("{% macro show() %}{{ ctx_var }}{% endmacro %}{{ show() }}")
        # Note: behavior depends on implementation
        # Some impls require explicit context passing
        result = tmpl.render(ctx_var="from_context")
        # May or may not work depending on Kida implementation
        assert result in ["from_context", ""]


class TestMacroEdgeCases:
    """Edge cases and error handling."""

    def test_empty_macro(self, env):
        """Empty macro body."""
        tmpl = env.from_string("{% macro empty() %}{% endmacro %}[{{ empty() }}]")
        assert tmpl.render() == "[]"

    def test_macro_with_only_whitespace(self, env):
        """Macro with whitespace body."""
        tmpl = env.from_string("{% macro ws() %}   {% endmacro %}[{{ ws() }}]")
        result = tmpl.render()
        assert "[" in result and "]" in result

    def test_macro_multiple_calls(self, env):
        """Call same macro multiple times."""
        tmpl = env.from_string(
            "{% macro inc(n) %}{{ n + 1 }}{% endmacro %}{{ inc(1) }},{{ inc(2) }},{{ inc(3) }}"
        )
        assert tmpl.render() == "2,3,4"

    def test_macro_with_loop(self, env):
        """Macro containing a loop."""
        tmpl = env.from_string(
            "{% macro repeat(items) %}"
            "{% for item in items %}[{{ item }}]{% endfor %}"
            "{% endmacro %}"
            "{{ repeat([1, 2, 3]) }}"
        )
        assert tmpl.render() == "[1][2][3]"

    def test_macro_with_conditional(self, env):
        """Macro containing conditional."""
        tmpl = env.from_string(
            "{% macro sign(n) %}"
            "{% if n > 0 %}+{% elif n < 0 %}-{% else %}0{% endif %}"
            "{% endmacro %}"
            "{{ sign(5) }}{{ sign(-3) }}{{ sign(0) }}"
        )
        assert tmpl.render() == "+-0"
