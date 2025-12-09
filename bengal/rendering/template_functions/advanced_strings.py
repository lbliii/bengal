"""
Advanced string manipulation functions for templates.

Provides 5 advanced string transformation functions.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register advanced string functions with Jinja2 environment."""
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

    Adds zero-width space (\u200b) after sensible breakpoints like dots, underscores,
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
