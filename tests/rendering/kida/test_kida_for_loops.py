"""Test for loop functionality in Kida template engine.

Based on Jinja2's test_core_tags.py TestForLoop class.
Tests loop variables, scoping, nesting, and edge cases.
"""

import pytest

from bengal.rendering.kida import Environment


@pytest.fixture
def env():
    """Create a Kida environment for testing."""
    return Environment()


class TestForLoopBasic:
    """Basic for loop functionality."""

    def test_simple(self, env):
        """Simple iteration over sequence."""
        tmpl = env.from_string("{% for item in seq %}{{ item }}{% endfor %}")
        assert tmpl.render(seq=list(range(10))) == "0123456789"

    def test_else_empty(self, env):
        """Else clause for empty sequence."""
        tmpl = env.from_string("{% for item in seq %}XXX{% else %}...{% endfor %}")
        assert tmpl.render(seq=[]) == "..."

    def test_else_with_items(self, env):
        """Else clause not executed with items."""
        tmpl = env.from_string("{% for item in seq %}{{ item }}{% else %}...{% endfor %}")
        assert tmpl.render(seq=[1, 2]) == "12"

    def test_empty_blocks(self, env):
        """Empty for block."""
        tmpl = env.from_string("<{% for item in seq %}{% else %}{% endfor %}>")
        assert tmpl.render(seq=[]) == "<>"

    def test_scope(self, env):
        """Loop variable should not leak outside loop."""
        tmpl = env.from_string("{% for item in seq %}{{ item }}{% endfor %}[{{ item }}]")
        output = tmpl.render(seq=[1, 2, 3], item="outer")
        assert output == "123[outer]"

    def test_varlen(self, env):
        """Iteration over range/iterator."""
        tmpl = env.from_string("{% for item in iter %}{{ item }}{% endfor %}")
        output = tmpl.render(iter=range(5))
        assert output == "01234"

    def test_unpacking(self, env):
        """Tuple unpacking in for loop."""
        tmpl = env.from_string(
            "{% for a, b, c in [[1, 2, 3]] %}{{ a }}|{{ b }}|{{ c }}{% endfor %}"
        )
        assert tmpl.render() == "1|2|3"

    def test_unpacking_pairs(self, env):
        """Tuple unpacking with dict items."""
        tmpl = env.from_string("{% for k, v in items %}{{ k }}={{ v }};{% endfor %}")
        assert tmpl.render(items=[("a", 1), ("b", 2)]) == "a=1;b=2;"


class TestForLoopVariables:
    """Test loop.* special variables."""

    def test_loop_index(self, env):
        """loop.index (1-based)."""
        tmpl = env.from_string("{% for item in seq %}{{ loop.index }}{% endfor %}")
        assert tmpl.render(seq=["a", "b", "c"]) == "123"

    def test_loop_index0(self, env):
        """loop.index0 (0-based)."""
        tmpl = env.from_string("{% for item in seq %}{{ loop.index0 }}{% endfor %}")
        assert tmpl.render(seq=["a", "b", "c"]) == "012"

    def test_loop_first(self, env):
        """loop.first."""
        tmpl = env.from_string(
            "{% for item in seq %}{% if loop.first %}F{% endif %}{{ item }}{% endfor %}"
        )
        assert tmpl.render(seq=["a", "b", "c"]) == "Fabc"

    def test_loop_last(self, env):
        """loop.last."""
        tmpl = env.from_string(
            "{% for item in seq %}{{ item }}{% if loop.last %}L{% endif %}{% endfor %}"
        )
        assert tmpl.render(seq=["a", "b", "c"]) == "abcL"

    def test_loop_length(self, env):
        """loop.length."""
        tmpl = env.from_string("{% for item in seq %}{{ loop.length }}{% endfor %}")
        assert tmpl.render(seq=["a", "b", "c"]) == "333"

    def test_loop_revindex(self, env):
        """loop.revindex (1-based from end)."""
        tmpl = env.from_string("{% for item in seq %}{{ loop.revindex }}{% endfor %}")
        assert tmpl.render(seq=["a", "b", "c"]) == "321"

    def test_context_vars_full(self, env):
        """All loop context variables together."""
        tmpl = env.from_string(
            """{% for item in seq -%}
            {{ loop.index }}|{{ loop.index0 }}|{{ loop.revindex }}|{{
                loop.revindex0 }}|{{ loop.first }}|{{ loop.last }}|{{
               loop.length }}###{% endfor %}"""
        )
        output = tmpl.render(seq=[42, 24])
        one, two, _ = output.split("###")

        # Parse values
        parts1 = one.strip().split("|")
        parts2 = two.strip().split("|")

        assert int(parts1[0]) == 1  # index
        assert int(parts1[1]) == 0  # index0
        assert int(parts1[2]) == 2  # revindex
        assert int(parts1[3]) == 1  # revindex0
        assert parts1[4].strip() == "True"  # first
        assert parts1[5].strip() == "False"  # last
        assert int(parts1[6]) == 2  # length

        assert int(parts2[0]) == 2
        assert int(parts2[1]) == 1
        assert int(parts2[2]) == 1
        assert int(parts2[3]) == 0
        assert parts2[4].strip() == "False"
        assert parts2[5].strip() == "True"


