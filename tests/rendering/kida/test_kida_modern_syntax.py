"""Test modern syntax features in Kida template engine.

RFC: kida-modern-syntax-features

Tests for:
- Optional chaining (?.)
- Null coalescing (??)
- Break/Continue loop control
- Inline if in for loops
- Unless block
- Range literals (.., ...)
- Spaceless block
"""

import pytest

from bengal.rendering.kida import DictLoader, Environment
from bengal.rendering.kida.parser.errors import ParseError


@pytest.fixture
def env():
    """Create a Kida environment for testing."""
    return Environment()


class TestOptionalChaining:
    """Test ?. and ?[ optional chaining operators.

    Note: Optional chaining returns None when the chain short-circuits.
    Use ?? '' to get empty string output, or the None value propagates
    to str() which outputs "None".

    Recommended pattern: {{ user?.name ?? '' }} for empty string fallback.
    """

    def test_simple_optional_dot(self, env):
        """Basic optional attribute access with null coalescing fallback."""
        # Optional chaining with explicit fallback for clean output
        tmpl = env.from_string("{{ user?.name ?? '' }}")
        assert tmpl.render(user=None) == ""
        assert tmpl.render(user={"name": "Alice"}) == "Alice"

    def test_nested_optional(self, env):
        """Nested optional chaining with fallback."""
        tmpl = env.from_string("{{ user?.profile?.avatar ?? '' }}")
        assert tmpl.render(user=None) == ""
        assert tmpl.render(user={"profile": None}) == ""
        assert tmpl.render(user={"profile": {"avatar": "pic.png"}}) == "pic.png"

    def test_optional_with_null_coalesce(self, env):
        """Optional chaining with null coalescing."""
        tmpl = env.from_string("{{ user?.name ?? 'Anonymous' }}")
        assert tmpl.render(user=None) == "Anonymous"
        assert tmpl.render(user={"name": "Bob"}) == "Bob"

    def test_optional_subscript(self, env):
        """Optional subscript access with fallback."""
        # Use with null coalescing for safe access
        tmpl = env.from_string("{{ items?[0] ?? '' }}")
        assert tmpl.render(items=None) == ""
        assert tmpl.render(items=["First"]) == "First"

    def test_mixed_optional_and_regular(self, env):
        """Mix optional and regular access with fallback."""
        tmpl = env.from_string("{{ user?.profile.name ?? '' }}")
        assert tmpl.render(user=None) == ""
        assert tmpl.render(user={"profile": {"name": "Test"}}) == "Test"


class TestNullCoalescing:
    """Test ?? null coalescing operator."""

    def test_none_fallback(self, env):
        """None triggers fallback."""
        tmpl = env.from_string("{{ x ?? 'default' }}")
        assert tmpl.render(x=None) == "default"
        assert tmpl.render(x="value") == "value"

    def test_preserves_falsy(self, env):
        """Unlike 'or', ?? preserves falsy values."""
        tmpl = env.from_string("{{ x ?? 'default' }}")
        assert tmpl.render(x=0) == "0"
        assert tmpl.render(x="") == ""
        assert tmpl.render(x=False) == "False"
        assert tmpl.render(x=[]) == "[]"

    def test_chained(self, env):
        """Chained null coalescing."""
        tmpl = env.from_string("{{ a ?? b ?? c ?? 'last' }}")
        assert tmpl.render(a=None, b=None, c=None) == "last"
        assert tmpl.render(a=None, b=None, c="found") == "found"
        assert tmpl.render(a="first", b="second", c="third") == "first"

    def test_with_optional_chaining(self, env):
        """Null coalescing with optional chaining."""
        tmpl = env.from_string("{{ user?.name ?? 'Anonymous' }}")
        assert tmpl.render(user=None) == "Anonymous"
        assert tmpl.render(user={"name": None}) == "Anonymous"
        assert tmpl.render(user={"name": "Alice"}) == "Alice"

    def test_vs_or_operator(self, env):
        """Show difference between ?? and or."""
        tmpl_nc = env.from_string("{{ count ?? 100 }}")
        tmpl_or = env.from_string("{{ count or 100 }}")

        # count = 0: ?? keeps 0, or replaces it
        assert tmpl_nc.render(count=0) == "0"
        assert tmpl_or.render(count=0) == "100"


