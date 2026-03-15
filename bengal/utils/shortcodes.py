"""Shortcode detection utilities (content parsing only).

Pure string/regex utilities for detecting shortcode usage in content.
Used by core (Page.HasShortcode) and rendering (shortcode expansion).
No rendering-specific imports.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.protocols import PageLike

# Hugo-compatible shortcode patterns
# Self-closing: {{< name args >}} or {{< name args />}}
# Paired opening: {{< name args >}} or {{% name args %}}
SHORTCODE_SELF_CLOSING = re.compile(
    r"\{\{<\s*([\w/.-]+)(?:\s+([^>]*))?\s*/?\s*>\s*\}\}",
    re.DOTALL,
)
SHORTCODE_OPENING = re.compile(
    r"\{\{([<%])\s*([\w/.-]+)(?:\s+([^>%]*?))?\s*[>%]\s*\}\}",
    re.DOTALL,
)


def shortcodes_used_in_content(content: str) -> frozenset[str]:
    """Extract shortcode names used in content ({{< name or {{% name)."""
    names: set[str] = set()
    for pattern in (SHORTCODE_OPENING, SHORTCODE_SELF_CLOSING):
        for m in pattern.finditer(content):
            name = m.group(2).strip()
            if name and not name.startswith("/"):
                names.add(name)
    return frozenset(names)


def has_shortcode(page: PageLike, name: str) -> bool:
    """Return True if page content uses the given shortcode."""
    source = getattr(page, "_source", None) or getattr(page, "_raw_content", "")
    return name in shortcodes_used_in_content(str(source or ""))
