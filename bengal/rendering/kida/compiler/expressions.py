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
        Recursively checks nested expressions to catch Filter nodes inside parentheses.

        This handles cases like (a | length) + (b | length) where the left/right
        operands are Filter nodes that need numeric coercion.
        """
        node_type = type(node).__name__

        # Direct match: Filter or FuncCall nodes
        if node_type in _POTENTIALLY_STRING_NODES:
            return True

        # Pipeline nodes contain filters, need coercion
        if node_type == "Pipeline":
            return True

        # Recursive check for nested expressions that might contain filters
        # This handles cases like (a | length) + (b | length) where
        # the left/right operands are Filter nodes
        if node_type == "BinOp":
            # Check both operands recursively
            return self._is_potentially_string(node.left) or self._is_potentially_string(node.right)

        if node_type == "UnaryOp":
            # Check the operand recursively
            return self._is_potentially_string(node.operand)

        # For CondExpr (ternary), check all branches
        if node_type == "CondExpr":
            return (
                self._is_potentially_string(node.test)
                or self._is_potentially_string(node.body)
                or self._is_potentially_string(node.orelse)
            )

        return False

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

            # Strict mode: check scope stack first, then ctx
            # _lookup_scope(ctx, _scope_stack, name) checks scopes then ctx
            return ast.Call(
                func=ast.Name(id="_lookup_scope", ctx=ast.Load()),
                args=[
                    ast.Name(id="ctx", ctx=ast.Load()),
                    ast.Name(id="_scope_stack", ctx=ast.Load()),
                    ast.Constant(value=node.name),
                ],
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
            # Special handling for 'defined' and 'undefined' tests
            # These need to work even when the value is undefined
            if node.name in ("defined", "undefined"):
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

            # Special handling for 'default' filter
            # The default filter needs to work even when the value is undefined
            if node.name in ("default", "d"):
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

        if node_type == "Pipeline":
            return self._compile_pipeline(node)

        if node_type == "InlinedFilter":
            return self._compile_inlined_filter(node)

        if node_type == "NullCoalesce":
            return self._compile_null_coalesce(node)

        if node_type == "OptionalGetattr":
            return self._compile_optional_getattr(node)

        if node_type == "OptionalGetitem":
            return self._compile_optional_getitem(node)

        if node_type == "Range":
            return self._compile_range(node)

        # Fallback
        return ast.Constant(value=None)

    def _compile_null_coalesce(self, node: Any) -> ast.expr:
        """Compile a ?? b to handle both None and undefined variables.

        Uses _null_coalesce helper to catch UndefinedError for undefined variables.
        Part of RFC: kida-modern-syntax-features.

        The helper is called as:
            _null_coalesce(lambda: a, lambda: b)

        This allows:
        - a ?? b to return b if a is undefined (UndefinedError)
        - a ?? b to return b if a is None
        - a ?? b to return a if a is any other value (including falsy: 0, '', [])
        """
        left = self._compile_expr(node.left)
        right = self._compile_expr(node.right)

        # _null_coalesce(lambda: left, lambda: right)
        return ast.Call(
            func=ast.Name(id="_null_coalesce", ctx=ast.Load()),
            args=[
                # lambda: left
                ast.Lambda(
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[],
                        vararg=None,
                        kwonlyargs=[],
                        kw_defaults=[],
                        kwarg=None,
                        defaults=[],
                    ),
                    body=left,
                ),
                # lambda: right
                ast.Lambda(
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[],
                        vararg=None,
                        kwonlyargs=[],
                        kw_defaults=[],
                        kwarg=None,
                        defaults=[],
                    ),
                    body=right,
                ),
            ],
            keywords=[],
        )

    def _compile_optional_getattr(self, node: Any) -> ast.expr:
        """Compile obj?.attr using walrus operator to avoid double evaluation.

        obj?.attr compiles to:
            '' if (_oc := obj) is None else (_oc_val := _getattr_none(_oc, 'attr')) if _oc_val is not None else ''

        The double check ensures that:
        1. If obj is None, return ''
        2. If obj.attr is None, return '' (for output) but preserve None for ??

        For null coalescing to work, we need a different approach: the optional
        chain preserves None so ?? can check it, but for direct output, None becomes ''.

        Actually, we return None but rely on the caller to handle None → '' conversion.
        For output, the expression is wrapped differently.

        Simplified: Return None when short-circuiting, let output handle conversion.

        Part of RFC: kida-modern-syntax-features.
        """
        self._block_counter += 1
        tmp_name = f"_oc_{self._block_counter}"

        obj = self._compile_expr(node.obj)

        # None if (_oc_N := obj) is None else _getattr_none(_oc_N, 'attr')
        # Uses _getattr_none to preserve None values for null coalescing
        return ast.IfExp(
            test=ast.Compare(
                left=ast.NamedExpr(
                    target=ast.Name(id=tmp_name, ctx=ast.Store()),
                    value=obj,
                ),
                ops=[ast.Is()],
                comparators=[ast.Constant(value=None)],
            ),
            body=ast.Constant(value=None),
            orelse=ast.Call(
                func=ast.Name(id="_getattr_none", ctx=ast.Load()),
                args=[
                    ast.Name(id=tmp_name, ctx=ast.Load()),
                    ast.Constant(value=node.attr),
                ],
                keywords=[],
            ),
        )

    def _compile_optional_getitem(self, node: Any) -> ast.expr:
        """Compile obj?[key] using walrus operator to avoid double evaluation.

        obj?[key] compiles to:
            None if (_oc := obj) is None else _oc[key]

        Part of RFC: kida-modern-syntax-features.
        """
        self._block_counter += 1
        tmp_name = f"_oc_{self._block_counter}"

        obj = self._compile_expr(node.obj)
        key = self._compile_expr(node.key)

        # None if (_oc_N := obj) is None else _oc_N[key]
        return ast.IfExp(
            test=ast.Compare(
                left=ast.NamedExpr(
                    target=ast.Name(id=tmp_name, ctx=ast.Store()),
                    value=obj,
                ),
                ops=[ast.Is()],
                comparators=[ast.Constant(value=None)],
            ),
            body=ast.Constant(value=None),
            orelse=ast.Subscript(
                value=ast.Name(id=tmp_name, ctx=ast.Load()),
                slice=key,
                ctx=ast.Load(),
            ),
        )

    def _compile_range(self, node: Any) -> ast.expr:
        """Compile range literal to range() call.

        1..10    → range(1, 11)      # inclusive
        1...11   → range(1, 11)      # exclusive
        1..10 by 2 → range(1, 11, 2)

        Part of RFC: kida-modern-syntax-features.
        """
        start = self._compile_expr(node.start)
        end = self._compile_expr(node.end)

        if node.inclusive:
            # Inclusive: 1..10 → range(1, 11)
            end = ast.BinOp(left=end, op=ast.Add(), right=ast.Constant(value=1))

        args = [start, end]
        if node.step:
            args.append(self._compile_expr(node.step))

        return ast.Call(
            func=ast.Name(id="_range", ctx=ast.Load()),
            args=args,
            keywords=[],
        )

    def _compile_inlined_filter(self, node: Any) -> ast.Call:
        """Compile inlined filter to direct method call.

        Generates: _str(value).method(*args)

        This replaces filter dispatch overhead with a direct method call,
        providing ~5-10% speedup for filter-heavy templates.
        """
        # _str(value) - use _str from namespace, not builtin str
        str_call = ast.Call(
            func=ast.Name(id="_str", ctx=ast.Load()),
            args=[self._compile_expr(node.value)],
            keywords=[],
        )

        # str(value).method
        method_attr = ast.Attribute(
            value=str_call,
            attr=node.method,
            ctx=ast.Load(),
        )

        # str(value).method(*args)
        return ast.Call(
            func=method_attr,
            args=[self._compile_expr(arg) for arg in node.args],
            keywords=[],
        )

    def _compile_pipeline(self, node: Any) -> ast.expr:
        """Compile pipeline: expr |> filter1 |> filter2.

        Pipelines compile to nested filter calls using the _filters dict,
        exactly like regular filter chains. The difference is purely syntactic.

        expr |> a |> b(x)  →  _filters['b'](_filters['a'](expr), x)

        Validates filter existence at compile time (same as Filter nodes).
        """
        result = self._compile_expr(node.value)

        for filter_name, args, kwargs in node.steps:
            # Validate filter exists at compile time
            if filter_name not in self._env._filters:
                suggestion = self._get_filter_suggestion(filter_name)
                msg = f"Unknown filter '{filter_name}'"
                if suggestion:
                    msg += f". Did you mean '{suggestion}'?"
                raise TemplateSyntaxError(msg, lineno=getattr(node, "lineno", None))

            # Compile filter arguments
            compiled_args = [self._compile_expr(arg) for arg in args]
            compiled_kwargs = [
                ast.keyword(arg=k, value=self._compile_expr(v)) for k, v in kwargs.items()
            ]

            # Call: _filters['filter_name'](prev_result, *args, **kwargs)
            result = ast.Call(
                func=ast.Subscript(
                    value=ast.Name(id="_filters", ctx=ast.Load()),
                    slice=ast.Constant(value=filter_name),
                    ctx=ast.Load(),
                ),
                args=[result] + compiled_args,
                keywords=compiled_kwargs,
            )

        return result
