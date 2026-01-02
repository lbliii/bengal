"""Core inline parsing for Patitas parser.

Provides the main inline tokenization and AST building logic.

Thread Safety:
    All methods are stateless or use instance-local state only.
    Safe for concurrent use when each parser instance is used by one thread.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.nodes import (
    CodeSpan,
    Emphasis,
    Inline,
    LineBreak,
    SoftBreak,
    Strikethrough,
    Strong,
    Text,
)
from bengal.rendering.parsers.patitas.parsing.charsets import (
    ASCII_PUNCTUATION,
    INLINE_SPECIAL,
)
from bengal.rendering.parsers.patitas.parsing.inline.match_registry import (
    MatchRegistry,
)
from bengal.rendering.parsers.patitas.parsing.inline.tokens import (
    CodeSpanToken,
    DelimiterToken,
    HardBreakToken,
    InlineToken,
    NodeToken,
    SoftBreakToken,
    TextToken,
)

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class InlineParsingCoreMixin:
    """Core inline parsing methods.

    Required Host Attributes:
        - _math_enabled: bool
        - _strikethrough_enabled: bool
        - _footnotes_enabled: bool
        - _link_refs: dict[str, tuple[str, str]]

    Required Host Methods (from other mixins):
        - _is_left_flanking(before, after, delim) -> bool
        - _is_right_flanking(before, after, delim) -> bool
        - _is_punctuation(char) -> bool
        - _process_emphasis(tokens, registry) -> MatchRegistry
        - _try_parse_footnote_ref(text, pos, location) -> tuple | None
        - _try_parse_link(text, pos, location) -> tuple | None
        - _try_parse_image(text, pos, location) -> tuple | None
        - _try_parse_autolink(text, pos, location) -> tuple | None
        - _try_parse_html_inline(text, pos, location) -> tuple | None
        - _try_parse_role(text, pos, location) -> tuple | None
        - _try_parse_math(text, pos, location) -> tuple | None
    """

    _math_enabled: bool
    _strikethrough_enabled: bool
    _footnotes_enabled: bool
    _link_refs: dict[str, tuple[str, str]]

    def _parse_inline(self, text: str, location: SourceLocation) -> tuple[Inline, ...]:
        """Parse inline content using CommonMark delimiter stack algorithm.

        This implements the proper flanking delimiter rules for emphasis/strong.
        See: https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis
        """
        if not text:
            return ()

        # Phase 1: Tokenize into typed token objects
        tokens = self._tokenize_inline(text, location)

        # Phase 2: Process delimiter stack to match openers/closers
        # Uses external registry (tokens are immutable)
        registry = self._process_emphasis(tokens)

        # Phase 3: Build AST from processed tokens using registry
        return self._build_inline_ast(tokens, registry, location)

    def _tokenize_inline(self, text: str, location: SourceLocation) -> list[InlineToken]:
        """Tokenize inline content into typed token objects.

        Returns list of InlineToken NamedTuples for type safety and performance.
        """
        tokens: list[InlineToken] = []
        pos = 0
        text_len = len(text)  # Cache length for hot loop
        tokens_append = tokens.append  # Local reference for speed

        while pos < text_len:
            char = text[pos]

            # Code span: `code` - handle first to avoid delimiter confusion
            if char == "`":
                count = 0
                while pos < text_len and text[pos] == "`":
                    count += 1
                    pos += 1

                # Find closing backticks
                close_pos = self._find_code_span_close(text, pos, count)
                if close_pos != -1:
                    code = text[pos:close_pos]
                    # CommonMark 6.3: "Line endings are converted to spaces"
                    code = code.replace("\n", " ")
                    # Normalize: strip one space from each end if both present
                    # But not if it's all spaces
                    code_len = len(code)
                    if code_len >= 2 and code[0] == " " and code[-1] == " " and code.strip():
                        code = code[1:-1]
                    tokens_append(CodeSpanToken(code=code))
                    pos = close_pos + count
                else:
                    tokens_append(TextToken(content="`" * count))
                continue

            # Emphasis delimiters: * or _
            if char in "*_":
                delim_start = pos
                delim_char = char
                count = 0
                while pos < text_len and text[pos] == delim_char:
                    count += 1
                    pos += 1

                # Determine flanking status (CommonMark rules)
                before = text[delim_start - 1] if delim_start > 0 else " "
                after = text[pos] if pos < text_len else " "

                left_flanking = self._is_left_flanking(before, after, delim_char)
                right_flanking = self._is_right_flanking(before, after, delim_char)

                # For underscore, additional rules apply
                if delim_char == "_":
                    can_open = left_flanking and (
                        not right_flanking or self._is_punctuation(before)
                    )
                    can_close = right_flanking and (
                        not left_flanking or self._is_punctuation(after)
                    )
                else:
                    can_open = left_flanking
                    can_close = right_flanking

                tokens_append(
                    DelimiterToken(
                        char=delim_char,  # type: ignore[arg-type]
                        count=count,
                        can_open=can_open,
                        can_close=can_close,
                    )
                )
                continue

            # Link or footnote reference: [text](url) or [^id]
            if char == "[":
                # Check for footnote reference: [^id]
                if self._footnotes_enabled and pos + 1 < text_len and text[pos + 1] == "^":
                    fn_result = self._try_parse_footnote_ref(text, pos, location)
                    if fn_result:
                        node, new_pos = fn_result
                        tokens_append(NodeToken(node=node))
                        pos = new_pos
                        continue

                # Try regular link
                link_result = self._try_parse_link(text, pos, location)
                if link_result:
                    node, new_pos = link_result
                    tokens_append(NodeToken(node=node))
                    pos = new_pos
                    continue
                tokens_append(TextToken(content="["))
                pos += 1
                continue

            # Image: ![alt](url)
            if char == "!":
                if pos + 1 < text_len and text[pos + 1] == "[":
                    img_result = self._try_parse_image(text, pos, location)
                    if img_result:
                        node, new_pos = img_result
                        tokens_append(NodeToken(node=node))
                        pos = new_pos
                        continue
                # Not an image, emit ! as literal text
                tokens_append(TextToken(content="!"))
                pos += 1
                continue

            # Hard break: \ at end of line
            if char == "\\" and pos + 1 < text_len and text[pos + 1] == "\n":
                tokens_append(HardBreakToken())
                pos += 2
                continue

            # Soft break or hard break (two+ trailing spaces)
            if char == "\n":
                # Check for two or more trailing spaces before this newline
                # CommonMark 6.11: "A line break that is preceded by two or more
                # spaces... is parsed as a hard line break"
                space_count = 0
                check_pos = pos - 1
                while check_pos >= 0 and text[check_pos] == " ":
                    space_count += 1
                    check_pos -= 1

                if space_count >= 2:
                    # Remove trailing spaces from previous text token
                    if tokens and isinstance(tokens[-1], TextToken):
                        content = tokens[-1].content.rstrip(" ")
                        if content:
                            tokens[-1] = TextToken(content=content)
                        else:
                            tokens.pop()
                    tokens_append(HardBreakToken())
                else:
                    tokens_append(SoftBreakToken())
                pos += 1
                continue

            # Escaped character
            if char == "\\":
                if pos + 1 < text_len:
                    next_char = text[pos + 1]
                    if next_char in ASCII_PUNCTUATION:
                        # CommonMark: any ASCII punctuation can be escaped
                        tokens_append(TextToken(content=next_char))
                        pos += 2
                        continue
                    else:
                        # Backslash before non-punctuation: emit literal backslash
                        tokens_append(TextToken(content="\\"))
                        pos += 1
                        continue
                else:
                    # Backslash at end of text: emit literal backslash
                    tokens_append(TextToken(content="\\"))
                    pos += 1
                    continue

            # Autolink or HTML inline: <...>
            if char == "<":
                # Try autolink first (CommonMark 6.7): <https://...> or <email@...>
                autolink_result = self._try_parse_autolink(text, pos, location)
                if autolink_result:
                    node, new_pos = autolink_result
                    tokens_append(NodeToken(node=node))
                    pos = new_pos
                    continue

                # Then try HTML inline: <tag>
                html_result = self._try_parse_html_inline(text, pos, location)
                if html_result:
                    node, new_pos = html_result
                    tokens_append(NodeToken(node=node))
                    pos = new_pos
                    continue
                else:
                    # Not valid autolink or HTML, emit < as literal text
                    tokens_append(TextToken(content="<"))
                    pos += 1
                    continue

            # Role: {role}`content`
            if char == "{":
                role_result = self._try_parse_role(text, pos, location)
                if role_result:
                    node, new_pos = role_result
                    tokens_append(NodeToken(node=node))
                    pos = new_pos
                    continue
                else:
                    # Not a valid role, emit { as literal text
                    tokens_append(TextToken(content="{"))
                    pos += 1
                    continue

            # Strikethrough: ~~text~~ (when enabled)
            if char == "~":
                if self._strikethrough_enabled and pos + 1 < text_len and text[pos + 1] == "~":
                    # Found ~~, treat as delimiter
                    pos += 2

                    # Determine flanking status
                    before = text[pos - 3] if pos > 2 else " "
                    after = text[pos] if pos < text_len else " "

                    left_flanking = self._is_left_flanking(before, after, "~")
                    right_flanking = self._is_right_flanking(before, after, "~")

                    tokens_append(
                        DelimiterToken(
                            char="~",
                            count=2,
                            can_open=left_flanking,
                            can_close=right_flanking,
                        )
                    )
                    continue
                # Strikethrough disabled or single ~, emit as text
                tokens_append(TextToken(content="~"))
                pos += 1
                continue

            # Math: $inline$ or $$block$$ (when enabled)
            if char == "$":
                if self._math_enabled:
                    math_result = self._try_parse_math(text, pos, location)
                    if math_result:
                        node, new_pos = math_result
                        tokens_append(NodeToken(node=node))
                        pos = new_pos
                        continue
                # Math disabled or not valid math, emit $ as literal text
                tokens_append(TextToken(content="$"))
                pos += 1
                continue

            # Regular text - accumulate using set lookup (O(1) per char)
            text_start = pos
            # Use frozenset for faster membership testing
            while pos < text_len and text[pos] not in INLINE_SPECIAL:
                pos += 1
            if pos > text_start:
                tokens_append(TextToken(content=text[text_start:pos]))

        return tokens

    def _find_code_span_close(self, text: str, start: int, backtick_count: int) -> int:
        """Find closing backticks for code span."""
        pos = start
        text_len = len(text)
        while True:
            idx = text.find("`", pos)
            if idx == -1:
                return -1
            # Count consecutive backticks
            count = 0
            check_pos = idx
            while check_pos < text_len and text[check_pos] == "`":
                count += 1
                check_pos += 1
            if count == backtick_count:
                return idx
            pos = check_pos

    def _build_inline_ast(
        self,
        tokens: list[InlineToken],
        registry: MatchRegistry,
        location: SourceLocation,
    ) -> tuple[Inline, ...]:
        """Build AST from processed tokens using match registry.

        Uses pattern matching for type-safe token dispatch.

        Args:
            tokens: List of InlineToken NamedTuples from _tokenize_inline().
            registry: MatchRegistry containing delimiter matches.
            location: Source location for node creation.

        Returns:
            Tuple of Inline nodes.
        """
        result: list[Inline] = []
        idx = 0

        while idx < len(tokens):
            token = tokens[idx]

            match token:
                case TextToken(content=content):
                    result.append(Text(location=location, content=content))
                    idx += 1

                case CodeSpanToken(code=code):
                    result.append(CodeSpan(location=location, code=code))
                    idx += 1

                case NodeToken(node=node):
                    result.append(node)  # type: ignore[arg-type]
                    idx += 1

                case HardBreakToken():
                    result.append(LineBreak(location=location))
                    idx += 1

                case SoftBreakToken():
                    result.append(SoftBreak(location=location))
                    idx += 1

                case DelimiterToken(char=delim_char, count=original_count):
                    # Check if this delimiter is an opener with matches
                    all_matches = registry.get_matches_for_opener(idx)
                    if all_matches and all_matches[0].closer_idx > idx:
                        # This is an opener - build nested emphasis/strong/strikethrough
                        # Matches are ordered: first match is outermost (e.g., strong for ***)
                        closer_idx = all_matches[0].closer_idx

                        # Collect children between opener and closer
                        children = self._build_inline_ast(
                            tokens[idx + 1 : closer_idx],
                            registry,
                            location,
                        )

                        # Build nested nodes from innermost to outermost
                        # For ***, matches are [match(count=2), match(count=1)]
                        # We need to wrap: emphasis(children) -> strong(emphasis)
                        for match_info in reversed(all_matches):
                            match_count = match_info.match_count
                            if delim_char == "~":
                                # Strikethrough: ~~ always uses 2 tildes
                                node: Inline = Strikethrough(location=location, children=children)
                            elif match_count == 2:
                                node = Strong(location=location, children=children)
                            else:
                                node = Emphasis(location=location, children=children)
                            # Wrap for next iteration
                            children = (node,)

                        # Unwrap the final single-element tuple
                        result.append(children[0])

                        # Skip to after closer
                        idx = closer_idx + 1
                    else:
                        # Unmatched delimiter - emit as text
                        remaining = registry.remaining_count(idx, original_count)
                        if remaining > 0:
                            result.append(Text(location=location, content=delim_char * remaining))
                        idx += 1

                case _:
                    # Unknown token type, skip
                    idx += 1

        return tuple(result)
