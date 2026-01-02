"""Link and image parsing for Patitas parser.

Handles inline links, reference links, images, and footnote references.
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

        # Find ]
        bracket_pos = text.find("]", pos + 1)
        if bracket_pos == -1:
            return None

        link_text = text[pos + 1 : bracket_pos]
        text_len = len(text)

        # Check for (url) or [ref]
        if bracket_pos + 1 < text_len:
            next_char = text[bracket_pos + 1]

            if next_char == "(":
                # Inline link: [text](url)
                close_paren = text.find(")", bracket_pos + 2)
                if close_paren != -1:
                    dest = text[bracket_pos + 2 : close_paren]
                    url = dest.strip()
                    title = None

                    # Check for title
                    if " " in dest or "\t" in dest:
                        parts = dest.split(None, 1)
                        if len(parts) == 2:
                            url = parts[0]
                            title_part = parts[1].strip()
                            if (title_part.startswith('"') and title_part.endswith('"')) or (
                                title_part.startswith("'") and title_part.endswith("'")
                            ):
                                title = title_part[1:-1]

                    # CommonMark: process backslash escapes in URL and title
                    url = _process_escapes(url)
                    if title is not None:
                        title = _process_escapes(title)

                    children = self._parse_inline(link_text, location)
                    return Link(
                        location=location, url=url, title=title, children=children
                    ), close_paren + 1

            elif next_char == "[":
                # Full or collapsed reference link: [text][ref] or [text][]
                ref_end = text.find("]", bracket_pos + 2)
                if ref_end != -1:
                    ref_label = text[bracket_pos + 2 : ref_end]
                    if not ref_label:
                        # Collapsed: [text][] uses link_text as label
                        ref_label = link_text
                    # Look up reference
                    ref_data = self._link_refs.get(ref_label.lower())
                    if ref_data:
                        url, title = ref_data
                        children = self._parse_inline(link_text, location)
                        return Link(
                            location=location,
                            url=url,
                            title=title if title else None,
                            children=children,
                        ), ref_end + 1

        # Try shortcut reference link: [ref] alone
        # Only if this looks like a reference (not followed by ( or [)
        ref_data = self._link_refs.get(link_text.lower())
        if ref_data:
            url, title = ref_data
            children = self._parse_inline(link_text, location)
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

        Returns (Image, new_position) or None if not an image.
        """
        if not (text[pos] == "!" and pos + 1 < len(text) and text[pos + 1] == "["):
            return None

        # Find ]
        bracket_pos = text.find("]", pos + 2)
        if bracket_pos == -1:
            return None

        alt_text = text[pos + 2 : bracket_pos]

        # Check for (url)
        if bracket_pos + 1 < len(text) and text[bracket_pos + 1] == "(":
            close_paren = text.find(")", bracket_pos + 2)
            if close_paren != -1:
                dest = text[bracket_pos + 2 : close_paren]
                url = dest.strip()
                title = None

                # Check for title
                if " " in dest or "\t" in dest:
                    parts = dest.split(None, 1)
                    if len(parts) == 2:
                        url = parts[0]
                        title_part = parts[1].strip()
                        if (title_part.startswith('"') and title_part.endswith('"')) or (
                            title_part.startswith("'") and title_part.endswith("'")
                        ):
                            title = title_part[1:-1]

                # CommonMark: process backslash escapes in URL and title
                url = _process_escapes(url)
                if title is not None:
                    title = _process_escapes(title)

                return Image(location=location, url=url, alt=alt_text, title=title), close_paren + 1

        return None