class TestForLoopNested:
    """Test nested for loops."""

    def test_nested_simple(self, env):
        """Simple nested loops."""
        tmpl = env.from_string(
            "{% for row in matrix %}{% for col in row %}{{ col }}{% endfor %}|{% endfor %}"
        )
        result = tmpl.render(matrix=[[1, 2], [3, 4]])
        assert result == "12|34|"

    def test_looploop(self, env):
        """Access outer loop from inner via set."""
        tmpl = env.from_string(
            """{% for row in table %}
            {%- set rowloop = loop -%}
            {% for cell in row -%}
                [{{ rowloop.index }}|{{ loop.index }}]
            {%- endfor %}
        {%- endfor %}"""
        )
        assert tmpl.render(table=["ab", "cd"]) == "[1|1][1|2][2|1][2|2]"

    def test_scoped_loop_var(self, env):
        """Loop variable scoped correctly in nested loops."""
        t = env.from_string(
            "{% for x in seq %}{{ loop.first }}{% for y in seq %}{% endfor %}{% endfor %}"
        )
        assert t.render(seq="ab") == "TrueFalse"


class TestForLoopWithSet:
    """Test set statement interaction with for loops."""

    def test_set_inside_loop(self, env):
        """Set inside loop affects context."""
        tmpl = env.from_string("{% for item in seq %}{% set x = item %}{{ x }}{% endfor %}")
        assert tmpl.render(seq=[1, 2, 3]) == "123"

    def test_set_before_and_in_loop(self, env):
        """Set before and inside loop."""
        tmpl = env.from_string(
            "{% set x = 9 %}{% for item in seq %}{{ x }}{% set x = item %}{{ x }}{% endfor %}"
        )
        # Note: Kida may have different scoping semantics
        result = tmpl.render(seq=[1, 2, 3])
        # Each iteration: print old x, set x to item, print new x
        assert "91" in result  # First iter shows 9, then 1


class TestForLoopEdgeCases:
    """Edge cases and error handling."""

    def test_empty_sequence(self, env):
        """Empty sequence with else."""
        tmpl = env.from_string("{% for i in [] %}{{ i }}{% else %}empty{% endfor %}")
        assert tmpl.render() == "empty"

    def test_string_iteration(self, env):
        """Iterate over string characters."""
        tmpl = env.from_string("{% for c in text %}[{{ c }}]{% endfor %}")
        assert tmpl.render(text="abc") == "[a][b][c]"

    def test_dict_iteration(self, env):
        """Iterate over dict keys."""
        tmpl = env.from_string("{% for k in d %}{{ k }}{% endfor %}")
        result = tmpl.render(d={"a": 1, "b": 2})
        assert "a" in result and "b" in result

    def test_reversed_list(self, env):
        """Iterate over reversed list."""
        tmpl = env.from_string("{% for i in items %}{{ i }}{% endfor %}")
        assert tmpl.render(items=reversed([1, 2, 3])) == "321"
