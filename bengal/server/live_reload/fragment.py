"""Fragment extraction for instant DOM reload.

Extracts the inner HTML of a selector (e.g. #main-content) from rendered HTML
for SSE-based content swap instead of full page reload.
"""

from __future__ import annotations

import re


def extract_main_content(html: str, selector: str = "#main-content") -> str:
    """Extract inner HTML of the first element matching the selector.

    Uses regex to find the opening tag and extract content up to the closing
    tag. Handles id selectors (#main-content) and common tag+id patterns.

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

    # Extract id from selector (#main-content -> main-content)
    id_match = re.search(r"#([a-zA-Z][\w-]*)", selector)
    if not id_match:
        return ""

    elem_id = id_match.group(1)

    # Match <tag id="main-content" ...> or <tag id='main-content' ...>
    # Use non-greedy .*? and allow attributes in any order
    attr_pattern = rf'\bid\s*=\s*["\']({re.escape(elem_id)})["\']'
    open_tag = re.compile(
        rf"<(\w+)[^>]*{attr_pattern}[^>]*>",
        re.IGNORECASE | re.DOTALL,
    )
    match = open_tag.search(html)
    if not match:
        return ""

    tag_name = match.group(1).lower()
    start = match.end()

    # Find closing </tagname> - use first occurrence (nested same-tag is rare)
    close_tag = re.compile(rf"</{re.escape(tag_name)}\s*>", re.IGNORECASE)
    next_close = close_tag.search(html, start)
    if not next_close:
        return ""
    return html[start : next_close.start()].strip()
