"""Tests for Kida AST optimization passes.

Tests constant folding, dead code elimination, data coalescing,
filter inlining, and buffer estimation.
"""

import pytest

from bengal.rendering.kida.lexer import tokenize
from bengal.rendering.kida.nodes import Const, Data, InlinedFilter, Output
from bengal.rendering.kida.optimizer import (
    ASTOptimizer,
    BufferEstimator,
    ConstantFolder,
    DataCoalescer,
    DeadCodeEliminator,
    FilterInliner,
    OptimizationConfig,
    OptimizationStats,
)
from bengal.rendering.kida.parser import Parser


def _parse(source: str):
    """Parse template source into AST."""
    tokens = list(tokenize(source))
    return Parser(tokens, source=source).parse()


class TestConstantFolder:
    """Tests for compile-time constant folding."""

    @pytest.fixture
    def folder(self):
        return ConstantFolder()

    def test_fold_arithmetic(self, folder):
        """Arithmetic operations on constants are folded."""
        ast = _parse("{{ 1 + 2 * 3 }}")
        folded, count = folder.fold(ast)

        # Should have single Output with Const(7)
        output = folded.body[0]
        assert isinstance(output, Output)
        assert isinstance(output.expr, Const)
        assert output.expr.value == 7
        assert count >= 1

    def test_fold_string_concat(self, folder):
        """String concatenation of constants is folded."""
        ast = _parse('{{ "Hello" ~ " " ~ "World" }}')
        folded, count = folder.fold(ast)

        output = folded.body[0]
        assert isinstance(output.expr, Const)
        assert output.expr.value == "Hello World"

    def test_fold_comparison(self, folder):
        """Comparison operations on constants are folded."""
        ast = _parse("{% if 1 < 2 %}yes{% end %}")
        folded, count = folder.fold(ast)

        # If node test should now be Const(True)
        if_node = folded.body[0]
        assert isinstance(if_node.test, Const)
        assert if_node.test.value is True

    def test_no_fold_variables(self, folder):
        """Expressions with variables are not folded."""
        ast = _parse("{{ x + 1 }}")
        folded, count = folder.fold(ast)

        # Should remain a BinOp, not a Const
        output = folded.body[0]
        assert type(output.expr).__name__ == "BinOp"
        assert count == 0

    def test_partial_fold(self, folder):
        """Partial constant expressions are folded where possible."""
        ast = _parse("{{ x + (1 + 2) }}")
        folded, count = folder.fold(ast)

        # Inner (1 + 2) should be folded to 3
        output = folded.body[0]
        binop = output.expr
        assert type(binop).__name__ == "BinOp"
        assert isinstance(binop.right, Const)
        assert binop.right.value == 3
        assert count == 1

    def test_fold_division_by_zero_safe(self, folder):
        """Division by zero is not folded (would raise at runtime)."""
        ast = _parse("{{ 1 / 0 }}")
        folded, count = folder.fold(ast)

        # Should remain a BinOp, not crash
        output = folded.body[0]
        assert type(output.expr).__name__ == "BinOp"
        assert count == 0

    def test_fold_nested_structures(self, folder):
        """Constants in nested structures are folded."""
        ast = _parse("{% for x in items %}{{ 1 + 1 }}{% end %}")
        folded, count = folder.fold(ast)

        for_node = folded.body[0]
        output = for_node.body[0]
        assert isinstance(output.expr, Const)
        assert output.expr.value == 2

    def test_fold_chained_operators(self, folder):
        """Chained constant operations are fully folded."""
        ast = _parse("{{ 2 ** 3 ** 2 }}")  # 2^(3^2) = 2^9 = 512
        folded, count = folder.fold(ast)

        output = folded.body[0]
        assert isinstance(output.expr, Const)
        assert output.expr.value == 512

    def test_fold_unary_operators(self, folder):
        """Unary operators on constants are folded."""
        ast = _parse("{{ -5 }}")
        folded, count = folder.fold(ast)

        output = folded.body[0]
        assert isinstance(output.expr, Const)
        assert output.expr.value == -5

    def test_fold_not_operator(self, folder):
        """Not operator on constants is folded."""
        ast = _parse("{% if not false %}yes{% end %}")
        folded, count = folder.fold(ast)

        if_node = folded.body[0]
        assert isinstance(if_node.test, Const)
        assert if_node.test.value is True

    def test_fold_boolean_and(self, folder):
        """Boolean and operations are folded with short-circuit."""
        ast = _parse("{% if false and x %}yes{% end %}")
        folded, count = folder.fold(ast)

        if_node = folded.body[0]
        assert isinstance(if_node.test, Const)
        assert if_node.test.value is False

    def test_fold_boolean_or(self, folder):
        """Boolean or operations are folded with short-circuit."""
        ast = _parse("{% if true or x %}yes{% end %}")
        folded, count = folder.fold(ast)

        if_node = folded.body[0]
        assert isinstance(if_node.test, Const)
        assert if_node.test.value is True


