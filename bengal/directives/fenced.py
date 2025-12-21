"""
Patched FencedDirective to support indentation, code block awareness, and named closers.

Mistune's default FencedDirective has several issues this patch addresses:
1. Does not support indented directives (e.g. inside lists)
2. Does not skip ::: sequences inside fenced code blocks
3. Does not support named closers (:::{/name})

Named Closers:
    Instead of counting fence depths (::::, :::::, etc.), users can use
    named closers to explicitly close directives:

    ```markdown
    :::{tab-set}
    :::{tab-item} First
    Content here
    :::{/tab-item}
    :::{tab-item} Second
    More content
    :::{/tab-item}
    :::{/tab-set}
    ```

    This eliminates the mental overhead of counting colons for deeply nested
    structures while remaining backward compatible with fence-depth counting.
"""

from __future__ import annotations

import re
from re import Match
from typing import TYPE_CHECKING, Any

from mistune.directives import FencedDirective as BaseFencedDirective
from mistune.directives._fenced import _directive_re

if TYPE_CHECKING:
    from mistune.block_parser import BlockParser
    from mistune.core import BlockState


# Pattern to find fenced code blocks (``` or ~~~) including their content
# This matches opening fence, content, and closing fence
_CODE_BLOCK_PATTERN = re.compile(
    r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)\n"  # Opening fence
    r"(?P<code>.*?)"  # Code content (non-greedy)
    r"^(?P=indent)(?P=fence)[ \t]*$",  # Closing fence (same indent and fence)
    re.MULTILINE | re.DOTALL,
)

# Pattern for named closer: :::{/name} or ::::{/name} etc.
# Captures the directive name being closed
_NAMED_CLOSER_PATTERN = re.compile(
    r"^ {0,3}(?P<closer_mark>:{3,})\{/(?P<closer_name>[a-zA-Z0-9_-]+)\}[ \t]*(?:\n|$)",
    re.MULTILINE,
)


