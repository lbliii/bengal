"""Comprehensive tests for LoopContext in Kida templates.

Tests all loop variable properties and edge cases.
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida import Environment
from bengal.rendering.kida.template import LoopContext


class TestLoopContextDirect:
    """Direct tests of LoopContext class."""

    def test_basic_iteration(self) -> None:
        """Basic iteration works."""
        items = [1, 2, 3]
        loop = LoopContext(items)
        collected = list(loop)
        assert collected == [1, 2, 3]

    def test_index(self) -> None:
        """index is 1-based."""
        loop = LoopContext(["a", "b", "c"])
        indices = []
        for _ in loop:
            indices.append(loop.index)
        assert indices == [1, 2, 3]

    def test_index0(self) -> None:
        """index0 is 0-based."""
        loop = LoopContext(["a", "b", "c"])
        indices = []
        for _ in loop:
            indices.append(loop.index0)
        assert indices == [0, 1, 2]

    def test_first(self) -> None:
        """first is True only on first iteration."""
        loop = LoopContext(["a", "b", "c"])
        firsts = []
        for _ in loop:
            firsts.append(loop.first)
        assert firsts == [True, False, False]

    def test_last(self) -> None:
        """last is True only on last iteration."""
        loop = LoopContext(["a", "b", "c"])
        lasts = []
        for _ in loop:
            lasts.append(loop.last)
        assert lasts == [False, False, True]

    def test_length(self) -> None:
        """length returns total items."""
        loop = LoopContext([1, 2, 3, 4, 5])
        assert loop.length == 5
        # Length available during iteration
        for _ in loop:
            assert loop.length == 5

    def test_revindex(self) -> None:
        """revindex counts down from length to 1."""
        loop = LoopContext(["a", "b", "c"])
        revidx = []
        for _ in loop:
            revidx.append(loop.revindex)
        assert revidx == [3, 2, 1]

    def test_revindex0(self) -> None:
        """revindex0 counts down from length-1 to 0."""
        loop = LoopContext(["a", "b", "c"])
        revidx = []
        for _ in loop:
            revidx.append(loop.revindex0)
        assert revidx == [2, 1, 0]

    def test_previtem(self) -> None:
        """previtem returns previous item or None."""
        loop = LoopContext(["a", "b", "c"])
        prevs = []
        for _ in loop:
            prevs.append(loop.previtem)
        assert prevs == [None, "a", "b"]

    def test_nextitem(self) -> None:
        """nextitem returns next item or None."""
        loop = LoopContext(["a", "b", "c"])
        nexts = []
        for _ in loop:
            nexts.append(loop.nextitem)
        assert nexts == ["b", "c", None]

    def test_cycle(self) -> None:
        """cycle returns values in rotation."""
        loop = LoopContext([1, 2, 3, 4, 5])
        cycles = []
        for _ in loop:
            cycles.append(loop.cycle("odd", "even"))
        assert cycles == ["odd", "even", "odd", "even", "odd"]

    def test_cycle_empty(self) -> None:
        """cycle with no values returns None."""
        loop = LoopContext([1])
        for _ in loop:
            assert loop.cycle() is None

    def test_repr(self) -> None:
        """repr shows position."""
        loop = LoopContext(["a", "b"])
        for _ in loop:
            pass
        repr_str = repr(loop)
        assert "LoopContext" in repr_str


class TestLoopContextSingleItem:
    """Test with single item."""

    def test_single_item(self) -> None:
        """Single item is both first and last."""
        loop = LoopContext(["only"])
        for _ in loop:
            assert loop.first
            assert loop.last
            assert loop.length == 1
            assert loop.index == 1
            assert loop.index0 == 0
            assert loop.previtem is None
            assert loop.nextitem is None


class TestLoopContextEmpty:
    """Test with empty list."""

    def test_empty_list(self) -> None:
        """Empty list produces no iterations."""
        loop = LoopContext([])
        assert loop.length == 0
        iterations = 0
        for _ in loop:
            iterations += 1
        assert iterations == 0


class TestLoopVariablesInTemplates:
    """Test loop variables in templates."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_loop_index(self, env: Environment) -> None:
        """loop.index in template."""
        tmpl = env.from_string("{% for x in items %}{{ loop.index }}{% endfor %}")
        assert tmpl.render(items=[1, 2, 3]) == "123"

    def test_loop_index0(self, env: Environment) -> None:
        """loop.index0 in template."""
        tmpl = env.from_string("{% for x in items %}{{ loop.index0 }}{% endfor %}")
        assert tmpl.render(items=[1, 2, 3]) == "012"

    def test_loop_first(self, env: Environment) -> None:
        """loop.first in template."""
        tmpl = env.from_string(
            "{% for x in items %}{% if loop.first %}F{% endif %}{{ x }}{% endfor %}"
        )
        assert tmpl.render(items=["a", "b", "c"]) == "Fabc"

    def test_loop_last(self, env: Environment) -> None:
        """loop.last in template."""
        tmpl = env.from_string(
            "{% for x in items %}{{ x }}{% if loop.last %}L{% endif %}{% endfor %}"
        )
        assert tmpl.render(items=["a", "b", "c"]) == "abcL"

    def test_loop_length(self, env: Environment) -> None:
        """loop.length in template."""
        tmpl = env.from_string("{% for x in items %}{{ loop.length }}{% endfor %}")
        assert tmpl.render(items=[1, 2, 3]) == "333"

    def test_loop_revindex(self, env: Environment) -> None:
        """loop.revindex in template."""
        tmpl = env.from_string("{% for x in items %}{{ loop.revindex }}{% endfor %}")
        assert tmpl.render(items=[1, 2, 3]) == "321"

    def test_loop_revindex0(self, env: Environment) -> None:
        """loop.revindex0 in template."""
        tmpl = env.from_string("{% for x in items %}{{ loop.revindex0 }}{% endfor %}")
        assert tmpl.render(items=[1, 2, 3]) == "210"

    def test_loop_cycle(self, env: Environment) -> None:
        """loop.cycle in template."""
        tmpl = env.from_string(
            "{% for x in items %}"
            "<tr class=\"{{ loop.cycle('odd', 'even') }}\">{{ x }}</tr>"
            "{% endfor %}"
        )
        result = tmpl.render(items=[1, 2, 3])
        assert 'class="odd"' in result
        assert 'class="even"' in result

    def test_loop_previtem(self, env: Environment) -> None:
        """loop.previtem in template."""
        tmpl = env.from_string("{% for x in items %}[{{ loop.previtem|default('-') }}]{% endfor %}")
        result = tmpl.render(items=["a", "b", "c"])
        assert "[-]" in result  # First has no prev

    def test_loop_nextitem(self, env: Environment) -> None:
        """loop.nextitem in template."""
        tmpl = env.from_string("{% for x in items %}[{{ loop.nextitem|default('-') }}]{% endfor %}")
        result = tmpl.render(items=["a", "b", "c"])
        assert "[-]" in result  # Last has no next


