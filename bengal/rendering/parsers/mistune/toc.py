"""
Table of contents extraction and heading anchor injection.

Provides fast regex-based TOC generation (5-10x faster than BeautifulSoup):
- Heading anchor injection (IDs only)
- TOC extraction from anchored headings
- Explicit anchor syntax support ({#custom-id})
- Blockquote heading handling
"""

from __future__ import annotations

import html as html_module
import re
from typing import Any

from bengal.errors import format_suggestion
from bengal.rendering.parsers.mistune.patterns import (
    EXPLICIT_ID_PATTERN,
    HEADING_PATTERN,
    HTML_TAG_PATTERN,
    TOC_HEADING_PATTERN,
)
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def inject_heading_anchors(html: str, slugify_func: Any) -> str:
    """
    Inject IDs into heading tags using fast regex (5-10x faster than BS4).

    Excludes headings inside blockquotes from getting IDs (so they don't appear in TOC).

    Single-pass regex replacement handles:
    - h2, h3, h4 headings (matching python-markdown's toc_depth)
    - Existing IDs (preserves them)
    - Heading content with nested HTML
    - Generates clean slugs from heading text
    - Skips headings inside <blockquote> tags

    Args:
        html: HTML content from markdown parser
        slugify_func: Function to convert text to slug

    Returns:
        HTML with heading IDs added (except those in blockquotes)
    """
    # Quick rejection: skip if no headings
    if not html or not ("<h2" in html or "<h3" in html or "<h4" in html):
        return html

    # If no blockquotes, use fast path
    if "<blockquote" not in html:

        def replace_heading(match: re.Match[str]) -> str:
            """Replace heading with ID only (no inline headerlink)."""
            tag = match.group(1)  # 'h2', 'h3', or 'h4'
            attrs = match.group(2)  # Existing attributes
            content = match.group(3)  # Heading content

            # Skip if already has id= attribute
            if "id=" in attrs or "id =" in attrs:
                return match.group(0)

            # Check for explicit {#custom-id} syntax (MyST-compatible)
            id_match = EXPLICIT_ID_PATTERN.search(content)
            if id_match:
                slug = id_match.group(1)
                # Remove {#id} from displayed content
                content = EXPLICIT_ID_PATTERN.sub("", content)
            else:
                # Fall back to auto-generated slug (existing behavior)
                text = HTML_TAG_PATTERN.sub("", content).strip()
                if not text:
                    return match.group(0)
                slug = slugify_func(text)

            # Build heading with ID only; theme JS adds copy-link anchor
            return f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'

        try:
            return HEADING_PATTERN.sub(replace_heading, html)
        except Exception as e:
            # On any error, return original HTML (safe fallback)
            logger.warning(
                "heading_anchor_injection_error", error=str(e), error_type=type(e).__name__
            )
            return html

    # Slow path: need to skip headings inside blockquotes
    try:
        parts: list[str] = []
        in_blockquote = 0  # Track nesting level
        current_pos = 0

        # Find all blockquote open/close tags
        blockquote_pattern = re.compile(r"<(/?)blockquote[^>]*>", re.IGNORECASE)

        for match in blockquote_pattern.finditer(html):
            # Process content before this tag
            before = html[current_pos : match.start()]

            if in_blockquote == 0:
                # Outside blockquote: add anchors
                def replace_heading(m: re.Match[str]) -> str:
                    tag = m.group(1)
                    attrs = m.group(2)
                    content = m.group(3)

                    if "id=" in attrs or "id =" in attrs:
                        return m.group(0)

                    # Check for explicit {#custom-id} syntax (MyST-compatible)
                    id_match = EXPLICIT_ID_PATTERN.search(content)
                    if id_match:
                        slug = id_match.group(1)
                        content = EXPLICIT_ID_PATTERN.sub("", content)
                    else:
                        text = HTML_TAG_PATTERN.sub("", content).strip()
                        if not text:
                            return m.group(0)
                        slug = slugify_func(text)

                    return f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'

                parts.append(HEADING_PATTERN.sub(replace_heading, before))
            else:
                # Inside blockquote: keep as-is
                parts.append(before)

            # Add the blockquote tag
            parts.append(match.group(0))

            # Update nesting level
            if match.group(1) == "/":
                in_blockquote = max(0, in_blockquote - 1)
            else:
                in_blockquote += 1

            current_pos = match.end()

        # Process remaining content
        remaining = html[current_pos:]
        if in_blockquote == 0:

            def replace_heading(m: re.Match[str]) -> str:
                tag = m.group(1)
                attrs = m.group(2)
                content = m.group(3)

                if "id=" in attrs or "id =" in attrs:
                    return m.group(0)

                # Check for explicit {#custom-id} syntax (MyST-compatible)
                id_match = EXPLICIT_ID_PATTERN.search(content)
                if id_match:
                    slug = id_match.group(1)
                    content = EXPLICIT_ID_PATTERN.sub("", content)
                else:
                    text = HTML_TAG_PATTERN.sub("", content).strip()
                    if not text:
                        return m.group(0)
                    slug = slugify_func(text)

                return f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'

            parts.append(HEADING_PATTERN.sub(replace_heading, remaining))
        else:
            parts.append(remaining)

        return "".join(parts)

    except Exception as e:
        # On any error, return original HTML (safe fallback)
        logger.warning(
            "heading_anchor_injection_error_blockquote",
            error=str(e),
            error_type=type(e).__name__,
        )
        return html


def extract_toc(html: str) -> str:
    """
    Extract table of contents from HTML with anchored headings using fast regex.

    Builds a nested list of links to heading anchors (5-8x faster than BS4).
    Expects headings to have IDs (anchors handled by theme).

    Args:
        html: HTML content with heading IDs and headerlinks

    Returns:
        TOC as HTML (div.toc > ul > li > a structure)
    """
    # Quick rejection: skip if no headings
    if not html or not ("<h2" in html or "<h3" in html or "<h4" in html):
        return ""

    try:
        toc_items = []

        # Match headings with IDs: <h2 id="slug" ...>Title</h2>
        for match in TOC_HEADING_PATTERN.finditer(html):
            level = int(match.group(1)[1])  # 'h2' → 2, 'h3' → 3, etc.
            heading_id = match.group(2)  # The slug/ID
            title_html = match.group(3).strip()  # Title with possible HTML

            # Strip HTML tags to get clean title text
            title = HTML_TAG_PATTERN.sub("", title_html).strip()
            # Decode HTML entities (e.g., &quot; -> ", &amp; -> &)
            title = html_module.unescape(title)
            # Remove pilcrow (¶) character that remains after stripping headerlink
            title = title.replace("¶", "").strip()
            if not title:
                continue

            # Truncate long titles (especially those with code) for TOC display
            # 50 chars is reasonable for 280px sidebar TOC to prevent overflow
            # This ensures titles fit even with code snippets and file paths
            if len(title) > 50:
                title = title[:47] + "..."

            # Build indented list item
            indent = "  " * (level - 2)
            toc_items.append(f'{indent}<li><a href="#{heading_id}">{title}</a></li>')

        if toc_items:
            return '<div class="toc">\n<ul>\n' + "\n".join(toc_items) + "\n</ul>\n</div>"

        return ""

    except Exception as e:
        # On any error, return empty TOC (safe fallback)
        suggestion = format_suggestion("parsing", "toc_extraction_error")
        logger.warning(
            "toc_extraction_error",
            error=str(e),
            error_type=type(e).__name__,
            suggestion=suggestion,
        )
        return ""
