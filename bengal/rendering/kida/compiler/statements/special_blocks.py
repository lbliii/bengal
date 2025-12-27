"""Special block statement compilation for Kida compiler.

Provides mixin for compiling special block statements (with, do, raw, capture, cache, filter_block).
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class SpecialBlockMixin:
    """Mixin for compiling special block statements.

    Required Host Attributes:
        - _block_counter: int
        - _compile_expr: method (from ExpressionCompilationMixin)
        - _compile_node: method (from core)
    """

    def _compile_with(self, node: Any) -> list[ast.stmt]:
        """Compile {% with var=value, ... %}...{% endwith %.

        Creates temporary variable bindings scoped to the with block.
        We store old values and restore them after the block.
        """
        stmts: list[ast.stmt] = []

        # Save old values and set new ones
        old_var_names = []
        for name, value in node.targets:
            old_var_name = f"_with_save_{name}"
            old_var_names.append((name, old_var_name))

            # _with_save_name = ctx.get('name')
            stmts.append(
                ast.Assign(
                    targets=[ast.Name(id=old_var_name, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            attr="get",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Constant(value=name)],
                        keywords=[],
                    ),
                )
            )

            # ctx['name'] = value
            stmts.append(
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            slice=ast.Constant(value=name),
                            ctx=ast.Store(),
                        )
                    ],
                    value=self._compile_expr(value),
                )
            )

        # Compile body
        for child in node.body:
            stmts.extend(self._compile_node(child))

        # Restore old values
        for name, old_var_name in old_var_names:
            # if _with_save_name is None: del ctx['name']
            # else: ctx['name'] = _with_save_name
            stmts.append(
                ast.If(
                    test=ast.Compare(
                        left=ast.Name(id=old_var_name, ctx=ast.Load()),
                        ops=[ast.Is()],
                        comparators=[ast.Constant(value=None)],
                    ),
                    body=[
                        ast.Delete(
                            targets=[
                                ast.Subscript(
                                    value=ast.Name(id="ctx", ctx=ast.Load()),
                                    slice=ast.Constant(value=name),
                                    ctx=ast.Del(),
                                )
                            ]
                        )
                    ],
                    orelse=[
                        ast.Assign(
                            targets=[
                                ast.Subscript(
                                    value=ast.Name(id="ctx", ctx=ast.Load()),
                                    slice=ast.Constant(value=name),
                                    ctx=ast.Store(),
                                )
                            ],
                            value=ast.Name(id=old_var_name, ctx=ast.Load()),
                        )
                    ],
                )
            )

        return stmts

    def _compile_with_conditional(self, node: Any) -> list[ast.stmt]:
        """Compile {% with expr as target %}...{% end %} (conditional form).

        Renders body only if expr is truthy. Binds expr result to target.
        Supports multiple bindings and structural unpacking.
        Provides nil-resilience: block is silently skipped when expr is falsy.

        Generates:
            _with_val_N = expr
            if _with_val_N:
                # [save old values]
                # [bind new values]
                ... body ...
                # [restore old values]
        """
        # Get unique suffix for this block
        self._block_counter += 1
        suffix = str(self._block_counter)
        val_name = f"_with_val_{suffix}"

        stmts: list[ast.stmt] = []

        # _with_val_N = expr
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id=val_name, ctx=ast.Store())],
                value=self._compile_expr(node.expr),
            )
        )

        # Build the if body
        if_body: list[ast.stmt] = []

        # Use pattern matching logic for bindings
        # This handles both single names and tuples/unpacking
        from bengal.rendering.kida.nodes import Name as KidaName
        from bengal.rendering.kida.nodes import Tuple as KidaTuple

        # 1. Determine truthy check
        # If it's a tuple, we might want to check if all elements are truthy
        # for nil-resilience. But for now, let's stick to Python truthiness
        # of the whole expression result.
        test = ast.Name(id=val_name, ctx=ast.Load())

        # If it's an implicit tuple from multiple 'with' subjects,
        # we check if all elements are truthy for better nil-resilience.
        if isinstance(node.expr, KidaTuple):
            # val_N[0] and val_N[1] and ...
            truth_checks = []
            for i in range(len(node.expr.items)):
                truth_checks.append(
                    ast.Subscript(
                        value=ast.Name(id=val_name, ctx=ast.Load()),
                        slice=ast.Constant(value=i),
                        ctx=ast.Load(),
                    )
                )
            if len(truth_checks) > 1:
                test = ast.BoolOp(op=ast.And(), values=truth_checks)
            elif truth_checks:
                test = truth_checks[0]

        # 2. Track names and handle bindings
        bound_names = self._extract_names(node.target)
        save_restore_stmts: list[tuple[str, str]] = []

        for name in bound_names:
            old_var_name = f"_with_save_{name}_{suffix}"
            save_restore_stmts.append((name, old_var_name))

            # _with_save_name_N = ctx.get('name')
            if_body.append(
                ast.Assign(
                    targets=[ast.Name(id=old_var_name, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            attr="get",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Constant(value=name)],
                        keywords=[],
                    ),
                )
            )

        # 3. Bind new values
        if isinstance(node.target, KidaName):
            # ctx['name'] = _with_val_N
            if_body.append(
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            slice=ast.Constant(value=node.target.name),
                            ctx=ast.Store(),
                        )
                    ],
                    value=ast.Name(id=val_name, ctx=ast.Load()),
                )
            )
        elif isinstance(node.target, KidaTuple):
            # Unpack: ctx['x'], ctx['y'] = _with_val_N
            targets = []
            for item in node.target.items:
                if isinstance(item, KidaName):
                    targets.append(
                        ast.Subscript(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            slice=ast.Constant(value=item.name),
                            ctx=ast.Store(),
                        )
                    )
                else:
                    # Nested tuples not supported in 'with' target yet, but could be
                    pass

            if targets:
                if_body.append(
                    ast.Assign(
                        targets=[ast.Tuple(elts=targets, ctx=ast.Store())],
                        value=ast.Name(id=val_name, ctx=ast.Load()),
                    )
                )

        # 4. Compile body
        for child in node.body:
            if_body.extend(self._compile_node(child))

        # 5. Restore old values
        for name, old_var_name in reversed(save_restore_stmts):
            # if _with_save_name_N is None: del ctx['name']
            # else: ctx['name'] = _with_save_name_N
            if_body.append(
                ast.If(
                    test=ast.Compare(
                        left=ast.Name(id=old_var_name, ctx=ast.Load()),
                        ops=[ast.Is()],
                        comparators=[ast.Constant(value=None)],
                    ),
                    body=[
                        ast.Delete(
                            targets=[
                                ast.Subscript(
                                    value=ast.Name(id="ctx", ctx=ast.Load()),
                                    slice=ast.Constant(value=name),
                                    ctx=ast.Del(),
                                )
                            ]
                        )
                    ],
                    orelse=[
                        ast.Assign(
                            targets=[
                                ast.Subscript(
                                    value=ast.Name(id="ctx", ctx=ast.Load()),
                                    slice=ast.Constant(value=name),
                                    ctx=ast.Store(),
                                )
                            ],
                            value=ast.Name(id=old_var_name, ctx=ast.Load()),
                        )
                    ],
                )
            )

        # 6. Build final If node
        stmts.append(
            ast.If(
                test=test,
                body=if_body,
                orelse=[],
            )
        )

        return stmts

    def _compile_do(self, node: Any) -> list[ast.stmt]:
        """Compile {% do expr %.

        Expression statement for side effects - just evaluate the expression
        and discard the result.
        """
        expr = self._compile_expr(node.expr)
        return [ast.Expr(value=expr)]

    def _compile_raw(self, node: Any) -> list[ast.stmt]:
        """Compile {% raw %}...{% endraw %.

        Raw block content is output as literal text.
        """
        if not node.value:
            return []

        return [
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_append", ctx=ast.Load()),
                    args=[ast.Constant(value=node.value)],
                    keywords=[],
                ),
            )
        ]

    def _compile_capture(self, node: Any) -> list[ast.stmt]:
        """Compile {% capture x %}...{% end %} (Kida) or {% set x %}...{% endset %} (Jinja).

        Captures rendered block content into a variable.
        """
        # Create a temporary buffer
        stmts: list[ast.stmt] = [
            # _capture_buf = []
            ast.Assign(
                targets=[ast.Name(id="_capture_buf", ctx=ast.Store())],
                value=ast.List(elts=[], ctx=ast.Load()),
            ),
            # _capture_append = _capture_buf.append
            ast.Assign(
                targets=[ast.Name(id="_capture_append", ctx=ast.Store())],
                value=ast.Attribute(
                    value=ast.Name(id="_capture_buf", ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
            ),
            # _save_append = _append
            ast.Assign(
                targets=[ast.Name(id="_save_append", ctx=ast.Store())],
                value=ast.Name(id="_append", ctx=ast.Load()),
            ),
            # _append = _capture_append
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Name(id="_capture_append", ctx=ast.Load()),
            ),
        ]

        # Compile body
        for child in node.body:
            stmts.extend(self._compile_node(child))

        # Restore original append and assign result
        stmts.extend(
            [
                # _append = _save_append
                ast.Assign(
                    targets=[ast.Name(id="_append", ctx=ast.Store())],
                    value=ast.Name(id="_save_append", ctx=ast.Load()),
                ),
                # ctx['name'] = ''.join(_capture_buf)
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            slice=ast.Constant(value=node.name),
                            ctx=ast.Store(),
                        )
                    ],
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Constant(value=""),
                            attr="join",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Name(id="_capture_buf", ctx=ast.Load())],
                        keywords=[],
                    ),
                ),
            ]
        )

        return stmts

    def _compile_cache(self, node: Any) -> list[ast.stmt]:
        """Compile {% cache key %}...{% endcache %.

        Fragment caching for expensive template sections.

        Generates:
            _cache_key = str(key)
            _cached = _cache_get(_cache_key)
            if _cached is not None:
                _append(_cached)
            else:
                _cache_buf = []
                _cache_append = _cache_buf.append
                _save_append = _append
                _append = _cache_append
                ... body ...
                _append = _save_append
                _cached = ''.join(_cache_buf)
                _cache_set(_cache_key, _cached, ttl)
                _append(_cached)
        """
        stmts: list[ast.stmt] = []

        # _cache_key = str(key)
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id="_cache_key", ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id="_str", ctx=ast.Load()),
                    args=[self._compile_expr(node.key)],
                    keywords=[],
                ),
            )
        )

        # _cached = _cache_get(_cache_key)
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id="_cached", ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id="_cache_get", ctx=ast.Load()),
                    args=[ast.Name(id="_cache_key", ctx=ast.Load())],
                    keywords=[],
                ),
            )
        )

        # Build the else block (cache miss)
        else_body: list[ast.stmt] = [
            # _cache_buf = []
            ast.Assign(
                targets=[ast.Name(id="_cache_buf", ctx=ast.Store())],
                value=ast.List(elts=[], ctx=ast.Load()),
            ),
            # _cache_append = _cache_buf.append
            ast.Assign(
                targets=[ast.Name(id="_cache_append", ctx=ast.Store())],
                value=ast.Attribute(
                    value=ast.Name(id="_cache_buf", ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
            ),
            # _save_append = _append
            ast.Assign(
                targets=[ast.Name(id="_save_append", ctx=ast.Store())],
                value=ast.Name(id="_append", ctx=ast.Load()),
            ),
            # _append = _cache_append
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Name(id="_cache_append", ctx=ast.Load()),
            ),
        ]

        # Compile body
        for child in node.body:
            else_body.extend(self._compile_node(child))

        # _append = _save_append
        else_body.append(
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Name(id="_save_append", ctx=ast.Load()),
            )
        )

        # _cached = ''.join(_cache_buf)
        else_body.append(
            ast.Assign(
                targets=[ast.Name(id="_cached", ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Constant(value=""),
                        attr="join",
                        ctx=ast.Load(),
                    ),
                    args=[ast.Name(id="_cache_buf", ctx=ast.Load())],
                    keywords=[],
                ),
            )
        )

        # _cache_set(_cache_key, _cached, ttl)
        cache_set_args = [
            ast.Name(id="_cache_key", ctx=ast.Load()),
            ast.Name(id="_cached", ctx=ast.Load()),
        ]
        if node.ttl:
            cache_set_args.append(self._compile_expr(node.ttl))
        else:
            cache_set_args.append(ast.Constant(value=None))

        else_body.append(
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_cache_set", ctx=ast.Load()),
                    args=cache_set_args,
                    keywords=[],
                ),
            )
        )

        # _append(_cached)
        else_body.append(
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_append", ctx=ast.Load()),
                    args=[ast.Name(id="_cached", ctx=ast.Load())],
                    keywords=[],
                ),
            )
        )

        # if _cached is not None: _append(_cached) else: ...
        stmts.append(
            ast.If(
                test=ast.Compare(
                    left=ast.Name(id="_cached", ctx=ast.Load()),
                    ops=[ast.IsNot()],
                    comparators=[ast.Constant(value=None)],
                ),
                body=[
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Name(id="_append", ctx=ast.Load()),
                            args=[ast.Name(id="_cached", ctx=ast.Load())],
                            keywords=[],
                        ),
                    )
                ],
                orelse=else_body,
            )
        )

        return stmts

    def _compile_filter_block(self, node: Any) -> list[ast.stmt]:
        """Compile {% filter name %}...{% endfilter %.

        Apply a filter to an entire block of content.

        Uses unique variable names to support nesting.

        Generates:
            _filter_buf_N = []
            _filter_append_N = _filter_buf_N.append
            _save_append_N = _append
            _append = _filter_append_N
            ... body ...
            _append = _save_append_N
            _append(_filters['name'](''.join(_filter_buf_N), *args, **kwargs))
        """
        # Get unique suffix for this filter block
        self._block_counter += 1
        suffix = str(self._block_counter)
        buf_name = f"_filter_buf_{suffix}"
        append_name = f"_filter_append_{suffix}"
        save_name = f"_save_append_{suffix}"

        stmts: list[ast.stmt] = [
            # _filter_buf_N = []
            ast.Assign(
                targets=[ast.Name(id=buf_name, ctx=ast.Store())],
                value=ast.List(elts=[], ctx=ast.Load()),
            ),
            # _filter_append_N = _filter_buf_N.append
            ast.Assign(
                targets=[ast.Name(id=append_name, ctx=ast.Store())],
                value=ast.Attribute(
                    value=ast.Name(id=buf_name, ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
            ),
            # _save_append_N = _append
            ast.Assign(
                targets=[ast.Name(id=save_name, ctx=ast.Store())],
                value=ast.Name(id="_append", ctx=ast.Load()),
            ),
            # _append = _filter_append_N
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Name(id=append_name, ctx=ast.Load()),
            ),
        ]

        # Compile body
        for child in node.body:
            stmts.extend(self._compile_node(child))

        # _append = _save_append_N
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Name(id=save_name, ctx=ast.Load()),
            )
        )

        # Build filter call: _filters['name'](''.join(_filter_buf_N), *args, **kwargs)
        filter_args = [
            ast.Call(
                func=ast.Attribute(
                    value=ast.Constant(value=""),
                    attr="join",
                    ctx=ast.Load(),
                ),
                args=[ast.Name(id=buf_name, ctx=ast.Load())],
                keywords=[],
            )
        ]

        # Add filter arguments from the Filter node
        filter_node = node.filter
        filter_args.extend([self._compile_expr(a) for a in filter_node.args])
        filter_kwargs = [
            ast.keyword(arg=k, value=self._compile_expr(v)) for k, v in filter_node.kwargs.items()
        ]

        # _append(_filters['name'](content, *args, **kwargs))
        stmts.append(
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_append", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Subscript(
                                value=ast.Name(id="_filters", ctx=ast.Load()),
                                slice=ast.Constant(value=filter_node.name),
                                ctx=ast.Load(),
                            ),
                            args=filter_args,
                            keywords=filter_kwargs,
                        ),
                    ],
                    keywords=[],
                ),
            )
        )

        return stmts

    def _compile_spaceless(self, node: Any) -> list[ast.stmt]:
        """Compile {% spaceless %}...{% end %}.

        Removes whitespace between HTML tags.
        Part of RFC: kida-modern-syntax-features.

        Generates:
            _spaceless_buf_N = []
            _spaceless_append_N = _spaceless_buf_N.append
            _save_append_N = _append
            _append = _spaceless_append_N
            ... body ...
            _append = _save_append_N
            _append(_spaceless(''.join(_spaceless_buf_N)))
        """
        # Get unique suffix for this spaceless block
        self._block_counter += 1
        suffix = str(self._block_counter)
        buf_name = f"_spaceless_buf_{suffix}"
        append_name = f"_spaceless_append_{suffix}"
        save_name = f"_save_append_{suffix}"

        stmts: list[ast.stmt] = [
            # _spaceless_buf_N = []
            ast.Assign(
                targets=[ast.Name(id=buf_name, ctx=ast.Store())],
                value=ast.List(elts=[], ctx=ast.Load()),
            ),
            # _spaceless_append_N = _spaceless_buf_N.append
            ast.Assign(
                targets=[ast.Name(id=append_name, ctx=ast.Store())],
                value=ast.Attribute(
                    value=ast.Name(id=buf_name, ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
            ),
            # _save_append_N = _append
            ast.Assign(
                targets=[ast.Name(id=save_name, ctx=ast.Store())],
                value=ast.Name(id="_append", ctx=ast.Load()),
            ),
            # _append = _spaceless_append_N
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Name(id=append_name, ctx=ast.Load()),
            ),
        ]

        # Compile body
        for child in node.body:
            stmts.extend(self._compile_node(child))

        # _append = _save_append_N
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Name(id=save_name, ctx=ast.Load()),
            )
        )

        # _append(_spaceless(''.join(_spaceless_buf_N)))
        stmts.append(
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_append", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Name(id="_spaceless", ctx=ast.Load()),
                            args=[
                                ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Constant(value=""),
                                        attr="join",
                                        ctx=ast.Load(),
                                    ),
                                    args=[ast.Name(id=buf_name, ctx=ast.Load())],
                                    keywords=[],
                                ),
                            ],
                            keywords=[],
                        ),
                    ],
                    keywords=[],
                ),
            )
        )

        return stmts

    def _compile_embed(self, node: Any) -> list[ast.stmt]:
        """Compile {% embed 'template.html' %}...{% end %}.

        Embed is like include but allows block overrides.
        Part of RFC: kida-modern-syntax-features.

        Generates:
            _saved_blocks_N = _blocks.copy()
            def _block_name(ctx, _blocks): ...  # For each override
            _blocks['name'] = _block_name
            _append(_include(template, ctx, _blocks))
            _blocks = _saved_blocks_N
        """
        # Get unique suffix for this embed
        self._block_counter += 1
        suffix = str(self._block_counter)
        saved_blocks_name = f"_saved_blocks_{suffix}"

        stmts: list[ast.stmt] = []

        # _saved_blocks_N = _blocks.copy()
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id=saved_blocks_name, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="_blocks", ctx=ast.Load()),
                        attr="copy",
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[],
                ),
            )
        )

        # Create block override functions
        for name, block in node.blocks.items():
            block_func_name = f"_block_{name}_{suffix}"

            # Build block function body
            block_body: list[ast.stmt] = [
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

            # Compile block body
            for child in block.body:
                block_body.extend(self._compile_node(child))

            # return ''.join(buf)
            block_body.append(
                ast.Return(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Constant(value=""),
                            attr="join",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Name(id="buf", ctx=ast.Load())],
                        keywords=[],
                    ),
                )
            )

            # def _block_name_N(ctx, _blocks): ...
            stmts.append(
                ast.FunctionDef(
                    name=block_func_name,
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[ast.arg(arg="ctx"), ast.arg(arg="_blocks")],
                        vararg=None,
                        kwonlyargs=[],
                        kw_defaults=[],
                        kwarg=None,
                        defaults=[],
                    ),
                    body=block_body,
                    decorator_list=[],
                    returns=None,
                )
            )

            # _blocks['name'] = _block_name_N
            stmts.append(
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=ast.Name(id="_blocks", ctx=ast.Load()),
                            slice=ast.Constant(value=name),
                            ctx=ast.Store(),
                        )
                    ],
                    value=ast.Name(id=block_func_name, ctx=ast.Load()),
                )
            )

        # Include the embedded template: _append(_include(template, ctx, blocks=_blocks))
        stmts.append(
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_append", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Name(id="_include", ctx=ast.Load()),
                            args=[
                                self._compile_expr(node.template),
                                ast.Name(id="ctx", ctx=ast.Load()),
                            ],
                            keywords=[
                                ast.keyword(
                                    arg="blocks",
                                    value=ast.Name(id="_blocks", ctx=ast.Load()),
                                ),
                            ],
                        ),
                    ],
                    keywords=[],
                ),
            )
        )

        # _blocks = _saved_blocks_N
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id="_blocks", ctx=ast.Store())],
                value=ast.Name(id=saved_blocks_name, ctx=ast.Load()),
            )
        )

        return stmts
