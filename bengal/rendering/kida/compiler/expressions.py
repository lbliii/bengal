"""Expression compilation for Kida compiler.

Provides mixin for compiling Kida expression AST nodes to Python AST expressions.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class ExpressionCompilationMixin:
    """Mixin for compiling expressions.

    Required Host Attributes:
        - _locals: set[str]
        - _get_binop: method (from OperatorUtilsMixin)
        - _get_unaryop: method (from OperatorUtilsMixin)
        - _get_cmpop: method (from OperatorUtilsMixin)
    """

    def _compile_expr(self, node: Any, store: bool = False) -> ast.expr:
        """Compile expression node to Python AST expression.

        Complexity: O(1) dispatch + O(d) for recursive expressions.
        """
        node_type = type(node).__name__

        # Fast path for common types
        if node_type == "Const":
            return ast.Constant(value=node.value)

        if node_type == "Name":
            ctx = ast.Store() if store else ast.Load()
            if store:
                return ast.Name(id=node.name, ctx=ctx)
            # Optimization: check if this is a local variable (loop var, etc.)
            # Locals use O(1) LOAD_FAST instead of O(1) dict lookup + hash
            if node.name in self._locals:
                return ast.Name(id=node.name, ctx=ast.Load())
            # Use ctx.get(name) to handle missing variables gracefully
            # This returns None for missing vars, which default() filter handles
            return ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="ctx", ctx=ast.Load()),
                    attr="get",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=node.name)],
                keywords=[],
            )

        if node_type == "Tuple":
            ctx = ast.Store() if store else ast.Load()
            return ast.Tuple(
                elts=[self._compile_expr(e, store) for e in node.items],
                ctx=ctx,
            )

        if node_type == "List":
            return ast.List(
                elts=[self._compile_expr(e) for e in node.items],
                ctx=ast.Load(),
            )

        if node_type == "Dict":
            return ast.Dict(
                keys=[self._compile_expr(k) for k in node.keys],
                values=[self._compile_expr(v) for v in node.values],
            )

        if node_type == "Getattr":
            # Use _getattr helper that falls back to __getitem__ for dicts
            # This handles both obj.attr and dict['key'] patterns
            return ast.Call(
                func=ast.Name(id="_getattr", ctx=ast.Load()),
                args=[
                    self._compile_expr(node.obj),
                    ast.Constant(value=node.attr),
                ],
                keywords=[],
            )

        if node_type == "Getitem":
            return ast.Subscript(
                value=self._compile_expr(node.obj),
                slice=self._compile_expr(node.key),
                ctx=ast.Load(),
            )

        if node_type == "Slice":
            # Compile slice to Python slice object
            return ast.Slice(
                lower=self._compile_expr(node.start) if node.start else None,
                upper=self._compile_expr(node.stop) if node.stop else None,
                step=self._compile_expr(node.step) if node.step else None,
            )

        if node_type == "Test":
            # Compile test: _tests['name'](value, *args, **kwargs)
            # If negated: not _tests['name'](value, *args, **kwargs)
            value = self._compile_expr(node.value)
            test_call = ast.Call(
                func=ast.Subscript(
                    value=ast.Name(id="_tests", ctx=ast.Load()),
                    slice=ast.Constant(value=node.name),
                    ctx=ast.Load(),
                ),
                args=[value] + [self._compile_expr(a) for a in node.args],
                keywords=[
                    ast.keyword(arg=k, value=self._compile_expr(v)) for k, v in node.kwargs.items()
                ],
            )
            if node.negated:
                return ast.UnaryOp(op=ast.Not(), operand=test_call)
            return test_call

        if node_type == "FuncCall":
            return ast.Call(
                func=self._compile_expr(node.func),
                args=[self._compile_expr(a) for a in node.args],
                keywords=[
                    ast.keyword(arg=k, value=self._compile_expr(v)) for k, v in node.kwargs.items()
                ],
            )

        if node_type == "Filter":
            value = self._compile_expr(node.value)
            return ast.Call(
                func=ast.Subscript(
                    value=ast.Name(id="_filters", ctx=ast.Load()),
                    slice=ast.Constant(value=node.name),
                    ctx=ast.Load(),
                ),
                args=[value] + [self._compile_expr(a) for a in node.args],
                keywords=[
                    ast.keyword(arg=k, value=self._compile_expr(v)) for k, v in node.kwargs.items()
                ],
            )

        if node_type == "BinOp":
            # Special handling for ~ (string concatenation)
            if node.op == "~":
                # str(left) + str(right)
                return ast.BinOp(
                    left=ast.Call(
                        func=ast.Name(id="_str", ctx=ast.Load()),
                        args=[self._compile_expr(node.left)],
                        keywords=[],
                    ),
                    op=ast.Add(),
                    right=ast.Call(
                        func=ast.Name(id="_str", ctx=ast.Load()),
                        args=[self._compile_expr(node.right)],
                        keywords=[],
                    ),
                )
            return ast.BinOp(
                left=self._compile_expr(node.left),
                op=self._get_binop(node.op),
                right=self._compile_expr(node.right),
            )

        if node_type == "UnaryOp":
            return ast.UnaryOp(
                op=self._get_unaryop(node.op),
                operand=self._compile_expr(node.operand),
            )

        if node_type == "Compare":
            return ast.Compare(
                left=self._compile_expr(node.left),
                ops=[self._get_cmpop(op) for op in node.ops],
                comparators=[self._compile_expr(c) for c in node.comparators],
            )

        if node_type == "BoolOp":
            op = ast.And() if node.op == "and" else ast.Or()
            return ast.BoolOp(
                op=op,
                values=[self._compile_expr(v) for v in node.values],
            )

        if node_type == "CondExpr":
            return ast.IfExp(
                test=self._compile_expr(node.test),
                body=self._compile_expr(node.if_true),
                orelse=self._compile_expr(node.if_false),
            )

        # Fallback
        return ast.Constant(value=None)
