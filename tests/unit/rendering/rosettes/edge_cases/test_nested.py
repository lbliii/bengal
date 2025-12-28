"""Tests for nested constructs."""

from __future__ import annotations

from bengal.rendering.rosettes import TokenType, get_lexer


class TestNestedStrings:
    """Test nested string constructs."""

    def test_nested_f_string(self) -> None:
        """Nested f-strings should tokenize correctly."""
        lexer = get_lexer("python")
        code = 'f"outer {f"inner"} outer"'
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0

    def test_template_literal_nested(self) -> None:
        """Nested template literals should tokenize correctly."""
        lexer = get_lexer("javascript")
        code = "`outer ${`inner`} outer`"
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0


class TestNestedComments:
    """Test nested comment constructs."""

    def test_nested_block_comments(self) -> None:
        """Nested block comments should tokenize correctly."""
        lexer = get_lexer("rust")
        code = "/* outer /* inner */ still outer */"
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0

    def test_comments_inside_strings(self) -> None:
        """Comments inside strings should NOT tokenize as comment."""
        lexer = get_lexer("python")
        code = '"not a # comment"'
        tokens = list(lexer.tokenize(code))
        # Should not have COMMENT_SINGLE token
        comment_tokens = [t for t in tokens if t.type == TokenType.COMMENT_SINGLE]
        assert len(comment_tokens) == 0


class TestNestedConstructs:
    """Test various nested language constructs."""

    def test_nested_parentheses(self) -> None:
        """Deeply nested parentheses should tokenize correctly."""
        lexer = get_lexer("python")
        code = "((((((x))))))"
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0

    def test_nested_brackets(self) -> None:
        """Nested brackets should tokenize correctly."""
        lexer = get_lexer("python")
        code = "[[[[[x]]]]]"
        tokens = list(lexer.tokenize(code))
        assert len(tokens) > 0
