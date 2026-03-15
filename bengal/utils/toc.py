"""Table of Contents (TOC) extraction from HTML.

Pure utility for parsing TOC HTML into structured data. Used by both
core (Page.toc_items) and rendering (pipeline). No rendering imports.

TOC_EXTRACTION_VERSION is incremented when extraction logic changes,
enabling cache invalidation in incremental builds.
"""

from __future__ import annotations

import html as html_module
import re

from bengal.core.page.types import TOCItem
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

# Increment when extract_toc_structure() logic changes
TOC_EXTRACTION_VERSION = "2"  # v2: Added regex-based indentation parsing for flat lists


def extract_toc_structure(toc_html: str) -> list[TOCItem]:
    """
    Parse TOC HTML into structured data for custom rendering.

    Handles both nested <ul> structures and flat lists with indentation.
    For flat lists, parses indentation to infer heading levels.

    Args:
        toc_html: HTML table of contents

    Returns:
        List of TOC items with id, title, and level (1=H2, 2=H3, 3=H4, etc.)
    """
    if not toc_html:
        return []

    try:
        # For flat TOC with indentation, use regex to preserve whitespace
        pattern = r'^(\s*)<li><a href="#([^"]+)">([^<]+)</a></li>'

        items: list[TOCItem] = []
        for line in toc_html.split("\n"):
            match = re.match(pattern, line)
            if match:
                indent_str, anchor_id, title = match.groups()
                title = html_module.unescape(title)
                indent_level = len(indent_str)
                level = (indent_level // 2) + 1

                items.append(TOCItem(id=anchor_id, title=title, level=level))

        if items:
            return items

        # Fallback to HTML parser for nested structures (python-markdown style)
        from html.parser import HTMLParser

        class TOCParser(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.items: list[TOCItem] = []
                self._current_id: str = ""
                self._current_title: str = ""
                self._current_level: int = 0
                self.depth = 0

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                if tag == "ul":
                    self.depth += 1
                elif tag == "a":
                    attrs_dict = dict(attrs)
                    self._current_id = (attrs_dict.get("href") or "").lstrip("#")
                    self._current_title = ""
                    self._current_level = self.depth

            def handle_data(self, data: str) -> None:
                if self._current_id:
                    decoded_data = html_module.unescape(data.strip())
                    self._current_title += decoded_data

            def handle_endtag(self, tag: str) -> None:
                if tag == "ul":
                    self.depth -= 1
                elif tag == "a" and self._current_id:
                    if self._current_title:
                        self.items.append(
                            TOCItem(
                                id=self._current_id,
                                title=self._current_title,
                                level=self._current_level,
                            )
                        )
                    self._current_id = ""
                    self._current_title = ""

        parser = TOCParser()
        parser.feed(toc_html)
        return parser.items

    except Exception as e:
        logger.debug(
            "toc_extraction_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="returning_empty_list",
        )
        return []
