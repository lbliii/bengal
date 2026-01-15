"""Tests for AST type definitions."""

from __future__ import annotations

import pytest

from bengal.parsing.ast.types import (
    ASTNode,
    CodeBlockNode,
    HeadingNode,
    TextNode,
    get_heading_level,
    get_node_text,
    is_code_block,
    is_heading,
    is_text,
)


class TestASTNodeTypes:
    """Test AST node type definitions."""

    def test_heading_node_structure(self) -> None:
        """HeadingNode has required fields."""
        node: HeadingNode = {
            "type": "heading",
            "level": 2,
            "children": [],
        }

        assert node["type"] == "heading"
        assert node["level"] == 2

    def test_text_node_structure(self) -> None:
        """TextNode has required fields."""
        node: TextNode = {
            "type": "text",
            "raw": "Hello world",
        }

        assert node["type"] == "text"
        assert node["raw"] == "Hello world"

    def test_code_block_structure(self) -> None:
        """CodeBlockNode has required fields."""
        node: CodeBlockNode = {
            "type": "block_code",
            "raw": "print('hello')",
            "info": "python",
        }

        assert node["type"] == "block_code"
        assert node["info"] == "python"


class TestTypeGuards:
    """Test type guard functions."""

    def test_is_heading(self) -> None:
        """is_heading identifies heading nodes."""
        heading: ASTNode = {"type": "heading", "level": 1, "children": []}
        text: ASTNode = {"type": "text", "raw": "hello"}

        assert is_heading(heading) is True
        assert is_heading(text) is False

    def test_is_text(self) -> None:
        """is_text identifies text nodes."""
        text: ASTNode = {"type": "text", "raw": "hello"}
        heading: ASTNode = {"type": "heading", "level": 1, "children": []}

        assert is_text(text) is True
        assert is_text(heading) is False

    def test_is_code_block(self) -> None:
        """is_code_block identifies code block nodes."""
        code: ASTNode = {"type": "block_code", "raw": "code", "info": None}
        text: ASTNode = {"type": "text", "raw": "hello"}

        assert is_code_block(code) is True
        assert is_code_block(text) is False


class TestHelpers:
    """Test helper functions."""

    def test_get_heading_level(self) -> None:
        """get_heading_level extracts level from heading."""
        heading: ASTNode = {"type": "heading", "level": 3, "children": []}
        text: ASTNode = {"type": "text", "raw": "hello"}

        assert get_heading_level(heading) == 3
        assert get_heading_level(text) is None

    def test_get_node_text(self) -> None:
        """get_node_text extracts raw text."""
        text: ASTNode = {"type": "text", "raw": "hello"}
        code: ASTNode = {"type": "block_code", "raw": "print()", "info": None}
        heading: ASTNode = {"type": "heading", "level": 1, "children": []}

        assert get_node_text(text) == "hello"
        assert get_node_text(code) == "print()"
        assert get_node_text(heading) == ""


class TestTypeNarrowing:
    """Test type narrowing with match statement."""

    def test_match_statement_works(self) -> None:
        """Type narrowing works with match statement."""
        node: ASTNode = {"type": "heading", "level": 2, "children": []}

        match node["type"]:
            case "heading":
                assert node["level"] == 2  # Type narrowed
            case _:
                pytest.fail("Should match heading")
