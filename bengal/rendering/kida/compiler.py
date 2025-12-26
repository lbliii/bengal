"""Kida Compiler — AST-to-Python code generator.

The compiler transforms Kida AST nodes into Python AST,
then compiles to executable code objects.

Key Design:
    - AST-to-AST transformation (not string manipulation)
    - StringBuilder pattern in generated code
    - Compile-time filter binding
    - Native async generation for async templates

Complexity:
    - compile(): O(n) where n = AST nodes
    - _compile_node(): O(1) dispatch table lookup
    - _compile_expr(): O(d) where d = expression depth
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from bengal.rendering.kida.environment import Environment
    from bengal.rendering.kida.nodes import Template as TemplateNode


class Compiler:
    """Compile Kida AST to Python code.

    Example:
        >>> compiler = Compiler(env)
        >>> code = compiler.compile(kida_ast, "template.html")
        >>> exec(code, namespace)
    """

    __slots__ = ("_env", "_name", "_filename", "_node_dispatch", "_locals")

    def __init__(self, env: Environment):
        self._env = env
        self._name: str | None = None
        self._filename: str | None = None
        # Track local variables (loop variables, etc.) for O(1) direct access
        self._locals: set[str] = set()

    def compile(
        self,
        node: TemplateNode,
        name: str | None = None,
        filename: str | None = None,
    ) -> Any:
        """Compile template AST to code object.

        Args:
            node: Root Template node
            name: Template name for error messages
            filename: Source filename for error messages

        Returns:
            Compiled code object ready for exec()
        """
        self._name = name
        self._filename = filename
        self._locals = set()  # Reset locals for each compilation

        # Generate Python AST
        module = self._compile_template(node)

        # Fix missing locations for Python 3.8+
        ast.fix_missing_locations(module)

        # Compile to code object
        return compile(
            module,
            filename or "<template>",
            "exec",
        )

    def _compile_template(self, node: TemplateNode) -> ast.Module:
        """Generate Python module from template."""
        # Generate render function
        render_func = self._make_render_function(node)

        return ast.Module(
            body=[render_func],
            type_ignores=[],
        )

    def _make_render_function(self, node: TemplateNode) -> ast.FunctionDef:
        """Generate the render(ctx) function.
        
        Optimization: Cache global function references as locals for
        O(1) LOAD_FAST instead of O(1) LOAD_GLOBAL + hash lookup.
        """

        body: list[ast.stmt] = []

        # Local function cache for hot-path operations
        # _e = _escape; _s = _str; _a = buf.append
        # This reduces per-iteration overhead in loops
        body.append(
            ast.Assign(
                targets=[ast.Name(id="_e", ctx=ast.Store())],
                value=ast.Name(id="_escape", ctx=ast.Load()),
            )
        )
        body.append(
            ast.Assign(
                targets=[ast.Name(id="_s", ctx=ast.Store())],
                value=ast.Name(id="_str", ctx=ast.Load()),
            )
        )

        # buf = []
        body.append(
            ast.Assign(
                targets=[ast.Name(id="buf", ctx=ast.Store())],
                value=ast.List(elts=[], ctx=ast.Load()),
            )
        )
        
        # _append = buf.append (cache method lookup)
        body.append(
            ast.Assign(
                targets=[ast.Name(id="_append", ctx=ast.Store())],
                value=ast.Attribute(
                    value=ast.Name(id="buf", ctx=ast.Load()),
                    attr="append",
                    ctx=ast.Load(),
                ),
            )
        )

        # Compile template body
        for child in node.body:
            body.extend(self._compile_node(child))

        # return ''.join(buf)
        body.append(
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

        return ast.FunctionDef(
            name="render",
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="ctx")],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=body,
            decorator_list=[],
            returns=None,
        )

    def _compile_node(self, node: Any) -> list[ast.stmt]:
        """Compile a single AST node to Python statements.
        
        Complexity: O(1) type dispatch using class name lookup.
        """
        # Dispatch table - O(1) lookup instead of isinstance chain
        dispatch = self._get_node_dispatch()
        handler = dispatch.get(type(node).__name__)
        if handler:
            return handler(node)
        return []
    
    def _get_node_dispatch(self) -> dict[str, Callable]:
        """Get node type dispatch table (cached on first call)."""
        if not hasattr(self, "_node_dispatch"):
            self._node_dispatch = {
                "Data": self._compile_data,
                "Output": self._compile_output,
                "If": self._compile_if,
                "For": self._compile_for,
                "Set": self._compile_set,
                "Let": self._compile_set,
                "Export": self._compile_export,
            }
        return self._node_dispatch

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
        """
        expr = self._compile_expr(node.expr)

        # Wrap in escape if needed - use local cached functions
        if node.escape:
            expr = ast.Call(
                func=ast.Name(id="_e", ctx=ast.Load()),  # cached _escape
                args=[
                    ast.Call(
                        func=ast.Name(id="_s", ctx=ast.Load()),  # cached _str
                        args=[expr],
                        keywords=[],
                    )
                ],
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
        """Compile {% for %} loop.
        
        Optimization: Loop variables are tracked as locals and accessed
        directly (O(1) LOAD_FAST) instead of through ctx dict lookup.
        Context injection is skipped for pure local usage.
        """
        # Get the loop variable name(s) and register as locals
        var_names = self._extract_names(node.target)
        for var_name in var_names:
            self._locals.add(var_name)
        
        target = self._compile_expr(node.target, store=True)
        iter_expr = self._compile_expr(node.iter)
        
        body = []
        # NO context injection - use direct local access
        # This eliminates O(n) dict updates per loop iteration
        
        for child in node.body:
            body.extend(self._compile_node(child))
        if not body:
            body = [ast.Pass()]
        
        orelse = []
        for child in node.else_:
            orelse.extend(self._compile_node(child))
        
        # Remove loop variables from locals after the loop
        # (they're no longer accessible outside)
        for var_name in var_names:
            self._locals.discard(var_name)
        
        return [
            ast.For(
                target=target,
                iter=iter_expr,
                body=body,
                orelse=orelse,
            )
        ]
    
    def _extract_names(self, node: Any) -> list[str]:
        """Extract variable names from a target expression."""
        from bengal.rendering.kida.nodes import Name as KidaName, Tuple as KidaTuple
        
        if isinstance(node, KidaName):
            return [node.name]
        elif isinstance(node, KidaTuple):
            names = []
            for item in node.items:
                names.extend(self._extract_names(item))
            return names
        return []

    def _compile_set(self, node: Any) -> list[ast.stmt]:
        """Compile {% set %} or {% let %}."""
        value = self._compile_expr(node.value)
        
        # Assign to context: ctx['name'] = value
        return [
            ast.Assign(
                targets=[
                    ast.Subscript(
                        value=ast.Name(id="ctx", ctx=ast.Load()),
                        slice=ast.Constant(value=node.name),
                        ctx=ast.Store(),
                    )
                ],
                value=value,
            )
        ]

    def _compile_export(self, node: Any) -> list[ast.stmt]:
        """Compile {% export %}."""
        # For now, same as set - proper scoping in later version
        return self._compile_set(node)

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
            return ast.Subscript(
                value=ast.Name(id="ctx", ctx=ast.Load()),
                slice=ast.Constant(value=node.name),
                ctx=ast.Load(),
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
                    ast.keyword(arg=k, value=self._compile_expr(v))
                    for k, v in node.kwargs.items()
                ],
            )
            if node.negated:
                return ast.UnaryOp(op=ast.Not(), operand=test_call)
            return test_call
        
        if node_type == "Call":
            return ast.Call(
                func=self._compile_expr(node.func),
                args=[self._compile_expr(a) for a in node.args],
                keywords=[
                    ast.keyword(arg=k, value=self._compile_expr(v))
                    for k, v in node.kwargs.items()
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
                    ast.keyword(arg=k, value=self._compile_expr(v))
                    for k, v in node.kwargs.items()
                ],
            )
        
        if node_type == "BinOp":
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

    def _get_binop(self, op: str) -> ast.operator:
        """Map operator string to AST operator."""
        ops = {
            "+": ast.Add(),
            "-": ast.Sub(),
            "*": ast.Mult(),
            "/": ast.Div(),
            "//": ast.FloorDiv(),
            "%": ast.Mod(),
            "**": ast.Pow(),
        }
        return ops.get(op, ast.Add())

    def _get_unaryop(self, op: str) -> ast.unaryop:
        """Map unary operator string to AST operator."""
        ops = {
            "-": ast.USub(),
            "+": ast.UAdd(),
            "not": ast.Not(),
        }
        return ops.get(op, ast.Not())

    def _get_cmpop(self, op: str) -> ast.cmpop:
        """Map comparison operator string to AST operator."""
        ops = {
            "==": ast.Eq(),
            "!=": ast.NotEq(),
            "<": ast.Lt(),
            "<=": ast.LtE(),
            ">": ast.Gt(),
            ">=": ast.GtE(),
            "in": ast.In(),
            "not in": ast.NotIn(),
            "is": ast.Is(),
            "is not": ast.IsNot(),
        }
        return ops.get(op, ast.Eq())
