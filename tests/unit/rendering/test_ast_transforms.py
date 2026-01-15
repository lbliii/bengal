"""Tests for AST-level link transformations."""

from __future__ import annotations

from bengal.parsing.ast.transforms import (
    add_baseurl_to_ast,
    normalize_md_links_in_ast,
    transform_ast_for_output,
    transform_links_in_ast,
)
from bengal.parsing.ast.types import ASTNode


class TestTransformLinksInAST:
    """Test transform_links_in_ast function."""

    def test_empty_ast(self) -> None:
        """transform_links_in_ast handles empty AST."""
        result = transform_links_in_ast([], lambda x: x)
        assert result == []

    def test_no_links(self) -> None:
        """transform_links_in_ast returns unchanged AST without links."""
        ast: list[ASTNode] = [
            {"type": "paragraph", "children": [{"type": "text", "raw": "No links"}]}
        ]
        result = transform_links_in_ast(ast, lambda x: x.upper())
        assert result[0]["type"] == "paragraph"

    def test_transforms_link_url(self) -> None:
        """transform_links_in_ast transforms link URLs."""
        ast: list[ASTNode] = [
            {
                "type": "link",
                "url": "/docs/",
                "children": [{"type": "text", "raw": "Docs"}],
            }
        ]
        result = transform_links_in_ast(ast, lambda x: f"/prefix{x}")
        assert result[0]["url"] == "/prefix/docs/"

    def test_transforms_nested_links(self) -> None:
        """transform_links_in_ast transforms nested links."""
        ast: list[ASTNode] = [
            {
                "type": "paragraph",
                "children": [
                    {
                        "type": "link",
                        "url": "/nested/",
                        "children": [{"type": "text", "raw": "Link"}],
                    }
                ],
            }
        ]
        result = transform_links_in_ast(ast, lambda x: x.upper())
        # Navigate to the link
        para = result[0]
        link = para["children"][0]
        assert link["url"] == "/NESTED/"

    def test_transforms_image_src(self) -> None:
        """transform_links_in_ast transforms image src."""
        ast: list[ASTNode] = [
            {"type": "image", "src": "/img/photo.jpg", "alt": "Photo", "title": None}
        ]
        result = transform_links_in_ast(ast, lambda x: f"/cdn{x}")
        assert result[0]["src"] == "/cdn/img/photo.jpg"

    def test_preserves_children(self) -> None:
        """transform_links_in_ast preserves link children."""
        ast: list[ASTNode] = [
            {
                "type": "link",
                "url": "/docs/",
                "children": [{"type": "strong", "children": [{"type": "text", "raw": "Bold"}]}],
            }
        ]
        result = transform_links_in_ast(ast, lambda x: x)
        link = result[0]
        assert len(link["children"]) == 1
        assert link["children"][0]["type"] == "strong"


class TestNormalizeMdLinksInAST:
    """Test normalize_md_links_in_ast function."""

    def test_regular_md_link(self) -> None:
        """normalize_md_links_in_ast converts .md to clean URL."""
        ast: list[ASTNode] = [{"type": "link", "url": "./guide.md", "children": []}]
        result = normalize_md_links_in_ast(ast)
        assert result[0]["url"] == "./guide/"

    def test_relative_md_link(self) -> None:
        """normalize_md_links_in_ast handles relative paths."""
        ast: list[ASTNode] = [{"type": "link", "url": "../other.md", "children": []}]
        result = normalize_md_links_in_ast(ast)
        assert result[0]["url"] == "../other/"

    def test_index_md(self) -> None:
        """normalize_md_links_in_ast handles _index.md."""
        ast: list[ASTNode] = [{"type": "link", "url": "./_index.md", "children": []}]
        result = normalize_md_links_in_ast(ast)
        assert result[0]["url"] == "./"

    def test_nested_index_md(self) -> None:
        """normalize_md_links_in_ast handles nested _index.md."""
        ast: list[ASTNode] = [{"type": "link", "url": "./docs/_index.md", "children": []}]
        result = normalize_md_links_in_ast(ast)
        assert result[0]["url"] == "./docs/"

    def test_plain_index_md(self) -> None:
        """normalize_md_links_in_ast handles plain index.md."""
        ast: list[ASTNode] = [{"type": "link", "url": "index.md", "children": []}]
        result = normalize_md_links_in_ast(ast)
        assert result[0]["url"] == "./"

    def test_non_md_link_unchanged(self) -> None:
        """normalize_md_links_in_ast leaves non-.md links unchanged."""
        ast: list[ASTNode] = [{"type": "link", "url": "/docs/guide/", "children": []}]
        result = normalize_md_links_in_ast(ast)
        assert result[0]["url"] == "/docs/guide/"

    def test_external_link_unchanged(self) -> None:
        """normalize_md_links_in_ast leaves external links unchanged."""
        ast: list[ASTNode] = [{"type": "link", "url": "https://example.com", "children": []}]
        result = normalize_md_links_in_ast(ast)
        assert result[0]["url"] == "https://example.com"


