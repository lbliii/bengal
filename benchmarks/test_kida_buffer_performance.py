"""Benchmarks for buffer pre-allocation optimization in Kida compiler.

These benchmarks measure:
1. Speedup from pre-allocation for large templates (target: ≥5%)
2. No regression for small templates
3. Overflow handling performance

Run with: pytest benchmarks/test_kida_buffer_performance.py -v --benchmark-only
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida import Environment
from bengal.rendering.kida.compiler.core import PRE_ALLOC_THRESHOLD

# Skip if pytest-benchmark not available
pytest.importorskip("pytest_benchmark")


class TestPreallocationPerformance:
    """Benchmark buffer pre-allocation impact on rendering speed."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create a fresh Environment for each test."""
        return Environment()

    def test_large_template_many_variables(self, env: Environment, benchmark) -> None:
        """Benchmark template with many variable outputs (above threshold).

        This is the primary use case for pre-allocation: templates with
        many output operations that benefit from avoided list resizes.

        Target: ≥5% speedup vs dynamic buffer (cannot measure directly,
        but this establishes a performance baseline).
        """
        # 1000 variable outputs - well above threshold
        template_source = "".join(f"{{{{ var{i} }}}}" for i in range(1000))
        template = env.from_string(template_source)
        context = {f"var{i}": f"value{i}" for i in range(1000)}

        def render():
            return template.render(**context)

        result = benchmark(render)

        # Verify correctness
        assert "value0" in result
        assert "value999" in result

    def test_small_template_baseline(self, env: Environment, benchmark) -> None:
        """Benchmark small template (below threshold) - no regression target.

        Small templates should not regress performance from the pre-allocation
        optimization since they use the original dynamic buffer pattern.
        """
        # 10 outputs - well below threshold
        template_source = "".join(f"{{{{ var{i} }}}}" for i in range(10))
        template = env.from_string(template_source)
        context = {f"var{i}": f"val{i}" for i in range(10)}

        def render():
            return template.render(**context)

        result = benchmark(render)

        assert "val0" in result
        assert "val9" in result

    def test_mixed_static_dynamic_content(self, env: Environment, benchmark) -> None:
        """Benchmark mixed static/dynamic content (common real-world pattern).

        Tests templates with alternating HTML structure and variable outputs,
        which is typical in real template usage.
        """
        # Create realistic HTML-like template
        parts = []
        for i in range(200):  # 600 total outputs (static + dynamic + static)
            parts.append(f"<div class='item-{i}'>")
            parts.append(f"{{{{ item{i} }}}}")
            parts.append("</div>")
        template_source = "".join(parts)
        template = env.from_string(template_source)
        context = {f"item{i}": f"content{i}" for i in range(200)}

        def render():
            return template.render(**context)

        result = benchmark(render)

        assert "<div class='item-0'>" in result
        assert "content199" in result

    def test_loop_rendering(self, env: Environment, benchmark) -> None:
        """Benchmark template with for loop over many items.

        Tests pre-allocation behavior with loops where the actual output
        count depends on runtime data. This exercises the overflow fallback
        path if the loop is longer than estimated.
        """
        # Template with static prefix + loop
        prefix = "".join(f"{{{{ p{i} }}}}" for i in range(100))
        template_source = f"{prefix}{{% for item in items %}}{{{{ item }}}}{{% end %}}"
        template = env.from_string(template_source)
        context = {
            **{f"p{i}": str(i) for i in range(100)},
            "items": [f"item{i}" for i in range(500)],  # May overflow estimation
        }

        def render():
            return template.render(**context)

        result = benchmark(render)

        assert "0" in result
        assert "item499" in result

    def test_at_threshold_boundary(self, env: Environment, benchmark) -> None:
        """Benchmark template exactly at threshold.

        This template is at the boundary where pre-allocation kicks in.
        """
        template_source = "".join(f"{{{{ var{i} }}}}" for i in range(PRE_ALLOC_THRESHOLD))
        template = env.from_string(template_source)
        context = {f"var{i}": f"val{i}" for i in range(PRE_ALLOC_THRESHOLD)}

        def render():
            return template.render(**context)

        result = benchmark(render)

        assert "val0" in result
        assert f"val{PRE_ALLOC_THRESHOLD - 1}" in result

    def test_just_below_threshold(self, env: Environment, benchmark) -> None:
        """Benchmark template just below threshold (uses dynamic buffer).

        Compare with at_threshold to see if there's any performance cliff.
        """
        count = PRE_ALLOC_THRESHOLD - 1
        template_source = "".join(f"{{{{ var{i} }}}}" for i in range(count))
        template = env.from_string(template_source)
        context = {f"var{i}": f"val{i}" for i in range(count)}

        def render():
            return template.render(**context)

        result = benchmark(render)

        assert "val0" in result
        assert f"val{count - 1}" in result


