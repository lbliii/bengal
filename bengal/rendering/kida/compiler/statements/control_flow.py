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

    def _compile_break(self, node: Any) -> list[ast.stmt]:
        """Compile {% break %} loop control.

        Part of RFC: kida-modern-syntax-features.
        """
        return [ast.Break()]

    def _compile_continue(self, node: Any) -> list[ast.stmt]:
        """Compile {% continue %} loop control.

        Part of RFC: kida-modern-syntax-features.
        """
        return [ast.Continue()]

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
            _iter_source = iterable
            _loop_items = list(_iter_source) if _iter_source is not None else []
            if _loop_items:
                loop = _LoopContext(_loop_items)
                for item in loop:
                    [if test:]  # inline filter (RFC: kida-modern-syntax-features)
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

        # Use unique variable name to avoid conflicts with nested loops
        self._block_counter += 1
        iter_var = f"_iter_source_{self._block_counter}"

        # _iter_source_N = iterable
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id=iter_var, ctx=ast.Store())],
                value=iter_expr,
            )
        )

        # _loop_items = list(_iter_source_N) if _iter_source_N is not None else []
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id="_loop_items", ctx=ast.Store())],
                value=ast.IfExp(
                    test=ast.Compare(
                        left=ast.Name(id=iter_var, ctx=ast.Load()),
                        ops=[ast.IsNot()],
                        comparators=[ast.Constant(value=None)],
                    ),
                    body=ast.Call(
                        func=ast.Name(id="_list", ctx=ast.Load()),
                        args=[ast.Name(id=iter_var, ctx=ast.Load())],
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

        # Handle inline test condition: {% for x in items if x.visible %}
        # Part of RFC: kida-modern-syntax-features
        if node.test:
            body = [
                ast.If(
                    test=self._compile_expr(node.test),
                    body=body,
                    orelse=[],
                )
            ]

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

    def _compile_match(self, node: Any) -> list[ast.stmt]:
        """Compile {% match expr %}{% case pattern [if guard] %}...{% end %}.

        Generates chained if/elif comparisons:
            _match_subject = expr
            if _match_subject == pattern1:
                ...body1...
            elif _match_subject == pattern2 and guard2:
                ...body2...
            elif guard3:  # Wildcard case (_) with guard
                ...
            elif True:  # Wildcard case (_) without guard
                ...default...

        The wildcard pattern (_) compiles to `True` (always matches).
        Guards are optional conditions added with `if`: {% case _ if condition %}

        Uses unique variable name with block counter to support nested match blocks.
        """
        from bengal.rendering.kida.nodes import Name as KidaName

        stmts: list[ast.stmt] = []

        # Use unique variable name to support nested match blocks
        self._block_counter += 1
        subject_var = f"_match_subject_{self._block_counter}"

        # _match_subject_N = expr
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id=subject_var, ctx=ast.Store())],
                value=self._compile_expr(node.subject),
            )
        )

        if not node.cases:
            return stmts

        # Build if/elif chain from cases
        # Process cases in reverse to build the orelse chain
        orelse: list[ast.stmt] = []

        for pattern_expr, guard_expr, case_body in reversed(node.cases):
            # Compile case body
            body_stmts: list[ast.stmt] = []
            for child in case_body:
                body_stmts.extend(self._compile_node(child))
            if not body_stmts:
                body_stmts = [ast.Pass()]

            # Check for wildcard pattern (_)
            is_wildcard = isinstance(pattern_expr, KidaName) and pattern_expr.name == "_"

            if is_wildcard:
                if guard_expr:
                    # Wildcard with guard: just use the guard as the test
                    test = self._compile_expr(guard_expr)
                else:
                    # Wildcard without guard: always True (becomes else clause)
                    test = ast.Constant(value=True)
            else:
                # Equality comparison: _match_subject_N == pattern
                pattern_test = ast.Compare(
                    left=ast.Name(id=subject_var, ctx=ast.Load()),
                    ops=[ast.Eq()],
                    comparators=[self._compile_expr(pattern_expr)],
                )
                if guard_expr:
                    # Pattern with guard: pattern_match AND guard
                    test = ast.BoolOp(
                        op=ast.And(),
                        values=[pattern_test, self._compile_expr(guard_expr)],
                    )
                else:
                    test = pattern_test

            # Build if node
            if_node = ast.If(
                test=test,
                body=body_stmts,
                orelse=orelse,
            )
            orelse = [if_node]

        # The first case becomes the outermost if
        if orelse:
            stmts.extend(orelse)

        return stmts