class TestAddBaseurlToAST:
    """Test add_baseurl_to_ast function."""

    def test_empty_baseurl(self) -> None:
        """add_baseurl_to_ast with empty baseurl returns unchanged."""
        ast: list[ASTNode] = [{"type": "link", "url": "/docs/", "children": []}]
        result = add_baseurl_to_ast(ast, "")
        assert result[0]["url"] == "/docs/"

    def test_adds_baseurl_to_internal(self) -> None:
        """add_baseurl_to_ast prepends baseurl to internal links."""
        ast: list[ASTNode] = [{"type": "link", "url": "/docs/guide/", "children": []}]
        result = add_baseurl_to_ast(ast, "/bengal")
        assert result[0]["url"] == "/bengal/docs/guide/"

    def test_skips_external_links(self) -> None:
        """add_baseurl_to_ast skips external links."""
        ast: list[ASTNode] = [{"type": "link", "url": "https://example.com", "children": []}]
        result = add_baseurl_to_ast(ast, "/bengal")
        assert result[0]["url"] == "https://example.com"

    def test_skips_relative_links(self) -> None:
        """add_baseurl_to_ast skips relative links."""
        ast: list[ASTNode] = [
            {"type": "link", "url": "./guide/", "children": []},
            {"type": "link", "url": "../other/", "children": []},
        ]
        result = add_baseurl_to_ast(ast, "/bengal")
        assert result[0]["url"] == "./guide/"
        assert result[1]["url"] == "../other/"

    def test_skips_anchor_links(self) -> None:
        """add_baseurl_to_ast skips anchor links."""
        ast: list[ASTNode] = [{"type": "link", "url": "#section", "children": []}]
        result = add_baseurl_to_ast(ast, "/bengal")
        assert result[0]["url"] == "#section"

    def test_skips_already_prefixed(self) -> None:
        """add_baseurl_to_ast skips links with baseurl already."""
        ast: list[ASTNode] = [{"type": "link", "url": "/bengal/docs/", "children": []}]
        result = add_baseurl_to_ast(ast, "/bengal")
        assert result[0]["url"] == "/bengal/docs/"

    def test_normalizes_trailing_slash(self) -> None:
        """add_baseurl_to_ast normalizes baseurl trailing slash."""
        ast: list[ASTNode] = [{"type": "link", "url": "/docs/", "children": []}]
        result = add_baseurl_to_ast(ast, "/bengal/")  # Trailing slash
        assert result[0]["url"] == "/bengal/docs/"


class TestTransformASTForOutput:
    """Test transform_ast_for_output convenience function."""

    def test_applies_both_transforms(self) -> None:
        """transform_ast_for_output applies both md normalization and baseurl."""
        ast: list[ASTNode] = [
            {"type": "link", "url": "./guide.md", "children": []},
            {"type": "link", "url": "/docs/", "children": []},
        ]
        result = transform_ast_for_output(ast, baseurl="/bengal", normalize_md=True)
        # First link: ./guide.md -> ./guide/ (relative, no baseurl)
        assert result[0]["url"] == "./guide/"
        # Second link: /docs/ -> /bengal/docs/
        assert result[1]["url"] == "/bengal/docs/"

    def test_skip_md_normalization(self) -> None:
        """transform_ast_for_output can skip md normalization."""
        ast: list[ASTNode] = [{"type": "link", "url": "./guide.md", "children": []}]
        result = transform_ast_for_output(ast, normalize_md=False)
        assert result[0]["url"] == "./guide.md"

    def test_no_baseurl(self) -> None:
        """transform_ast_for_output works without baseurl."""
        ast: list[ASTNode] = [{"type": "link", "url": "./guide.md", "children": []}]
        result = transform_ast_for_output(ast, baseurl=None)
        assert result[0]["url"] == "./guide/"
