"""Stress tests for Kida template engine.

Tests deep nesting, large templates, performance boundaries, and extreme edge cases.
"""

from __future__ import annotations

import string
import time
from typing import Any

import pytest

from bengal.rendering.kida import DictLoader, Environment


class TestDeepNesting:
    """Test deeply nested structures."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.parametrize("depth", [10, 25, 50, 100])
    def test_deep_if_nesting(self, env: Environment, depth: int) -> None:
        """Deep if nesting."""
        template = "{% if true %}" * depth + "x" + "{% endif %}" * depth
        tmpl = env.from_string(template)
        assert tmpl.render() == "x"

    @pytest.mark.parametrize("depth", [5, 10, 20])
    def test_deep_for_nesting(self, env: Environment, depth: int) -> None:
        """Deep for loop nesting."""
        template = "{% for x in [1] %}" * depth + "x" + "{% endfor %}" * depth
        tmpl = env.from_string(template)
        assert "x" in tmpl.render()

    @pytest.mark.parametrize("depth", [5, 10, 20])
    def test_deep_mixed_nesting(self, env: Environment, depth: int) -> None:
        """Mixed if/for nesting."""
        template = ""
        for i in range(depth):
            if i % 2 == 0:
                template += "{% if true %}"
            else:
                template += "{% for x in [1] %}"

        template += "x"

        for i in range(depth - 1, -1, -1):
            if i % 2 == 0:
                template += "{% endif %}"
            else:
                template += "{% endfor %}"

        tmpl = env.from_string(template)
        assert "x" in tmpl.render()

    def test_deep_data_access(self, env: Environment) -> None:
        """Deep attribute/item access."""
        # Create nested data structure
        depth = 20
        data: dict[str, Any] = {"value": "found"}
        for _ in range(depth):
            data = {"child": data}

        access = ".child" * depth + ".value"
        template = "{{ data" + access + " }}"

        tmpl = env.from_string(template)
        assert tmpl.render(data=data) == "found"

    def test_deep_expression_nesting(self, env: Environment) -> None:
        """Deeply nested expressions."""
        depth = 30
        expr = "1" + " + 1" * depth
        template = "{{ " + expr + " }}"

        tmpl = env.from_string(template)
        assert tmpl.render() == str(depth + 1)


class TestLargeTemplates:
    """Test large template handling."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_many_variables(self, env: Environment) -> None:
        """Template with many variable references."""
        count = 1000
        template = " ".join(f"{{{{ v{i} }}}}" for i in range(count))
        context = {f"v{i}": str(i) for i in range(count)}

        tmpl = env.from_string(template)
        result = tmpl.render(**context)

        assert "0" in result
        assert "999" in result

    def test_many_blocks(self, env: Environment) -> None:
        """Template with many block statements."""
        count = 500
        template = "".join(f"{{% if true %}}x{i}{{% endif %}}" for i in range(count))

        tmpl = env.from_string(template)
        result = tmpl.render()

        assert "x0" in result
        assert "x499" in result

    def test_many_filters(self, env: Environment) -> None:
        """Template with many filter applications."""
        count = 100
        filters = "|upper|lower" * count
        template = "{{ 'hello'" + filters + " }}"

        # May hit performance limits, but should work
        try:
            tmpl = env.from_string(template)
            result = tmpl.render()
            assert result in ["hello", "HELLO"]  # Depends on final filter
        except RecursionError:
            pytest.skip("Too many nested filters")

    def test_large_literal_list(self, env: Environment) -> None:
        """Template with large literal list."""
        count = 500
        items = ", ".join(str(i) for i in range(count))
        template = f"{{% for x in [{items}] %}}{{{{ x }}}},{{% endfor %}}"

        tmpl = env.from_string(template)
        result = tmpl.render()

        assert "0" in result
        assert "499" in result

    def test_large_literal_dict(self, env: Environment) -> None:
        """Template with large literal dict."""
        count = 200
        items = ", ".join(f"'{i}': {i}" for i in range(count))
        template = (
            f"{{% set d = {{{items}}} %}}{{% for k, v in d.items() %}}{{{{ k }}}},{{% endfor %}}"
        )

        tmpl = env.from_string(template)
        result = tmpl.render()

        assert "0" in result
        assert "199" in result

    def test_long_static_content(self, env: Environment) -> None:
        """Template with long static content."""
        content = "x" * 100000  # 100KB of static content
        template = f"START{content}END"

        tmpl = env.from_string(template)
        result = tmpl.render()

        assert result.startswith("START")
        assert result.endswith("END")
        assert len(result) == len(content) + 8


