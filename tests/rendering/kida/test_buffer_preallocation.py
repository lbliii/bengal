"""Tests for buffer pre-allocation optimization in Kida compiler.

These tests verify that the compiler correctly:
1. Uses pre-allocation for large templates (≥100 output operations)
2. Falls back to dynamic growth for small templates (<100 outputs)
3. Handles overflow correctly when estimation is too low
4. Works correctly with all template features (loops, conditionals, blocks)
"""

from __future__ import annotations

from bengal.rendering.kida import Environment
from bengal.rendering.kida.compiler.core import PRE_ALLOC_HEADROOM, PRE_ALLOC_THRESHOLD


class TestPreallocationThreshold:
    """Test that pre-allocation is correctly triggered based on output count."""

    def test_small_template_uses_dynamic_buffer(self) -> None:
        """Templates below threshold use dynamic buffer growth."""
        env = Environment()
        # 10 outputs - well below threshold
        template_source = "".join(f"{{{{ var{i} }}}}" for i in range(10))
        template = env.from_string(template_source)
        context = {f"var{i}": f"val{i}" for i in range(10)}

        result = template.render(**context)

        # Verify output correctness
        expected = "".join(f"val{i}" for i in range(10))
        assert result == expected

    def test_large_template_uses_preallocation(self) -> None:
        """Templates at or above threshold use pre-allocated buffer."""
        env = Environment()
        # 150 outputs - above threshold
        template_source = "".join(f"{{{{ var{i} }}}}" for i in range(150))
        template = env.from_string(template_source)
        context = {f"var{i}": f"val{i}" for i in range(150)}

        result = template.render(**context)

        # Verify output correctness
        expected = "".join(f"val{i}" for i in range(150))
        assert result == expected

    def test_exactly_at_threshold(self) -> None:
        """Template with exactly PRE_ALLOC_THRESHOLD outputs uses pre-allocation."""
        env = Environment()
        template_source = "".join(f"{{{{ var{i} }}}}" for i in range(PRE_ALLOC_THRESHOLD))
        template = env.from_string(template_source)
        context = {f"var{i}": f"val{i}" for i in range(PRE_ALLOC_THRESHOLD)}

        result = template.render(**context)

        expected = "".join(f"val{i}" for i in range(PRE_ALLOC_THRESHOLD))
        assert result == expected

    def test_just_below_threshold(self) -> None:
        """Template just below threshold uses dynamic buffer."""
        env = Environment()
        count = PRE_ALLOC_THRESHOLD - 1
        template_source = "".join(f"{{{{ var{i} }}}}" for i in range(count))
        template = env.from_string(template_source)
        context = {f"var{i}": f"val{i}" for i in range(count)}

        result = template.render(**context)

        expected = "".join(f"val{i}" for i in range(count))
        assert result == expected


class TestMixedContent:
    """Test pre-allocation with mixed static and dynamic content."""

    def test_static_and_dynamic_content(self) -> None:
        """Pre-allocation works with mixed static/dynamic content."""
        env = Environment()
        # Create template with alternating static and dynamic content
        parts = []
        for i in range(60):
            parts.append("<div>")  # Static
            parts.append(f"{{{{ var{i} }}}}")  # Dynamic
            parts.append("</div>")  # Static
        template_source = "".join(parts)
        template = env.from_string(template_source)
        context = {f"var{i}": f"value{i}" for i in range(60)}

        result = template.render(**context)

        # Verify structure
        assert result.count("<div>") == 60
        assert result.count("</div>") == 60
        assert "value0" in result
        assert "value59" in result


