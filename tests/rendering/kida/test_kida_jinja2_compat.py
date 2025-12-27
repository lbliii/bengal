"""Test Kida compatibility with Jinja2.

Runs the same templates through both Kida and Jinja2 to verify output matches.
"""

import pytest

try:
    import jinja2

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

from bengal.rendering.kida import Environment as KidaEnv


@pytest.fixture
def kida_env():
    """Create Kida environment."""
    return KidaEnv()


@pytest.fixture
def jinja_env():
    """Create Jinja2 environment."""
    if not HAS_JINJA2:
        pytest.skip("Jinja2 not installed")
    return jinja2.Environment()


def compare_outputs(kida_env, jinja_env, template_str: str, context: dict = None):
    """Compare Kida and Jinja2 outputs for same template.

    Args:
        kida_env: Kida Environment instance.
        jinja_env: Jinja2 Environment instance.
        template_str: Template string to render.
        context: Context dict for rendering.

    Returns:
        Tuple of (kida_output, jinja_output, match).
    """
    context = context or {}

    kida_tmpl = kida_env.from_string(template_str)
    kida_output = kida_tmpl.render(**context)

    jinja_tmpl = jinja_env.from_string(template_str)
    jinja_output = jinja_tmpl.render(**context)

    return kida_output, jinja_output, kida_output == jinja_output


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatBasic:
    """Basic compatibility tests."""

    def test_variable_output(self, kida_env, jinja_env):
        """Variable output matches."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, "{{ x }}", {"x": 42})
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"

    def test_string_output(self, kida_env, jinja_env):
        """String literal output matches."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, '{{ "hello" }}')
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"

    def test_integer_output(self, kida_env, jinja_env):
        """Integer literal output matches."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, "{{ 42 }}")
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"

    def test_bool_output(self, kida_env, jinja_env):
        """Boolean output matches."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, "{{ true }}-{{ false }}")
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatArithmetic:
    """Arithmetic compatibility tests."""

    @pytest.mark.parametrize(
        "expr,expected",
        [
            ("{{ 2 + 3 }}", "5"),
            ("{{ 5 - 2 }}", "3"),
            ("{{ 3 * 4 }}", "12"),
            ("{{ 10 // 3 }}", "3"),
            ("{{ 10 % 3 }}", "1"),
            ("{{ 2 ** 3 }}", "8"),
        ],
    )
    def test_arithmetic(self, kida_env, jinja_env, expr, expected):
        """Arithmetic operations match."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, expr)
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"
        assert kida == expected


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatFilters:
    """Filter compatibility tests."""

    @pytest.mark.parametrize(
        "template,context",
        [
            ('{{ "hello"|upper }}', {}),
            ('{{ "HELLO"|lower }}', {}),
            ('{{ "  hello  "|trim }}', {}),
            ("{{ items|length }}", {"items": [1, 2, 3]}),
            ("{{ items|first }}", {"items": [1, 2, 3]}),
            ("{{ items|last }}", {"items": [1, 2, 3]}),
            ('{{ items|join(", ") }}', {"items": ["a", "b", "c"]}),
            ("{{ items|sort|list }}", {"items": [3, 1, 2]}),
            ('{{ x|default("missing") }}', {}),
            ('{{ x|default("missing") }}', {"x": "present"}),
            ("{{ 3.14159|round(2) }}", {}),
            ("{{ -5|abs }}", {}),
        ],
    )
    def test_filters(self, kida_env, jinja_env, template, context):
        """Filter outputs match."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, template, context)
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatForLoop:
    """For loop compatibility tests."""

    def test_simple_for(self, kida_env, jinja_env):
        """Simple for loop matches."""
        kida, jinja, match = compare_outputs(
            kida_env, jinja_env, "{% for i in items %}{{ i }}{% endfor %}", {"items": [1, 2, 3]}
        )
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"

    def test_for_else(self, kida_env, jinja_env):
        """For-else matches."""
        kida, jinja, match = compare_outputs(
            kida_env,
            jinja_env,
            "{% for i in items %}{{ i }}{% else %}empty{% endfor %}",
            {"items": []},
        )
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatConditionals:
    """Conditional compatibility tests."""

    @pytest.mark.parametrize(
        "template,context,expected",
        [
            ("{% if x %}yes{% endif %}", {"x": True}, "yes"),
            ("{% if x %}yes{% endif %}", {"x": False}, ""),
            ("{% if x %}yes{% else %}no{% endif %}", {"x": True}, "yes"),
            ("{% if x %}yes{% else %}no{% endif %}", {"x": False}, "no"),
            ("{% if a %}A{% elif b %}B{% else %}C{% endif %}", {"a": True, "b": False}, "A"),
            ("{% if a %}A{% elif b %}B{% else %}C{% endif %}", {"a": False, "b": True}, "B"),
            ("{% if a %}A{% elif b %}B{% else %}C{% endif %}", {"a": False, "b": False}, "C"),
        ],
    )
    def test_conditionals(self, kida_env, jinja_env, template, context, expected):
        """Conditional outputs match."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, template, context)
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"
        assert kida == expected


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatTernary:
    """Ternary expression compatibility tests."""

    @pytest.mark.parametrize(
        "template,context",
        [
            ("{{ 'yes' if true else 'no' }}", {}),
            ("{{ 'yes' if false else 'no' }}", {}),
            ("{{ a if cond else b }}", {"cond": True, "a": "A", "b": "B"}),
            ("{{ a if cond else b }}", {"cond": False, "a": "A", "b": "B"}),
        ],
    )
    def test_ternary(self, kida_env, jinja_env, template, context):
        """Ternary expression outputs match."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, template, context)
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatSet:
    """Set statement compatibility tests."""

    @pytest.mark.parametrize(
        "template,expected",
        [
            ("{% set x = 42 %}{{ x }}", "42"),
            ("{% set x = 'hello' %}{{ x }}", "hello"),
            ("{% set x = 1 + 2 %}{{ x }}", "3"),
        ],
    )
    def test_set(self, kida_env, jinja_env, template, expected):
        """Set statement outputs match."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, template)
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"
        assert kida == expected


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatMacro:
    """Macro compatibility tests."""

    def test_simple_macro(self, kida_env, jinja_env):
        """Simple macro matches."""
        kida, jinja, match = compare_outputs(
            kida_env,
            jinja_env,
            "{% macro greet(name) %}Hello {{ name }}{% endmacro %}{{ greet('World') }}",
        )
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"

    def test_macro_with_default(self, kida_env, jinja_env):
        """Macro with default arg matches."""
        kida, jinja, match = compare_outputs(
            kida_env,
            jinja_env,
            "{% macro greet(name='World') %}Hello {{ name }}{% endmacro %}{{ greet() }}",
        )
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatTests:
    """Test operator compatibility tests."""

    @pytest.mark.parametrize(
        "template,context,expected",
        [
            ("{% if x is defined %}yes{% endif %}", {"x": 1}, "yes"),
            ("{% if x is defined %}yes{% endif %}", {}, ""),
            ("{% if x is none %}yes{% endif %}", {"x": None}, "yes"),
            ("{% if x is even %}yes{% endif %}", {"x": 4}, "yes"),
            ("{% if x is odd %}yes{% endif %}", {"x": 3}, "yes"),
        ],
    )
    def test_tests(self, kida_env, jinja_env, template, context, expected):
        """Test operator outputs match."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, template, context)
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"
        assert kida == expected


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatComments:
    """Comment compatibility tests."""

    def test_comment(self, kida_env, jinja_env):
        """Comments are stripped."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, "Hello{# comment #} World")
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatRaw:
    """Raw block compatibility tests."""

    def test_raw(self, kida_env, jinja_env):
        """Raw block preserves content."""
        kida, jinja, match = compare_outputs(
            kida_env, jinja_env, "{% raw %}{{ not_a_var }}{% endraw %}"
        )
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"


@pytest.mark.skipif(not HAS_JINJA2, reason="Jinja2 not installed")
class TestJinja2CompatStringConcat:
    """String concatenation compatibility tests."""

    def test_tilde(self, kida_env, jinja_env):
        """Tilde concatenation matches."""
        kida, jinja, match = compare_outputs(kida_env, jinja_env, "{{ 'hello' ~ ' ' ~ 'world' }}")
        assert match, f"Kida: {kida!r}, Jinja2: {jinja!r}"
