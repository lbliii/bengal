"""
Patched FencedDirective to support indentation.

Mistune's default FencedDirective does not support indented directives (e.g. inside lists),
unlike fenced code blocks which allow up to 3 spaces.
This patch adds support for indentation to enable robust nesting.
"""

from __future__ import annotations

import re
from re import Match
from typing import TYPE_CHECKING

from mistune.directives import FencedDirective as BaseFencedDirective

if TYPE_CHECKING:
    from mistune.block_parser import BlockParser
    from mistune.core import BlockState


class FencedDirective(BaseFencedDirective):
    """
    FencedDirective that allows indentation up to 3 spaces.

    This is crucial for nesting directives inside lists or other blocks
    where indentation is required/present.
    """

    def __init__(self, plugins, markers="`~"):
        super().__init__(plugins, markers)

        # Rebuild pattern to allow 0-3 spaces indentation
        # Original: r"^(?P<fenced_directive_mark>(?:" + _marker_pattern + r"){3,})\{[a-zA-Z0-9_-]+\}"

        _marker_pattern = "|".join(re.escape(c) for c in markers)
        self.directive_pattern = (
            r"^(?P<fenced_directive_indent> {0,3})"
            r"(?P<fenced_directive_mark>(?:" + _marker_pattern + r"){3,})"
            r"\{[a-zA-Z0-9_-]+\}"
        )

    def parse_directive(self, block: BlockParser, m: Match[str], state: BlockState) -> int | None:
        marker = m.group("fenced_directive_mark")
        # Use the start of the marker group, not the whole match (which includes indent)
        return self._process_directive(block, marker, m.start("fenced_directive_mark"), state)