class TestBreakContinue:
    """Test break and continue loop control."""

    def test_break(self, env):
        """Break exits loop early."""
        tmpl = env.from_string("""
            {% for i in range(10) %}
                {{ i }}
                {% if i == 3 %}{% break %}{% endif %}
            {% endfor %}
        """)
        result = tmpl.render().split()
        assert result == ["0", "1", "2", "3"]

    def test_continue(self, env):
        """Continue skips iteration."""
        tmpl = env.from_string("""
            {% for i in range(5) %}
                {% if i == 2 %}{% continue %}{% endif %}
                {{ i }}
            {% endfor %}
        """)
        result = tmpl.render().split()
        assert result == ["0", "1", "3", "4"]

    def test_break_in_nested(self, env):
        """Break only exits innermost loop."""
        tmpl = env.from_string("""
            {% for i in range(3) %}
                {% for j in range(3) %}
                    {% if j == 1 %}{% break %}{% endif %}
                    {{ i }}-{{ j }}
                {% endfor %}
            {% endfor %}
        """)
        result = tmpl.render().split()
        assert result == ["0-0", "1-0", "2-0"]

    def test_break_outside_loop_error(self, env):
        """Break outside loop raises error."""
        with pytest.raises(ParseError, match="outside loop"):
            env.from_string("{% break %}")

    def test_continue_outside_loop_error(self, env):
        """Continue outside loop raises error."""
        with pytest.raises(ParseError, match="outside loop"):
            env.from_string("{% continue %}")


class TestInlineIfFor:
    """Test inline if filter in for loops."""

    def test_simple_filter(self, env):
        """Basic inline filter."""
        tmpl = env.from_string("""
            {% for x in items if x.visible %}{{ x.name }}{% endfor %}
        """)
        items = [
            {"name": "a", "visible": True},
            {"name": "b", "visible": False},
            {"name": "c", "visible": True},
        ]
        assert tmpl.render(items=items).strip() == "ac"

    def test_complex_condition(self, env):
        """Complex filter condition."""
        tmpl = env.from_string("""
            {% for x in items if x.count > 0 and x.active %}{{ x.name }}{% endfor %}
        """)
        items = [
            {"name": "a", "count": 5, "active": True},
            {"name": "b", "count": 0, "active": True},
            {"name": "c", "count": 3, "active": False},
            {"name": "d", "count": 1, "active": True},
        ]
        assert tmpl.render(items=items).strip() == "ad"

    def test_with_empty_clause(self, env):
        """Empty clause triggers when original iterable is empty.

        Note: Inline if filters items but empty clause only triggers for
        empty source, matching Jinja2 behavior.
        """
        tmpl = env.from_string("""
            {% for x in items if x.visible %}{{ x.name }}{% empty %}None{% endfor %}
        """)
        # Empty source triggers empty clause
        assert tmpl.render(items=[]).strip() == "None"
        # Items that don't pass filter don't trigger empty clause
        items = [{"name": "a", "visible": False}]
        assert tmpl.render(items=items).strip() == ""

    def test_empty_when_source_empty(self, env):
        """Empty clause for empty source."""
        tmpl = env.from_string("""
            {% for x in items if x.visible %}{{ x.name }}{% empty %}None{% endfor %}
        """)
        assert tmpl.render(items=[]).strip() == "None"


class TestUnless:
    """Test unless block (negated if)."""

    def test_basic_unless(self, env):
        """Basic unless condition."""
        tmpl = env.from_string("{% unless x %}yes{% endunless %}")
        assert tmpl.render(x=False) == "yes"
        assert tmpl.render(x=True) == ""

    def test_unless_with_else(self, env):
        """Unless with else clause."""
        tmpl = env.from_string("{% unless x %}no{% else %}yes{% endunless %}")
        assert tmpl.render(x=False) == "no"
        assert tmpl.render(x=True) == "yes"

    def test_unless_complex_condition(self, env):
        """Unless with complex condition."""
        tmpl = env.from_string("{% unless user.admin or user.moderator %}denied{% endunless %}")
        assert tmpl.render(user={"admin": False, "moderator": False}) == "denied"
        assert tmpl.render(user={"admin": True, "moderator": False}) == ""

    def test_unless_with_end(self, env):
        """Unless with unified end."""
        tmpl = env.from_string("{% unless x %}body{% end %}")
        assert tmpl.render(x=False) == "body"


class TestRangeLiterals:
    """Test range literals (.., ...)."""

    def test_inclusive_range(self, env):
        """Inclusive range with .."""
        tmpl = env.from_string("{% for i in 1..5 %}{{ i }}{% endfor %}")
        assert tmpl.render() == "12345"

    def test_exclusive_range(self, env):
        """Exclusive range with ..."""
        tmpl = env.from_string("{% for i in 1...5 %}{{ i }}{% endfor %}")
        assert tmpl.render() == "1234"

    def test_with_variables(self, env):
        """Range with variables."""
        tmpl = env.from_string("{% for i in start..end %}{{ i }}{% endfor %}")
        assert tmpl.render(start=3, end=6) == "3456"

    def test_with_step(self, env):
        """Range with step."""
        tmpl = env.from_string("{% for i in 0..10 by 2 %}{{ i }}{% endfor %}")
        assert tmpl.render() == "0246810"

    def test_negative_range(self, env):
        """Range with negative values.

        Note: Use parentheses for negative start values since unary minus
        has higher precedence than range operators.
        """
        tmpl = env.from_string("{% for i in (-2)..2 %}{{ i }}{% endfor %}")
        assert tmpl.render() == "-2-1012"

    def test_in_expression(self, env):
        """Range as expression."""
        tmpl = env.from_string("{{ 1..5 | list }}")
        assert tmpl.render() == "[1, 2, 3, 4, 5]"