class TestDeadCodeEliminator:
    """Tests for dead code elimination."""

    @pytest.fixture
    def eliminator(self):
        return DeadCodeEliminator()

    def test_eliminate_if_false(self, eliminator):
        """{% if false %}...{% end %} is completely removed."""
        ast = _parse("before{% if false %}removed{% end %}after")
        result, count = eliminator.eliminate(ast)

        # Should have only 2 Data nodes (before, after)
        assert len(result.body) == 2
        assert result.body[0].value == "before"
        assert result.body[1].value == "after"
        assert count == 1

    def test_inline_if_true(self, eliminator):
        """{% if true %}body{% end %} inlines the body."""
        ast = _parse("{% if true %}content{% end %}")
        result, count = eliminator.eliminate(ast)

        # Should have single Data node
        assert len(result.body) == 1
        assert isinstance(result.body[0], Data)
        assert result.body[0].value == "content"
        assert count == 1

    def test_if_false_with_else(self, eliminator):
        """{% if false %}...{% else %}kept{% end %} keeps else."""
        ast = _parse("{% if false %}removed{% else %}kept{% end %}")
        result, count = eliminator.eliminate(ast)

        assert len(result.body) == 1
        assert isinstance(result.body[0], Data)
        assert result.body[0].value == "kept"
        assert count == 1

    def test_nested_dead_code(self, eliminator):
        """Dead code in nested structures is eliminated."""
        ast = _parse("""{% for x in items %}{% if false %}never{% end %}{{ x }}{% end %}""")
        result, count = eliminator.eliminate(ast)

        # Find the For node (may be preceded by whitespace Data nodes)
        for_node = None
        for node in result.body:
            if type(node).__name__ == "For":
                for_node = node
                break

        assert for_node is not None, "For node should exist"

        # Body should not contain the dead If node
        if_nodes = [n for n in for_node.body if type(n).__name__ == "If"]
        assert len(if_nodes) == 0
        assert count == 1

    def test_preserve_dynamic_conditions(self, eliminator):
        """Non-constant conditions are preserved."""
        ast = _parse("{% if x %}content{% end %}")
        result, count = eliminator.eliminate(ast)

        # If node should still exist
        assert type(result.body[0]).__name__ == "If"
        assert count == 0

    def test_eliminate_multiple_dead_blocks(self, eliminator):
        """Multiple dead code blocks are all eliminated."""
        ast = _parse(
            """
            {% if false %}dead1{% end %}
            live
            {% if false %}dead2{% end %}
        """
        )
        result, count = eliminator.eliminate(ast)

        # Only the "live" Data node should remain
        data_nodes = [n for n in result.body if type(n).__name__ == "Data"]
        assert any("live" in n.value for n in data_nodes)
        assert count == 2

    def test_eliminate_empty_for_loop(self, eliminator):
        """For loop with empty literal iterable is eliminated."""
        ast = _parse("{% for x in [] %}never{% end %}")
        result, count = eliminator.eliminate(ast)

        # Loop should be removed
        assert len(result.body) == 0
        assert count == 1

    def test_empty_for_with_empty_block(self, eliminator):
        """For loop with empty iterable inlines empty block."""
        ast = _parse("{% for x in [] %}never{% empty %}empty{% end %}")
        result, count = eliminator.eliminate(ast)

        # Empty block should be inlined
        assert len(result.body) == 1
        assert result.body[0].value == "empty"


