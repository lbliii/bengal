"""Test advanced Kida template features.

Tests for Kida-native features that go beyond Jinja2 compatibility:
- {% def %} - functions with lexical scoping
- {% call %} / {% slot %} - component patterns
- {% capture %} - capture block content to variable
- {% cache %} - fragment caching
- {% filter %} - apply filter to block content
"""

import pytest

from bengal.rendering.kida import DictLoader, Environment


@pytest.fixture
def env():
    """Create a Kida environment for testing."""
    return Environment()


@pytest.fixture
def env_no_autoescape():
    """Create a Kida environment without autoescaping."""
    return Environment(autoescape=False)


# =============================================================================
# {% def %} - Kida functions with lexical scoping
# =============================================================================


class TestDefBasics:
    """Basic {% def %} functionality."""

    def test_simple_def(self, env):
        """Simple function definition and call."""
        tmpl = env.from_string(
            "{% def greet(name) %}Hello {{ name }}!{% enddef %}{{ greet('World') }}"
        )
        assert tmpl.render() == "Hello World!"

    def test_def_with_end(self, env):
        """Function using unified {% end %} closing."""
        tmpl = env.from_string(
            "{% def greet(name) %}Hello {{ name }}!{% end %}{{ greet('World') }}"
        )
        assert tmpl.render() == "Hello World!"

    def test_def_no_args(self, env):
        """Function with no arguments."""
        tmpl = env.from_string("{% def hello() %}Hello!{% enddef %}{{ hello() }}")
        assert tmpl.render() == "Hello!"

    def test_def_multiple_args(self, env):
        """Function with multiple arguments."""
        tmpl = env.from_string(
            "{% def greet(first, last) %}Hello {{ first }} {{ last }}!{% enddef %}"
            "{{ greet('John', 'Doe') }}"
        )
        assert tmpl.render() == "Hello John Doe!"

    def test_def_with_defaults(self, env):
        """Function with default argument values."""
        tmpl = env.from_string(
            "{% def greet(name='World') %}Hello {{ name }}!{% enddef %}{{ greet() }}"
        )
        assert tmpl.render() == "Hello World!"

    def test_def_override_defaults(self, env):
        """Override function default arguments."""
        tmpl = env.from_string(
            "{% def greet(name='World') %}Hello {{ name }}!{% enddef %}{{ greet('User') }}"
        )
        assert tmpl.render() == "Hello User!"


class TestDefScoping:
    """{% def %} lexical scoping - functions can access outer scope."""

    def test_access_outer_scope(self, env):
        """Function can access outer scope variables."""
        tmpl = env.from_string(
            "{% set title = 'Welcome' %}"
            "{% def card(content) %}"
            "<div>{{ title }}: {{ content }}</div>"
            "{% enddef %}"
            "{{ card('Hello') }}"
        )
        assert tmpl.render() == "<div>Welcome: Hello</div>"

    def test_access_context_vars(self, env):
        """Function can access template context variables."""
        tmpl = env.from_string("{% def show() %}Site: {{ site_name }}{% enddef %}{{ show() }}")
        assert tmpl.render(site_name="Bengal") == "Site: Bengal"

    def test_arg_shadows_outer(self, env):
        """Function argument shadows outer variable."""
        tmpl = env.from_string(
            "{% set name = 'outer' %}"
            "{% def greet(name) %}{{ name }}{% enddef %}"
            "{{ greet('inner') }}"
        )
        assert tmpl.render() == "inner"


class TestDefNested:
    """Nested function definitions."""

    def test_nested_def(self, env):
        """Function defined inside another function."""
        tmpl = env.from_string(
            "{% def outer(text) %}"
            "{% def inner(x) %}[{{ x }}]{% enddef %}"
            "{{ inner(text) }}"
            "{% enddef %}"
            "{{ outer('test') }}"
        )
        assert "[test]" in tmpl.render()

    def test_recursive_def(self, env):
        """Recursive function call."""
        tmpl = env.from_string(
            "{% def countdown(n) %}"
            "{{ n }}"
            "{% if n > 0 %}{{ countdown(n - 1) }}{% endif %}"
            "{% enddef %}"
            "{{ countdown(3) }}"
        )
        result = tmpl.render()
        assert "3" in result and "2" in result and "1" in result and "0" in result


# =============================================================================
# {% call %} / {% slot %} - Component patterns
# =============================================================================


