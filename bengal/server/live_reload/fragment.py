"""Fragment extraction for instant DOM reload.

Extracts the inner HTML of a selector (e.g. #main-content) from rendered HTML
for SSE-based content swap instead of full page reload.

Uses BeautifulSoup with html.parser when bs4 is installed (supports #id,
.class, tag.class). Falls back to regex-based extraction for #id only when
bs4 is not available.
"""

from __future__ import annotations

import re

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

_BS4_AVAILABLE: bool | None = None


def _has_bs4() -> bool:
    """Check if BeautifulSoup is available (lazy, cached)."""
    global _BS4_AVAILABLE
    if _BS4_AVAILABLE is None:
        try:
            __import__("bs4")
            _BS4_AVAILABLE = True
        except ImportError:
            _BS4_AVAILABLE = False
    return _BS4_AVAILABLE


def _extract_with_bs4(html: str, selector: str) -> str:
    """Extract using BeautifulSoup (html.parser). Returns empty string on failure."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    elem = soup.select_one(selector)
    if elem is None:
        logger.debug("fragment_extraction_not_found", selector=selector)
        return ""
    return elem.decode_contents().strip()


def _extract_with_regex(html: str, selector: str) -> str:
    """Regex-based extraction for #id selectors only. Fallback when bs4 unavailable."""
    id_match = re.search(r"#([a-zA-Z][\w-]*)", selector)
    if not id_match:
        logger.debug("fragment_extraction_unsupported_selector", selector=selector)
        return ""

    elem_id = id_match.group(1)
    attr_pattern = rf'\bid\s*=\s*["\']({re.escape(elem_id)})["\']'
    open_tag = re.compile(
        rf"<(\w+)[^>]*{attr_pattern}[^>]*>",
        re.IGNORECASE | re.DOTALL,
    )
    match = open_tag.search(html)
    if not match:
        logger.debug("fragment_extraction_not_found", selector=selector)
        return ""

    tag_name = match.group(1)
    start = match.end()

    depth = 1
    i = start
    open_pat = re.compile(rf"<\s*{re.escape(tag_name)}\b", re.IGNORECASE)
    close_pat = re.compile(rf"<\s*/\s*{re.escape(tag_name)}\s*>", re.IGNORECASE)

    while i < len(html) and depth > 0:
        next_lt = html.find("<", i)
        if next_lt == -1:
            break
        rest = html[next_lt:]
        close_m = close_pat.match(rest)
        open_m = open_pat.match(rest)
        if close_m:
            depth -= 1
            if depth == 0:
                return html[start:next_lt].strip()
            i = next_lt + 1
        elif open_m:
            depth += 1
            i = next_lt + 1
        else:
            i = next_lt + 1

    logger.debug("fragment_extraction_unclosed_tag", selector=selector)
    return ""


def extract_main_content(html: str, selector: str = "#main-content") -> str:
    """Extract inner HTML of the first element matching the selector.

    Uses BeautifulSoup (html.parser) when bs4 is installed, supporting #id,
    .class, and tag.class selectors. Falls back to regex for #id only when
    bs4 is not available.

    Args:
        html: Full HTML document string
        selector: CSS selector (default #main-content). With bs4: #id, .class,
            tag.class. With regex fallback: #id only.

    Returns:
        Inner HTML of the matched element, or empty string if not found.
        Empty string triggers client fallback to full reload.
    """
    if not html or not selector.strip():
        return ""

    if _has_bs4():
        return _extract_with_bs4(html, selector)
    return _extract_with_regex(html, selector)
