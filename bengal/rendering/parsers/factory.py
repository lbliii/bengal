from bs4 import BeautifulSoup

try:
    from lxml import etree as lxml_parser

    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False
    lxml_parser = None

from .native_html import NativeHTMLParser


class ParserBackend:
    BS4 = "bs4"
    LXML = "lxml"
    NATIVE = "native"


class ParserFactory:
    @staticmethod
    def get_html_parser(backend: str | None = None) -> callable:
        """
        Factory for HTML parsers. Defaults to bs4 if available, else lxml, else native.

        :param backend: Preferred backend ('bs4', 'lxml', 'native')
        :return: Parser callable (soup constructor or etree.fromstring)
        """
        if backend == ParserBackend.LXML and LXML_AVAILABLE:
            return lambda content: lxml_parser.fromstring(content, parser=lxml_parser.HTMLParser())
        if backend == ParserBackend.BS4:
            return lambda content: BeautifulSoup(content, "html.parser")
        if backend == ParserBackend.NATIVE:
            return lambda content: NativeHTMLParser().feed(content)  # Returns parser instance

        # Default: Native first
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