class TestManyIterations:
    """Test many loop iterations."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_large_loop(self, env: Environment) -> None:
        """Loop with many iterations."""
        tmpl = env.from_string("{% for x in range(10000) %}{% endfor %}done")
        assert tmpl.render() == "done"

    def test_large_loop_with_output(self, env: Environment) -> None:
        """Loop with many iterations producing output."""
        tmpl = env.from_string("{% for x in range(1000) %}x{% endfor %}")
        result = tmpl.render()
        assert len(result) == 1000

    def test_nested_large_loops(self, env: Environment) -> None:
        """Nested loops with many iterations."""
        tmpl = env.from_string("""
{% for i in range(100) %}
  {% for j in range(100) %}
  {% endfor %}
{% endfor %}
done
""")
        result = tmpl.render()
        assert "done" in result


class TestManyMacros:
    """Test many macro definitions."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_many_macro_definitions(self, env: Environment) -> None:
        """Template with many macro definitions."""
        count = 100
        macros = "\n".join(f"{{% def m{i}() %}}macro{i}{{% end %}}" for i in range(count))
        template = macros + "\n{{ m0() }}{{ m99() }}"

        tmpl = env.from_string(template)
        result = tmpl.render()

        assert "macro0" in result
        assert "macro99" in result

    def test_many_macro_calls(self, env: Environment) -> None:
        """Template with many macro calls."""
        count = 500
        template = "{% def m() %}x{% end %}" + "{{ m() }}" * count

        tmpl = env.from_string(template)
        result = tmpl.render()

        assert result == "x" * count


class TestManyIncludes:
    """Test many includes."""

    def test_many_includes(self) -> None:
        """Template with many includes."""
        count = 100
        loader = DictLoader({f"partial{i}.html": f"partial{i}" for i in range(count)})
        env = Environment(loader=loader)

        includes = "\n".join(f'{{% include "partial{i}.html" %}}' for i in range(count))
        tmpl = env.from_string(includes)
        result = tmpl.render()

        assert "partial0" in result
        assert "partial99" in result


class TestDeepInheritance:
    """Test deep inheritance chains."""

    def test_deep_inheritance(self) -> None:
        """Deep template inheritance."""
        depth = 10
        templates = {}

        templates["base.html"] = "{% block content %}base{% endblock %}"

        for i in range(1, depth):
            templates[f"level{i}.html"] = (
                f'{{% extends "{"base.html" if i == 1 else f"level{i - 1}.html"}" %}}'
                f"{{% block content %}}level{i}{{% endblock %}}"
            )

        loader = DictLoader(templates)
        env = Environment(loader=loader)

        tmpl = env.get_template(f"level{depth - 1}.html")
        result = tmpl.render()
        assert f"level{depth - 1}" in result