class TestSpaceless:
    """Test spaceless block."""

    def test_removes_whitespace(self, env):
        """Removes whitespace between tags."""
        tmpl = env.from_string("""
            {% spaceless %}
            <div>
                <p>Hello</p>
            </div>
            {% end %}
        """)
        assert tmpl.render().strip() == "<div><p>Hello</p></div>"

    def test_preserves_content_whitespace(self, env):
        """Preserves whitespace inside tags."""
        tmpl = env.from_string("""
            {% spaceless %}
            <p>Hello   World</p>
            {% end %}
        """)
        assert "Hello   World" in tmpl.render()

    def test_with_loop(self, env):
        """Spaceless with loop."""
        tmpl = env.from_string("""
            {% spaceless %}
            <ul>
                {% for i in items %}
                <li>{{ i }}</li>
                {% endfor %}
            </ul>
            {% end %}
        """)
        result = tmpl.render(items=["a", "b"])
        assert result.strip() == "<ul><li>a</li><li>b</li></ul>"


class TestEmbed:
    """Test embed block for template composition."""

    def test_basic_embed(self):
        """Basic embed with block override."""
        env = Environment(
            loader=DictLoader(
                {
                    "card.html": """
<div class="card">
    <h3>{% block title %}Default{% endblock %}</h3>
    <div>{% block body %}Empty{% endblock %}</div>
</div>
""",
                }
            )
        )
        tmpl = env.from_string("""
            {% embed 'card.html' %}
                {% block title %}Custom Title{% end %}
            {% end %}
        """)
        result = tmpl.render()
        assert "Custom Title" in result
        assert "Empty" in result  # Body uses default

    def test_multiple_block_overrides(self):
        """Override multiple blocks."""
        env = Environment(
            loader=DictLoader(
                {
                    "card.html": """
<div class="card">
    <h3>{% block title %}Default{% endblock %}</h3>
    <div>{% block body %}Empty{% endblock %}</div>
</div>
""",
                }
            )
        )
        tmpl = env.from_string("""
            {% embed 'card.html' %}
                {% block title %}My Title{% end %}
                {% block body %}My Content{% end %}
            {% end %}
        """)
        result = tmpl.render()
        assert "My Title" in result
        assert "My Content" in result

    def test_multiple_embeds(self):
        """Multiple embeds of same template."""
        env = Environment(
            loader=DictLoader(
                {
                    "card.html": """
<div class="card">
    <h3>{% block title %}Default{% endblock %}</h3>
</div>
""",
                }
            )
        )
        tmpl = env.from_string("""
            {% embed 'card.html' %}
                {% block title %}Card 1{% end %}
            {% end %}
            {% embed 'card.html' %}
                {% block title %}Card 2{% end %}
            {% end %}
        """)
        result = tmpl.render()
        assert "Card 1" in result
        assert "Card 2" in result


class TestCombinedFeatures:
    """Test combinations of modern syntax features."""

    def test_optional_chain_with_range(self, env):
        """Optional chaining in range."""
        # Test with None items
        tmpl = env.from_string("""
            {% for i in 1..3 %}{{ items?.name ?? 'missing' }}{% endfor %}
        """)
        assert tmpl.render(items=None).strip() == "missingmissingmissing"
        # Test with valid items
        assert tmpl.render(items={"name": "test"}).strip() == "testtesttest"

    def test_break_with_inline_if(self, env):
        """Break with inline if filter."""
        tmpl = env.from_string("""
            {% for x in items if x.active %}
                {{ x.name }}
                {% if x.stop %}{% break %}{% endif %}
            {% endfor %}
        """)
        items = [
            {"name": "a", "active": True, "stop": False},
            {"name": "b", "active": False, "stop": False},
            {"name": "c", "active": True, "stop": True},
            {"name": "d", "active": True, "stop": False},
        ]
        result = tmpl.render(items=items).split()
        assert result == ["a", "c"]  # b filtered, d after break

    def test_null_coalesce_chain_with_filter(self, env):
        """Null coalescing with filters."""
        tmpl = env.from_string("{{ (name ?? 'anonymous') | upper }}")
        assert tmpl.render(name=None) == "ANONYMOUS"
        assert tmpl.render(name="alice") == "ALICE"
