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

    def _compile_while(self, node: Any) -> list[ast.stmt]:
        """Compile {% while cond %}...{% end %} loop.

        Generates:
            while condition:
                ... body ...

        Part of RFC: kida-2.0-moonshot (While Loops).

        Example:
            {% let counter = 0 %}
            {% while counter < 5 %}
                {{ counter }}
                {% let counter = counter + 1 %}
            {% end %}
        """
        test = self._compile_expr(node.test)

        body: list[ast.stmt] = []
        for child in node.body:
            body.extend(self._compile_node(child))
        if not body:
            body = [ast.Pass()]

        return [
            ast.While(
                test=test,
                body=body,
                orelse=[],
            )
        ]

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

        Generates chained if/elif comparisons with structural pattern matching
        and variable binding support.

        Example:
            {% match site.logo, site.logo_text %}
                {% case logo, _ if logo %}...
            {% end %}

        Generates:
            _match_subject_N = (site.logo, site.logo_text)
            if isinstance(_match_subject_N, (list, tuple)) and len(_match_subject_N) == 2:
                logo = _match_subject_N[0]
                if logo:
                    ...
        """

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
        orelse: list[ast.stmt] = []

        for pattern_expr, guard_expr, case_body in reversed(node.cases):
            # 1. Generate pattern match test and variable bindings
            pattern_test, bindings = self._make_pattern_match(
                pattern_expr, ast.Name(id=subject_var, ctx=ast.Load())
            )

            # 2. Track names for body/guard compilation
            bound_names = [name for name, _ in bindings]
            for name in bound_names:
                self._locals.add(name)

            # 3. Build the test condition, including walrus bindings if needed
            # We use walrus operators (name := value) in the test so that
            # variables are bound before the guard is evaluated.
            test = pattern_test
            if bindings:
                walrus_exprs = []
                for name, value_ast in bindings:
                    # (name := value)
                    walrus = ast.NamedExpr(
                        target=ast.Name(id=name, ctx=ast.Store()),
                        value=value_ast,
                    )
                    # (name := value) or True -- ensures the test continues
                    walrus_or_true = ast.BoolOp(
                        op=ast.Or(),
                        values=[walrus, ast.Constant(value=True)],
                    )
                    walrus_exprs.append(walrus_or_true)

                # Combine with existing test
                if isinstance(test, ast.Constant) and test.value is True:
                    if len(walrus_exprs) == 1:
                        test = walrus_exprs[0]
                    else:
                        test = ast.BoolOp(op=ast.And(), values=walrus_exprs)
                else:
                    test = ast.BoolOp(op=ast.And(), values=[test] + walrus_exprs)

            if guard_expr:
                # Guard can now safely refer to bound names
                compiled_guard = self._compile_expr(guard_expr)
                if isinstance(test, ast.Constant) and test.value is True:
                    test = compiled_guard
                else:
                    # Append guard to the And chain
                    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
                        test.values.append(compiled_guard)
                    else:
                        test = ast.BoolOp(
                            op=ast.And(),
                            values=[test, compiled_guard],
                        )

            # 4. Compile case body
            body_stmts: list[ast.stmt] = []
            # We still prepend assignments for clarity and to ensure locals
            # are defined even if something strange happens with short-circuiting.
            for name, value_ast in bindings:
                body_stmts.append(
                    ast.Assign(
                        targets=[ast.Name(id=name, ctx=ast.Store())],
                        value=value_ast,
                    )
                )

            for child in case_body:
                body_stmts.extend(self._compile_node(child))

            if not body_stmts:
                body_stmts = [ast.Pass()]

            # 5. Build If node
            if_node = ast.If(
                test=test,
                body=body_stmts,
                orelse=orelse,
            )
            orelse = [if_node]

            # 6. Cleanup locals after compiling this case
            for name in bound_names:
                self._locals.discard(name)

        # The first case becomes the outermost if
        if orelse:
            stmts.extend(orelse)

        return stmts

    def _make_pattern_match(
        self, pattern: Any, subject_ast: ast.expr
    ) -> tuple[ast.expr, list[tuple[str, ast.expr]]]:
        """Generate match test and bindings for a pattern.

        Returns:
            (test_ast, [(name, value_ast), ...])
        """
        from bengal.rendering.kida.nodes import Const as KidaConst
        from bengal.rendering.kida.nodes import Name as KidaName
        from bengal.rendering.kida.nodes import Tuple as KidaTuple

        if isinstance(pattern, KidaName):
            if pattern.name == "_":
                return ast.Constant(value=True), []
            else:
                # Binding pattern: always matches, binds subject to name
                return ast.Constant(value=True), [(pattern.name, subject_ast)]

        if isinstance(pattern, KidaTuple):
            # Match fixed-size tuple/sequence
            n = len(pattern.items)

            # Test: _isinstance(subject, (_list, _tuple)) and _len(subject) == n
            type_check = ast.Call(
                func=ast.Name(id="_isinstance", ctx=ast.Load()),
                args=[
                    subject_ast,
                    ast.Tuple(
                        elts=[
                            ast.Name(id="_list", ctx=ast.Load()),
                            ast.Name(id="_tuple", ctx=ast.Load()),
                        ],
                        ctx=ast.Load(),
                    ),
                ],
                keywords=[],
            )
            len_check = ast.Compare(
                left=ast.Call(
                    func=ast.Name(id="_len", ctx=ast.Load()),
                    args=[subject_ast],
                    keywords=[],
                ),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=n)],
            )

            all_bindings = []
            sub_tests = [type_check, len_check]

            for i, item in enumerate(pattern.items):
                # subject[i]
                item_subject = ast.Subscript(
                    value=subject_ast,
                    slice=ast.Constant(value=i),
                    ctx=ast.Load(),
                )
                sub_test, sub_bindings = self._make_pattern_match(item, item_subject)
                if not (isinstance(sub_test, ast.Constant) and sub_test.value is True):
                    sub_tests.append(sub_test)
                all_bindings.extend(sub_bindings)

            if len(sub_tests) == 1:
                test = sub_tests[0]
            else:
                test = ast.BoolOp(op=ast.And(), values=sub_tests)

            return test, all_bindings

        if isinstance(pattern, KidaConst):
            return (
                ast.Compare(
                    left=subject_ast,
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=pattern.value)],
                ),
                [],
            )

        # Default: simple equality match for complex expressions
        test = ast.Compare(
            left=subject_ast,
            ops=[ast.Eq()],
            comparators=[self._compile_expr(pattern)],
        )
        return test, []