class FencedDirective(BaseFencedDirective):
    """
    FencedDirective that allows indentation, skips code blocks, and supports named closers.

    This is crucial for:
    1. Nesting directives inside lists or other blocks where indentation
       is required/present
    2. Showing directive syntax examples inside code blocks without the
       ::: sequences being consumed by the directive parser
    3. Using named closers (:::{/name}) for complex nested structures

    Example with fence-depth counting (traditional):
        ::::{tab-set}
        :::{tab-item} Example
        Content here
        :::
        ::::

    Example with named closers (new):
        :::{tab-set}
        :::{tab-item} Example
        Content here
        :::{/tab-item}
        :::{/tab-set}

    Both syntaxes work and can be mixed. Named closers are optional but
    recommended for deeply nested structures where counting colons is error-prone.
    """

    def __init__(self, plugins: list[Any], markers: str = ":") -> None:
        super().__init__(plugins, markers)

        # Rebuild pattern to allow indentation for nested directives
        # The pattern matches directives with leading whitespace, which is
        # necessary when directives are nested inside list items or other
        # indented blocks.

        _marker_pattern = "|".join(re.escape(c) for c in markers)
        # Match directives with optional leading whitespace
        # Standard markdown list indentation is 2-4 spaces, so 3 spaces covers
        # most cases. For deeper nesting, users can use colon syntax (:::) which
        # doesn't have this limitation, or ensure proper dedentation.
        self.directive_pattern = (
            r"^(?P<fenced_directive_indent> {0,3})"
            r"(?P<fenced_directive_mark>(?:" + _marker_pattern + r"){3,})"
            r"\{[a-zA-Z0-9_-]+\}"
        )

    def parse_directive(self, block: BlockParser, m: Match[str], state: BlockState) -> int | None:
        marker = m.group("fenced_directive_mark")
        # Use the start of the marker group, not the whole match (which includes indent)
        return self._process_directive(block, marker, m.start("fenced_directive_mark"), state)

    def _process_directive(
        self, block: BlockParser, marker: str, start: int, state: BlockState
    ) -> int | None:
        """
        Process a directive, supporting named closers and skipping code blocks.

        This overrides the base implementation to handle:
        1. Named closers: :::{/name} explicitly closes :::{name}
        2. Code blocks: ::: sequences inside fenced code blocks are skipped
        3. Traditional fence-depth: :::: closes ::::{name}

        Named closers take precedence when found, otherwise falls back to
        fence-depth counting for backward compatibility.
        """
        mlen = len(marker)
        cursor_start = start + len(marker)

        # Get the remaining source text to search
        remaining_src = state.src[cursor_start:]

        # Extract the directive name from the opening
        directive_name = self._extract_directive_name(remaining_src)

        # Find all fenced code block regions in the remaining source
        # These regions should be skipped when searching for closing patterns
        code_block_regions: list[tuple[int, int]] = []
        for code_match in _CODE_BLOCK_PATTERN.finditer(remaining_src):
            code_block_regions.append((code_match.start(), code_match.end()))

        def is_inside_code_block(pos: int) -> bool:
            """Check if position is inside a fenced code block."""
            for region_start, region_end in code_block_regions:
                if region_start <= pos < region_end:
                    return True
            return False

        # Try named closer first if we have a directive name
        end_pos = None
        text = None

        if directive_name:
            # Look for named closer: :::{/directive_name}
            named_closer_result = self._find_named_closer(
                remaining_src, directive_name, is_inside_code_block
            )
            if named_closer_result:
                text, end_pos = named_closer_result
                end_pos = cursor_start + end_pos

        # Fall back to fence-depth counting if no named closer found
        if end_pos is None:
            _end_pattern = r"^ {0,3}" + marker[0] + "{" + str(mlen) + r",}" + r"[ \t]*(?:\n|$)"
            _end_re = re.compile(_end_pattern, re.M)

            for _end_m in _end_re.finditer(remaining_src):
                if not is_inside_code_block(_end_m.start()):
                    # Found a valid closing fence outside code blocks
                    text = remaining_src[: _end_m.start()]
                    end_pos = cursor_start + _end_m.end()
                    break

        if end_pos is None:
            # No closing fence found, consume rest of content
            text = remaining_src
            end_pos = state.cursor_max

        # Parse the directive content
        if text is None:
            return None
        m = _directive_re.match(text)
        if not m:
            return None

        self.parse_method(block, m, state)
        return end_pos

    def _extract_directive_name(self, text: str) -> str | None:
        """Extract directive name from opening pattern like {name}."""
        match = re.match(r"\{([a-zA-Z0-9_-]+)\}", text)
        return match.group(1) if match else None

    def _find_named_closer(
        self,
        text: str,
        directive_name: str,
        is_inside_code_block: Any,
    ) -> tuple[str, int] | None:
        """
        Find a named closer for the given directive.

        Handles nested directives of the same type by tracking nesting depth.

        Args:
            text: Remaining source text after the opening directive
            directive_name: Name of the directive to close (e.g., "tab-set")
            is_inside_code_block: Function to check if position is in code block

        Returns:
            Tuple of (content_before_closer, end_position) or None if not found
        """
        # Pattern for this specific directive's named closer
        closer_pattern = re.compile(
            r"^ {0,3}:{3,}\{/" + re.escape(directive_name) + r"\}[ \t]*(?:\n|$)",
            re.MULTILINE,
        )

        # Pattern for nested opener of the same directive
        opener_pattern = re.compile(
            r"^ {0,3}:{3,}\{" + re.escape(directive_name) + r"\}",
            re.MULTILINE,
        )

        # Track nesting depth - we start inside the directive (depth 1)
        # When we see another opener of same type, increment
        # When we see a closer, decrement - at 0 we found our closer
        nesting_depth = 0

        # Find all openers and closers, sorted by position
        events: list[tuple[int, str, Match[str]]] = []

        for m in opener_pattern.finditer(text):
            if not is_inside_code_block(m.start()):
                events.append((m.start(), "open", m))

        for m in closer_pattern.finditer(text):
            if not is_inside_code_block(m.start()):
                events.append((m.start(), "close", m))

        # Sort by position
        events.sort(key=lambda x: x[0])

        # Process events to find matching closer
        for _pos, event_type, match in events:
            if event_type == "open":
                nesting_depth += 1
            elif event_type == "close":
                if nesting_depth == 0:
                    # Found our closer!
                    return (text[: match.start()], match.end())
                nesting_depth -= 1

        return None
