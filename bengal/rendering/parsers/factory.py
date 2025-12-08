"""
HTML parser factory for Bengal.

Returns NativeHTMLParser, optimized for build-time validation and health checks.
Replaced BeautifulSoup4 for performance (~5-10x faster for text extraction).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bengal.utils.logger import get_logger

from .native_html import NativeHTMLParser

logger = get_logger(__name__)


class ParserBackend:
    """HTML parser backend identifiers."""

    NATIVE = "native"


class ParserFactory:
    """
    Factory for HTML parsers used in Bengal.

    Currently returns NativeHTMLParser, which is optimized for build-time
    validation and health checks. Replaced BeautifulSoup4 for performance
    (~5-10x faster for text extraction).
    """

    @staticmethod
    def get_html_parser(backend: str | None = None) -> Callable[..., Any]:
        """
        Get HTML parser for build-time validation and health checks.

        Args:
            backend: Parser backend (currently only 'native' supported)

        Returns:
            Parser callable that returns NativeHTMLParser instance

        Example:
            >>> parser_fn = ParserFactory.get_html_parser()
            >>> result = parser_fn("<p>Text</p>")
            >>> text = result.get_text()
        """
        if backend and backend != ParserBackend.NATIVE:
            logger.warning(
                f"Unsupported parser backend '{backend}', using native. "
                f"Only '{ParserBackend.NATIVE}' is currently supported."
            )

        # NativeHTMLParser.feed() returns self, allowing parser(html).get_text()
        return lambda content: NativeHTMLParser().feed(content)

    @staticmethod
    def get_parser_features(backend: str) -> dict[str, Any]:
        """
        Get features/capabilities for a backend.

        Args:
            backend: Parser backend identifier

        Returns:
            Dictionary of parser features
        """
        features = {
            ParserBackend.NATIVE: {
                "tolerant": True,
                "speed": "fast",
                "xpath": False,
                "dependencies": None,
            },
        }
        return features.get(backend, {})
