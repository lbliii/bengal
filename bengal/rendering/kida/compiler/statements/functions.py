"""Function and macro statement compilation for Kida compiler.

Provides mixin for compiling function/macro statements (macro, def, call_block, slot).
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class FunctionCompilationMixin:
    """Mixin for compiling function and macro statements.

    Required Host Attributes:
        - _locals: set[str]
        - _compile_expr: method (from ExpressionCompilationMixin)
        - _compile_node: method (from core)
    """

    def _compile_macro(self, node: Any) -> list[ast.stmt]:
        """Compile {% macro name(args) %}...{% endmacro %.

        Generates a function and assigns it to context:
            def _macro_name(arg1, arg2=default):
                buf = []
                ... body ...
                return ''.join(buf)
            ctx['name'] = _macro_name

        Macros have access to outer context variables but create a local scope
        for their arguments. Local {% set %} inside macro shadows outer vars.
        """
        macro_name = node.name
        func_name = f"_macro_{macro_name}"

        # Build function arguments - include _outer_ctx for closure access
        args_list = [ast.arg(arg=name) for name in node.args]
        defaults = [self._compile_expr(d) for d in node.defaults]

        # Build function body
        func_body: list[ast.stmt] = [
            # _e = _escape
            ast.Assign(
                targets=[ast.Name(id="_e", ctx=ast.Store())],
                value=ast.Name(id="_escape", ctx=ast.Load()),
            ),
            # _s = _str
            ast.Assign(
                targets=[ast.Name(id="_s", ctx=ast.Store())],
                value=ast.Name(id="_str", ctx=ast.Load()),
            ),
            # buf = []
            ast.Assign(
                targets=[ast.Name(id="buf", ctx=ast.Store())],
                value=ast.List(elts=[], ctx=ast.Load()),
            ),
            # _append = buf.append
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Attribute(
                    value=ast.Name(id="buf", ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
            ),
            # Create local context by copying outer context + adding macro args
            # ctx = {**_outer_ctx, **{arg1: arg1, arg2: arg2}}
            ast.Assign(
                targets=[ast.Name(id="ctx", ctx=ast.Store())],
                value=ast.Dict(
                    keys=[None, None],  # Spread operators
                    values=[
                        ast.Name(id="_outer_ctx", ctx=ast.Load()),
                        ast.Dict(
                            keys=[ast.Constant(value=name) for name in node.args],
                            values=[ast.Name(id=name, ctx=ast.Load()) for name in node.args],
                        ),
                    ],
                ),
            ),
        ]

        # Add macro args to locals
        for arg_name in node.args:
            self._locals.add(arg_name)

        # Compile macro body
        for child in node.body:
            func_body.extend(self._compile_node(child))

        # Remove macro args from locals
        for arg_name in node.args:
            self._locals.discard(arg_name)

        # return _Markup(''.join(buf))
        # Wrap output in Markup to prevent double-escaping
        func_body.append(
            ast.Return(
                value=ast.Call(
                    func=ast.Name(id="_Markup", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Attribute(
                                value=ast.Constant(value=""),
                                attr="join",
                                ctx=ast.Load(),
                            ),
                            args=[ast.Name(id="buf", ctx=ast.Load())],
                            keywords=[],
                        ),
                    ],
                    keywords=[],
                ),
            )
        )

        # Create function definition with _outer_ctx as keyword-only arg with default
        # This captures the current context at macro definition time for closure behavior
        func_def = ast.FunctionDef(
            name=func_name,
            args=ast.arguments(
                posonlyargs=[],
                args=args_list,
                vararg=None,
                kwonlyargs=[ast.arg(arg="_outer_ctx")],
                kw_defaults=[ast.Name(id="ctx", ctx=ast.Load())],  # Default to current ctx
                kwarg=None,
                defaults=defaults,
            ),
            body=func_body,
            decorator_list=[],
            returns=None,
        )

        # Assign to context BEFORE the function is fully compiled
        # This enables recursive calls: ctx['name'] = _macro_name
        assign = ast.Assign(
            targets=[
                ast.Subscript(
                    value=ast.Name(id="ctx", ctx=ast.Load()),
                    slice=ast.Constant(value=macro_name),
                    ctx=ast.Store(),
                )
            ],
            value=ast.Name(id=func_name, ctx=ast.Load()),
        )

        return [func_def, assign]

    def _compile_def(self, node: Any) -> list[ast.stmt]:
        """Compile {% def name(args) %}...{% enddef %.

        Kida functions have true lexical scoping - they can access variables
        from their enclosing scope, unlike Jinja2 macros.

        Generates:
            def _def_name(arg1, arg2=default, *, _caller=None, _outer_ctx=ctx):
                buf = []
                ctx = {**_outer_ctx, 'arg1': arg1, 'arg2': arg2}
                if _caller:
                    ctx['caller'] = _caller
                ... body ...
                return Markup(''.join(buf))
            ctx['name'] = _def_name
        """
        def_name = node.name
        func_name = f"_def_{def_name}"

        # Build function arguments
        args_list = [ast.arg(arg=name) for name in node.args]
        defaults = [self._compile_expr(d) for d in node.defaults]

        # Build function body
        func_body: list[ast.stmt] = [
            # _e = _escape
            ast.Assign(
                targets=[ast.Name(id="_e", ctx=ast.Store())],
                value=ast.Name(id="_escape", ctx=ast.Load()),
            ),
            # _s = _str
            ast.Assign(
                targets=[ast.Name(id="_s", ctx=ast.Store())],
                value=ast.Name(id="_str", ctx=ast.Load()),
            ),
            # buf = []
            ast.Assign(
                targets=[ast.Name(id="buf", ctx=ast.Store())],
                value=ast.List(elts=[], ctx=ast.Load()),
            ),
            # _append = buf.append
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Attribute(
                    value=ast.Name(id="buf", ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
            ),
            # Create local context: ctx = {**_outer_ctx, 'arg1': arg1, ...}
            ast.Assign(
                targets=[ast.Name(id="ctx", ctx=ast.Store())],
                value=ast.Dict(
                    keys=[None, None],  # Spread operators
                    values=[
                        ast.Name(id="_outer_ctx", ctx=ast.Load()),
                        ast.Dict(
                            keys=[ast.Constant(value=name) for name in node.args],
                            values=[ast.Name(id=name, ctx=ast.Load()) for name in node.args],
                        ),
                    ],
                ),
            ),
            # if _caller: ctx['caller'] = _caller
            ast.If(
                test=ast.Name(id="_caller", ctx=ast.Load()),
                body=[
                    ast.Assign(
                        targets=[
                            ast.Subscript(
                                value=ast.Name(id="ctx", ctx=ast.Load()),
                                slice=ast.Constant(value="caller"),
                                ctx=ast.Store(),
                            )
                        ],
                        value=ast.Name(id="_caller", ctx=ast.Load()),
                    )
                ],
                orelse=[],
            ),
        ]

        # Add args to locals for direct access
        for arg_name in node.args:
            self._locals.add(arg_name)

        # Compile function body
        for child in node.body:
            func_body.extend(self._compile_node(child))

        # Remove args from locals
        for arg_name in node.args:
            self._locals.discard(arg_name)

        # return _Markup(''.join(buf))
        func_body.append(
            ast.Return(
                value=ast.Call(
                    func=ast.Name(id="_Markup", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Attribute(
                                value=ast.Constant(value=""),
                                attr="join",
                                ctx=ast.Load(),
                            ),
                            args=[ast.Name(id="buf", ctx=ast.Load())],
                            keywords=[],
                        ),
                    ],
                    keywords=[],
                ),
            )
        )

        # Create function with _caller and _outer_ctx as keyword-only args
        func_def = ast.FunctionDef(
            name=func_name,
            args=ast.arguments(
                posonlyargs=[],
                args=args_list,
                vararg=None,
                kwonlyargs=[
                    ast.arg(arg="_caller"),
                    ast.arg(arg="_outer_ctx"),
                ],
                kw_defaults=[
                    ast.Constant(value=None),  # _caller=None
                    ast.Name(id="ctx", ctx=ast.Load()),  # _outer_ctx=ctx
                ],
                kwarg=None,
                defaults=defaults,
            ),
            body=func_body,
            decorator_list=[],
            returns=None,
        )

        # Assign to context: ctx['name'] = _def_name
        assign = ast.Assign(
            targets=[
                ast.Subscript(
                    value=ast.Name(id="ctx", ctx=ast.Load()),
                    slice=ast.Constant(value=def_name),
                    ctx=ast.Store(),
                )
            ],
            value=ast.Name(id=func_name, ctx=ast.Load()),
        )

        return [func_def, assign]

    def _compile_call_block(self, node: Any) -> list[ast.stmt]:
        """Compile {% call func(args) %}body{% endcall %.

        Calls a function with the body content as the caller.

        Generates:
            def _caller():
                buf = []
                ... body ...
                return Markup(''.join(buf))
            _append(func(args, _caller=_caller))
        """
        stmts: list[ast.stmt] = []

        # Create caller function
        caller_body: list[ast.stmt] = [
            # _e = _escape
            ast.Assign(
                targets=[ast.Name(id="_e", ctx=ast.Store())],
                value=ast.Name(id="_escape", ctx=ast.Load()),
            ),
            # _s = _str
            ast.Assign(
                targets=[ast.Name(id="_s", ctx=ast.Store())],
                value=ast.Name(id="_str", ctx=ast.Load()),
            ),
            # buf = []
            ast.Assign(
                targets=[ast.Name(id="buf", ctx=ast.Store())],
                value=ast.List(elts=[], ctx=ast.Load()),
            ),
            # _append = buf.append
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Attribute(
                    value=ast.Name(id="buf", ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
            ),
        ]

        # Compile body
        for child in node.body:
            caller_body.extend(self._compile_node(child))

        # return Markup(''.join(buf))
        caller_body.append(
            ast.Return(
                value=ast.Call(
                    func=ast.Name(id="_Markup", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Attribute(
                                value=ast.Constant(value=""),
                                attr="join",
                                ctx=ast.Load(),
                            ),
                            args=[ast.Name(id="buf", ctx=ast.Load())],
                            keywords=[],
                        ),
                    ],
                    keywords=[],
                ),
            )
        )

        # def _caller():
        caller_func = ast.FunctionDef(
            name="_caller",
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=caller_body,
            decorator_list=[],
            returns=None,
        )
        stmts.append(caller_func)

        # Compile the call expression and add _caller keyword argument
        call_expr = self._compile_expr(node.call)

        # If it's a function call, add _caller keyword
        if isinstance(call_expr, ast.Call):
            call_expr.keywords.append(
                ast.keyword(arg="_caller", value=ast.Name(id="_caller", ctx=ast.Load()))
            )
        else:
            # Wrap in a call with _caller
            call_expr = ast.Call(
                func=call_expr,
                args=[],
                keywords=[ast.keyword(arg="_caller", value=ast.Name(id="_caller", ctx=ast.Load()))],
            )

        # _append(result)
        stmts.append(
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_append", ctx=ast.Load()),
                    args=[call_expr],
                    keywords=[],
                ),
            )
        )

        return stmts

    def _compile_slot(self, node: Any) -> list[ast.stmt]:
        """Compile {% slot %.

        Renders the caller content inside a {% def %}.

        Generates:
            if ctx.get('caller'):
                _append(ctx['caller']())
        """
        return [
            ast.If(
                test=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="ctx", ctx=ast.Load()),
                        attr="get",
                        ctx=ast.Load(),
                    ),
                    args=[ast.Constant(value="caller")],
                    keywords=[],
                ),
                body=[
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Name(id="_append", ctx=ast.Load()),
                            args=[
                                ast.Call(
                                    func=ast.Subscript(
                                        value=ast.Name(id="ctx", ctx=ast.Load()),
                                        slice=ast.Constant(value="caller"),
                                        ctx=ast.Load(),
                                    ),
                                    args=[],
                                    keywords=[],
                                ),
                            ],
                            keywords=[],
                        ),
                    )
                ],
                orelse=[],
            )
        ]