class TestOverflowPerformance:
    """Benchmark overflow handling when estimation is too low."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_overflow_heavy(self, env: Environment, benchmark) -> None:
        """Benchmark template where overflow is guaranteed.

        Tests the fallback path performance when the pre-allocated buffer
        is too small and multiple appends are needed.
        """
        # 100 static outputs (triggers pre-allocation with ~120 buffer slots)
        # But loop adds 1000 more outputs (guaranteed overflow)
        prefix = "".join(f"{{{{ p{i} }}}}" for i in range(100))
        template_source = f"{prefix}{{% for item in items %}}{{{{ item }}}}{{% end %}}"
        template = env.from_string(template_source)
        context = {
            **{f"p{i}": str(i) for i in range(100)},
            "items": [f"x{i}" for i in range(1000)],  # Major overflow
        }

        def render():
            return template.render(**context)

        result = benchmark(render)

        assert "99" in result
        assert "x999" in result

    def test_minimal_overflow(self, env: Environment, benchmark) -> None:
        """Benchmark template with minimal overflow.

        Tests when the buffer is just slightly too small, exercising
        the transition from pre-allocated to dynamic growth.
        """
        # 100 outputs (buffer ~120) + loop that exceeds by small amount
        prefix = "".join(f"{{{{ p{i} }}}}" for i in range(100))
        template_source = f"{prefix}{{% for item in items %}}{{{{ item }}}}{{% end %}}"
        template = env.from_string(template_source)
        # Total: 100 + 50 = 150, buffer is 120, so ~30 overflows
        context = {
            **{f"p{i}": str(i) for i in range(100)},
            "items": [f"y{i}" for i in range(50)],
        }

        def render():
            return template.render(**context)

        result = benchmark(render)

        assert "99" in result
        assert "y49" in result


class TestRealWorldScenarios:
    """Benchmark realistic template patterns."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    def test_table_rendering(self, env: Environment, benchmark) -> None:
        """Benchmark HTML table rendering (common pattern).

        Tables with many rows are a common case where pre-allocation helps.
        """
        rows = 100
        cols = 5
        header = "<table><tr>" + "".join(f"<th>Col{c}</th>" for c in range(cols)) + "</tr>"
        row_template = "<tr>" + "".join(f"{{{{ row.col{c} }}}}" for c in range(cols)) + "</tr>"
        template_source = f"{header}{{% for row in rows %}}{row_template}{{% end %}}</table>"
        template = env.from_string(template_source)

        context = {"rows": [{f"col{c}": f"R{r}C{c}" for c in range(cols)} for r in range(rows)]}

        def render():
            return template.render(**context)

        result = benchmark(render)

        assert "<table>" in result
        assert "R0C0" in result
        assert f"R{rows - 1}C{cols - 1}" in result

    def test_card_list(self, env: Environment, benchmark) -> None:
        """Benchmark card/list component rendering.

        Simulates rendering a list of cards/items with multiple fields each.
        """
        template_source = """<div class="cards">
{% for card in cards %}
<div class="card">
    <h2>{{ card.title }}</h2>
    <p>{{ card.description }}</p>
    <span class="author">{{ card.author }}</span>
    <time>{{ card.date }}</time>
</div>
{% end %}
</div>"""
        template = env.from_string(template_source)

        context = {
            "cards": [
                {
                    "title": f"Card Title {i}",
                    "description": f"This is the description for card number {i}.",
                    "author": f"Author {i}",
                    "date": f"2024-01-{(i % 28) + 1:02d}",
                }
                for i in range(50)
            ]
        }

        def render():
            return template.render(**context)

        result = benchmark(render)

        assert "Card Title 0" in result
        assert "Card Title 49" in result


class TestCompilationOverhead:
    """Benchmark compilation overhead with/without optimization."""

    def test_compilation_with_optimization(self, benchmark) -> None:
        """Benchmark template compilation with optimization enabled."""
        template_source = "".join(f"{{{{ var{i} }}}}" for i in range(200))

        def compile_template():
            env = Environment(optimized=True)
            return env.from_string(template_source)

        template = benchmark(compile_template)

        # Verify template works
        context = {f"var{i}": str(i) for i in range(200)}
        assert "0" in template.render(**context)

    def test_compilation_without_optimization(self, benchmark) -> None:
        """Benchmark template compilation without optimization."""
        template_source = "".join(f"{{{{ var{i} }}}}" for i in range(200))

        def compile_template():
            env = Environment(optimized=False)
            return env.from_string(template_source)

        template = benchmark(compile_template)

        # Verify template works
        context = {f"var{i}": str(i) for i in range(200)}
        assert "0" in template.render(**context)
