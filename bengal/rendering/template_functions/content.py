"""
Content transformation functions for templates.

Provides 6 functions for HTML/content manipulation and transformation.
"""

from __future__ import annotations

import html as html_module
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register content transformation functions with Jinja2 environment."""
    env.filters.update(
        {
            "safe_html": safe_html,
            "html_escape": html_escape,
            "html_unescape": html_unescape,
            "nl2br": nl2br,
            "smartquotes": smartquotes,
            "emojify": emojify,
            "extract_content": extract_content,
        }
    )


def safe_html(text: str) -> str:
    """
    Mark HTML as safe (prevents auto-escaping).

    This is a marker function - Jinja2's 'safe' filter should be used instead.
    Included for compatibility with other SSGs.

    Args:
        text: HTML text to mark as safe

    Returns:
        Same text (use with Jinja2's |safe filter)

    Example:
        {{ content | safe_html | safe }}
    """
    return text


def html_escape(text: str) -> str:
    """
    Escape HTML entities.

    Converts special characters to HTML entities:
    - < becomes &lt;
    - > becomes &gt;
    - & becomes &amp;
    - " becomes &quot;
    - ' becomes &#x27;

    Args:
        text: Text to escape

    Returns:
        Escaped HTML text

    Example:
        {{ user_input | html_escape }}
        # "<script>" becomes "&lt;script&gt;"
    """
    if not text:
        return ""

    return html_module.escape(text)


def html_unescape(text: str) -> str:
    """
    Unescape HTML entities.

    Converts HTML entities back to characters:
    - &lt; becomes <
    - &gt; becomes >
    - &amp; becomes &
    - &quot; becomes "

    Args:
        text: HTML text with entities

    Returns:
        Unescaped text

    Example:
        {{ escaped_text | html_unescape }}
        # "&lt;Hello&gt;" becomes "<Hello>"
    """
    if not text:
        return ""

    return html_module.unescape(text)


def nl2br(text: str) -> str:
    """
    Convert newlines to HTML <br> tags.

    Replaces \n with <br>\n to preserve both HTML and text formatting.

    Args:
        text: Text with newlines

    Returns:
        HTML with <br> tags

    Example:
        {{ text | nl2br | safe }}
        # "Line 1\nLine 2" becomes "Line 1<br>\nLine 2"
    """
    if not text:
        return ""

    return text.replace("\n", "<br>\n")


def smartquotes(text: str) -> str:
    """
    Convert straight quotes to smart (curly) quotes.

    Converts:
    - " to " and "
    - ' to ' and '
    - -- to –
    - --- to —

    Args:
        text: Text with straight quotes

    Returns:
        Text with smart quotes

    Example:
        {{ text | smartquotes }}
        # "Hello" becomes "Hello"
    """
    if not text:
        return ""

    # Convert triple dash to em-dash
    text = re.sub(r"---", "—", text)

    # Convert double dash to en-dash
    text = re.sub(r"--", "–", text)

    # Convert straight quotes to curly quotes
    # This is a simplified implementation
    # Opening double quote (use Unicode escape)
    text = re.sub(r'(\s|^)"', "\\1\u201c", text)
    # Closing double quote
    text = re.sub(r'"', "\u201d", text)

    # Opening single quote
    text = re.sub(r"(\s|^)'", "\\1\u2018", text)
    # Closing single quote (including apostrophes)
    text = re.sub(r"'", "\u2019", text)

    return text


def emojify(text: str) -> str:
    """
    Convert emoji shortcodes to Unicode emoji.

    Converts :emoji_name: to actual emoji characters.

    Args:
        text: Text with emoji shortcodes

    Returns:
        Text with Unicode emoji

    Example:
        {{ text | emojify }}
        # "Hello :smile:" becomes "Hello 😊"
        # "I :heart: Python" becomes "I ❤️ Python"
    """
    if not text:
        return ""

    # Common emoji mappings
    emoji_map = {
        ":smile:": "😊",
        ":grin:": "😁",
        ":joy:": "😂",
        ":heart:": "❤️",
        ":star:": "⭐",
        ":fire:": "🔥",
        ":rocket:": "🚀",
        ":check:": "✅",
        ":x:": "❌",
        ":warning:": "⚠️",
        ":tada:": "🎉",
        ":thumbsup:": "👍",
        ":thumbsdown:": "👎",
        ":eyes:": "👀",
        ":bulb:": "💡",
        ":sparkles:": "✨",
        ":zap:": "⚡",
        ":wave:": "👋",
        ":clap:": "👏",
        ":raised_hands:": "🙌",
        ":100:": "💯",
    }

    for shortcode, emoji in emoji_map.items():
        text = text.replace(shortcode, emoji)

    return text


def extract_content(html: str) -> str:
    """
    Extract content portion from full rendered HTML page.

    Removes the page wrapper (html, head, body, navigation, footer) and
    extracts just the main content area. This is useful for embedding
    page content within other pages (e.g., track pages).

    Tries multiple strategies to find content:
    1. Look for <article class="prose"> or <div class="docs-content">
    2. Look for <main> content (excluding nav/footer)
    3. Fall back to empty string if no content area found

    Args:
        html: Full rendered HTML page

    Returns:
        Extracted content HTML (or empty string if extraction fails)

    Example:
        {{ page.rendered_html | extract_content | safe }}
    """
    if not html:
        return ""

    # Strategy 1: Extract <div class="docs-content"> content
    # This matches docs layout structure (most common)
    # Use a more robust pattern that handles nested divs
    docs_pattern = r'<div[^>]*class="[^"]*docs-content[^"]*"[^>]*>'
    docs_start = re.search(docs_pattern, html, re.IGNORECASE)
    if docs_start:
        # Find the matching closing </div> by counting depth
        start_pos = docs_start.end()
        depth = 1
        pos = start_pos
        while pos < len(html) and depth > 0:
            # Look for opening or closing div tags
            div_match = re.search(r"</?div[^>]*>", html[pos:], re.IGNORECASE)
            if not div_match:
                break
            tag = div_match.group(0)
            if tag.startswith("</"):
                depth -= 1
            else:
                depth += 1
            pos += div_match.end()

        if depth == 0:
            content = html[docs_start.end() : pos - len("</div>")].strip()
            return content

    # Strategy 2: Extract <article class="prose"> content
    # This matches the default theme structure
    article_pattern = r'<article[^>]*class="[^"]*prose[^"]*"[^>]*>'
    article_start = re.search(article_pattern, html, re.IGNORECASE)
    if article_start:
        # Find the matching closing </article>
        start_pos = article_start.end()
        depth = 1
        pos = start_pos
        while pos < len(html) and depth > 0:
            article_match = re.search(r"</?article[^>]*>", html[pos:], re.IGNORECASE)
            if not article_match:
                break
            tag = article_match.group(0)
            if tag.startswith("</"):
                depth -= 1
            else:
                depth += 1
            pos += article_match.end()

        if depth == 0:
            content = html[article_start.end() : pos - len("</article>")].strip()
            return content

    # Strategy 3: Extract <main> content (excluding nav/footer)
    # Find <main> tag and extract its content
    main_start = re.search(r"<main[^>]*>", html, re.IGNORECASE)
    if main_start:
        start_pos = main_start.end()
        # Find closing </main>
        main_end = re.search(r"</main>", html[start_pos:], re.IGNORECASE)
        if main_end:
            main_content = html[start_pos : start_pos + main_end.start()].strip()
            # Remove navigation and footer if present
            main_content = re.sub(
                r"<nav[^>]*>.*?</nav>",
                "",
                main_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            main_content = re.sub(
                r"<footer[^>]*>.*?</footer>",
                "",
                main_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            # Remove action-bar and sidebar elements
            main_content = re.sub(
                r'<div[^>]*class="[^"]*action-bar[^"]*"[^>]*>.*?</div>',
                "",
                main_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            main_content = re.sub(
                r"<aside[^>]*>.*?</aside>",
                "",
                main_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            return main_content.strip()

    # Strategy 4: If it looks like it's already just content (no html/head/body tags),
    # return as-is
    if not re.search(r"<html|<head|<body|<header|<nav", html, re.IGNORECASE):
        return html.strip()

    # Fallback: Return empty string if we can't extract content
    # This prevents embedding full page HTML
    return ""
