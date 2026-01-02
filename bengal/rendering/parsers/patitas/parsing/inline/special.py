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

        # Look for closing >
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
        if inner.startswith("![CDATA[") and inner.endswith("]]"):
            return HtmlInline(location=location, html=html), close_pos + 1

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

        # Open tag: <tagname attributes...>
        if first.isalpha():
            # Extract tag name (up to first space, /, or >)
            tag_end = 0
            for i, c in enumerate(inner):
                if c in " \t\n/":
                    tag_end = i
                    break
                tag_end = i + 1

            tag_name = inner[:tag_end]

            # Validate tag name: must be alphanumeric with hyphens only
            # No dots (like foo.bar), no colons (like m:abc) - those aren't HTML tags
            if not tag_name or not tag_name[0].isalpha():
                return None
            if not all(c.isalnum() or c == "-" for c in tag_name):
                return None

            # Has valid tag name - accept (even if attributes are malformed,
            # that's okay for pass-through raw HTML)
            return HtmlInline(location=location, html=html), close_pos + 1

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
