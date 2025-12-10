"""
String manipulation functions for templates.

Provides 14 essential string functions for text processing in templates.

Many of these functions are now thin wrappers around bengal.utils.text utilities
to avoid code duplication and ensure consistency.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from bengal.utils import text as text_utils
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register string functions with Jinja2 environment."""
    env.filters.update(
        {
            "truncatewords": truncatewords,
            "truncatewords_html": truncatewords_html,
            "slugify": slugify,
            "markdownify": markdownify,
            "strip_html": strip_html,
            "truncate_chars": truncate_chars,
            "replace_regex": replace_regex,
            "pluralize": pluralize,
            "reading_time": reading_time,
            "word_count": word_count,
            "wordcount": word_count,  # Alias matching Jinja naming convention
            "excerpt": excerpt,
            "strip_whitespace": strip_whitespace,
            "get": dict_get,
            "first_sentence": first_sentence,
            "filesize": filesize,
        }
    )


def dict_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safe get supporting dict-like objects for component preview contexts."""
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        # Allow attribute access as fallback
        if hasattr(obj, key):
            return getattr(obj, key)
    except Exception as e:
        logger.debug(
            "safe_get_failed",
            key=key,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_default",
        )
        pass
    return default


def truncatewords(text: str, count: int, suffix: str = "...") -> str:
    """
    Truncate text to a specified number of words.

    Uses bengal.utils.text.truncate_words internally.

    Args:
        text: Text to truncate
        count: Maximum number of words
        suffix: Text to append when truncated (default: "...")

    Returns:
        Truncated text with suffix if needed

    Example:
        {{ post.content | truncatewords(50) }}
        {{ post.content | truncatewords(30, " [Read more]") }}
    """
    return text_utils.truncate_words(text, count, suffix)


def truncatewords_html(html: str, count: int, suffix: str = "...") -> str:
    """
    Truncate HTML text to word count, preserving HTML structure.

    Uses a tag-aware approach that:
    1. Counts only text content words (not tag content)
    2. Keeps track of open tags
    3. Closes any unclosed tags at truncation point

    Args:
        html: HTML text to truncate
        count: Maximum number of words
        suffix: Text to append when truncated

    Returns:
        Truncated HTML with properly closed tags

    Example:
        {{ post.html_content | truncatewords_html(50) }}
        {{ "<p>Hello <strong>world</strong></p>" | truncatewords_html(1) }}  # "<p>Hello...</p>"
    """
    if not html:
        return ""

    # Quick check - if plain text word count is under limit, return as-is
    text_only = strip_html(html)
    if len(text_only.split()) <= count:
        return html

    # HTML5 void elements (no closing tag needed)
    void_elements = frozenset(
        {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "source",
            "track",
            "wbr",
        }
    )

    # Tag-aware truncation
    result: list[str] = []
    word_count = 0
    open_tags: list[str] = []
    i = 0

    while i < len(html) and word_count < count:
        if html[i] == "<":
            # Find end of tag
            tag_end = html.find(">", i)
            if tag_end == -1:
                break
            tag = html[i : tag_end + 1]
            result.append(tag)

            # Track open/close tags
            if tag.startswith("</"):
                # Closing tag
                tag_name = tag[2:-1].split()[0].lower() if len(tag) > 3 else ""
                if open_tags and open_tags[-1] == tag_name:
                    open_tags.pop()
            elif not tag.endswith("/>") and not tag.startswith("<!"):
                # Opening tag (not self-closing, not comment/doctype)
                tag_content = tag[1:-1]
                tag_name = tag_content.split()[0].lower() if tag_content else ""
                if tag_name and tag_name not in void_elements:
                    open_tags.append(tag_name)

            i = tag_end + 1
        else:
            # Find next tag or end
            next_tag = html.find("<", i)
            text = html[i:] if next_tag == -1 else html[i:next_tag]

            # Count and truncate words in this text segment
            words = text.split()
            remaining = count - word_count

            if len(words) <= remaining:
                result.append(text)
                word_count += len(words)
                i = next_tag if next_tag != -1 else len(html)
            else:
                # Truncate within this segment
                result.append(" ".join(words[:remaining]))
                word_count = count
                break

    # Add suffix
    result.append(suffix)

    # Close any unclosed tags (in reverse order)
    for tag in reversed(open_tags):
        result.append(f"</{tag}>")

    return "".join(result)


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.

    Uses bengal.utils.text.slugify internally.
    Converts to lowercase, removes special characters, replaces spaces with hyphens.

    Args:
        text: Text to convert

    Returns:
        URL-safe slug

    Example:
        {{ page.title | slugify }}  # "Hello World!" -> "hello-world"
    """
    return text_utils.slugify(text, unescape_html=False)


