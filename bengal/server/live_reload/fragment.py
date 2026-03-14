"""Fragment extraction for instant DOM reload.

Extracts the inner HTML of a selector (e.g. #main-content) from rendered HTML
for SSE-based content swap instead of full page reload.
"""

from __future__ import annotations

import re

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


def extract_main_content(html: str, selector: str = "#main-content") -> str:
    """Extract inner HTML of the first element matching the selector.

    Uses depth-tracking to handle nested same-tag elements correctly
    (e.g. <div id="main-content"><div>inner</div></div>). Handles id
    selectors (#main-content) and common tag+id patterns.

    Args:
        html: Full HTML document string
        selector: CSS selector (default #main-content). Only id selectors
            (#id) are supported; the id value is used to match.

    Returns:
        Inner HTML of the matched element, or empty string if not found.
        Empty string triggers client fallback to full reload.
    """
    if not html or not selector.strip():
        return ""

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

    # Depth-tracking: scan for <tagname and </tagname> to handle nesting
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