class TestNestedLoops:
    """Test loop variables in nested loops."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_nested_loop_index(self, env: Environment) -> None:
        """Each nested loop has its own index."""
        tmpl = env.from_string(
            "{% for row in matrix %}{% for col in row %}[{{ loop.index }}]{% endfor %}{% endfor %}"
        )
        result = tmpl.render(matrix=[[1, 2], [3, 4]])
        assert result == "[1][2][1][2]"

    def test_access_outer_loop(self, env: Environment) -> None:
        """Access outer loop via set."""
        tmpl = env.from_string(
            "{% for row in matrix %}"
            "{% set rowloop = loop %}"
            "{% for col in row %}"
            "[{{ rowloop.index }}.{{ loop.index }}]"
            "{% endfor %}"
            "{% endfor %}"
        )
        result = tmpl.render(matrix=[[1, 2], [3, 4]])
        assert "[1.1][1.2][2.1][2.2]" in result

    def test_outer_loop_first_last(self, env: Environment) -> None:
        """Outer loop first/last accessible from inner."""
        tmpl = env.from_string(
            "{% for row in matrix %}"
            "{% set rowloop = loop %}"
            "{% for col in row %}"
            "{% if rowloop.first and loop.first %}TL{% endif %}"
            "{% endfor %}"
            "{% endfor %}"
        )
        result = tmpl.render(matrix=[[1, 2], [3, 4]])
        assert "TL" in result


class TestLoopWithFilters:
    """Test loop with filter operations."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_loop_over_filtered(self, env: Environment) -> None:
        """Loop over filtered list has correct length."""
        tmpl = env.from_string(
            "{% for x in items|select('odd') %}{{ x }}:{{ loop.length }},{% endfor %}"
        )
        result = tmpl.render(items=[1, 2, 3, 4, 5])
        # Odd numbers: 1, 3, 5 (length 3)
        assert "1:3" in result
        assert "3:3" in result
        assert "5:3" in result

    def test_loop_over_reversed(self, env: Environment) -> None:
        """Loop over reversed list."""
        tmpl = env.from_string("{% for x in items|reverse %}{{ x }}:{{ loop.index }},{% endfor %}")
        result = tmpl.render(items=[1, 2, 3])
        # Reversed: 3, 2, 1 with indices 1, 2, 3
        assert "3:1" in result
        assert "2:2" in result
        assert "1:3" in result