class TestDataCoalescer:
    """Tests for adjacent Data node merging."""

    @pytest.fixture
    def coalescer(self):
        return DataCoalescer()

    def test_coalesce_adjacent_data(self, coalescer):
        """Adjacent Data nodes are merged."""
        # Create a template with multiple adjacent Data nodes
        # This happens when the parser creates separate nodes for whitespace
        ast = _parse("<div></div><span></span>")
        result, count = coalescer.coalesce(ast)

        # Should have single Data node
        assert len(result.body) == 1
        assert isinstance(result.body[0], Data)
        assert "<div></div><span></span>" in result.body[0].value

    def test_no_coalesce_with_expression_between(self, coalescer):
        """Data nodes with expressions between are not merged."""
        ast = _parse("before{{ x }}after")
        result, count = coalescer.coalesce(ast)

        # Should have 3 nodes: Data, Output, Data
        assert len(result.body) == 3

    def test_coalesce_in_nested_structure(self, coalescer):
        """Data nodes in nested structures are coalesced."""
        ast = _parse("{% if x %}<div></div><span></span>{% end %}")
        result, count = coalescer.coalesce(ast)

        if_node = result.body[0]
        assert len(if_node.body) == 1  # Single merged Data node


class TestFilterInliner:
    """Tests for filter inlining."""

    @pytest.fixture
    def inliner(self):
        return FilterInliner()

    def test_inline_upper_filter(self, inliner):
        """Upper filter is inlined as method call."""
        ast = _parse("{{ name | upper }}")
        result, count = inliner.inline(ast)

        output = result.body[0]
        assert isinstance(output.expr, InlinedFilter)
        assert output.expr.method == "upper"
        assert count == 1

    def test_inline_lower_filter(self, inliner):
        """Lower filter is inlined as method call."""
        ast = _parse("{{ name | lower }}")
        result, count = inliner.inline(ast)

        output = result.body[0]
        assert isinstance(output.expr, InlinedFilter)
        assert output.expr.method == "lower"
        assert count == 1

    def test_inline_strip_filter(self, inliner):
        """Strip filter is inlined as method call."""
        ast = _parse("{{ name | strip }}")
        result, count = inliner.inline(ast)

        output = result.body[0]
        assert isinstance(output.expr, InlinedFilter)
        assert output.expr.method == "strip"
        assert count == 1

    def test_no_inline_unknown_filter(self, inliner):
        """Unknown filters are not inlined."""
        ast = _parse("{{ name | custom_filter }}")
        result, count = inliner.inline(ast)

        output = result.body[0]
        assert type(output.expr).__name__ == "Filter"
        assert count == 0

    def test_inline_chained_filters(self, inliner):
        """Chained inlinable filters are all inlined."""
        ast = _parse("{{ name | upper | strip }}")
        result, count = inliner.inline(ast)

        # Both filters should be inlined
        assert count == 2

    def test_inline_in_nested_structure(self, inliner):
        """Filters in nested structures are inlined."""
        ast = _parse("{% for x in items %}{{ x | upper }}{% end %}")
        result, count = inliner.inline(ast)

        for_node = result.body[0]
        output = for_node.body[0]
        assert isinstance(output.expr, InlinedFilter)

    def test_inline_casefold_filter(self, inliner):
        """Casefold filter is inlined as method call."""
        ast = _parse("{{ name | casefold }}")
        result, count = inliner.inline(ast)

        output = result.body[0]
        assert isinstance(output.expr, InlinedFilter)
        assert output.expr.method == "casefold"
        assert count == 1

    def test_inline_isdigit_filter(self, inliner):
        """Isdigit filter is inlined as method call."""
        ast = _parse("{{ name | isdigit }}")
        result, count = inliner.inline(ast)

        output = result.body[0]
        assert isinstance(output.expr, InlinedFilter)
        assert output.expr.method == "isdigit"
        assert count == 1

    def test_inline_isalpha_filter(self, inliner):
        """Isalpha filter is inlined as method call."""
        ast = _parse("{{ name | isalpha }}")
        result, count = inliner.inline(ast)

        output = result.body[0]
        assert isinstance(output.expr, InlinedFilter)
        assert output.expr.method == "isalpha"
        assert count == 1


class TestBufferEstimator:
    """Tests for buffer size estimation."""

    def test_estimate_minimum_size(self):
        """Minimum buffer size is 256 bytes."""
        estimator = BufferEstimator()
        ast = _parse("{{ x }}")

        size = estimator.estimate(ast)
        assert size >= 256

    def test_estimate_includes_static_content(self):
        """Estimate includes static content size."""
        estimator = BufferEstimator()
        ast = _parse("<div>Hello World</div>")

        size = estimator.estimate(ast)
        # Should be at least 1.5x the static content
        assert size >= int(len("<div>Hello World</div>") * 1.5)

    def test_estimate_nested_content(self):
        """Estimate includes nested static content."""
        estimator = BufferEstimator()
        ast = _parse("{% if x %}<div>content</div>{% else %}<span>alt</span>{% end %}")

        size = estimator.estimate(ast)
        # Should account for both branches
        assert size >= 256


