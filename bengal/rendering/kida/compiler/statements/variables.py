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

        Handles both single names and tuple unpacking:
            {% set x = value %}
            {% set a, b = 1, 2 %}
        """
        value = self._compile_expr(node.value)
        target_type = type(node.target).__name__

        if target_type == "Name":
            # Single variable: ctx['name'] = value
            return [
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            slice=ast.Constant(value=node.target.name),
                            ctx=ast.Store(),
                        )
                    ],
                    value=value,
                )
            ]
        elif target_type == "Tuple":
            # Tuple unpacking: temp = value; ctx['a'] = temp[0]; ctx['b'] = temp[1]; ...
            stmts: list[ast.stmt] = [
                # _unpack_tmp = value
                ast.Assign(
                    targets=[ast.Name(id="_unpack_tmp", ctx=ast.Store())],
                    value=value,
                )
            ]
            for i, item in enumerate(node.target.items):
                if type(item).__name__ == "Name":
                    # ctx['name'] = _unpack_tmp[i]
                    stmts.append(
                        ast.Assign(
                            targets=[
                                ast.Subscript(
                                    value=ast.Name(id="ctx", ctx=ast.Load()),
                                    slice=ast.Constant(value=item.name),
                                    ctx=ast.Store(),
                                )
                            ],
                            value=ast.Subscript(
                                value=ast.Name(id="_unpack_tmp", ctx=ast.Load()),
                                slice=ast.Constant(value=i),
                                ctx=ast.Load(),
                            ),
                        )
                    )
            return stmts
        else:
            # Fallback for compatibility - treat as single name string
            return [
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            slice=ast.Constant(value=str(node.target)),
                            ctx=ast.Store(),
                        )
                    ],
                    value=value,
                )
            ]

    def _compile_let(self, node: Any) -> list[ast.stmt]:
        """Compile {% let name = value %.

        Let is like set but semantically represents a template-scoped variable.
        """
        value = self._compile_expr(node.value)
        return [
            ast.Assign(
                targets=[
                    ast.Subscript(
                        value=ast.Name(id="ctx", ctx=ast.Load()),
                        slice=ast.Constant(value=node.name),
                        ctx=ast.Store(),
                    )
                ],
                value=value,
            )
        ]

    def _compile_export(self, node: Any) -> list[ast.stmt]:
        """Compile {% export name = value %.

        Export makes a variable available in outer scope.
        Currently same semantics as let - proper scoping in later version.
        """
        value = self._compile_expr(node.value)
        return [
            ast.Assign(
                targets=[
                    ast.Subscript(
                        value=ast.Name(id="ctx", ctx=ast.Load()),
                        slice=ast.Constant(value=node.name),
                        ctx=ast.Store(),
                    )
                ],
                value=value,
            )
        ]
