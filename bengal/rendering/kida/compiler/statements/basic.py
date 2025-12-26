"""Basic statement compilation for Kida compiler.

Provides mixin for compiling basic output statements (data, output).
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class BasicStatementMixin:
    """Mixin for compiling basic output statements.

    Required Host Attributes:
        - _compile_expr: method (from ExpressionCompilationMixin)
    """

    def _compile_data(self, node: Any) -> list[ast.stmt]:
        """Compile raw text data."""
        if not node.value:
            return []

        # _append("literal text") - uses cached method
        return [
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_append", ctx=ast.Load()),
                    args=[ast.Constant(value=node.value)],
                    keywords=[],
                ),
            )
        ]

    def _compile_output(self, node: Any) -> list[ast.stmt]:
        """Compile {{ expression }} output.

        Uses cached local functions for hot path:
        _e = _escape, _s = _str, _append = buf.append

        Note: _escape handles str conversion internally to preserve Markup type
        """
        expr = self._compile_expr(node.expr)

        # Wrap in escape if needed - _e handles str conversion internally
        # to properly detect Markup objects before converting to str
        if node.escape:
            expr = ast.Call(
                func=ast.Name(id="_e", ctx=ast.Load()),  # cached _escape
                args=[expr],  # Pass raw value, _e handles str conversion
                keywords=[],
            )
        else:
            expr = ast.Call(
                func=ast.Name(id="_s", ctx=ast.Load()),  # cached _str
                args=[expr],
                keywords=[],
            )

        # _append(escaped_value) - uses cached method
        return [
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_append", ctx=ast.Load()),
                    args=[expr],
                    keywords=[],
                ),
            )
        ]