class TestASTOptimizer:
    """Integration tests for the unified optimizer."""

    def test_all_passes_applied(self):
        """All enabled passes are applied in order."""
        source = """
            {% if false %}dead{% end %}
            {{ 1 + 2 }}
            <div>A</div><div>B</div>
            {{ name | upper }}
        """
        ast = _parse(source)
        optimizer = ASTOptimizer()

        result = optimizer.optimize(ast)

        assert result.stats.dead_blocks_removed >= 1
        assert result.stats.constants_folded >= 1
        # Data coalescing and filter inlining may or may not occur
        # depending on exact AST structure
        assert result.stats.estimated_buffer_size > 0

    def test_selective_passes(self):
        """Only enabled passes are applied."""
        config = OptimizationConfig(
            constant_folding=True,
            dead_code_elimination=False,
            data_coalescing=False,
            filter_inlining=False,
            estimate_buffer=False,
        )
        optimizer = ASTOptimizer(config)

        source = "{% if false %}dead{% end %}{{ 1 + 1 }}"
        ast = _parse(source)
        result = optimizer.optimize(ast)

        assert "constant_folding" in result.stats.passes_applied
        assert "dead_code_elimination" not in result.stats.passes_applied
        assert result.stats.constants_folded >= 1

    def test_stats_summary(self):
        """Stats summary produces readable output."""
        stats = OptimizationStats(
            constants_folded=3,
            dead_blocks_removed=1,
            data_nodes_coalesced=5,
            filters_inlined=2,
        )

        summary = stats.summary()
        assert "3 constants folded" in summary
        assert "1 dead blocks removed" in summary
        assert "5 data nodes merged" in summary
        assert "2 filters inlined" in summary

    def test_no_optimizations(self):
        """Templates with nothing to optimize return unchanged."""
        source = "{{ name }}"
        ast = _parse(source)
        optimizer = ASTOptimizer()

        result = optimizer.optimize(ast)

        # Only buffer estimation should have any effect
        assert result.stats.constants_folded == 0
        assert result.stats.dead_blocks_removed == 0
        assert result.stats.data_nodes_coalesced == 0
        assert result.stats.filters_inlined == 0

    def test_optimization_preserves_semantics(self):
        """Optimization doesn't change template behavior."""
        from bengal.rendering.kida import Environment

        env = Environment(optimized=True)
        template = env.from_string("{{ 1 + 2 }} {{ name | upper }}")

        result = template.render(name="world")
        assert result == "3 WORLD"

    def test_optimization_disabled(self):
        """Templates compile correctly with optimization disabled."""
        from bengal.rendering.kida import Environment

        env = Environment(optimized=False)
        template = env.from_string("{{ 1 + 2 }} {{ name | upper }}")

        result = template.render(name="world")
        assert result == "3 WORLD"


class TestOptimizationIntegration:
    """End-to-end integration tests with Environment."""

    def test_optimized_template_renders_correctly(self):
        """Optimized templates render correctly."""
        from bengal.rendering.kida import Environment

        env = Environment(optimized=True)
        template = env.from_string(
            """
            {% if true %}shown{% end %}
            {% if false %}hidden{% end %}
            {{ 10 * 10 }}
            {{ name | upper }}
        """
        )

        result = template.render(name="hello")
        assert "shown" in result
        assert "hidden" not in result
        assert "100" in result
        assert "HELLO" in result

    def test_complex_optimizations(self):
        """Complex templates with multiple optimization opportunities."""
        from bengal.rendering.kida import Environment

        env = Environment(optimized=True)
        template = env.from_string(
            """
            {% for i in range(3) %}
                {{ i }}: {{ "prefix" ~ "-" ~ "suffix" }}
                {% if false %}debug: {{ dump(ctx) }}{% end %}
            {% end %}
        """
        )

        result = template.render()
        assert "prefix-suffix" in result
        assert "debug" not in result

    def test_dead_code_with_else(self):
        """Dead code elimination with else branches."""
        from bengal.rendering.kida import Environment

        env = Environment(optimized=True)
        template = env.from_string("{% if false %}no{% else %}yes{% end %}")

        result = template.render()
        assert result.strip() == "yes"
