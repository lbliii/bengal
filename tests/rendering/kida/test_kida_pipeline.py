"""Tests for |> pipeline operator (Kida-native feature)."""

import pytest

from bengal.rendering.kida.environment.exceptions import TemplateSyntaxError


class TestPipelineOperator:
    """Tests for |> pipeline operator."""

    def test_single_pipeline(self, env):
        """Single pipeline step works."""
        template = env.from_string("{{ 'hello' |> upper }}")
        assert template.render() == "HELLO"

    def test_chained_pipeline(self, env):
        """Multiple pipeline steps chain correctly."""
        template = env.from_string("{{ 'hello world' |> upper |> replace('O', '0') }}")
        assert template.render() == "HELL0 W0RLD"

    def test_pipeline_with_args(self, env):
        """Pipeline with positional arguments."""
        template = env.from_string("{{ items |> batch(2) |> list }}")
        result = template.render(items=[1, 2, 3, 4])
        # batch returns generator, list converts it
        assert "[[1, 2], [3, 4]]" in result or "[1, 2]" in result

    def test_pipeline_with_kwargs(self, env):
        """Pipeline with keyword arguments."""
        template = env.from_string("{{ items |> sort(reverse=true) |> first }}")
        result = template.render(items=[1, 3, 2])
        assert result.strip() == "3"

    def test_pipeline_in_expression(self, env):
        """Pipeline within larger expression."""
        template = env.from_string("{{ (items |> length) + 10 }}")
        assert template.render(items=[1, 2, 3]) == "13"

    def test_mixed_pipe_and_pipeline_error(self, env):
        """Cannot mix | and |> in same expression."""
        from bengal.rendering.kida.parser.errors import ParseError

        with pytest.raises(ParseError, match="Cannot mix"):
            env.from_string("{{ x | upper |> lower }}")

    def test_mixed_pipeline_and_pipe_error(self, env):
        """Cannot mix |> and | in same expression."""
        from bengal.rendering.kida.parser.errors import ParseError

        with pytest.raises(ParseError, match="Cannot mix"):
            env.from_string("{{ x |> upper | lower }}")

    def test_pipeline_preserves_filter_semantics(self, env):
        """Pipeline should behave identically to filter chain."""
        items = [{"name": "b"}, {"name": "a"}]

        filter_result = env.from_string("{{ items | sort(attribute='name') | first }}").render(
            items=items
        )

        pipeline_result = env.from_string("{{ items |> sort(attribute='name') |> first }}").render(
            items=items
        )

        assert filter_result == pipeline_result

    def test_pipeline_unknown_filter_error(self, env):
        """Unknown filter in pipeline raises error at compile time."""
        with pytest.raises(TemplateSyntaxError, match="Unknown filter"):
            env.from_string("{{ x |> nonexistent_filter }}")

    def test_pipeline_filter_typo_suggestion(self, env):
        """Typo in filter name suggests correction."""
        with pytest.raises(TemplateSyntaxError, match="Did you mean"):
            env.from_string("{{ x |> uper }}")  # typo for 'upper'

    def test_pipeline_single_filter_with_multiple_args(self, env):
        """Pipeline filter with multiple arguments."""
        template = env.from_string("{{ 'hello' |> replace('l', 'x') }}")
        assert template.render() == "hexxo"


class TestPipelineEdgeCases:
    """Edge cases for pipeline operator."""

    def test_expression_without_pipeline(self, env):
        """Expression without pipeline returns value unchanged."""
        template = env.from_string("{{ x }}")
        assert template.render(x="hello") == "hello"

    def test_pipeline_with_none(self, env):
        """Pipeline handles None values correctly."""
        template = env.from_string("{{ x |> default('fallback') }}")
        assert template.render(x=None) == "fallback"

    def test_nested_pipelines_in_ternary(self, env):
        """Pipelines work in ternary expressions."""
        template = env.from_string("{{ (a |> upper) if condition else (b |> lower) }}")
        assert template.render(a="hi", b="BYE", condition=True) == "HI"
        assert template.render(a="hi", b="BYE", condition=False) == "bye"

    def test_pipeline_in_for_loop(self, env):
        """Pipeline works inside for loop."""
        template = env.from_string("{% for item in items |> sort %}{{ item }}{% end %}")
        result = template.render(items=[3, 1, 2])
        assert result == "123"

    def test_pipeline_with_string_filters(self, env):
        """Pipeline with string manipulation filters."""
        template = env.from_string("{{ text |> trim |> upper |> replace(' ', '-') }}")
        result = template.render(text="  hello world  ")
        assert result == "HELLO-WORLD"

    def test_pipeline_result_in_comparison(self, env):
        """Pipeline result can be used in comparisons."""
        template = env.from_string("{% if items |> length > 2 %}many{% else %}few{% end %}")
        assert "many" in template.render(items=[1, 2, 3])
        assert "few" in template.render(items=[1])

    def test_pipeline_with_default_filter(self, env):
        """Pipeline with default filter for undefined values."""
        template = env.from_string("{{ x |> default('N/A') |> upper }}")
        # In strict mode, undefined x with default filter should return 'N/A'
        # Note: default behavior depends on strict mode
        assert template.render(x=None) == "N/A"
        assert template.render(x="test") == "TEST"

    def test_pipeline_preserves_markup(self, env_autoescape):
        """Pipeline with safe filter preserves markup."""
        template = env_autoescape.from_string("{{ html |> safe }}")
        result = template.render(html="<b>bold</b>")
        assert result == "<b>bold</b>"

    def test_pipeline_chained_with_complex_args(self, env):
        """Pipeline with complex argument expressions."""
        template = env.from_string("{{ items |> join(separator) }}")
        result = template.render(items=["a", "b", "c"], separator="-")
        assert result == "a-b-c"


class TestPipelineLexer:
    """Tests for pipeline lexer tokenization."""

    def test_pipeline_token_generated(self, env):
        """Verify |> is tokenized correctly."""
        from bengal.rendering.kida._types import TokenType
        from bengal.rendering.kida.lexer import tokenize

        tokens = tokenize("{{ x |> filter }}")
        token_types = [t.type for t in tokens]
        assert TokenType.PIPELINE in token_types

    def test_pipeline_not_confused_with_pipe_gt(self, env):
        """|> is a single token, not PIPE followed by GT."""
        from bengal.rendering.kida._types import TokenType
        from bengal.rendering.kida.lexer import tokenize

        tokens = tokenize("{{ x |> filter }}")
        # Should not have a standalone GT token
        gt_count = sum(1 for t in tokens if t.type == TokenType.GT)
        assert gt_count == 0, "GT token found - |> was incorrectly split"
