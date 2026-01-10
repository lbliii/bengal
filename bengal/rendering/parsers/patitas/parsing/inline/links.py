"""Link and image parsing for Patitas parser.

Handles inline links, reference links, images, and footnote references.

CommonMark 0.31.2 compliance:
- Link destinations can be angle-bracket delimited or raw
- Angle-bracket destinations: no newlines, can have spaces
- Raw destinations: no spaces, no control chars, balanced parens
- Backslash escapes work in destinations and titles
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.nodes import FootnoteRef, Image, Link

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


# CommonMark: ASCII punctuation that can be backslash-escaped
_ESCAPABLE_CHARS = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")

# Pattern to find backslash escapes
_ESCAPE_PATTERN = re.compile(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])")


def _process_escapes(text: str) -> str:
    """Process backslash escapes in link URLs and titles.

    CommonMark: Backslash escapes work in link destinations and titles.
    A backslash followed by ASCII punctuation is replaced with the literal char.

    Args:
        text: Raw text that may contain backslash escapes

    Returns:
        Text with escapes processed
    """
    return _ESCAPE_PATTERN.sub(r"\1", text)


# Pattern for whitespace normalization
_WHITESPACE_PATTERN = re.compile(r"[ \t\n]+")


def _normalize_label(label: str) -> str:
    """Normalize a link reference label for matching.

    CommonMark 4.7: "Label matching is case-insensitive and Unicode case fold
    equivalent. Spaces, tabs, and line endings are normalized to single space."

    Args:
        label: Raw label text

    Returns:
        Normalized label (lowercase, whitespace normalized)
    """
    # Collapse runs of whitespace to single space
    normalized = _WHITESPACE_PATTERN.sub(" ", label.strip())
    # Case-fold for Unicode case-insensitive matching
    return normalized.casefold()


def _parse_link_destination(text: str, pos: int) -> tuple[str, int] | None:
    """Parse a link destination starting at pos.

    CommonMark 6.5: Link destination is either:
    1. Angle-bracket delimited: <url> (can contain spaces, no newlines or unescaped </>)
    2. Raw URL: sequence of non-space chars with balanced parens

    Args:
        text: The full text being parsed
        pos: Position after the opening (

    Returns:
        (url, end_pos) or None if invalid
    """
    if pos >= len(text):
        return None

    # Skip leading whitespace (but not newlines for raw destinations)
    while pos < len(text) and text[pos] in " \t":
        pos += 1

    if pos >= len(text):
        return None

    # Case 1: Angle-bracket delimited destination
    if text[pos] == "<":
        pos += 1  # Skip opening <
        start = pos
        while pos < len(text):
            char = text[pos]
            if char == ">":
                # Found closing - success
                url = text[start:pos]
                return _process_escapes(url), pos + 1
            if char == "\n" or char == "\r":
                # Newlines not allowed in angle-bracket destinations
                return None
            if char == "<":
                # Unescaped < not allowed
                return None
            if char == "\\" and pos + 1 < len(text):
                # Skip escaped character
                pos += 2
                continue
            pos += 1
        # No closing > found
        return None

    # Case 2: Raw destination (no angle brackets)
    # Cannot contain spaces, newlines, or unbalanced parens
    start = pos
    paren_depth = 0

    while pos < len(text):
        char = text[pos]

        # Space, newline, or tab ends raw destination
        if char in " \t\n\r":
            break

        # Control characters (< 0x20) are not allowed except for escaped ones
        if ord(char) < 0x20:
            break

        # Handle parentheses with balancing
        if char == "(":
            paren_depth += 1
            pos += 1
            continue

        if char == ")":
            if paren_depth > 0:
                paren_depth -= 1
                pos += 1
                continue
            # Unbalanced ) ends the destination
            break

        # Backslash escape
        if char == "\\" and pos + 1 < len(text):
            next_char = text[pos + 1]
            if next_char in _ESCAPABLE_CHARS:
                pos += 2  # Skip both backslash and escaped char
                continue

        pos += 1

    if pos == start:
        # Empty destination is valid (becomes empty URL)
        return "", pos

    url = text[start:pos]
    return _process_escapes(url), pos


def _parse_link_title(text: str, pos: int) -> tuple[str | None, int]:
    """Parse an optional link title starting at pos.

    CommonMark: Title is enclosed in ", ', or ()
    Can span lines but opening/closing delimiters must match.

    Args:
        text: The full text being parsed
        pos: Position to start looking for title

    Returns:
        (title, end_pos) - title may be None if no valid title found
    """
    # Skip whitespace including newlines (title can be on next line)
    while pos < len(text) and text[pos] in " \t\n\r":
        pos += 1

    if pos >= len(text):
        return None, pos

    char = text[pos]
    if char == '"':
        closer = '"'
    elif char == "'":
        closer = "'"
    elif char == "(":
        closer = ")"
    else:
        return None, pos

    pos += 1  # Skip opening delimiter
    start = pos

    while pos < len(text):
        c = text[pos]
        if c == closer:
            title = text[start:pos]
            return _process_escapes(title), pos + 1
        if c == "\\" and pos + 1 < len(text):
            # Skip escaped character
            pos += 2
            continue
        pos += 1

    # No closing delimiter found
    return None, start - 1


def _parse_inline_link(text: str, pos: int) -> tuple[str, str | None, int] | None:
    """Parse an inline link destination and optional title.

    Format: (url) or (url "title") or (<url> 'title')

    Args:
        text: Full text being parsed
        pos: Position at the opening (

    Returns:
        (url, title, end_pos) or None if invalid
    """
    if pos >= len(text) or text[pos] != "(":
        return None

    pos += 1  # Skip opening (

    # Skip leading whitespace
    while pos < len(text) and text[pos] in " \t\n\r":
        pos += 1

    # Check for empty destination immediately closed
    if pos < len(text) and text[pos] == ")":
        return "", None, pos + 1

    # Parse destination
    dest_result = _parse_link_destination(text, pos)
    if dest_result is None:
        return None

    url, pos = dest_result

    # Skip whitespace between destination and title (or closing paren)
    while pos < len(text) and text[pos] in " \t\n\r":
        pos += 1

    if pos >= len(text):
        return None

    # Check for closing paren (no title)
    if text[pos] == ")":
        return url, None, pos + 1

    # Try to parse title
    title, pos = _parse_link_title(text, pos)

    # Skip whitespace after title
    while pos < len(text) and text[pos] in " \t\n\r":
        pos += 1

    if pos >= len(text) or text[pos] != ")":
        return None

    return url, title, pos + 1


def _skip_html_tag(text: str, pos: int) -> int:
    """Skip over an HTML tag starting at pos.

    Handles open tags, close tags, and self-closing tags.
    Properly handles quoted attribute values that may contain special chars.

    Args:
        text: Full text to search
        pos: Position at the opening <

    Returns:
        Position after the closing > or pos if not a valid tag
    """
    text_len = len(text)
    if pos >= text_len or text[pos] != "<":
        return pos

    # Skip the opening <
    p = pos + 1

    # Check for closing tag </
    if p < text_len and text[p] == "/":
        p += 1

    # Must have at least one letter for tag name
    if p >= text_len or not text[p].isalpha():
        return pos

    # Skip tag name
    while p < text_len and (text[p].isalnum() or text[p] in "-_:"):
        p += 1

    # Now we're in the attribute section - look for >
    # But we need to respect quoted values
    while p < text_len:
        c = text[p]

        if c == ">":
            return p + 1

        if c == '"':
            # Double-quoted attribute value - find closing "
            p += 1
            while p < text_len and text[p] != '"':
                p += 1
            if p < text_len:
                p += 1  # Skip closing "
            continue

        if c == "'":
            # Single-quoted attribute value - find closing '
            p += 1
            while p < text_len and text[p] != "'":
                p += 1
            if p < text_len:
                p += 1  # Skip closing '
            continue

        if c == "\n":
            # Newline in tag is OK, continue
            p += 1
            continue

        p += 1

    # No closing > found
    return pos


def _find_closing_bracket(text: str, start: int) -> int:
    """Find closing bracket ] while respecting code spans, HTML tags, and nested brackets.

    CommonMark: Code spans have higher precedence than link text brackets.
    A code span inside link text means the ] inside the code span doesn't count.
    HTML tags protect their contents - ] inside HTML attribute values doesn't count.
    Nested brackets [ ] are allowed inside link text.

    Args:
        text: Full text to search
        start: Position to start searching (should be after opening [)

    Returns:
        Position of closing ] or -1 if not found
    """
    pos = start
    text_len = len(text)
    bracket_depth = 0  # Track nested [ ]

    while pos < text_len:
        char = text[pos]

        if char == "`":
            # Found backtick - find matching closing backticks
            backtick_count = 0
            while pos < text_len and text[pos] == "`":
                backtick_count += 1
                pos += 1

            # Search for matching closing backticks
            close_pos = pos
            while True:
                close_idx = text.find("`", close_pos)
                if close_idx == -1:
                    # No closing backticks - remaining backticks are literal
                    break
                # Count consecutive backticks at this position
                close_count = 0
                check_pos = close_idx
                while check_pos < text_len and text[check_pos] == "`":
                    close_count += 1
                    check_pos += 1
                if close_count == backtick_count:
                    # Found matching closer - skip past the code span
                    pos = check_pos
                    break
                close_pos = check_pos
            continue

        if char == "<":
            # Try to skip over HTML tag - ] inside tag attributes doesn't count
            new_pos = _skip_html_tag(text, pos)
            if new_pos > pos:
                pos = new_pos
                continue
            # Not a valid HTML tag, treat < as literal
            pos += 1
            continue

        if char == "[":
            # Nested opening bracket
            bracket_depth += 1
            pos += 1
            continue

        if char == "]":
            if bracket_depth > 0:
                # Close a nested bracket
                bracket_depth -= 1
                pos += 1
                continue
            # This is the actual closing bracket
            return pos

        if char == "\\":
            # Skip escaped character
            pos += 2
            continue

        pos += 1

    return -1


def _extract_plain_text(text: str) -> str:
    """Extract plain text from inline content for image alt text.

    CommonMark: Image alt text is the plain text content with formatting stripped.
    E.g., "*foo* bar" becomes "foo bar".

    Args:
        text: Raw inline content that may contain formatting

    Returns:
        Plain text with formatting markers removed
    """
    # Remove emphasis markers: *, _, **, __
    result = text
    # Remove ** and __ first (strong)
    result = re.sub(r"\*\*(.+?)\*\*", r"\1", result)
    result = re.sub(r"__(.+?)__", r"\1", result)
    # Remove * and _ (emphasis)
    result = re.sub(r"\*(.+?)\*", r"\1", result)
    result = re.sub(r"_(.+?)_", r"\1", result)
    # Remove code spans
    result = re.sub(r"`(.+?)`", r"\1", result)
    # Remove image text FIRST: ![alt](url) -> alt (before links, so ! is included)
    result = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", result)
    # Remove link text: [text](url) -> text
    result = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", result)
    return result


def _contains_link(children: tuple) -> bool:
    """Check if children contain a Link node at any nesting level.

    CommonMark: Links may not contain other links, at any level of nesting.
    If parsing link text produces a link, the outer link is invalid.

    Args:
        children: Tuple of inline nodes

    Returns:
        True if any child is or contains a Link node
    """
    for child in children:
        if isinstance(child, Link):
            return True
        # Check nested children (e.g., inside emphasis)
        if hasattr(child, "children") and child.children and _contains_link(child.children):
            return True
    return False


class LinkParsingMixin:
    """Mixin for link and image parsing.

    Required Host Attributes:
        - _link_refs: dict[str, tuple[str, str]]

    Required Host Methods:
        - _parse_inline(text, location) -> tuple[Inline, ...]
    """

    _link_refs: dict[str, tuple[str, str]]

    def _try_parse_footnote_ref(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[FootnoteRef, int] | None:
        """Try to parse a footnote reference at position.

        Format: [^identifier]
        Returns (FootnoteRef, new_position) or None if not a footnote ref.
        """
        if pos + 2 >= len(text) or text[pos : pos + 2] != "[^":
            return None

        # Find closing ]
        bracket_pos = text.find("]", pos + 2)
        if bracket_pos == -1:
            return None

        identifier = text[pos + 2 : bracket_pos]

        # Validate identifier (alphanumeric with dashes/underscores)
        if not identifier or not all(c.isalnum() or c in "-_" for c in identifier):
            return None

        # Make sure this isn't followed by : (which would be a definition)
        if bracket_pos + 1 < len(text) and text[bracket_pos + 1] == ":":
            return None

        return FootnoteRef(location=location, identifier=identifier), bracket_pos + 1

    def _try_parse_link(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Link, int] | None:
        """Try to parse a link at position.

        Handles:
        - [text](url) - inline link
        - [text][ref] - full reference link
        - [text][] - collapsed reference link
        - [ref] - shortcut reference link

        Returns (Link, new_position) or None if not a link.
        """
        if text[pos] != "[":
            return None

        # Find ] while respecting code spans (CommonMark precedence)
        bracket_pos = _find_closing_bracket(text, pos + 1)
        if bracket_pos == -1:
            return None

        link_text = text[pos + 1 : bracket_pos]
        text_len = len(text)

        # Check for (url) or [ref]
        if bracket_pos + 1 < text_len:
            next_char = text[bracket_pos + 1]

            if next_char == "(":
                # Inline link: [text](url) or [text](<url>)
                result = _parse_inline_link(text, bracket_pos + 1)
                if result is not None:
                    url, title, end_pos = result
                    children = self._parse_inline(link_text, location)
                    # CommonMark: Links cannot contain other links at any nesting level
                    if _contains_link(children):
                        return None
                    return Link(location=location, url=url, title=title, children=children), end_pos

            elif next_char == "[":
                # Full or collapsed reference link: [text][ref] or [text][]
                ref_end = text.find("]", bracket_pos + 2)
                if ref_end != -1:
                    ref_label = text[bracket_pos + 2 : ref_end]
                    if not ref_label:
                        # Collapsed: [text][] uses link_text as label
                        ref_label = link_text
                    # Look up reference
                    ref_data = self._link_refs.get(_normalize_label(ref_label))
                    if ref_data:
                        url, title = ref_data
                        children = self._parse_inline(link_text, location)
                        # CommonMark: Links cannot contain other links at any nesting level
                        if _contains_link(children):
                            return None
                        return Link(
                            location=location,
                            url=url,
                            title=title if title else None,
                            children=children,
                        ), ref_end + 1

        # Try shortcut reference link: [ref] alone
        # CommonMark: A shortcut reference link consists of a link label that
        # matches a link reference definition and is NOT followed by [] or a link label.
        if bracket_pos + 1 < text_len and text[bracket_pos + 1] == "[":
            # Followed by [, so can't be a shortcut reference
            return None
        ref_data = self._link_refs.get(_normalize_label(link_text))
        if ref_data:
            url, title = ref_data
            children = self._parse_inline(link_text, location)
            # CommonMark: Links cannot contain other links at any nesting level
            if _contains_link(children):
                return None
            return Link(
                location=location,
                url=url,
                title=title if title else None,
                children=children,
            ), bracket_pos + 1

        return None

    def _try_parse_image(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Image, int] | None:
        """Try to parse an image at position.

        Handles:
        - ![alt](url) - inline image
        - ![alt][ref] - full reference image
        - ![alt][] - collapsed reference image
        - ![alt] - shortcut reference image

        Returns (Image, new_position) or None if not an image.
        """
        if not (text[pos] == "!" and pos + 1 < len(text) and text[pos + 1] == "["):
            return None

        # Find ] while respecting code spans (CommonMark precedence)
        bracket_pos = _find_closing_bracket(text, pos + 2)
        if bracket_pos == -1:
            return None

        alt_text_raw = text[pos + 2 : bracket_pos]
        text_len = len(text)

        # Check for (url) or [ref]
        if bracket_pos + 1 < text_len:
            next_char = text[bracket_pos + 1]

            if next_char == "(":
                # Inline image: ![alt](url) or ![alt](<url>)
                result = _parse_inline_link(text, bracket_pos + 1)
                if result is not None:
                    url, title, end_pos = result
                    # CommonMark: alt text is plain text, no formatting
                    alt = _extract_plain_text(alt_text_raw)
                    return Image(location=location, url=url, alt=alt, title=title), end_pos

            elif next_char == "[":
                # Full or collapsed reference image: ![alt][ref] or ![alt][]
                ref_end = text.find("]", bracket_pos + 2)
                if ref_end != -1:
                    ref_label = text[bracket_pos + 2 : ref_end]
                    if not ref_label:
                        # Collapsed: ![alt][] uses alt_text as label
                        ref_label = alt_text_raw
                    # Look up reference
                    ref_data = self._link_refs.get(_normalize_label(ref_label))
                    if ref_data:
                        url, title = ref_data
                        # CommonMark: alt text is plain text, no formatting
                        alt = _extract_plain_text(alt_text_raw)
                        return Image(
                            location=location,
                            url=url,
                            alt=alt,
                            title=title if title else None,
                        ), ref_end + 1

        # Try shortcut reference image: ![ref] alone
        ref_data = self._link_refs.get(_normalize_label(alt_text_raw))
        if ref_data:
            url, title = ref_data
            # CommonMark: alt text is plain text, no formatting
            alt = _extract_plain_text(alt_text_raw)
            return Image(
                location=location,
                url=url,
                alt=alt,
                title=title if title else None,
            ), bracket_pos + 1

        return None