class TestLoopWithUnpacking:
    """Test loop with tuple unpacking."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_loop_unpacking(self, env: Environment) -> None:
        """Loop with tuple unpacking has correct loop vars."""
        tmpl = env.from_string(
            "{% for k, v in items %}{{ k }}={{ v }}:{{ loop.index }};{% endfor %}"
        )
        result = tmpl.render(items=[("a", 1), ("b", 2)])
        assert "a=1:1" in result
        assert "b=2:2" in result


class TestLoopEdgeCases:
    """Edge cases for loop variables."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_empty_loop(self, env: Environment) -> None:
        """Empty loop with else."""
        tmpl = env.from_string("{% for x in items %}{{ x }}{% else %}empty{% endfor %}")
        assert tmpl.render(items=[]) == "empty"

    def test_single_item_loop(self, env: Environment) -> None:
        """Single item is first and last."""
        tmpl = env.from_string(
            "{% for x in items %}"
            "{% if loop.first %}F{% endif %}"
            "{% if loop.last %}L{% endif %}"
            "{% endfor %}"
        )
        assert tmpl.render(items=["only"]) == "FL"

    def test_loop_over_string(self, env: Environment) -> None:
        """Loop over string characters."""
        tmpl = env.from_string("{% for c in text %}{{ c }}:{{ loop.index }},{% endfor %}")
        result = tmpl.render(text="abc")
        assert "a:1" in result
        assert "b:2" in result
        assert "c:3" in result

    def test_loop_over_dict_keys(self, env: Environment) -> None:
        """Loop over dict keys."""
        tmpl = env.from_string("{% for k in data %}{{ k }}:{{ loop.index }},{% endfor %}")
        # Dict iteration order preserved in Python 3.7+
        result = tmpl.render(data={"a": 1, "b": 2})
        assert "a:" in result
        assert "b:" in result

    def test_loop_over_range(self, env: Environment) -> None:
        """Loop over range."""
        tmpl = env.from_string("{% for x in range(3) %}{{ x }}:{{ loop.length }},{% endfor %}")
        result = tmpl.render()
        assert "0:3" in result
        assert "1:3" in result
        assert "2:3" in result

    def test_loop_variable_scope(self, env: Environment) -> None:
        """Loop variable doesn't leak outside."""
        tmpl = env.from_string(
            "{% set item = 'outer' %}{% for item in items %}{{ item }}{% endfor %}[{{ item }}]"
        )
        result = tmpl.render(items=[1, 2])
        assert "[outer]" in result


class TestLoopCycleAdvanced:
    """Advanced cycle tests."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_cycle_three_values(self, env: Environment) -> None:
        """Cycle through three values."""
        tmpl = env.from_string("{% for x in items %}{{ loop.cycle('a', 'b', 'c') }}{% endfor %}")
        result = tmpl.render(items=range(7))
        assert result == "abcabca"

    def test_cycle_with_single_value(self, env: Environment) -> None:
        """Cycle with single value."""
        tmpl = env.from_string("{% for x in items %}{{ loop.cycle('x') }}{% endfor %}")
        result = tmpl.render(items=[1, 2, 3])
        assert result == "xxx"


class TestLoopWithConditionals:
    """Test loop with conditionals."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_conditional_on_first(self, env: Environment) -> None:
        """Conditional on first item."""
        tmpl = env.from_string(
            "{% for x in items %}{% if loop.first %}<first>{% endif %}{{ x }}{% endfor %}"
        )
        result = tmpl.render(items=[1, 2, 3])
        assert result == "<first>123"

    def test_conditional_on_last(self, env: Environment) -> None:
        """Conditional on last item."""
        tmpl = env.from_string(
            "{% for x in items %}{{ x }}{% if loop.last %}<last>{% endif %}{% endfor %}"
        )
        result = tmpl.render(items=[1, 2, 3])
        assert result == "123<last>"

    def test_separator_pattern(self, env: Environment) -> None:
        """Common pattern: separator between items."""
        tmpl = env.from_string(
            "{% for x in items %}{{ x }}{% if not loop.last %}, {% endif %}{% endfor %}"
        )
        result = tmpl.render(items=["a", "b", "c"])
        assert result == "a, b, c"

    def test_first_last_combined(self, env: Environment) -> None:
        """First and last styling."""
        tmpl = env.from_string(
            "{% for x in items %}"
            '<li class="'
            "{% if loop.first %}first {% endif %}"
            "{% if loop.last %}last{% endif %}"
            '">{{ x }}</li>'
            "{% endfor %}"
        )
        result = tmpl.render(items=["a", "b", "c"])
        assert 'class="first "' in result
        assert 'class="last"' in result
