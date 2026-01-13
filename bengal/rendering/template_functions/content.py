"""
Content transformation functions for templates.

Provides 6 functions for HTML/content manipulation and transformation.
"""

from __future__ import annotations

import html as html_module
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.rendering.engines.protocol import TemplateEnvironment


def register(env: TemplateEnvironment, site: Site) -> None:
    """Register content transformation functions with template environment."""
    env.filters.update(
        {
            "safe_html": safe_html,
            "html_escape": html_escape,
            "html_unescape": html_unescape,
            "nl2br": nl2br,
            "smartquotes": smartquotes,
            "emojify": emojify,
            "extract_content": extract_content,
            "demote_headings": demote_headings,
            "prefix_heading_ids": prefix_heading_ids,
            "urlize": urlize,
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
    
    Replaces 
     with <br>
     to preserve both HTML and text formatting.
    
    Args:
        text: Text with newlines
    
    Returns:
        HTML with <br> tags
    
    Example:
        {{ text | nl2br | safe }}
        # "Line 1
    Line 2" becomes "Line 1<br>
    Line 2"
        
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


def demote_headings(html: str, levels: int = 1) -> str:
    """
    Demote HTML headings by the specified number of levels.
    
    Shifts heading levels down (h1→h2, h2→h3, etc.) to maintain proper
    document hierarchy when embedding content within other pages.
    Headings cannot go below h6.
    
    Args:
        html: HTML content with headings
        levels: Number of levels to demote (default: 1)
    
    Returns:
        HTML with demoted headings
    
    Example:
        {{ page.content | demote_headings | safe }}
        # <h1>Title</h1> becomes <h2>Title</h2>
        # <h2>Section</h2> becomes <h3>Section</h3>
    
        {{ page.content | demote_headings(2) | safe }}
        # <h1>Title</h1> becomes <h3>Title</h3>
        
    """
    if not html or levels < 1:
        return html or ""

    def replace_heading(match: re.Match[str]) -> str:
        tag = match.group(1)  # 'h' or '/h'
        level = int(match.group(2))
        rest = match.group(3)  # attributes or empty for closing tag

        # Demote heading level, capping at h6
        new_level = min(level + levels, 6)

        return f"<{tag}{new_level}{rest}>"

    # Match opening and closing heading tags: <h1>, </h1>, <h2 class="...">, etc.
    pattern = r"<(/?h)([1-6])([^>]*)>"

    return re.sub(pattern, replace_heading, html, flags=re.IGNORECASE)


def prefix_heading_ids(html: str, prefix: str) -> str:
    """
    Prefix all heading IDs and their corresponding anchor links with a prefix.
    
    This ensures heading IDs are unique when embedding multiple pages on a
    single page (e.g., track pillar pages). Also updates href="#id" links
    that point to these headings.
    
    Args:
        html: HTML content with headings
        prefix: Prefix to add (e.g., "s1-" for section 1)
    
    Returns:
        HTML with prefixed heading IDs and updated anchor links
    
    Example:
        {{ page.content | prefix_heading_ids("s1-") | safe }}
        # <h2 id="quick-start"> becomes <h2 id="s1-quick-start">
        # <a href="#quick-start"> becomes <a href="#s1-quick-start">
        
    """
    if not html or not prefix:
        return html or ""

    # Collect all heading IDs first
    heading_ids: set[str] = set()
    id_pattern = r'<h[1-6][^>]*\sid=["\']([^"\']+)["\']'
    for match in re.finditer(id_pattern, html, re.IGNORECASE):
        heading_ids.add(match.group(1))

    if not heading_ids:
        return html

    # Replace heading IDs
    def replace_heading_id(match: re.Match[str]) -> str:
        tag_start = match.group(1)
        old_id = match.group(2)
        quote = match.group(3)
        tag_rest = match.group(4)
        return f"{tag_start}id={quote}{prefix}{old_id}{quote}{tag_rest}"

    # Pattern for heading tags with id attribute
    html = re.sub(
        r'(<h[1-6][^>]*\s)id=(["\'])([^"\']+)\2([^>]*>)',
        lambda m: f"{m.group(1)}id={m.group(2)}{prefix}{m.group(3)}{m.group(2)}{m.group(4)}",
        html,
        flags=re.IGNORECASE,
    )

    # Update anchor links that reference these IDs
    for old_id in heading_ids:
        # Match href="#old_id" patterns
        html = re.sub(
            rf'href=(["\'])#{re.escape(old_id)}\1',
            rf"href=\1#{prefix}{old_id}\1",
            html,
        )

    return html


def urlize(
    text: str | None,
    target: str = "",
    rel: str = "",
    shorten: bool = False,
    shorten_length: int = 50,
) -> str:
    """
    Convert plain URLs in text to clickable HTML links.
    
    Detects URLs starting with http://, https://, or www. and wraps them
    in anchor tags.
    
    Args:
        text: Text containing URLs
        target: Optional target attribute (e.g., "_blank")
        rel: Optional rel attribute (e.g., "noopener noreferrer")
        shorten: If True, shorten displayed URL text
        shorten_length: Maximum length for shortened display (default: 50)
    
    Returns:
        Text with URLs converted to anchor tags
    
    Example:
        {{ "Check out https://example.com for more info" | urlize }}
        # "Check out <a href="https://example.com">https://example.com</a> for more info"
    
        {{ text | urlize(target='_blank', rel='noopener') }}
        # Opens links in new tab with security attributes
        
    """
    if not text:
        return ""

    # URL pattern: matches http://, https://, or www. URLs
    url_pattern = r'(https?://[^\s<>"\']+|www\.[^\s<>"\']+)'

    def replace_url(match: re.Match[str]) -> str:
        url = match.group(1)
        href = url if url.startswith("http") else f"https://{url}"

        # Build display text
        display = url
        if shorten and len(display) > shorten_length:
            display = display[: shorten_length - 3] + "..."

        # Build attributes
        attrs = [f'href="{html_module.escape(href)}"']
        if target:
            attrs.append(f'target="{html_module.escape(target)}"')
        if rel:
            attrs.append(f'rel="{html_module.escape(rel)}"')

        return f"<a {' '.join(attrs)}>{html_module.escape(display)}</a>"

    return re.sub(url_pattern, replace_url, text)
