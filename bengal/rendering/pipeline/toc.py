"""
Table of Contents (TOC) extraction for rendering pipeline.

Provides TOC parsing and structure extraction from rendered HTML.

Related Modules:
    - bengal.rendering.pipeline.core: Uses TOC extraction
    - bengal.core.page: Page model with toc_items property
"""

from __future__ import annotations

import html as html_module
import re

from bengal.utils.logger import get_logger

# TOC extraction version - increment when extract_toc_structure() logic changes
TOC_EXTRACTION_VERSION = "2"  # v2: Added regex-based indentation parsing for mistune

logger = get_logger(__name__)


def extract_toc_structure(toc_html: str) -> list:
    """
    Parse TOC HTML into structured data for custom rendering.

    Handles both nested <ul> structures (python-markdown style) and flat lists (mistune style).
    For flat lists from mistune, parses indentation to infer heading levels.

    This is a standalone function so it can be called from Page.toc_items
    property for lazy evaluation.

    Args:
        toc_html: HTML table of contents

    Returns:
        List of TOC items with id, title, and level (1=H2, 2=H3, 3=H4, etc.)
    """
    if not toc_html:
        return []

    try:
        # For mistune's flat TOC with indentation, use regex to preserve whitespace
        # Pattern: optional spaces + <li><a href="#id">title</a></li>
        pattern = r'^(\s*)<li><a href="#([^"]+)">([^<]+)</a></li>'

        items = []
        for line in toc_html.split("\n"):
            match = re.match(pattern, line)
            if match:
                indent_str, anchor_id, title = match.groups()
                # Decode HTML entities (e.g., &quot; -> ", &amp; -> &)
                title = html_module.unescape(title)
                # Count spaces to determine level (mistune uses 2 spaces per level)
                indent_level = len(indent_str)
                level = (
                    indent_level // 2
                ) + 1  # 0 spaces = level 1 (H2), 2 spaces = level 2 (H3), etc.

                items.append({"id": anchor_id, "title": title, "level": level})

        if items:
            return items

        # Fallback to HTML parser for nested structures (python-markdown style)
        from html.parser import HTMLParser

        class TOCParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.items = []
                self.current_item = None
                self.depth = 0

            def handle_starttag(self, tag, attrs):
                if tag == "ul":
                    self.depth += 1
                elif tag == "a":
                    attrs_dict = dict(attrs)
                    self.current_item = {
                        "id": attrs_dict.get("href", "").lstrip("#"),
                        "title": "",
                        "level": self.depth,
                    }

            def handle_data(self, data):
                if self.current_item is not None:
                    # Decode HTML entities (e.g., &quot; -> ", &amp; -> &)
                    decoded_data = html_module.unescape(data.strip())
                    self.current_item["title"] += decoded_data

            def handle_endtag(self, tag):
                if tag == "ul":
                    self.depth -= 1
                elif tag == "a" and self.current_item:
                    if self.current_item["title"]:
                        self.items.append(self.current_item)
                    self.current_item = None

        parser = TOCParser()
        parser.feed(toc_html)
        return parser.items

    except Exception as e:
        # If parsing fails, return empty list
        logger.debug(
            "toc_extraction_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="returning_empty_list",
        )
        return []