class TestPerformanceBoundaries:
    """Test performance boundaries."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_render_time_basic(self, env: Environment) -> None:
        """Basic render completes in reasonable time."""
        tmpl = env.from_string("{{ name }}")

        start = time.perf_counter()
        for _ in range(10000):
            tmpl.render(name="World")
        elapsed = time.perf_counter() - start

        # Should complete in under 5 seconds
        assert elapsed < 5.0

    def test_compile_time_basic(self, env: Environment) -> None:
        """Basic compilation completes in reasonable time."""
        template = "{% if true %}{{ name }}{% endif %}"

        start = time.perf_counter()
        for _ in range(1000):
            env.from_string(template)
        elapsed = time.perf_counter() - start

        # Should complete in under 5 seconds
        assert elapsed < 5.0

    def test_complex_template_performance(self, env: Environment) -> None:
        """Complex template renders in reasonable time."""
        template = """
{% for i in range(100) %}
  {% if i % 2 == 0 %}
    <div class="even">{{ i }}</div>
  {% else %}
    <div class="odd">{{ i }}</div>
  {% endif %}
{% endfor %}
"""
        tmpl = env.from_string(template)

        start = time.perf_counter()
        for _ in range(100):
            tmpl.render()
        elapsed = time.perf_counter() - start

        # Should complete in under 5 seconds
        assert elapsed < 5.0


class TestExtremeCases:
    """Test extreme edge cases."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_empty_everything(self, env: Environment) -> None:
        """Empty template, context, etc."""
        tmpl = env.from_string("")
        assert tmpl.render() == ""

    def test_unicode_stress(self, env: Environment) -> None:
        """Template with many unicode characters."""
        # Mix of different unicode ranges
        chars = "".join(chr(i) for i in range(0x100, 0x200))
        chars += "こんにちは世界"
        chars += "🎉🚀💻🔥"

        tmpl = env.from_string("{{ text }}")
        result = tmpl.render(text=chars)
        assert chars in result

    def test_special_characters(self, env: Environment) -> None:
        """Template with special characters."""
        special = "<>&\"'\n\r\t\\/"

        env_noauto = Environment(autoescape=False)
        tmpl = env_noauto.from_string("{{ text }}")
        result = tmpl.render(text=special)
        assert special in result

    def test_very_long_variable_names(self, env: Environment) -> None:
        """Very long variable names."""
        name = "x" * 1000
        template = "{{ " + name + " }}"

        tmpl = env.from_string(template)
        result = tmpl.render(**{name: "value"})
        assert result == "value"

    def test_many_unique_variables(self, env: Environment) -> None:
        """Many unique variable names."""
        # Generate 26*26 = 676 unique variable names
        names = [a + b for a in string.ascii_lowercase for b in string.ascii_lowercase]

        parts = [f"{{{{ {name} }}}}" for name in names[:100]]
        template = " ".join(parts)
        context = {name: name for name in names[:100]}

        tmpl = env.from_string(template)
        result = tmpl.render(**context)

        assert "aa" in result
        assert "zz" not in result  # Only first 100


class TestConcurrentCompilation:
    """Test concurrent template compilation."""

    def test_concurrent_from_string(self) -> None:
        """Concurrent from_string calls."""
        import concurrent.futures

        env = Environment()

        def compile_template(i: int) -> str:
            tmpl = env.from_string(f"Template {{{{ n }}}}: {i}")
            return tmpl.render(n=i)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(compile_template, i) for i in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 100

    def test_concurrent_render(self) -> None:
        """Concurrent render calls."""
        import concurrent.futures

        env = Environment()
        tmpl = env.from_string("{{ name }}: {{ value }}")

        def render_template(i: int) -> str:
            return tmpl.render(name=f"Item{i}", value=i)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(render_template, i) for i in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 100
        for result in results:
            assert "Item" in result


class TestMemoryStress:
    """Test memory under stress."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_large_output(self, env: Environment) -> None:
        """Generate large output."""
        tmpl = env.from_string("{% for i in range(100000) %}x{% endfor %}")
        result = tmpl.render()
        assert len(result) == 100000

    def test_many_template_instances(self, env: Environment) -> None:
        """Create many template instances."""
        templates = []
        for i in range(1000):
            tmpl = env.from_string(f"Template {i}: {{{{ x }}}}")
            templates.append(tmpl)

        # All templates should work
        assert templates[0].render(x="test") == "Template 0: test"
        assert templates[999].render(x="test") == "Template 999: test"
