import ast
from typing import Any


class VariableAssignmentMixin:
    """Mixin for compiling variable assignment statements.

    Required Host Attributes:
        - _compile_expr: method (from ExpressionCompilationMixin)
        - _block_counter: int (for unique variable names)
    """

    def _compile_set(self, node: Any) -> list[ast.stmt]:
        """Compile {% set %} - block-scoped variable assignment.

        Variables assigned with {% set %} are scoped to the current block
        (if/for/while/etc.) and are not accessible outside the block.

        Handles both single names and structural unpacking:
            {% set x = value %}
            {% set a, b = 1, 2 %}
            {% set (a, b), c = ([1, 2], 3) %}
        """
        return self._compile_block_scoped_assignment(node.target, node.value)

    def _compile_let(self, node: Any) -> list[ast.stmt]:
        """Compile {% let %} - template-scoped variable assignment.

        Variables assigned with {% let %} are available throughout the template.
        Supports structural unpacking: {% let a, b = 1, 2 %}
        """
        return self._compile_assignment(node.name, node.value)

    def _compile_export(self, node: Any) -> list[ast.stmt]:
        """Compile {% export %} - export variable to outer scope.

        Variables assigned with {% export %} are promoted from inner scope
        (e.g., inside a loop) to the outer scope (e.g., outside the loop).

        Supports structural unpacking: {% export a, b = 1, 2 %}
        """
        return self._compile_export_assignment(node.name, node.value)

    def _compile_block_scoped_assignment(self, target: Any, value: Any) -> list[ast.stmt]:
        """Compile block-scoped assignment ({% set %}).

        Assigns to current scope: _scope_stack[-1][name] = value
        If no scope exists (top level), falls back to ctx (template-scoped).
        """
        from bengal.rendering.kida.nodes import Name as KidaName
        from bengal.rendering.kida.nodes import Tuple as KidaTuple

        compiled_value = self._compile_expr(value)

        if isinstance(target, KidaName):
            # Block-scoped: _scope_stack[-1][name] = value (if scope exists)
            # Fallback to ctx if no scope (top-level set)
            return [
                ast.If(
                    test=ast.Compare(
                        left=ast.Call(
                            func=ast.Name(id="_len", ctx=ast.Load()),
                            args=[ast.Name(id="_scope_stack", ctx=ast.Load())],
                            keywords=[],
                        ),
                        ops=[ast.Gt()],
                        comparators=[ast.Constant(value=0)],
                    ),
                    body=[
                        # _scope_stack[-1][name] = value
                        ast.Assign(
                            targets=[
                                ast.Subscript(
                                    value=ast.Subscript(
                                        value=ast.Name(id="_scope_stack", ctx=ast.Load()),
                                        slice=ast.UnaryOp(
                                            op=ast.USub(),
                                            operand=ast.Constant(value=1),
                                        ),
                                        ctx=ast.Load(),
                                    ),
                                    slice=ast.Constant(value=target.name),
                                    ctx=ast.Store(),
                                )
                            ],
                            value=compiled_value,
                        )
                    ],
                    orelse=[
                        # ctx[name] = value (fallback for top-level)
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
                    ],
                )
            ]
        elif isinstance(target, KidaTuple):
            # Structural unpacking for block-scoped variables
            self._block_counter += 1
            tmp_name = f"_unpack_tmp_{self._block_counter}"

            stmts: list[ast.stmt] = [
                ast.Assign(
                    targets=[ast.Name(id=tmp_name, ctx=ast.Store())],
                    value=compiled_value,
                )
            ]

            def _gen_unpack(
                current_target: Any, current_val_ast: ast.expr, is_block_scoped: bool = True
            ) -> list[ast.stmt]:
                inner_stmts = []
                if isinstance(current_target, KidaName):
                    if is_block_scoped:
                        # Block-scoped unpacking
                        inner_stmts.append(
                            ast.If(
                                test=ast.Compare(
                                    left=ast.Call(
                                        func=ast.Name(id="_len", ctx=ast.Load()),
                                        args=[ast.Name(id="_scope_stack", ctx=ast.Load())],
                                        keywords=[],
                                    ),
                                    ops=[ast.Gt()],
                                    comparators=[ast.Constant(value=0)],
                                ),
                                body=[
                                    ast.Assign(
                                        targets=[
                                            ast.Subscript(
                                                value=ast.Subscript(
                                                    value=ast.Name(
                                                        id="_scope_stack", ctx=ast.Load()
                                                    ),
                                                    slice=ast.UnaryOp(
                                                        op=ast.USub(),
                                                        operand=ast.Constant(value=1),
                                                    ),
                                                    ctx=ast.Load(),
                                                ),
                                                slice=ast.Constant(value=current_target.name),
                                                ctx=ast.Store(),
                                            )
                                        ],
                                        value=current_val_ast,
                                    )
                                ],
                                orelse=[
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
                                ],
                            )
                        )
                    else:
                        # Template-scoped unpacking
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
                        inner_stmts.extend(_gen_unpack(item, sub_val, is_block_scoped))
                return inner_stmts

            stmts.extend(
                _gen_unpack(target, ast.Name(id=tmp_name, ctx=ast.Load()), is_block_scoped=True)
            )
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

    def _compile_export_assignment(self, target: Any, value: Any) -> list[ast.stmt]:
        """Compile export assignment ({% export %}).

        Export always assigns to ctx (template scope) to ensure the variable
        persists after blocks end. This matches the common use case of
        promoting values from loops/conditionals to template scope.
        """
        from bengal.rendering.kida.nodes import Name as KidaName
        from bengal.rendering.kida.nodes import Tuple as KidaTuple

        compiled_value = self._compile_expr(value)

        if isinstance(target, KidaName):
            # Export always goes to ctx (template scope) for persistence
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
            # Structural unpacking for export
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
                    # Export unpacking - always assign to ctx (template scope)
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

    def _compile_assignment(self, target: Any, value: Any) -> list[ast.stmt]:
        """Common logic for template-scoped assignments ({% let %}).

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
