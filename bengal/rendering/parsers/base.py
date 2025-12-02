"""Base class for Markdown parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseMarkdownParser(ABC):
    """
    Abstract base class for Markdown parsers.
    All parser implementations must implement this interface.

    AST Support (Phase 3):
        Parsers may optionally support true AST output via:
        - parse_to_ast(): Parse content to AST tokens
        - render_ast(): Render AST tokens to HTML
        - supports_ast: Property indicating AST support

        See: plan/active/rfc-content-ast-architecture.md
    """

    @property
    def supports_ast(self) -> bool:
        """
        Check if this parser supports true AST output.

        Returns:
            True if parser can return AST tokens via parse_to_ast()

        Note:
            Override in subclasses that support AST (e.g., MistuneParser).
        """
        return False

    @abstractmethod
    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        """
        Parse Markdown content into HTML.

        Args:
            content: Raw Markdown content
            metadata: Page metadata

        Returns:
            Parsed HTML content
        """
        pass

    @abstractmethod
    def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]:
        """
        Parse Markdown content and extract table of contents.

        Args:
            content: Raw Markdown content
            metadata: Page metadata

        Returns:
            Tuple of (parsed HTML, table of contents HTML)
        """
        pass

    def parse_to_ast(self, content: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse Markdown content to AST tokens.

        Optional method for parsers that support true AST output.
        Override in subclasses (e.g., MistuneParser).

        Args:
            content: Raw Markdown content
            metadata: Page metadata

        Returns:
            List of AST token dictionaries

        Raises:
            NotImplementedError: If parser doesn't support AST

        Example:
            >>> parser.parse_to_ast("# Hello")
            [{'type': 'heading', 'level': 1, 'children': [{'type': 'text', 'raw': 'Hello'}]}]
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support AST output. "
            f"Use parse() for HTML output instead."
        )

    def render_ast(self, ast: list[dict[str, Any]]) -> str:
        """
        Render AST tokens to HTML.

        Optional method for parsers that support true AST output.
        Override in subclasses (e.g., MistuneParser).

        Args:
            ast: List of AST token dictionaries

        Returns:
            Rendered HTML string

        Raises:
            NotImplementedError: If parser doesn't support AST

        Example:
            >>> ast = [{'type': 'heading', 'level': 1, 'children': [...]}]
            >>> parser.render_ast(ast)
            '<h1>Hello</h1>'
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support AST rendering. "
            f"Use parse() for direct HTML output instead."
        )
