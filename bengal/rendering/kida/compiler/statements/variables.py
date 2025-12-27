"""Variable assignment statement compilation for Kida compiler.

Provides mixin for compiling variable assignment statements (set, let, export).
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class VariableAssignmentMixin:
    """Mixin for compiling variable assignment statements.

    Required Host Attributes:
        - _compile_expr: method (from ExpressionCompilationMixin)
    """

    def _compile_set(self, node: Any) -> list[ast.stmt]:
        """Compile {% set %}.

        Handles both single names and structural unpacking:
            {% set x = value %}
            {% set a, b = 1, 2 %}
            {% set (a, b), c = ([1, 2], 3) %}
        """
        return self._compile_assignment(node.target, node.value)

    def _compile_let(self, node: Any) -> list[ast.stmt]:
        """Compile {% let %}.

        Let is like set but semantically represents a template-scoped variable.
        Supports structural unpacking: {% let a, b = 1, 2 %}
        """
        return self._compile_assignment(node.name, node.value)

    def _compile_export(self, node: Any) -> list[ast.stmt]:
        """Compile {% export %}.

        Export makes a variable available in outer scope.
        Supports structural unpacking: {% export a, b = 1, 2 %}
        """
        return self._compile_assignment(node.name, node.value)

    def _compile_assignment(self, target: Any, value: Any) -> list[ast.stmt]:
        """Common logic for set/let/export assignments.

        Handles recursive structural unpacking using ctx dict for all variables.
        """
        from bengal.rendering.kida.nodes import Name as KidaName
        from bengal.rendering.kida.nodes import Tuple as KidaTuple

        compiled_value = self._compile_expr(value)

        if isinstance(target, KidaName):
            # Single variable: ctx['name'] = value
            return [
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            slice=ast.Constant(value=target.name),
                            ctx=ast.Store(),
                        )
                    ],
                    value=compiled_value,
                )
            ]
        elif isinstance(target, KidaTuple):
            # Structural unpacking:
            # _unpack_tmp_N = value
            # _compile_unpacking(_unpack_tmp_N, target)
            self._block_counter += 1
            tmp_name = f"_unpack_tmp_{self._block_counter}"

            stmts: list[ast.stmt] = [
                ast.Assign(
                    targets=[ast.Name(id=tmp_name, ctx=ast.Store())],
                    value=compiled_value,
                )
            ]

            def _gen_unpack(current_target: Any, current_val_ast: ast.expr) -> list[ast.stmt]:
                inner_stmts = []
                if isinstance(current_target, KidaName):
                    inner_stmts.append(
                        ast.Assign(
                            targets=[
                                ast.Subscript(
                                    value=ast.Name(id="ctx", ctx=ast.Load()),
                                    slice=ast.Constant(value=current_target.name),
                                    ctx=ast.Store(),
                                )
                            ],
                            value=current_val_ast,
                        )
                    )
                elif isinstance(current_target, KidaTuple):
                    for i, item in enumerate(current_target.items):
                        sub_val = ast.Subscript(
                            value=current_val_ast,
                            slice=ast.Constant(value=i),
                            ctx=ast.Load(),
                        )
                        inner_stmts.extend(_gen_unpack(item, sub_val))
                return inner_stmts

            stmts.extend(_gen_unpack(target, ast.Name(id=tmp_name, ctx=ast.Load())))
            return stmts
        else:
            # Fallback
            return [
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            slice=ast.Constant(value=str(target)),
                            ctx=ast.Store(),
                        )
                    ],
                    value=compiled_value,
                )
            ]
