"""Python-markdown parser implementation."""

from __future__ import annotations

from typing import Any, override

from bengal.rendering.parsers.base import BaseMarkdownParser
from bengal.rendering.parsers.pygments_patch import PygmentsPatch
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class PythonMarkdownParser(BaseMarkdownParser):
    """
    Parser using python-markdown library.
    Full-featured with all extensions.

    Performance Note:
        Uses cached Pygments lexers to avoid expensive plugin discovery
        on every code block. This provides 3-10× speedup on sites with
        many code blocks.
    """

    def __init__(self) -> None:
        """Initialize the python-markdown parser with extensions."""
        import markdown

        # Apply performance patch for Pygments lexer caching
        # This is a process-wide optimization that improves code highlighting speed
        PygmentsPatch.apply()

        self.md = markdown.Markdown(
            extensions=[
                "extra",
                "codehilite",
                "fenced_code",
                "tables",
                "toc",
                "meta",
                "attr_list",
                "def_list",
                "footnotes",
                "admonition",
            ],
            extension_configs={
                "codehilite": {
                    "css_class": "highlight",
                    "linenums": False,
                },
                "toc": {
                    "permalink": False,  # Permalink handled by JavaScript copy-link
                    "toc_depth": "2-4",
                },
            },
        )

    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        """Parse Markdown content into HTML."""
        self.md.reset()
        return self.md.convert(content)

    @override
    def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]:
        """Parse Markdown content and extract table of contents."""
        self.md.reset()
        html = self.md.convert(content)
        toc = getattr(self.md, "toc", "")
        return html, toc
