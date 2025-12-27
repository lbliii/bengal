"""Template structure statement compilation for Kida compiler.

Provides mixin for compiling template structure statements (block, include, from_import).
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class TemplateStructureMixin:
    """Mixin for compiling template structure statements.

    Required Host Attributes:
        - _compile_expr: method (from ExpressionCompilationMixin)
    """

    def _compile_block(self, node: Any) -> list[ast.stmt]:
        """Compile {% block name %} ... {% endblock %.

        Generates: _append(_blocks.get('name', _block_name)(ctx, _blocks))

        This allows child templates to override blocks by providing
        their own function in the _blocks dict.
        """
        block_name = node.name

        # _append(_blocks.get('name', _block_name)(ctx, _blocks))
        return [
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_append", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id="_blocks", ctx=ast.Load()),
                                    attr="get",
                                    ctx=ast.Load(),
                                ),
                                args=[
                                    ast.Constant(value=block_name),
                                    ast.Name(id=f"_block_{block_name}", ctx=ast.Load()),
                                ],
                                keywords=[],
                            ),
                            args=[
                                ast.Name(id="ctx", ctx=ast.Load()),
                                ast.Name(id="_blocks", ctx=ast.Load()),
                            ],
                            keywords=[],
                        ),
                    ],
                    keywords=[],
                ),
            )
        ]

    def _compile_include(self, node: Any) -> list[ast.stmt]:
        """Compile {% include "template.html" [with context] %.

        Generates: buf.append(_include(template_name, ctx))
        where _include is a helper function that loads and renders the template.
        """
        template_expr = self._compile_expr(node.template)

        # Build the _include call
        # _include(template_name, ctx if with_context else {}, ignore_missing)
        args = [template_expr]

        if node.with_context:
            # Pass current context
            args.append(ast.Name(id="ctx", ctx=ast.Load()))
        else:
            # Pass empty context
            args.append(ast.Dict(keys=[], values=[]))

        # Add ignore_missing flag
        args.append(ast.Constant(value=node.ignore_missing))

        include_call = ast.Call(
            func=ast.Name(id="_include", ctx=ast.Load()),
            args=args,
            keywords=[],
        )

        # Append the result to buffer
        return [
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_append", ctx=ast.Load()),
                    args=[include_call],
                    keywords=[],
                ),
            )
        ]

    def _compile_from_import(self, node: Any) -> list[ast.stmt]:
        """Compile {% from "template.html" import name1, name2 as alias %.

        Generates:
            _imported = _import_macros(template_name, with_context, ctx)
            ctx['name1'] = _imported['name1']
            ctx['alias'] = _imported['name2']
        """
        template_expr = self._compile_expr(node.template)

        stmts: list[ast.stmt] = []

        # _imported = _import_macros(template_name, with_context, ctx)
        stmts.append(
            ast.Assign(
                targets=[ast.Name(id="_imported", ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id="_import_macros", ctx=ast.Load()),
                    args=[
                        template_expr,
                        ast.Constant(value=node.with_context),
                        ast.Name(id="ctx", ctx=ast.Load()),
                    ],
                    keywords=[],
                ),
            )
        )

        # ctx['name'] = _imported['name'] for each imported name
        for name, alias in node.names:
            target_name = alias if alias else name
            stmts.append(
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=ast.Name(id="ctx", ctx=ast.Load()),
                            slice=ast.Constant(value=target_name),
                            ctx=ast.Store(),
                        )
                    ],
                    value=ast.Subscript(
                        value=ast.Name(id="_imported", ctx=ast.Load()),
                        slice=ast.Constant(value=name),
                        ctx=ast.Load(),
                    ),
                )
            )

        return stmts

    def _compile_import(self, node: Any) -> list[ast.stmt]:
        """Compile {% import "template.html" as f %.

        Generates: ctx['f'] = _import_macros(template_name, with_context, ctx)
        """
        template_expr = self._compile_expr(node.template)

        return [
            ast.Assign(
                targets=[
                    ast.Subscript(
                        value=ast.Name(id="ctx", ctx=ast.Load()),
                        slice=ast.Constant(value=node.target),
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Call(
                    func=ast.Name(id="_import_macros", ctx=ast.Load()),
                    args=[
                        template_expr,
                        ast.Constant(value=node.with_context),
                        ast.Name(id="ctx", ctx=ast.Load()),
                    ],
                    keywords=[],
                ),
            )
        ]
