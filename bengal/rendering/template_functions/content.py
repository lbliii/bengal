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
