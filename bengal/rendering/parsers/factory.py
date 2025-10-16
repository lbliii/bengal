try:
    from lxml import etree as lxml_parser

    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False
    lxml_parser = None

from bengal.utils.logger import get_logger

from .native_html import NativeHTMLParser

logger = get_logger(__name__)

# Lazy import bs4 to avoid making it a required dependency
BS4_AVAILABLE = False
try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None


class ParserBackend:
    BS4 = "bs4"
    LXML = "lxml"
    NATIVE = "native"


class ParserFactory:
    @staticmethod
    def get_html_parser(backend: str | None = None) -> callable:
        """
        Factory for HTML parsers. Defaults to bs4 if available, else lxml, else native.

        ⚠️  Note: Native parser is test-only with limitations.
        See bengal.rendering.parsers.native_html for details.

        :param backend: Preferred backend ('bs4', 'lxml', 'native')
        :return: Parser callable (soup constructor or etree.fromstring)
        """
        if backend == ParserBackend.LXML and LXML_AVAILABLE:
            return lambda content: lxml_parser.fromstring(content, parser=lxml_parser.HTMLParser())
        if backend == ParserBackend.BS4:
            if not BS4_AVAILABLE:
                raise ImportError(
                    "beautifulsoup4 is not installed. "
                    "Install it with: pip install beautifulsoup4 or pip install bengal[parsing]"
                )
            return lambda content: BeautifulSoup(content, "html.parser")
        if backend == ParserBackend.NATIVE:
            logger.warning(
                "Using NativeHTMLParser (test/validation only). "
                "Has limitations: no nested code blocks, fragile with malformed HTML. "
                "Install beautifulsoup4 for robust production parsing."
            )
            # NativeHTMLParser.feed() returns self, allowing parser(html).get_text()
            return lambda content: NativeHTMLParser().feed(content)

        # Default: Native first (with warning)
        return ParserFactory.get_html_parser("native")

    @staticmethod
    def get_parser_features(backend: str) -> dict:
        """Get features/capabilities for a backend."""
        features = {
            ParserBackend.BS4: {"tolerant": True, "speed": "medium", "xpath": False},
            ParserBackend.LXML: {"tolerant": False, "speed": "fast", "xpath": True},
            ParserBackend.NATIVE: {"tolerant": True, "speed": "slow", "xpath": False},
        }
        return features.get(backend, {})