class TestCallSlot:
    """{% call %} and {% slot %} for component patterns."""

    def test_simple_call_slot(self, env):
        """Basic call/slot pattern for components."""
        tmpl = env.from_string(
            "{% def wrapper() %}"
            "<div class='wrapper'>{% slot %}</div>"
            "{% enddef %}"
            "{% call wrapper() %}Content here{% endcall %}"
        )
        result = tmpl.render()
        assert result == "<div class='wrapper'>Content here</div>"

    def test_call_slot_with_end(self, env):
        """Call block using unified {% end %} closing."""
        tmpl = env.from_string(
            "{% def box() %}<box>{% slot %}</box>{% end %}{% call box() %}Inside{% end %}"
        )
        assert tmpl.render() == "<box>Inside</box>"

    def test_call_with_args(self, env):
        """Call passing arguments to function."""
        tmpl = env.from_string(
            "{% def card(title) %}"
            "<div class='card'><h2>{{ title }}</h2>{% slot %}</div>"
            "{% enddef %}"
            "{% call card('My Card') %}<p>Card content</p>{% endcall %}"
        )
        result = tmpl.render()
        assert "<h2>My Card</h2>" in result
        assert "<p>Card content</p>" in result

    def test_nested_calls(self, env):
        """Nested call blocks."""
        tmpl = env.from_string(
            "{% def outer() %}<outer>{% slot %}</outer>{% enddef %}"
            "{% def inner() %}<inner>{% slot %}</inner>{% enddef %}"
            "{% call outer() %}{% call inner() %}Content{% endcall %}{% endcall %}"
        )
        result = tmpl.render()
        assert result == "<outer><inner>Content</inner></outer>"

    def test_slot_not_rendered_without_call(self, env):
        """Slot is empty when function called directly (not via call block)."""
        tmpl = env.from_string("{% def box() %}[{% slot %}]{% enddef %}{{ box() }}")
        assert tmpl.render() == "[]"


# =============================================================================
# {% capture %} - Capture block to variable
# =============================================================================


class TestCapture:
    """{% capture %} to capture block content to a variable."""

    def test_simple_capture(self, env):
        """Basic capture block."""
        tmpl = env.from_string("{% capture content %}Hello World{% endcapture %}{{ content }}")
        assert tmpl.render() == "Hello World"

    def test_capture_with_end(self, env):
        """Capture using unified {% end %} closing."""
        tmpl = env.from_string("{% capture msg %}Captured{% end %}{{ msg }}")
        assert tmpl.render() == "Captured"

    def test_capture_with_expressions(self, env):
        """Capture block with expressions."""
        tmpl = env.from_string(
            "{% capture greeting %}Hello {{ name }}!{% endcapture %}{{ greeting }}"
        )
        assert tmpl.render(name="World") == "Hello World!"

    def test_capture_with_loop(self, env):
        """Capture block containing a loop."""
        tmpl = env.from_string(
            "{% capture items %}{% for i in [1,2,3] %}{{ i }}{% endfor %}{% endcapture %}"
            "{{ items }}"
        )
        assert tmpl.render() == "123"

    def test_multiple_captures(self, env):
        """Multiple capture blocks."""
        tmpl = env.from_string(
            "{% capture a %}A{% endcapture %}{% capture b %}B{% endcapture %}{{ b }}{{ a }}"
        )
        assert tmpl.render() == "BA"

    def test_capture_reuse(self, env):
        """Capture and reuse multiple times."""
        tmpl = env.from_string("{% capture x %}X{% endcapture %}{{ x }}{{ x }}{{ x }}")
        assert tmpl.render() == "XXX"


# =============================================================================
# {% cache %} - Fragment caching
# =============================================================================