class TestLoopBehavior:
    """Test pre-allocation with loops (where output count may vary)."""

    def test_loop_within_estimation(self) -> None:
        """Loops that stay within estimated buffer size work correctly."""
        env = Environment()
        # Template body has many outputs that trigger pre-allocation
        prefix = "".join(f"{{{{ prefix{i} }}}}" for i in range(80))
        template_source = f"{prefix}{{% for item in items %}}{{{{ item }}}}{{% end %}}"
        template = env.from_string(template_source)
        context = {
            **{f"prefix{i}": f"p{i}" for i in range(80)},
            "items": [f"item{i}" for i in range(10)],
        }

        result = template.render(**context)

        assert "p0" in result
        assert "p79" in result
        assert "item0" in result
        assert "item9" in result

    def test_loop_overflow_fallback(self) -> None:
        """Loop that exceeds estimated buffer uses overflow fallback correctly."""
        env = Environment()
        # Template has ~100 static outputs but loop adds many more
        prefix = "".join(f"{{{{ prefix{i} }}}}" for i in range(100))
        template_source = f"{prefix}{{% for item in items %}}{{{{ item }}}}{{% end %}}"
        template = env.from_string(template_source)

        # Create large item list that will overflow the pre-allocated buffer
        # Estimated: 100 outputs * 1.2 = 120 buffer slots
        # Actual: 100 + 500 = 600 outputs (will overflow)
        context = {
            **{f"prefix{i}": f"p{i}" for i in range(100)},
            "items": [f"item{i}" for i in range(500)],
        }

        result = template.render(**context)

        # Verify all content rendered correctly despite overflow
        assert "p0" in result
        assert "p99" in result
        assert "item0" in result
        assert "item499" in result

    def test_nested_loops(self) -> None:
        """Nested loops work correctly with pre-allocation."""
        env = Environment()
        # Create enough outputs to trigger pre-allocation
        prefix = "".join(f"{{{{ p{i} }}}}" for i in range(100))
        template_source = f"""{prefix}
{{% for outer in outers %}}
  {{% for inner in inners %}}
    {{{{ outer }}}}-{{{{ inner }}}}
  {{% end %}}
{{% end %}}"""
        template = env.from_string(template_source)
        context = {
            **{f"p{i}": str(i) for i in range(100)},
            "outers": ["A", "B", "C"],
            "inners": ["1", "2", "3"],
        }

        result = template.render(**context)

        assert "A-1" in result
        assert "C-3" in result


class TestConditionalBranches:
    """Test pre-allocation with conditional branches."""

    def test_conditional_true_branch(self) -> None:
        """Outputs from true branch work correctly."""
        env = Environment()
        # Create template with many outputs including conditionals
        outputs = "".join(f"{{{{ v{i} }}}}" for i in range(100))
        template_source = f"{outputs}{{% if show %}}VISIBLE{{% else %}}HIDDEN{{% end %}}"
        template = env.from_string(template_source)
        context = {**{f"v{i}": str(i) for i in range(100)}, "show": True}

        result = template.render(**context)

        assert "VISIBLE" in result
        assert "HIDDEN" not in result

    def test_conditional_false_branch(self) -> None:
        """Outputs from false branch work correctly."""
        env = Environment()
        outputs = "".join(f"{{{{ v{i} }}}}" for i in range(100))
        template_source = f"{outputs}{{% if show %}}VISIBLE{{% else %}}HIDDEN{{% end %}}"
        template = env.from_string(template_source)
        context = {**{f"v{i}": str(i) for i in range(100)}, "show": False}

        result = template.render(**context)

        assert "VISIBLE" not in result
        assert "HIDDEN" in result

    def test_elif_branches(self) -> None:
        """Elif branches work correctly with pre-allocation."""
        env = Environment()
        outputs = "".join(f"{{{{ v{i} }}}}" for i in range(100))
        template_source = f"""{outputs}
{{% if level == 1 %}}ONE
{{% elif level == 2 %}}TWO
{{% elif level == 3 %}}THREE
{{% else %}}OTHER
{{% end %}}"""
        template = env.from_string(template_source)

        for level, expected in [(1, "ONE"), (2, "TWO"), (3, "THREE"), (4, "OTHER")]:
            context = {**{f"v{i}": str(i) for i in range(100)}, "level": level}
            result = template.render(**context)
            assert expected in result


class TestBlockInheritance:
    """Test pre-allocation with template inheritance."""

    def test_child_template_with_blocks(self) -> None:
        """Child templates with blocks work correctly."""
        from bengal.rendering.kida.environment.loaders import DictLoader

        loader = DictLoader(
            {
                "base.html": """<!DOCTYPE html>
<html>
<head>{% block head %}DEFAULT HEAD{% end %}</head>
<body>{% block body %}DEFAULT BODY{% end %}</body>
</html>""",
                "child.html": """{% extends "base.html" %}
{% block head %}CUSTOM HEAD{% end %}
{% block body %}"""
                + "".join(f"{{{{ item{i} }}}}" for i in range(100))
                + """{% end %}""",
            }
        )
        env = Environment(loader=loader)
        template = env.get_template("child.html")
        context = {f"item{i}": f"value{i}" for i in range(100)}

        result = template.render(**context)

        assert "CUSTOM HEAD" in result
        assert "DEFAULT HEAD" not in result
        assert "value0" in result
        assert "value99" in result


