"""
Advanced string manipulation functions for templates.

Provides advanced string transformation functions including regex extraction,
prefix/suffix operations, and case conversions.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.protocols import TemplateEnvironment


def register(env: TemplateEnvironment, site: Site) -> None:
    """Register functions with template environment."""
    env.filters.update(
        {
            "camelize": camelize,
            "underscore": underscore,
            "titleize": titleize,
            "wrap": wrap_text,
            "indent": indent_text,
            # Insert zero-width break opportunities into long identifiers
            # E.g., "cache.dependency_tracker" -> "cache\u200b.\u200bdependency\u200b_\u200btracker"
            "softwrap_ident": softwrap_identifier,
            # Extract last segment of dotted or path-like identifiers
            # E.g., "cache.dependency_tracker" -> "dependency_tracker"
            "last_segment": last_segment,
            # Regex extraction filters
            "regex_search": regex_search,
            "regex_findall": regex_findall,
            # Prefix/suffix operations
            "trim_prefix": trim_prefix,
            "trim_suffix": trim_suffix,
            "has_prefix": has_prefix,
            "has_suffix": has_suffix,
            "contains": contains,
            # Natural language
            "to_sentence": to_sentence,
        }
    )


def camelize(text: str) -> str:
    """
    Convert string to camelCase.
    
    Args:
        text: Text to convert
    
    Returns:
        camelCase text
    
    Example:
        {{ "hello_world" | camelize }}  # "helloWorld"
        {{ "hello-world" | camelize }}  # "helloWorld"
        
    """
    if not text:
        return ""

    # Split on underscores, hyphens, or spaces
    words = re.split(r"[-_\s]+", text)

    if not words:
        return text

    # First word lowercase, rest titlecase
    result = words[0].lower()
    for word in words[1:]:
        if word:
            result += word.capitalize()

    return result


def underscore(text: str) -> str:
    """
    Convert string to snake_case.
    
    Args:
        text: Text to convert
    
    Returns:
        snake_case text
    
    Example:
        {{ "helloWorld" | underscore }}  # "hello_world"
        {{ "HelloWorld" | underscore }}  # "hello_world"
        
    """
    if not text:
        return ""

    # Insert underscore before uppercase letters
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    text = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", text)

    # Replace hyphens and spaces with underscores
    text = text.replace("-", "_").replace(" ", "_")

    # Lowercase and remove multiple underscores
    text = text.lower()
    text = re.sub(r"_+", "_", text)

    return text.strip("_")


def titleize(text: str) -> str:
    """
    Convert string to Title Case (proper title capitalization).
    
    More sophisticated than str.title() - handles articles, conjunctions,
    and prepositions correctly.
    
    Args:
        text: Text to convert
    
    Returns:
        Properly title-cased text
    
    Example:
        {{ "the lord of the rings" | titleize }}
        # "The Lord of the Rings"
        
    """
    if not text:
        return ""

    # Words that should stay lowercase (unless first/last word)
    lowercase_words = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "in",
        "nor",
        "of",
        "on",
        "or",
        "so",
        "the",
        "to",
        "up",
        "yet",
    }

    words = text.split()
    if not words:
        return text

    result = []
    for i, word in enumerate(words):
        # Always capitalize first and last word
        if i == 0 or i == len(words) - 1:
            result.append(word.capitalize())
        # Keep lowercase words lowercase
        elif word.lower() in lowercase_words:
            result.append(word.lower())
        # Capitalize other words
        else:
            result.append(word.capitalize())

    return " ".join(result)


def wrap_text(text: str, width: int = 80) -> str:
    """
    Wrap text to specified width.
    
    Args:
        text: Text to wrap
        width: Maximum line width (default: 80)
    
    Returns:
        Wrapped text with newlines
    
    Example:
        {{ long_text | wrap(60) }}
        
    """
    if not text or width <= 0:
        return text

    import textwrap

    return textwrap.fill(text, width=width)


def indent_text(text: str, spaces: int = 4, first_line: bool = True) -> str:
    """
    Indent text by specified number of spaces.
    
    Args:
        text: Text to indent
        spaces: Number of spaces to indent (default: 4)
        first_line: Indent first line too (default: True)
    
    Returns:
        Indented text
    
    Example:
        {{ code | indent(2) }}
        {{ text | indent(4, first_line=false) }}
        
    """
    if not text:
        return ""

    indent = " " * spaces
    lines = text.split("\n")

    if first_line:
        return "\n".join(indent + line for line in lines)
    else:
        if len(lines) == 0:
            return text
        return lines[0] + "\n" + "\n".join(indent + line for line in lines[1:])


def softwrap_identifier(text: str) -> str:
    """
    Insert soft wrap opportunities into API identifiers and dotted paths.
    
    Adds zero-width space (​) after sensible breakpoints like dots, underscores,
    and before uppercase letters in camelCase/PascalCase to allow titles like
    "cache.dependency_tracker" to wrap nicely.
        
    """
    if not text:
        return ""

    # Insert ZWSP after dots and underscores
    result = re.sub(r"([._])", r"\1\u200b", text)

    # Insert ZWSP before uppercase letters that follow a lowercase or digit (camelCase boundaries)
    result = re.sub(r"(?<=[a-z0-9])([A-Z])", r"\u200b\1", result)

    return result


def last_segment(text: str) -> str:
    """
    Return the last segment of a dotted or path-like identifier.
    
    Examples:
    - "cache.dependency_tracker" -> "dependency_tracker"
    - "a.b.c.ClassName" -> "ClassName"
    - "path/to/module" -> "module"
        
    """
    if not text:
        return ""

    # Prefer splitting on dots if present; otherwise split on slashes
    if "." in text:
        return text.split(".")[-1]
    if "/" in text:
        return text.rsplit("/", 1)[-1]
    return text


def regex_search(text: str | None, pattern: str, group: int = 0) -> str | None:
    """
    Extract first regex match from text.
    
    Args:
        text: Text to search in
        pattern: Regular expression pattern
        group: Capture group to return (0 for full match)
    
    Returns:
        Matched text or None if no match
    
    Example:
        {{ "Price: $99.99" | regex_search(r'\\$[\\d.]+') }}  # "$99.99"
        {{ "v2.3.1" | regex_search(r'v(\\d+)', group=1) }}  # "2"
        
    """
    if text is None:
        return None

    try:
        match = re.search(pattern, text)
        if not match:
            return None
        return match.group(group)
    except re.error as e:
        logger.warning("regex_search_failed", pattern=pattern, error=str(e))
        return None
    except IndexError:
        # Group doesn't exist, return full match
        if match:
            return match.group(0)
        return None


def regex_findall(text: str | None, pattern: str) -> list[str]:
    """
    Find all regex matches in text.
    
    Args:
        text: Text to search in
        pattern: Regular expression pattern
    
    Returns:
        List of all matches
    
    Example:
        {{ "a1 b2 c3" | regex_findall(r'\\d+') }}  # ["1", "2", "3"]
        {{ text | regex_findall(r'\\b\\w+@\\w+\\.\\w+\\b') }}  # Find emails
        
    """
    if text is None:
        return []

    try:
        return re.findall(pattern, text)
    except re.error as e:
        logger.warning("regex_findall_failed", pattern=pattern, error=str(e))
        return []


def trim_prefix(text: str | None, prefix: str) -> str:
    """
    Remove prefix from string if present.
    
    Args:
        text: Text to trim
        prefix: Prefix to remove
    
    Returns:
        Text with prefix removed (or unchanged if no prefix)
    
    Example:
        {{ "hello_world" | trim_prefix("hello_") }}  # "world"
        {{ "test" | trim_prefix("hello_") }}  # "test" (unchanged)
        
    """
    if not text:
        return ""
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text


def trim_suffix(text: str | None, suffix: str) -> str:
    """
    Remove suffix from string if present.
    
    Args:
        text: Text to trim
        suffix: Suffix to remove
    
    Returns:
        Text with suffix removed (or unchanged if no suffix)
    
    Example:
        {{ "file.txt" | trim_suffix(".txt") }}  # "file"
        {{ "test" | trim_suffix(".txt") }}  # "test" (unchanged)
        
    """
    if not text:
        return ""
    if not suffix:
        return text
    if text.endswith(suffix):
        return text[: -len(suffix)]
    return text


def has_prefix(text: str | None, prefix: str) -> bool:
    """
    Check if string starts with prefix.
    
    Args:
        text: Text to check
        prefix: Prefix to look for
    
    Returns:
        True if text starts with prefix
    
    Example:
        {% if url | has_prefix("https://") %}secure{% endif %}
        
    """
    if not text:
        return False
    return text.startswith(prefix)


def has_suffix(text: str | None, suffix: str) -> bool:
    """
    Check if string ends with suffix.
    
    Args:
        text: Text to check
        suffix: Suffix to look for
    
    Returns:
        True if text ends with suffix
    
    Example:
        {% if file | has_suffix(".md") %}markdown{% endif %}
        
    """
    if not text:
        return False
    return text.endswith(suffix)


def contains(text: str | None, substring: str) -> bool:
    """
    Check if string contains substring.
    
    Args:
        text: Text to search in
        substring: Substring to find
    
    Returns:
        True if substring is found
    
    Example:
        {% if text | contains("error") %}has error{% endif %}
        
    """
    if not text:
        return False
    return substring in text


def to_sentence(items: list | None, connector: str = "and", oxford: bool = True) -> str:
    """
    Convert list to natural language sentence.
    
    Args:
        items: List of items to join
        connector: Word to use before last item (default: "and")
        oxford: Whether to use Oxford comma (default: True)
    
    Returns:
        Natural language string
    
    Example:
        {{ ['Alice', 'Bob', 'Charlie'] | to_sentence }}  # "Alice, Bob, and Charlie"
        {{ ['Alice', 'Bob'] | to_sentence }}  # "Alice and Bob"
        {{ tags | to_sentence(connector='or', oxford=false) }}  # "A, B or C"
        
    """
    if not items:
        return ""

    items = [str(item) for item in items]

    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {connector} {items[1]}"

    if oxford:
        return f"{', '.join(items[:-1])}, {connector} {items[-1]}"
    return f"{', '.join(items[:-1])} {connector} {items[-1]}"
