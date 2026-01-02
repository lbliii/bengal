"""Special inline parsing for Patitas parser.

Handles HTML inline, autolinks, roles, and math expressions.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.nodes import HtmlInline, Link, Math, Role, Text

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


# CommonMark autolink patterns (section 6.7)
# URI autolink: starts with scheme (letter followed by 1-31 letters, digits, +, -, .)
# followed by : and then non-space, non-<, non-> characters
# The scheme must be at least 2 characters total (letter + at least 1 more)
_URI_AUTOLINK_RE = re.compile(r"^<([a-zA-Z][a-zA-Z0-9+.\-]{1,31}):([^\s<>]*)>$")

# Tag name pattern: ASCII letter followed by letters, digits, or hyphens
_TAG_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9-]*$")

# Attribute name pattern per CommonMark:
# [a-zA-Z_:][a-zA-Z0-9_.\-:]*
_ATTR_NAME_RE = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_.:\-]*$")


def _parse_html_open_tag(text: str, pos: int) -> tuple[str, int] | None:
    """Parse an HTML open tag per CommonMark spec.

    CommonMark requires strict validation:
    - Tag name: ASCII letter followed by letters, digits, hyphens
    - Attribute names: [a-zA-Z_:][a-zA-Z0-9_.:-]*
    - Attribute values: unquoted (no spaces/quotes/=/<>/`),
                        single-quoted (no '), double-quoted (no ")
    - Space required between tag name and first attribute
    - Space required between attributes
    - Optional / before final >

    Returns (html_text, end_pos) or None if not valid.
    """
    if pos >= len(text) or text[pos] != "<":
        return None

    i = pos + 1
    text_len = len(text)

    # Must start with letter (tag name)
    if i >= text_len or not text[i].isalpha():
        return None

    # Parse tag name
    tag_start = i
    while i < text_len and (text[i].isalnum() or text[i] == "-"):
        i += 1
    tag_name = text[tag_start:i]

    if not tag_name or not _TAG_NAME_RE.match(tag_name):
        return None

    # After tag name: whitespace, /, or >
    while i < text_len:
        char = text[i]

        # End of tag
        if char == ">":
            return text[pos : i + 1], i + 1

        # Self-closing
        if char == "/":
            if i + 1 < text_len and text[i + 1] == ">":
                return text[pos : i + 2], i + 2
            # / not followed by > is invalid
            return None

        # Whitespace before attributes
        if char in " \t\n":
            i += 1
            continue

        # Must be attribute name starting with valid char
        if not (char.isalpha() or char in "_:"):
            return None

        # Parse attribute name
        attr_start = i
        while i < text_len:
            c = text[i]
            if c.isalnum() or c in "_.::-":
                i += 1
            else:
                break
        attr_name = text[attr_start:i]

        if not _ATTR_NAME_RE.match(attr_name):
            return None

        # Skip whitespace
        while i < text_len and text[i] in " \t\n":
            i += 1

        if i >= text_len:
            return None

        # Check for = (attribute value)
        if text[i] == "=":
            i += 1  # Skip =

            # Skip whitespace after =
            while i < text_len and text[i] in " \t\n":
                i += 1

            if i >= text_len:
                return None

            val_char = text[i]

            # Double-quoted value
            if val_char == '"':
                i += 1
                while i < text_len:
                    if text[i] == '"':
                        i += 1
                        break
                    elif text[i] == "\\":
                        # Backslash doesn't escape in HTML attributes
                        # But we still consume it normally
                        i += 1
                    else:
                        i += 1
                else:
                    # Unclosed quote
                    return None

            # Single-quoted value
            elif val_char == "'":
                i += 1
                while i < text_len and text[i] != "'":
                    i += 1
                if i >= text_len:
                    return None
                i += 1  # Skip closing '

            # Unquoted value - cannot contain: " ' = < > ` or whitespace
            else:
                if val_char in "\"'=<>`":
                    return None
                while i < text_len and text[i] not in "\"'=<>` \t\n>":
                    i += 1
                # Check we actually parsed something
                if i == attr_start:
                    return None

        # After attribute: must be whitespace, /, or >
        if i < text_len and text[i] not in " \t\n/>":
            # Invalid: no space between attributes
            return None

    # Reached end without closing >
    return None


# Email autolink pattern (CommonMark spec)
# The local-part cannot contain backslashes (which would be escapes)
# local-part@domain where local-part has restricted chars
_EMAIL_AUTOLINK_RE = re.compile(
    r"^<([a-zA-Z0-9.!#$%&'*+/=?^_`{|}~\-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*)>$"
)


def _percent_encode_url(url: str) -> str:
    """Percent-encode special characters in URL for href attribute.

    CommonMark requires certain characters to be percent-encoded.
    """
    # Characters that should be percent-encoded in the URL
    # (but not the entire URL, just special chars like backslash, brackets)
    result = []
    for char in url:
        if char == "\\":
            result.append("%5C")
        elif char == "[":
            result.append("%5B")
        elif char == "]":
            result.append("%5D")
        else:
            result.append(char)
    return "".join(result)


class SpecialInlineMixin:
    """Mixin for special inline element parsing.

    Handles autolinks, HTML inline, roles ({role}`content`), and math ($expression$).

    Required Host Attributes: None

    Required Host Methods: None
    """

    def _try_parse_autolink(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Link, int] | None:
        """Try to parse a CommonMark autolink at position.

        Autolinks are URLs or email addresses wrapped in angle brackets:
        - <https://example.com> -> <a href="https://example.com">...</a>
        - <foo@example.com> -> <a href="mailto:foo@example.com">...</a>

        Returns (Link, new_position) or None if not an autolink.

        Per CommonMark 6.7:
        - URI autolinks: <scheme:...> where scheme is [a-zA-Z][a-zA-Z0-9+.-]{1,31}
        - Email autolinks: <local@domain> (no backslashes allowed)
        """
        if text[pos] != "<":
            return None

        # Look for closing >
        close_pos = text.find(">", pos + 1)
        if close_pos == -1:
            return None

        # Get the content between < and >
        bracket_content = text[pos : close_pos + 1]
        inner = bracket_content[1:-1]

        # Empty or contains forbidden characters = not an autolink
        # Spaces, tabs, newlines are not allowed
        if not inner or " " in inner or "\n" in inner or "\t" in inner:
            return None

        # Try URI autolink first
        uri_match = _URI_AUTOLINK_RE.match(bracket_content)
        if uri_match:
            # URL for href needs percent-encoding of special chars
            url_encoded = _percent_encode_url(inner)
            # Display text keeps original characters
            display_text = inner
            children = (Text(location=location, content=display_text),)
            return Link(
                location=location, url=url_encoded, title=None, children=children
            ), close_pos + 1

        # Try email autolink - but reject if contains backslash (escape sequence)
        if "\\" not in inner:
            email_match = _EMAIL_AUTOLINK_RE.match(bracket_content)
            if email_match:
                email = email_match.group(1)
                url = f"mailto:{email}"
                children = (Text(location=location, content=email),)
                return Link(
                    location=location, url=url, title=None, children=children
                ), close_pos + 1

        return None

    def _try_parse_html_inline(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[HtmlInline, int] | None:
        """Try to parse inline HTML at position.

        CommonMark section 6.8 defines valid raw HTML inline elements:
        - Open tags: <tagname attributes...>
        - Closing tags: </tagname>
        - HTML comments: <!-- ... -->
        - Processing instructions: <? ... ?>
        - Declarations: <!LETTER ... >
        - CDATA: <![CDATA[ ... ]]>

        Returns (HtmlInline, new_position) or None if not valid HTML.
        """
        if text[pos] != "<":
            return None

        # Need to find > but be careful about quotes in attributes
        result = _parse_html_open_tag(text, pos)
        if result is not None:
            html, end_pos = result
            return HtmlInline(location=location, html=html), end_pos

        # Check other HTML constructs that don't have attribute parsing issues
        close_pos = text.find(">", pos + 1)
        if close_pos == -1:
            return None

        html = text[pos : close_pos + 1]

        # Basic validation: should look like HTML tag
        if len(html) < 3:
            return None

        inner = html[1:-1]
        if not inner:
            return None

        first = inner[0]

        # HTML comment: <!-- ... -->
        if inner.startswith("!--") and inner.endswith("--"):
            return HtmlInline(location=location, html=html), close_pos + 1

        # CDATA section: <![CDATA[ ... ]]>
        if inner.startswith("![CDATA["):
            # CDATA may contain > so need to find ]]>
            cdata_end = text.find("]]>", pos)
            if cdata_end != -1:
                cdata_html = text[pos : cdata_end + 3]
                return HtmlInline(location=location, html=cdata_html), cdata_end + 3
            return None

        # Processing instruction: <? ... ?>
        if inner.startswith("?") and inner.endswith("?"):
            return HtmlInline(location=location, html=html), close_pos + 1

        # Declaration: <!LETTER ... >
        if inner.startswith("!") and len(inner) > 1 and inner[1].isalpha():
            return HtmlInline(location=location, html=html), close_pos + 1

        # Closing tag: </tagname>
        if first == "/":
            # Rest should be valid tag name (letters, digits, hyphens only after first)
            tag_name = inner[1:].rstrip()
            if (
                tag_name
                and tag_name[0].isalpha()
                and all(c.isalnum() or c == "-" for c in tag_name)
            ):
                return HtmlInline(location=location, html=html), close_pos + 1
            return None

        return None

    def _try_parse_role(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Role, int] | None:
        """Try to parse a role at position.

        Syntax: {role}`content`

        Returns (Role, new_position) or None if not a role.
        """
        if text[pos] != "{":
            return None

        # Find closing }
        brace_close = text.find("}", pos + 1)
        if brace_close == -1:
            return None

        role_name = text[pos + 1 : brace_close].strip()

        # Validate role name (alphanumeric + - + _)
        if not role_name or not all(c.isalnum() or c in "-_" for c in role_name):
            return None

        # Must have backtick immediately after }
        if brace_close + 1 >= len(text) or text[brace_close + 1] != "`":
            return None

        # Find closing backtick
        content_start = brace_close + 2
        backtick_close = text.find("`", content_start)
        if backtick_close == -1:
            return None

        content = text[content_start:backtick_close]

        return Role(
            location=location,
            name=role_name,
            content=content,
        ), backtick_close + 1

    def _try_parse_math(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Math, int] | None:
        """Try to parse inline math at position.

        Syntax: $expression$ (not $$, that's block math)

        Returns (Math, new_position) or None if not valid math.
        """
        if text[pos] != "$":
            return None

        text_len = len(text)

        # Check for $$ (block math delimiter - skip here, handled at block level)
        if pos + 1 < text_len and text[pos + 1] == "$":
            return None

        # Find closing $
        content_start = pos + 1
        dollar_close = text.find("$", content_start)
        if dollar_close == -1:
            return None

        # Content cannot be empty
        content = text[content_start:dollar_close]
        if not content:
            return None

        # Content cannot start or end with space (unless single char)
        if len(content) > 1 and content[0] == " " and content[-1] == " ":
            return None

        return Math(location=location, content=content), dollar_close + 1