def _convert_docstring_to_markdown(text: str) -> str:
    """
    Convert Google/NumPy-style docstrings to markdown.

    Handles:
    - Indented lists (    - Item) → proper markdown lists
    - Section headers (Section:) → bold labels or headings
    - Preserves code blocks

    Args:
        text: Docstring text

    Returns:
        Markdown-formatted text
    """
    if not text:
        return ""

    lines = text.split("\n")
    result = []
    in_code_block = False

    for line in lines:
        # Track code blocks - don't modify inside them
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        # Convert indented list items to proper markdown lists
        # "    - Item: Description" → "- **Item**: Description"
        # Match: 4+ spaces, dash, text
        match = re.match(r"^(\s{4,})- (.+)$", line)
        if match:
            content = match.group(2)
            # Check if it's "Term: Description" format
            term_match = re.match(r"^([^:]+):\s*(.*)$", content)
            if term_match:
                term, desc = term_match.groups()
                result.append(f"- **{term}**: {desc}")
            else:
                result.append(f"- {content}")
            continue

        # Convert section headers: "Section:" at start of line → "**Section:**"
        section_match = re.match(r"^([A-Z][A-Za-z\s]+):$", line.strip())
        if section_match and not line.startswith(" "):
            section_name = section_match.group(1)
            result.append(f"\n**{section_name}:**\n")
            continue

        result.append(line)

    return "\n".join(result)


def markdownify(text: str) -> str:
    """
    Render Markdown text to HTML.

    Pre-processes Google-style docstrings to markdown, then converts to HTML
    using mistune (production dependency) with table support.

    Args:
        text: Markdown or docstring text

    Returns:
        Rendered HTML

    Example:
        {{ markdown_text | markdownify | safe }}
    """
    if not text:
        return ""

    # Pre-process docstring-style text to markdown
    text = _convert_docstring_to_markdown(text)

    import mistune

    # Use lightweight mistune instance with table support
    # This avoids the full Bengal parser overhead while using a production dependency
    md = mistune.create_markdown(plugins=["table", "strikethrough"])
    return md(text)


def strip_html(text: str) -> str:
    """
    Remove all HTML tags from text.

    Uses bengal.utils.text.strip_html internally.

    Args:
        text: HTML text

    Returns:
        Text with HTML tags removed

    Example:
        {{ post.html_content | strip_html }}
    """
    return text_utils.strip_html(text, decode_entities=True)


def truncate_chars(text: str, length: int, suffix: str = "...") -> str:
    """
    Truncate text to character length.

    Uses bengal.utils.text.truncate_chars internally.

    Args:
        text: Text to truncate
        length: Maximum character length
        suffix: Text to append when truncated

    Returns:
        Truncated text with suffix if needed

    Example:
        {{ post.excerpt | truncate_chars(200) }}
    """
    return text_utils.truncate_chars(text, length, suffix)


def replace_regex(text: str, pattern: str, replacement: str) -> str:
    """
    Replace text using regular expression.

    Args:
        text: Text to search in
        pattern: Regular expression pattern
        replacement: Replacement text

    Returns:
        Text with replacements made

    Example:
        {{ text | replace_regex('\\d+', 'NUM') }}
    """
    if not text:
        return ""

    try:
        return re.sub(pattern, replacement, text)
    except re.error as e:
        # Log warning for invalid regex (developer error)
        logger.warning(
            "replace_regex_invalid_pattern",
            pattern=pattern,
            error=str(e),
            caller="template",
        )
        return text


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    """
    Return singular or plural form based on count.

    Uses bengal.utils.text.pluralize internally.

    Args:
        count: Number to check
        singular: Singular form
        plural: Plural form (default: singular + 's')

    Returns:
        Appropriate form based on count

    Example:
        {{ posts | length }} {{ posts | length | pluralize('post', 'posts') }}
        {{ count | pluralize('item') }}  # auto-pluralizes to "items"
    """
    return text_utils.pluralize(count, singular, plural)