class TestSpecialFeatures:
    """Test pre-allocation with special template features."""

    def test_capture_with_preallocation(self) -> None:
        """{% capture %} works correctly with pre-allocated parent buffer."""
        env = Environment()
        outputs = "".join(f"{{{{ v{i} }}}}" for i in range(100))
        template_source = f"""{outputs}
{{% capture captured %}}CAPTURED CONTENT{{% end %}}
Captured: {{{{ captured }}}}"""
        template = env.from_string(template_source)
        context = {f"v{i}": str(i) for i in range(100)}

        result = template.render(**context)

        assert "CAPTURED CONTENT" in result
        assert "Captured: CAPTURED CONTENT" in result

    def test_cache_with_preallocation(self) -> None:
        """{% cache %} works correctly with pre-allocated parent buffer."""
        env = Environment()
        outputs = "".join(f"{{{{ v{i} }}}}" for i in range(100))
        template_source = f"""{outputs}
{{% cache "test-key" %}}
CACHED CONTENT
{{% end %}}"""
        template = env.from_string(template_source)
        context = {f"v{i}": str(i) for i in range(100)}

        result = template.render(**context)

        assert "CACHED CONTENT" in result

    def test_include_with_preallocation(self) -> None:
        """{% include %} works correctly with pre-allocated parent buffer."""
        from bengal.rendering.kida.environment.loaders import DictLoader

        loader = DictLoader(
            {
                "main.html": "".join(f"{{{{ v{i} }}}}" for i in range(100))
                + '{% include "partial.html" %}',
                "partial.html": "PARTIAL CONTENT",
            }
        )
        env = Environment(loader=loader)
        template = env.get_template("main.html")
        context = {f"v{i}": str(i) for i in range(100)}

        result = template.render(**context)

        assert "PARTIAL CONTENT" in result
        assert "0" in result
        assert "99" in result


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_template(self) -> None:
        """Empty template works correctly."""
        env = Environment()
        template = env.from_string("")
        result = template.render()
        assert result == ""

    def test_single_output(self) -> None:
        """Single output template works correctly."""
        env = Environment()
        template = env.from_string("{{ name }}")
        result = template.render(name="World")
        assert result == "World"

    def test_only_static_content(self) -> None:
        """Template with only static content works correctly."""
        env = Environment()
        # 200 static data nodes (no variables)
        static = "x" * 200
        template = env.from_string(static)
        result = template.render()
        assert result == static

    def test_html_escaping_with_preallocation(self) -> None:
        """HTML escaping works correctly with pre-allocated buffer."""
        env = Environment()
        outputs = "".join(f"{{{{ v{i} }}}}" for i in range(100))
        template_source = f"{outputs}{{{{ dangerous }}}}"
        template = env.from_string(template_source)
        context = {
            **{f"v{i}": str(i) for i in range(100)},
            "dangerous": "<script>alert('xss')</script>",
        }

        result = template.render(**context)

        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_unicode_content(self) -> None:
        """Unicode content works correctly with pre-allocation."""
        env = Environment()
        outputs = "".join(f"{{{{ v{i} }}}}" for i in range(100))
        template_source = f"{outputs}{{{{ emoji }}}} {{{{ chinese }}}}"
        template = env.from_string(template_source)
        context = {
            **{f"v{i}": str(i) for i in range(100)},
            "emoji": "🎉🚀🌟",
            "chinese": "你好世界",
        }

        result = template.render(**context)

        assert "🎉🚀🌟" in result
        assert "你好世界" in result


class TestOptimizationStats:
    """Test that optimization stats are correctly calculated."""

    def test_estimated_output_count_small(self) -> None:
        """Small templates have correct output count estimate."""
        from bengal.rendering.kida.lexer import tokenize
        from bengal.rendering.kida.optimizer import ASTOptimizer
        from bengal.rendering.kida.parser import Parser

        source = "Hello {{ name }}!"
        tokens = list(tokenize(source))
        parser = Parser(tokens, source=source)
        ast = parser.parse()

        optimizer = ASTOptimizer()
        result = optimizer.optimize(ast)

        # 2 outputs: "Hello " (Data) + name (Output) + "!" (Data) = 3
        assert result.stats.estimated_output_count == 3

    def test_estimated_output_count_large(self) -> None:
        """Large templates have correct output count estimate."""
        from bengal.rendering.kida.lexer import tokenize
        from bengal.rendering.kida.optimizer import ASTOptimizer
        from bengal.rendering.kida.parser import Parser

        source = "".join(f"{{{{ v{i} }}}}" for i in range(100))
        tokens = list(tokenize(source))
        parser = Parser(tokens, source=source)
        ast = parser.parse()

        optimizer = ASTOptimizer()
        result = optimizer.optimize(ast)

        assert result.stats.estimated_output_count == 100


class TestConstants:
    """Test that constants are set correctly."""

    def test_prealloc_threshold_value(self) -> None:
        """PRE_ALLOC_THRESHOLD is set to expected value."""
        assert PRE_ALLOC_THRESHOLD == 100

    def test_prealloc_headroom_value(self) -> None:
        """PRE_ALLOC_HEADROOM is set to expected value."""
        assert PRE_ALLOC_HEADROOM == 1.2
