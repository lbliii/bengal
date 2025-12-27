"""Tests for Python-style keyword recognition.

RFC: rfc-kida-python-compatibility.md

Kida uses Python-style keywords (True, False, None) as canonical.
Lowercase (true, false, none) also accepted for convenience.

This module verifies that both styles work identically.
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida import DictLoader, Environment


@pytest.fixture
def env() -> Environment:
    """Create a fresh Kida environment for each test."""
    return Environment()


class TestPythonKeywords:
    """Python-style True/False/None recognition."""

    # --- True keyword tests ---

    def test_True_in_conditional(self, env: Environment) -> None:
        """{% if True %} should execute the block."""
        result = env.from_string("{% if True %}yes{% endif %}").render()
        assert result == "yes"

    def test_true_in_conditional(self, env: Environment) -> None:
        """{% if true %} should also work (lowercase accepted)."""
        result = env.from_string("{% if true %}yes{% endif %}").render()
        assert result == "yes"

    def test_True_expression(self, env: Environment) -> None:
        """{{ True }} should render as 'True'."""
        result = env.from_string("{{ True }}").render()
        assert result == "True"

    def test_true_expression(self, env: Environment) -> None:
        """{{ true }} should also render as 'True'."""
        result = env.from_string("{{ true }}").render()
        assert result == "True"

    # --- False keyword tests ---

    def test_False_in_conditional(self, env: Environment) -> None:
        """{% if False %} should skip the block."""
        result = env.from_string("{% if False %}no{% else %}yes{% endif %}").render()
        assert result == "yes"

    def test_false_in_conditional(self, env: Environment) -> None:
        """{% if false %} should also skip (lowercase accepted)."""
        result = env.from_string("{% if false %}no{% else %}yes{% endif %}").render()
        assert result == "yes"

    def test_False_expression(self, env: Environment) -> None:
        """{{ False }} should render as 'False'."""
        result = env.from_string("{{ False }}").render()
        assert result == "False"

    def test_false_expression(self, env: Environment) -> None:
        """{{ false }} should also render as 'False'."""
        result = env.from_string("{{ false }}").render()
        assert result == "False"

    # --- None keyword tests ---

    def test_None_in_conditional(self, env: Environment) -> None:
        """{% if None %} should be falsy."""
        result = env.from_string("{% if None %}no{% else %}yes{% endif %}").render()
        assert result == "yes"

    def test_none_in_conditional(self, env: Environment) -> None:
        """{% if none %} should also be falsy."""
        result = env.from_string("{% if none %}no{% else %}yes{% endif %}").render()
        assert result == "yes"

    def test_None_expression(self, env: Environment) -> None:
        """{{ None }} should render as 'None' (string representation)."""
        result = env.from_string("{{ None }}").render()
        assert result == "None"

    def test_none_expression(self, env: Environment) -> None:
        """{{ none }} should also render as 'None'."""
        result = env.from_string("{{ none }}").render()
        assert result == "None"

    # --- Equality tests ---

    def test_True_equals_true(self, env: Environment) -> None:
        """True and true should be equal."""
        result = env.from_string("{% if True == true %}yes{% endif %}").render()
        assert result == "yes"

    def test_False_equals_false(self, env: Environment) -> None:
        """False and false should be equal."""
        result = env.from_string("{% if False == false %}yes{% endif %}").render()
        assert result == "yes"

    def test_None_equals_none(self, env: Environment) -> None:
        """None and none should be equal."""
        result = env.from_string("{% if None == none %}yes{% endif %}").render()
        assert result == "yes"

    # --- Identity tests ---

    def test_None_is_none(self, env: Environment) -> None:
        """None is none should be true."""
        result = env.from_string("{% if None is none %}yes{% endif %}").render()
        assert result == "yes"

    def test_True_is_not_False(self, env: Environment) -> None:
        """True is not False."""
        result = env.from_string("{% if True is not False %}yes{% endif %}").render()
        assert result == "yes"

    # --- Ternary expression tests ---

    def test_ternary_with_True(self, env: Environment) -> None:
        """Ternary with True condition."""
        result = env.from_string("{{ 'yes' if True else 'no' }}").render()
        assert result == "yes"

    def test_ternary_with_False(self, env: Environment) -> None:
        """Ternary with False condition."""
        result = env.from_string("{{ 'yes' if False else 'no' }}").render()
        assert result == "no"

    # --- Test argument context (sameas) ---

    def test_sameas_True(self, env: Environment) -> None:
        """is sameas True should work."""
        result = env.from_string("{% if true is sameas True %}yes{% endif %}").render()
        assert result == "yes"

    def test_sameas_False(self, env: Environment) -> None:
        """is sameas False should work."""
        result = env.from_string("{% if false is sameas False %}yes{% endif %}").render()
        assert result == "yes"

    def test_sameas_None(self, env: Environment) -> None:
        """is sameas None should work."""
        result = env.from_string("{% if none is sameas None %}yes{% endif %}").render()
        assert result == "yes"

    # --- Boolean operations ---

    def test_True_and_True(self, env: Environment) -> None:
        """True and True should be True."""
        result = env.from_string("{% if True and True %}yes{% endif %}").render()
        assert result == "yes"

    def test_True_or_False(self, env: Environment) -> None:
        """True or False should be True."""
        result = env.from_string("{% if True or False %}yes{% endif %}").render()
        assert result == "yes"

    def test_not_False(self, env: Environment) -> None:
        """not False should be True."""
        result = env.from_string("{% if not False %}yes{% endif %}").render()
        assert result == "yes"

    def test_not_None(self, env: Environment) -> None:
        """not None should be True."""
        result = env.from_string("{% if not None %}yes{% endif %}").render()
        assert result == "yes"


class TestPythonKeywordsRegression:
    """Regression tests for the original bug reports."""

    def test_def_inside_if_True(self, env: Environment) -> None:
        """Regression: def blocks inside {% if True %} should work."""
        tmpl = env.from_string("""
{% def greet() %}Hello{% enddef %}
{% if True %}{{ greet() }}{% endif %}
""")
        result = tmpl.render()
        assert "Hello" in result

    def test_def_inside_if_True_with_inheritance(self) -> None:
        """Regression: def in conditional with extends."""
        loader = DictLoader(
            {
                "base.html": "{% def helper() %}Helper{% enddef %}{% block content %}{% endblock %}",
                "child.html": '{% extends "base.html" %}{% block content %}{% if True %}{{ helper() }}{% endif %}{% endblock %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "Helper" in result

    def test_nested_if_True_blocks(self, env: Environment) -> None:
        """Nested conditionals with True should all execute."""
        tmpl = env.from_string("""
{% if True %}
outer
{% if True %}
inner
{% endif %}
{% endif %}
""")
        result = tmpl.render()
        assert "outer" in result
        assert "inner" in result

    def test_for_loop_inside_if_True(self, env: Environment) -> None:
        """For loop inside {% if True %} should work."""
        tmpl = env.from_string("""
{% if True %}
{% for i in [1, 2, 3] %}{{ i }}{% endfor %}
{% endif %}
""")
        result = tmpl.render()
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_set_inside_if_True(self, env: Environment) -> None:
        """Variable assignment inside {% if True %} should work."""
        tmpl = env.from_string("""
{% if True %}
{% set x = 42 %}
{{ x }}
{% endif %}
""")
        result = tmpl.render()
        assert "42" in result