def reading_time(text: str, wpm: int = 200) -> int:
    """
    Calculate reading time in minutes.

    Args:
        text: Text to analyze
        wpm: Words per minute reading speed (default: 200)

    Returns:
        Reading time in minutes (minimum 1)

    Example:
        {{ post.content | reading_time }} min read
        {{ post.content | reading_time(250) }} min read
    """
    if not text:
        return 1

    # Strip HTML if present
    clean_text = strip_html(text)

    # Count words
    words = len(clean_text.split())

    # Calculate reading time
    minutes = words / wpm

    # Always return at least 1 minute
    return max(1, round(minutes))


def word_count(text: str) -> int:
    """
    Count words in text.

    Strips HTML tags before counting. Uses same logic as reading_time.

    Args:
        text: Text to count (can contain HTML)

    Returns:
        Number of words

    Example:
        {{ page.content | word_count }} words
        {{ page.content | word_count }} words ({{ page.content | reading_time }} min read)
    """
    if not text:
        return 0
    clean_text = strip_html(text)
    return len(clean_text.split())


def excerpt(text: str, length: int = 200, respect_word_boundaries: bool = True) -> str:
    """
    Extract excerpt from text, optionally respecting word boundaries.

    Args:
        text: Text to excerpt from
        length: Maximum length in characters
        respect_word_boundaries: Don't cut words in half (default: True)

    Returns:
        Excerpt with ellipsis if truncated

    Example:
        {{ post.content | excerpt(200) }}
        {{ post.content | excerpt(150, false) }}  # Can cut words
    """
    if not text:
        return ""

    # Strip HTML first
    clean_text = strip_html(text)

    if len(clean_text) <= length:
        return clean_text

    if respect_word_boundaries:
        # Find the last space before the limit
        excerpt_text = clean_text[:length].rsplit(" ", 1)[0]
        return excerpt_text + "..."
    else:
        return clean_text[:length] + "..."


def strip_whitespace(text: str) -> str:
    """
    Remove extra whitespace (multiple spaces, newlines, tabs).

    Uses bengal.utils.text.normalize_whitespace internally.
    Replaces all whitespace sequences with a single space.

    Args:
        text: Text to clean

    Returns:
        Text with normalized whitespace

    Example:
        {{ messy_text | strip_whitespace }}
    """
    return text_utils.normalize_whitespace(text, collapse=True)


def first_sentence(text: str, max_length: int = 120) -> str:
    """
    Extract first sentence from text, or truncate if too long.

    Useful for generating short descriptions from longer text blocks.
    Looks for sentence-ending punctuation (. ! ?) followed by whitespace.

    Args:
        text: Text to extract first sentence from
        max_length: Maximum length before truncation (default: 120)

    Returns:
        First sentence or truncated text with ellipsis

    Example:
        {{ page.description | first_sentence }}
        {{ section.metadata.description | first_sentence(80) }}
    """
    if not text:
        return ""

    text = text.strip()

    # Try to find first sentence by looking for sentence-ending punctuation
    for end in [". ", ".\n", "!\n", "?\n", "! ", "? "]:
        if end in text:
            first = text.split(end)[0] + end[0]
            if len(first) <= max_length:
                return first
            break

    # Truncate if too long
    if len(text) > max_length:
        # Try to break at word boundary
        truncated = text[: max_length - 3].rsplit(" ", 1)[0]
        return truncated + "..."

    return text


def filesize(size_bytes: int) -> str:
    """
    Format bytes as human-readable file size.

    Wraps bengal.utils.text.humanize_bytes for template use.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 MB", "256 KB")

    Example:
        {{ asset.size | filesize }}
        {{ page.content | length | filesize }}
    """
    return text_utils.humanize_bytes(size_bytes)
