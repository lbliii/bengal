"""Statement compilation for Kida compiler.

Provides mixins for compiling Kida statement AST nodes to Python AST statements.

The statements package is organized into logical modules:
    - basic: Basic output (data, output)
    - control_flow: Control flow (if, for)
    - variables: Variable assignments (set, let, export)
    - template_structure: Template structure (block, include, from_import)
    - functions: Functions/macros (macro, def, call_block, slot)
    - special_blocks: Special blocks (with, do, raw, capture, cache, filter_block)
"""

from __future__ import annotations

from bengal.rendering.kida.compiler.statements.basic import BasicStatementMixin
from bengal.rendering.kida.compiler.statements.control_flow import ControlFlowMixin
from bengal.rendering.kida.compiler.statements.functions import FunctionCompilationMixin
from bengal.rendering.kida.compiler.statements.special_blocks import SpecialBlockMixin
from bengal.rendering.kida.compiler.statements.template_structure import TemplateStructureMixin
from bengal.rendering.kida.compiler.statements.variables import VariableAssignmentMixin


class StatementCompilationMixin(
    BasicStatementMixin,
    ControlFlowMixin,
    VariableAssignmentMixin,
    TemplateStructureMixin,
    FunctionCompilationMixin,
    SpecialBlockMixin,
):
    """Combined mixin for compiling all statement types.

    This class combines all statement compilation mixins into a single
    interface that can be inherited by the Compiler class.

    Required Host Attributes:
        - _locals: set[str]
        - _block_counter: int
        - _compile_expr: method (from ExpressionCompilationMixin)
        - _compile_node: method (from core)
    """

    pass
