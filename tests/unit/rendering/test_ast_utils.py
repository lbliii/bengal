"""Tests for AST utilities (walk, extract, transform)."""

from __future__ import annotations

from bengal.rendering.ast_types import ASTNode
from bengal.rendering.ast_utils import (
    extract_links_from_ast,
    extract_plain_text,
    extract_toc_from_ast,
    generate_heading_id,
    walk_ast,
)


class TestWalkAST:
    """Test walk_ast generator."""

    def test_empty_ast(self) -> None:
        """walk_ast handles empty list."""
        nodes = list(walk_ast([]))
        assert nodes == []

    def test_flat_ast(self) -> None:
        """walk_ast traverses flat list."""
        ast: list[ASTNode] = [
            {"type": "paragraph", "children": []},
            {"type": "paragraph", "children": []},
        ]
        nodes = list(walk_ast(ast))
        assert len(nodes) == 2

    def test_nested_ast(self) -> None:
        """walk_ast traverses nested children."""
        ast: list[ASTNode] = [
            {
                "type": "heading",
                "level": 1,
                "children": [{"type": "text", "raw": "Title"}],
            },
            {
                "type": "paragraph",
                "children": [
                    {"type": "text", "raw": "Hello "},
                    {"type": "strong", "children": [{"type": "text", "raw": "world"}]},
                ],
            },
        ]
        nodes = list(walk_ast(ast))
        # heading, text, paragraph, text, strong, text
        assert len(nodes) == 6

    def test_deeply_nested(self) -> None:
        """walk_ast handles deep nesting."""
        ast: list[ASTNode] = [
            {
                "type": "block_quote",
                "children": [
                    {
                        "type": "paragraph",
                        "children": [
                            {
                                "type": "emphasis",
                                "children": [{"type": "text", "raw": "deep"}],
                            }
                        ],
                    }
                ],
            }
        ]
        nodes = list(walk_ast(ast))
        assert len(nodes) == 4
        # Check all types are present
        types = [n.get("type") for n in nodes]
        assert "block_quote" in types
        assert "paragraph" in types
        assert "emphasis" in types
        assert "text" in types


class TestGenerateHeadingId:
    """Test generate_heading_id function."""

    def test_simple_heading(self) -> None:
        """generate_heading_id creates simple slug."""
        node: ASTNode = {
            "type": "heading",
            "level": 1,
            "children": [{"type": "text", "raw": "Hello World"}],
        }
        assert generate_heading_id(node) == "hello-world"

    def test_removes_special_chars(self) -> None:
        """generate_heading_id removes special characters."""
        node: ASTNode = {
            "type": "heading",
            "level": 2,
            "children": [{"type": "text", "raw": "Hello! World?"}],
        }
        assert generate_heading_id(node) == "hello-world"

    def test_handles_unicode(self) -> None:
        """generate_heading_id normalizes unicode."""
        node: ASTNode = {
            "type": "heading",
            "level": 1,
            "children": [{"type": "text", "raw": "Café résumé"}],
        }
        assert generate_heading_id(node) == "cafe-resume"

    def test_nested_formatting(self) -> None:
        """generate_heading_id extracts text from nested children."""
        node: ASTNode = {
            "type": "heading",
            "level": 1,
            "children": [
                {"type": "text", "raw": "Hello "},
                {"type": "strong", "children": [{"type": "text", "raw": "World"}]},
            ],
        }
        assert generate_heading_id(node) == "hello-world"


class TestExtractTocFromAST:
    """Test extract_toc_from_ast function."""

    def test_empty_ast(self) -> None:
        """extract_toc_from_ast handles empty AST."""
        toc = extract_toc_from_ast([])
        assert toc == []

    def test_no_headings(self) -> None:
        """extract_toc_from_ast returns empty for no headings."""
        ast: list[ASTNode] = [
            {"type": "paragraph", "children": [{"type": "text", "raw": "Just text"}]}
        ]
        toc = extract_toc_from_ast(ast)
        assert toc == []

    def test_single_heading(self) -> None:
        """extract_toc_from_ast extracts single heading."""
        ast: list[ASTNode] = [
            {
                "type": "heading",
                "level": 2,
                "children": [{"type": "text", "raw": "Introduction"}],
            }
        ]
        toc = extract_toc_from_ast(ast)
        assert len(toc) == 1
        assert toc[0]["id"] == "introduction"
        assert toc[0]["title"] == "Introduction"
        assert toc[0]["level"] == 1  # H2 -> level 1

    def test_multiple_headings(self) -> None:
        """extract_toc_from_ast extracts multiple headings."""
        ast: list[ASTNode] = [
            {
                "type": "heading",
                "level": 2,
                "children": [{"type": "text", "raw": "First"}],
            },
            {"type": "paragraph", "children": []},
            {
                "type": "heading",
                "level": 3,
                "children": [{"type": "text", "raw": "Second"}],
            },
            {
                "type": "heading",
                "level": 2,
                "children": [{"type": "text", "raw": "Third"}],
            },
        ]
        toc = extract_toc_from_ast(ast)
        assert len(toc) == 3
        assert toc[0]["level"] == 1  # H2
        assert toc[1]["level"] == 2  # H3
        assert toc[2]["level"] == 1  # H2

    def test_heading_with_level_in_attrs(self) -> None:
        """extract_toc_from_ast handles attrs.level format."""
        ast: list[ASTNode] = [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "children": [{"type": "text", "raw": "Test"}],
            }
        ]
        toc = extract_toc_from_ast(ast)
        assert len(toc) == 1
        # Should still work (falls back to attrs.level)


