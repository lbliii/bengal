"""
Patched FencedDirective to support indentation and code block awareness.

Mistune's default FencedDirective has two issues:
1. Does not support indented directives (e.g. inside lists)
2. Does not skip ::: sequences inside fenced code blocks

This patch fixes both issues to enable robust directive parsing.
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


class FencedDirective(BaseFencedDirective):
    """
    FencedDirective that allows indentation and skips code blocks.

    This is crucial for:
    1. Nesting directives inside lists or other blocks where indentation
       is required/present
    2. Showing directive syntax examples inside code blocks without the
       ::: sequences being consumed by the directive parser

    Example that now works correctly:
        ::::{tab-set}
        :::{tab-item} Example
        ```markdown
        :::{note}
        This is shown as literal text, not parsed as directive
        :::
        ```
        :::
        ::::
    """

    def __init__(self, plugins: list[Any], markers: str = ":") -> None:
        super().__init__(plugins, markers)

        # Rebuild pattern to allow indentation for nested directives
        # The pattern matches directives with leading whitespace, which is
        # necessary when directives are nested inside list items or other
        # indented blocks. We use a non-greedy approach: match any amount
        # of leading spaces, but the directive parser will handle the actual
        # indentation logic.
        # Original: r"^(?P<fenced_directive_mark>(?:" + _marker_pattern + r"){3,})\{[a-zA-Z0-9_-]+\}"

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
        Process a directive, skipping ::: sequences inside fenced code blocks.

        This overrides the base implementation to handle the case where directive
        closing markers (:::) appear inside fenced code blocks. Without this fix,
        the parser would incorrectly close the directive at the first ::: it finds,
        even if that ::: is inside a code block showing directive syntax as an example.
        """
        mlen = len(marker)
        cursor_start = start + len(marker)

        # Build the end pattern (same as base class)
        _end_pattern = r"^ {0,3}" + marker[0] + "{" + str(mlen) + r",}" r"[ \t]*(?:\n|$)"
        _end_re = re.compile(_end_pattern, re.M)

        # Get the remaining source text to search
        remaining_src = state.src[cursor_start:]

        # Find all fenced code block regions in the remaining source
        # These regions should be skipped when searching for the closing fence
        code_block_regions: list[tuple[int, int]] = []
        for code_match in _CODE_BLOCK_PATTERN.finditer(remaining_src):
            code_block_regions.append((code_match.start(), code_match.end()))

        def is_inside_code_block(pos: int) -> bool:
            """Check if position is inside a fenced code block."""
            for region_start, region_end in code_block_regions:
                if region_start <= pos < region_end:
                    return True
            return False

        # Find the closing fence, skipping matches inside code blocks
        end_pos = None
        text = None

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
        m = _directive_re.match(text)
        if not m:
            return None

        self.parse_method(block, m, state)
        return end_pos
