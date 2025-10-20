"""Base class for Markdown parsers."""


from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseMarkdownParser(ABC):
    """
    Abstract base class for Markdown parsers.
    All parser implementations must implement this interface.
    """

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
