"""Block parsing and stack management for Kida parser.

Provides mixin for parsing block statements (if, for, def, macro, etc.)
and managing block stack for unified {% end %} syntax.
"""

from __future__ import annotations

from bengal.rendering.kida.parser.blocks.control_flow import ControlFlowBlockParsingMixin
from bengal.rendering.kida.parser.blocks.core import BlockStackMixin
from bengal.rendering.kida.parser.blocks.functions import FunctionBlockParsingMixin
from bengal.rendering.kida.parser.blocks.special_blocks import SpecialBlockParsingMixin
from bengal.rendering.kida.parser.blocks.template_structure import (
    TemplateStructureBlockParsingMixin,
)
from bengal.rendering.kida.parser.blocks.variables import VariableBlockParsingMixin


class BlockParsingMixin(
    ControlFlowBlockParsingMixin,
    VariableBlockParsingMixin,
    TemplateStructureBlockParsingMixin,
    FunctionBlockParsingMixin,
    SpecialBlockParsingMixin,
):
    """Mixin for parsing block statements.

    Combines all block parsing mixins into a single class.

    Required Host Attributes:
        - All from BlockStackMixin
        - All from TokenNavigationMixin
        - _parse_body: method
        - _parse_expression: method
        - _parse_primary: method
        - _parse_call_args: method
        - _parse_for_target: method
        - _parse_tuple_or_name: method
        - _parse_tuple_or_expression: method
        - _skip_comment: method
        - _get_eof_error_suggestion: method
        - _parse_block_content: method
    """

    pass


__all__ = ["BlockParsingMixin", "BlockStackMixin"]
