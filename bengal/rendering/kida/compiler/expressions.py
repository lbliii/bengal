"""Expression compilation for Kida compiler.

Provides mixin for compiling Kida expression AST nodes to Python AST expressions.
"""

from __future__ import annotations

import ast
from difflib import get_close_matches
from typing import TYPE_CHECKING, Any

from bengal.rendering.kida.environment.exceptions import TemplateSyntaxError

if TYPE_CHECKING:
    pass

# Arithmetic operators that require numeric operands
_ARITHMETIC_OPS = frozenset({"*", "/", "-", "+", "**", "//", "%"})

# Node types that may produce string values (like Markup from macros)
_POTENTIALLY_STRING_NODES = frozenset({"FuncCall", "Filter"})


class ExpressionCompilationMixin:
    """Mixin for compiling expressions.

    Required Host Attributes:
        - _locals: set[str]
        - _env: Environment (with strict mode setting)
        - _get_binop: method (from OperatorUtilsMixin)
        - _get_unaryop: method (from OperatorUtilsMixin)
        - _get_cmpop: method (from OperatorUtilsMixin)
    """

    def _get_filter_suggestion(self, name: str) -> str | None:
        """Find closest matching filter name for typo suggestions.

        Uses difflib.get_close_matches with 0.6 cutoff for reasonable typo detection.
        Returns None if no close match found.
        """
        matches = get_close_matches(name, self._env._filters.keys(), n=1, cutoff=0.6)
        return matches[0] if matches else None

    def _get_test_suggestion(self, name: str) -> str | None:
        """Find closest matching test name for typo suggestions.

        Uses difflib.get_close_matches with 0.6 cutoff for reasonable typo detection.
        Returns None if no close match found.
        """
        matches = get_close_matches(name, self._env._tests.keys(), n=1, cutoff=0.6)
        return matches[0] if matches else None

    def _is_potentially_string(self, node: Any) -> bool:
        """Check if node could produce a string value (macro call, filter chain).

        Used to determine when numeric coercion is needed for arithmetic operations.
        """
        return type(node).__name__ in _POTENTIALLY_STRING_NODES

    def _wrap_coerce_numeric(self, expr: ast.expr) -> ast.expr:
        """Wrap expression in _coerce_numeric() call for arithmetic safety.

        Ensures that Markup objects (from macros) are converted to numbers
        before arithmetic operations, preventing string multiplication.
        """
        return ast.Call(
            func=ast.Name(id="_coerce_numeric", ctx=ast.Load()),
            args=[expr],
            keywords=[],
        )

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

            # Check strict mode from environment
            if self._env.strict:
                # Strict mode: use _lookup(ctx, name) which raises UndefinedError
                # Performance: O(1) dict lookup on fast path (defined var)
                # Error path converts KeyError to UndefinedError with context
                return ast.Call(
                    func=ast.Name(id="_lookup", ctx=ast.Load()),
                    args=[
                        ast.Name(id="ctx", ctx=ast.Load()),
                        ast.Constant(value=node.name),
                    ],
                    keywords=[],
                )
            else:
                # Legacy mode: use ctx.get(name) which returns None for missing vars
                # The default() filter can handle None values
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
            # Special handling for 'defined' and 'undefined' tests in strict mode
            # These need to work even when the value is undefined
            if node.name in ("defined", "undefined") and self._env.strict:
                # Generate: _is_defined(lambda: <value>) or not _is_defined(lambda: <value>)
                value_lambda = ast.Lambda(
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[],
                        vararg=None,
                        kwonlyargs=[],
                        kw_defaults=[],
                        kwarg=None,
                        defaults=[],
                    ),
                    body=self._compile_expr(node.value),
                )
                test_call = ast.Call(
                    func=ast.Name(id="_is_defined", ctx=ast.Load()),
                    args=[value_lambda],
                    keywords=[],
                )
                # For 'undefined' test, negate the result
                if node.name == "undefined":
                    test_call = ast.UnaryOp(op=ast.Not(), operand=test_call)
                # Handle negated tests (is not defined, is not undefined)
                if node.negated:
                    return ast.UnaryOp(op=ast.Not(), operand=test_call)
                return test_call

            # Validate test exists at compile time
            if node.name not in self._env._tests:
                suggestion = self._get_test_suggestion(node.name)
                msg = f"Unknown test '{node.name}'"
                if suggestion:
                    msg += f". Did you mean '{suggestion}'?"
                raise TemplateSyntaxError(msg, lineno=getattr(node, "lineno", None))

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
            # Validate filter exists at compile time
            # Special case: 'default' and 'd' are handled specially below but still valid
            if node.name not in self._env._filters:
                suggestion = self._get_filter_suggestion(node.name)
                msg = f"Unknown filter '{node.name}'"
                if suggestion:
                    msg += f". Did you mean '{suggestion}'?"
                raise TemplateSyntaxError(msg, lineno=getattr(node, "lineno", None))

            # Special handling for 'default' filter in strict mode
            # The default filter needs to work even when the value is undefined
            if node.name in ("default", "d") and self._env.strict:
                # Generate: _default_safe(lambda: <value>, <default>, <boolean>)
                # This catches UndefinedError and returns the default value
                value_lambda = ast.Lambda(
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[],
                        vararg=None,
                        kwonlyargs=[],
                        kw_defaults=[],
                        kwarg=None,
                        defaults=[],
                    ),
                    body=self._compile_expr(node.value),
                )
                # Build args: default_value and boolean flag
                filter_args = [self._compile_expr(a) for a in node.args]
                filter_kwargs = {k: self._compile_expr(v) for k, v in node.kwargs.items()}

                return ast.Call(
                    func=ast.Name(id="_default_safe", ctx=ast.Load()),
                    args=[value_lambda] + filter_args,
                    keywords=[ast.keyword(arg=k, value=v) for k, v in filter_kwargs.items()],
                )

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

            # For arithmetic ops, coerce potential string operands (from macros) to numeric
            # This prevents string multiplication when macro returns Markup('1')
            if node.op in _ARITHMETIC_OPS:
                left = self._compile_expr(node.left)
                right = self._compile_expr(node.right)

                # Wrap FuncCall/Filter results in numeric coercion
                if self._is_potentially_string(node.left):
                    left = self._wrap_coerce_numeric(left)
                if self._is_potentially_string(node.right):
                    right = self._wrap_coerce_numeric(right)

                return ast.BinOp(
                    left=left,
                    op=self._get_binop(node.op),
                    right=right,
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
            # In strict mode, 'or' expressions need special handling:
            # `undefined_var or fallback()` should evaluate fallback() when var is undefined
            # Python's BoolOp short-circuits, but _lookup() raises before or can evaluate
            # Solution: wrap left operand in _or_safe() which catches UndefinedError
            if node.op == "or" and self._env.strict:
                # Compile: _or_safe(lambda: left, right)
                # For chained or: _or_safe(lambda: _or_safe(lambda: a, b), c)
                values = list(node.values)
                if len(values) == 2:
                    # Simple case: a or b -> _or_safe(lambda: a, b)
                    left_lambda = ast.Lambda(
                        args=ast.arguments(
                            posonlyargs=[],
                            args=[],
                            vararg=None,
                            kwonlyargs=[],
                            kw_defaults=[],
                            kwarg=None,
                            defaults=[],
                        ),
                        body=self._compile_expr(values[0]),
                    )
                    return ast.Call(
                        func=ast.Name(id="_or_safe", ctx=ast.Load()),
                        args=[left_lambda, self._compile_expr(values[1])],
                        keywords=[],
                    )
                else:
                    # Chained case: a or b or c -> _or_safe(lambda: _or_safe(...), c)
                    # Build from left to right
                    from bengal.rendering.kida.nodes import BoolOp as KidaBoolOp

                    # Create nested BoolOp for first N-1 values
                    left_boolop = KidaBoolOp(
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        op="or",
                        values=values[:-1],
                    )
                    left_lambda = ast.Lambda(
                        args=ast.arguments(
                            posonlyargs=[],
                            args=[],
                            vararg=None,
                            kwonlyargs=[],
                            kw_defaults=[],
                            kwarg=None,
                            defaults=[],
                        ),
                        body=self._compile_expr(left_boolop),
                    )
                    return ast.Call(
                        func=ast.Name(id="_or_safe", ctx=ast.Load()),
                        args=[left_lambda, self._compile_expr(values[-1])],
                        keywords=[],
                    )
            else:
                # Non-strict mode or 'and' operator: use standard Python BoolOp
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
