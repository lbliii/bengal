"""Control flow statement compilation for Kida compiler.

Provides mixin for compiling control flow statements (if, for).
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class ControlFlowMixin:
    """Mixin for compiling control flow statements.

    Required Host Attributes:
        - _locals: set[str]
        - _compile_expr: method (from ExpressionCompilationMixin)
        - _compile_node: method (from core)
    """

    def _compile_if(self, node: Any) -> list[ast.stmt]:
        """Compile {% if %} conditional."""
        test = self._compile_expr(node.test)
        body = []
        for child in node.body:
            body.extend(self._compile_node(child))
        if not body:
            body = [ast.Pass()]

        orelse: list[ast.stmt] = []

        # Handle elif chains
        for elif_test, elif_body in node.elif_:
            elif_stmts = []
            for child in elif_body:
                elif_stmts.extend(self._compile_node(child))
            if not elif_stmts:
                elif_stmts = [ast.Pass()]
            orelse = [
                ast.If(
                    test=self._compile_expr(elif_test),
                    body=elif_stmts,
                    orelse=orelse,
                )
            ]

        # Handle else
        if node.else_:
            else_stmts = []
            for child in node.else_:
                else_stmts.extend(self._compile_node(child))
            if orelse:
                # Attach to innermost elif's orelse
                innermost = orelse[0]
                while innermost.orelse and isinstance(innermost.orelse[0], ast.If):
                    innermost = innermost.orelse[0]
                innermost.orelse = else_stmts
            else:
                orelse = else_stmts

        return [
            ast.If(
                test=test,
                body=body,
                orelse=orelse,
            )
        ]

    def _compile_for(self, node: Any) -> list[ast.stmt]:
        """Compile {% for %} loop with loop variable support.

        Generates:
            _loop_items = list(iterable)
            if _loop_items:
                loop = _LoopContext(_loop_items)
                for item in loop:
                    ... body with loop.index, loop.first, etc. available ...
            else:
                ... else block ...

        Optimization: Loop variables are tracked as locals and accessed
        directly (O(1) LOAD_FAST) instead of through ctx dict lookup.
        """
        # Get the loop variable name(s) and register as locals
        var_names = self._extract_names(node.target)
        for var_name in var_names:
            self._locals.add(var_name)

        # Also register 'loop' as a local variable
        self._locals.add("loop")

        target = self._compile_expr(node.target, store=True)
        iter_expr = self._compile_expr(node.iter)

        stmts: list[ast.stmt] = []

        # _loop_items = list(iterable) if iterable is not None else []
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id="_loop_items", ctx=ast.Store())],
                value=ast.IfExp(
                    test=ast.Compare(
                        left=iter_expr,
                        ops=[ast.IsNot()],
                        comparators=[ast.Constant(value=None)],
                    ),
                    body=ast.Call(
                        func=ast.Name(id="_list", ctx=ast.Load()),
                        args=[iter_expr],
                        keywords=[],
                    ),
                    orelse=ast.List(elts=[], ctx=ast.Load()),
                ),
            )
        )

        # Build the loop body
        loop_body_stmts: list[ast.stmt] = []

        # loop = _LoopContext(_loop_items)
        loop_body_stmts.append(
            ast.Assign(
                targets=[ast.Name(id="loop", ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id="_LoopContext", ctx=ast.Load()),
                    args=[ast.Name(id="_loop_items", ctx=ast.Load())],
                    keywords=[],
                ),
            )
        )

        # Compile the inner body
        body = []
        for child in node.body:
            body.extend(self._compile_node(child))
        if not body:
            body = [ast.Pass()]

        # for item in loop:
        loop_body_stmts.append(
            ast.For(
                target=target,
                iter=ast.Name(id="loop", ctx=ast.Load()),
                body=body,
                orelse=[],  # No Python else - we handle it with if/else
            )
        )

        # Compile the empty block (for empty iterable)
        orelse = []
        for child in node.empty:
            orelse.extend(self._compile_node(child))

        # if _loop_items: ... else: ...
        if orelse:
            stmts.append(
                ast.If(
                    test=ast.Name(id="_loop_items", ctx=ast.Load()),
                    body=loop_body_stmts,
                    orelse=orelse,
                )
            )
        else:
            # No else block - just check if items exist and run the loop
            stmts.append(
                ast.If(
                    test=ast.Name(id="_loop_items", ctx=ast.Load()),
                    body=loop_body_stmts,
                    orelse=[],
                )
            )

        # Remove loop variables from locals after the loop
        for var_name in var_names:
            self._locals.discard(var_name)
        self._locals.discard("loop")

        return stmts

    def _extract_names(self, node: Any) -> list[str]:
        """Extract variable names from a target expression."""
        from bengal.rendering.kida.nodes import Name as KidaName
        from bengal.rendering.kida.nodes import Tuple as KidaTuple

        if isinstance(node, KidaName):
            return [node.name]
        elif isinstance(node, KidaTuple):
            names = []
            for item in node.items:
                names.extend(self._extract_names(item))
            return names
        return []