class TestExtractLinksFromAST:
    """Test extract_links_from_ast function."""

    def test_empty_ast(self) -> None:
        """extract_links_from_ast handles empty AST."""
        links = extract_links_from_ast([])
        assert links == []

    def test_no_links(self) -> None:
        """extract_links_from_ast returns empty for no links."""
        ast: list[ASTNode] = [
            {"type": "paragraph", "children": [{"type": "text", "raw": "No links here"}]}
        ]
        links = extract_links_from_ast(ast)
        assert links == []

    def test_single_link(self) -> None:
        """extract_links_from_ast extracts single link."""
        ast: list[ASTNode] = [
            {
                "type": "paragraph",
                "children": [
                    {
                        "type": "link",
                        "url": "/docs/guide/",
                        "children": [{"type": "text", "raw": "Guide"}],
                    }
                ],
            }
        ]
        links = extract_links_from_ast(ast)
        assert links == ["/docs/guide/"]

    def test_multiple_links(self) -> None:
        """extract_links_from_ast extracts all links."""
        ast: list[ASTNode] = [
            {
                "type": "paragraph",
                "children": [
                    {"type": "link", "url": "/first/", "children": []},
                    {"type": "text", "raw": " and "},
                    {"type": "link", "url": "/second/", "children": []},
                ],
            }
        ]
        links = extract_links_from_ast(ast)
        assert links == ["/first/", "/second/"]

    def test_link_with_attrs_url(self) -> None:
        """extract_links_from_ast handles attrs.url format."""
        ast: list[ASTNode] = [
            {
                "type": "link",
                "attrs": {"url": "https://example.com"},
                "children": [],
            }
        ]
        links = extract_links_from_ast(ast)
        assert links == ["https://example.com"]

    def test_nested_links(self) -> None:
        """extract_links_from_ast finds nested links."""
        ast: list[ASTNode] = [
            {
                "type": "block_quote",
                "children": [
                    {
                        "type": "paragraph",
                        "children": [{"type": "link", "url": "/deep/", "children": []}],
                    }
                ],
            }
        ]
        links = extract_links_from_ast(ast)
        assert links == ["/deep/"]


class TestExtractPlainText:
    """Test extract_plain_text function."""

    def test_empty_ast(self) -> None:
        """extract_plain_text handles empty AST."""
        text = extract_plain_text([])
        assert text == ""

    def test_simple_text(self) -> None:
        """extract_plain_text extracts simple text."""
        ast: list[ASTNode] = [
            {"type": "paragraph", "children": [{"type": "text", "raw": "Hello world"}]}
        ]
        text = extract_plain_text(ast)
        assert "Hello world" in text

    def test_multiple_paragraphs(self) -> None:
        """extract_plain_text handles multiple paragraphs."""
        ast: list[ASTNode] = [
            {"type": "paragraph", "children": [{"type": "text", "raw": "First"}]},
            {"type": "paragraph", "children": [{"type": "text", "raw": "Second"}]},
        ]
        text = extract_plain_text(ast)
        assert "First" in text
        assert "Second" in text

    def test_heading_and_content(self) -> None:
        """extract_plain_text extracts headings and content."""
        ast: list[ASTNode] = [
            {
                "type": "heading",
                "level": 1,
                "children": [{"type": "text", "raw": "Title"}],
            },
            {"type": "paragraph", "children": [{"type": "text", "raw": "Content"}]},
        ]
        text = extract_plain_text(ast)
        assert "Title" in text
        assert "Content" in text

    def test_inline_code(self) -> None:
        """extract_plain_text includes inline code."""
        ast: list[ASTNode] = [
            {
                "type": "paragraph",
                "children": [
                    {"type": "text", "raw": "Use "},
                    {"type": "codespan", "raw": "print()"},
                ],
            }
        ]
        text = extract_plain_text(ast)
        assert "Use" in text
        assert "print()" in text

    def test_code_block(self) -> None:
        """extract_plain_text includes code block content."""
        ast: list[ASTNode] = [
            {"type": "block_code", "raw": "def hello():\n    pass", "info": "python"}
        ]
        text = extract_plain_text(ast)
        assert "def hello():" in text

    def test_nested_formatting(self) -> None:
        """extract_plain_text handles nested formatting."""
        ast: list[ASTNode] = [
            {
                "type": "paragraph",
                "children": [
                    {"type": "text", "raw": "Hello "},
                    {
                        "type": "strong",
                        "children": [
                            {"type": "emphasis", "children": [{"type": "text", "raw": "world"}]}
                        ],
                    },
                ],
            }
        ]
        text = extract_plain_text(ast)
        assert "Hello" in text
        assert "world" in text