class TestCache:
    """{% cache %} for fragment caching."""

    def test_simple_cache(self, env):
        """Basic cache block."""
        tmpl = env.from_string("{% cache 'test-key' %}Cached content{% endcache %}")
        assert tmpl.render() == "Cached content"

    def test_cache_with_end(self, env):
        """Cache using unified {% end %} closing."""
        tmpl = env.from_string("{% cache 'key' %}Content{% end %}")
        assert tmpl.render() == "Content"

    def test_cache_with_expression_key(self, env):
        """Cache with expression as key."""
        tmpl = env.from_string("{% cache 'item-' ~ id %}Item {{ id }}{% endcache %}")
        assert tmpl.render(id=42) == "Item 42"

    def test_cache_hit(self, env):
        """Cache returns cached value on second render."""
        tmpl = env.from_string("{% cache 'counter' %}{{ counter }}{% endcache %}")
        # First render
        result1 = tmpl.render(counter=1)
        # Second render with different counter - should still get cached value
        result2 = tmpl.render(counter=2)
        assert result1 == "1"
        assert result2 == "1"  # Cached

    def test_cache_different_keys(self, env):
        """Different cache keys store different values."""
        tmpl1 = env.from_string("{% cache 'a' %}A{% endcache %}")
        tmpl2 = env.from_string("{% cache 'b' %}B{% endcache %}")
        assert tmpl1.render() == "A"
        assert tmpl2.render() == "B"

    def test_cache_with_ttl(self, env):
        """Cache with TTL parameter (not enforced, just parsed)."""
        tmpl = env.from_string('{% cache "key", ttl="5m" %}Expires{% endcache %}')
        assert tmpl.render() == "Expires"


# =============================================================================
# {% filter %} - Apply filter to block content
# =============================================================================


class TestFilterBlock:
    """{% filter %} to apply filter to entire block."""

    def test_simple_filter_block(self, env_no_autoescape):
        """Basic filter block."""
        tmpl = env_no_autoescape.from_string("{% filter upper %}hello world{% endfilter %}")
        assert tmpl.render() == "HELLO WORLD"

    def test_filter_block_with_end(self, env_no_autoescape):
        """Filter block using unified {% end %} closing."""
        tmpl = env_no_autoescape.from_string("{% filter lower %}HELLO{% end %}")
        assert tmpl.render() == "hello"

    def test_filter_block_with_expressions(self, env_no_autoescape):
        """Filter block containing expressions."""
        tmpl = env_no_autoescape.from_string("{% filter upper %}hello {{ name }}{% endfilter %}")
        assert tmpl.render(name="world") == "HELLO WORLD"

    def test_filter_block_with_loop(self, env_no_autoescape):
        """Filter block containing a loop."""
        tmpl = env_no_autoescape.from_string(
            "{% filter upper %}{% for x in ['a', 'b', 'c'] %}{{ x }}{% endfor %}{% endfilter %}"
        )
        assert tmpl.render() == "ABC"

    def test_nested_filter_blocks(self, env_no_autoescape):
        """Nested filter blocks."""
        tmpl = env_no_autoescape.from_string(
            "{% filter upper %}{% filter trim %}  hello  {% endfilter %}{% endfilter %}"
        )
        assert tmpl.render() == "HELLO"

    def test_filter_with_args(self, env_no_autoescape):
        """Filter block with filter arguments."""
        tmpl = env_no_autoescape.from_string("{% filter truncate(5) %}hello world{% endfilter %}")
        result = tmpl.render()
        assert len(result) <= 8  # truncate adds "..."


# =============================================================================
# Integration tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_def_with_capture(self, env):
        """Use def with capture inside."""
        tmpl = env.from_string(
            "{% def make_list(items) %}"
            "{% capture result %}"
            "{% for item in items %}{{ item }},{% endfor %}"
            "{% endcapture %}"
            "{{ result }}"
            "{% enddef %}"
            "{{ make_list([1,2,3]) }}"
        )
        assert tmpl.render() == "1,2,3,"

    def test_call_with_conditional(self, env):
        """Call block with conditional slot content."""
        tmpl = env.from_string(
            "{% def box() %}<box>{% slot %}</box>{% enddef %}"
            "{% call box() %}"
            "{% if show %}Visible{% endif %}"
            "{% endcall %}"
        )
        assert tmpl.render(show=True) == "<box>Visible</box>"
        assert tmpl.render(show=False) == "<box></box>"

    def test_def_import_pattern(self):
        """Import def from another template."""
        loader = DictLoader(
            {
                "components.html": (
                    "{% def button(text) %}<button>{{ text }}</button>{% enddef %}"
                ),
                "main.html": (
                    "{% from \"components.html\" import button %}{{ button('Click me') }}"
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("main.html")
        assert tmpl.render() == "<button>Click me</button>"

    def test_def_with_inheritance(self):
        """Def in template with inheritance."""
        loader = DictLoader(
            {
                "base.html": ("<html>{% block content %}{% endblock %}</html>"),
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% def greet(n) %}Hi {{ n }}{% enddef %}"
                    "{% block content %}{{ greet('World') }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        tmpl = env.get_template("child.html")
        result = tmpl.render()
        assert "Hi World" in result
        assert "<html>" in result
