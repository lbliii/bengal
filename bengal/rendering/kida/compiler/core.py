"""Kida Compiler Core — main Compiler class.

The Compiler transforms Kida AST into Python AST, then compiles to
executable code objects. Uses a mixin-based design for maintainability.

Design Principles:
    1. **AST-to-AST**: Generate `ast.Module`, not source strings
    2. **StringBuilder**: Output via `buf.append()`, join at end
    3. **Local caching**: Cache `_escape`, `_str`, `buf.append` as locals
    4. **O(1) dispatch**: Dict-based node type → handler lookup

Performance Optimizations:
    - `LOAD_FAST` for cached functions (vs `LOAD_GLOBAL` + hash)
    - Method lookup cached once: `_append = buf.append`
    - Single `''.join(buf)` at return (vs repeated concatenation)
    - Line markers only for error-prone nodes (Output, For, If, etc.)

Block Inheritance:
    Templates with `{% extends %}` generate:
    1. Block functions: `_block_header(ctx, _blocks)`
    2. Render function: Registers blocks, delegates to parent

    ```python
    def _block_header(ctx, _blocks):
        buf = []
        # Block body...
        return ''.join(buf)

    def render(ctx, _blocks=None):
        if _blocks is None: _blocks = {}
        _blocks.setdefault('header', _block_header)
        return _extends('base.html', ctx, _blocks)
    ```
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from bengal.rendering.kida.compiler.expressions import ExpressionCompilationMixin
from bengal.rendering.kida.compiler.statements import StatementCompilationMixin
from bengal.rendering.kida.compiler.utils import OperatorUtilsMixin

if TYPE_CHECKING:
    from bengal.rendering.kida.environment import Environment
    from bengal.rendering.kida.nodes import Template as TemplateNode


class Compiler(
    OperatorUtilsMixin,
    ExpressionCompilationMixin,
    StatementCompilationMixin,
):
    """Compile Kida AST to Python code objects.

    The Compiler transforms a Kida Template AST into an `ast.Module`, then
    compiles it to a code object ready for `exec()`. The generated code
    defines a `render(ctx, _blocks=None)` function.

    Attributes:
        _env: Parent Environment (for filter/test access)
        _name: Template name for error messages
        _filename: Source file path for compile()
        _locals: Set of local variable names (loop vars, macro args)
        _blocks: Dict of block_name → Block node (for inheritance)
        _block_counter: Counter for unique variable names

    Node Dispatch:
        Uses O(1) dict lookup for node type → handler:
        ```python
        dispatch = {
            "Data": self._compile_data,
            "Output": self._compile_output,
            "If": self._compile_if,
            ...
        }
        handler = dispatch[type(node).__name__]
        ```

    Line Tracking:
        For nodes that can cause runtime errors (Output, For, If, etc.),
        injects `ctx['_line'] = N` before the node's code. This enables
        rich error messages with source line numbers.

    Example:
        >>> from bengal.rendering.kida import Environment
        >>> from bengal.rendering.kida.compiler import Compiler
        >>> from bengal.rendering.kida.parser import Parser
        >>> from bengal.rendering.kida.lexer import tokenize
        >>>
        >>> env = Environment()
        >>> tokens = tokenize("Hello, {{ name }}!")
        >>> parser = Parser(tokens)
        >>> ast = parser.parse()
        >>> compiler = Compiler(env)
        >>> code = compiler.compile(ast, name="greeting.html")
        >>>
        >>> namespace = {"_escape": str, "_str": str, ...}
        >>> exec(code, namespace)
        >>> namespace["render"]({"name": "World"})
        'Hello, World!'
    """

    __slots__ = (
        "_env",
        "_name",
        "_filename",
        "_node_dispatch",
        "_locals",
        "_blocks",
        "_block_counter",
    )

    def __init__(self, env: Environment):
        self._env = env
        self._name: str | None = None
        self._filename: str | None = None
        # Track local variables (loop variables, etc.) for O(1) direct access
        self._locals: set[str] = set()
        # Track blocks for inheritance
        self._blocks: dict[str, Any] = {}
        # Counter for unique variable names in nested structures
        self._block_counter: int = 0

    def _collect_blocks(self, nodes: Any) -> None:
        """Recursively collect all Block nodes from the AST.

        This ensures nested blocks (blocks inside blocks, blocks inside
        conditionals, etc.) are all registered for compilation.
        """
        for node in nodes:
            node_type = type(node).__name__

            if node_type == "Block":
                self._blocks[node.name] = node
                # Recurse into block body to find nested blocks
                self._collect_blocks(node.body)
            elif hasattr(node, "body"):
                # Node has a body (If, For, With, Macro, etc.)
                self._collect_blocks(node.body)
                # Check for else/elif bodies
                if hasattr(node, "else_") and node.else_:
                    self._collect_blocks(node.else_)
                if hasattr(node, "empty") and node.empty:
                    self._collect_blocks(node.empty)
                if hasattr(node, "elif_") and node.elif_:
                    for _, elif_body in node.elif_:
                        self._collect_blocks(elif_body)

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
        self._block_counter = 0  # Reset counter for each compilation

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
        # Generate render function (also populates self._blocks)
        render_func = self._make_render_function(node)

        module_body: list[ast.stmt] = []

        # Generate block functions
        for block_name, block_node in self._blocks.items():
            block_func = self._make_block_function(block_name, block_node)
            module_body.append(block_func)

        # Add render function
        module_body.append(render_func)

        return ast.Module(
            body=module_body,
            type_ignores=[],
        )

    def _make_block_function(self, name: str, block_node: Any) -> ast.FunctionDef:
        """Generate a block function: _block_name(ctx, _blocks) -> str."""
        body: list[ast.stmt] = [
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
        for child in block_node.body:
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
            name=f"_block_{name}",
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="ctx"), ast.arg(arg="_blocks")],
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

    def _make_render_function(self, node: TemplateNode) -> ast.FunctionDef:
        """Generate the render(ctx, _blocks=None) function.

        Optimization: Cache global function references as locals for
        O(1) LOAD_FAST instead of O(1) LOAD_GLOBAL + hash lookup.

        For templates with extends:
            def render(ctx, _blocks=None):
                if _blocks is None: _blocks = {}
                # Register child blocks
                _blocks.setdefault('name', _block_name)
                # Render parent with blocks
                return _extends('parent.html', ctx, _blocks)
        """
        # Reset blocks dict for this compilation
        self._blocks = {}

        # First pass: recursively collect ALL blocks (including nested) and find extends
        extends_node = None
        self._collect_blocks(node.body)
        for child in node.body:
            if type(child).__name__ == "Extends":
                extends_node = child
                break

        body: list[ast.stmt] = []

        # Initialize _blocks parameter: if _blocks is None: _blocks = {}
        body.append(
            ast.If(
                test=ast.Compare(
                    left=ast.Name(id="_blocks", ctx=ast.Load()),
                    ops=[ast.Is()],
                    comparators=[ast.Constant(value=None)],
                ),
                body=[
                    ast.Assign(
                        targets=[ast.Name(id="_blocks", ctx=ast.Store())],
                        value=ast.Dict(keys=[], values=[]),
                    )
                ],
                orelse=[],
            )
        )

        if extends_node:
            # Template with inheritance - collect blocks and delegate to parent

            # First, execute top-level statements that modify context (imports, sets, etc.)
            # These need to run before blocks are called so imported macros are available.
            # We compile FromImport, Import, Set, Macro, and Def nodes at the top level.
            for child in node.body:
                child_type = type(child).__name__
                if child_type in ("FromImport", "Set", "Macro", "Def"):
                    body.extend(self._compile_node(child))

            # For each block: _blocks.setdefault('name', block_func)
            # Block functions are added to module namespace during compilation
            for block_name in self._blocks:
                body.append(
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id="_blocks", ctx=ast.Load()),
                                attr="setdefault",
                                ctx=ast.Load(),
                            ),
                            args=[
                                ast.Constant(value=block_name),
                                ast.Name(id=f"_block_{block_name}", ctx=ast.Load()),
                            ],
                            keywords=[],
                        ),
                    )
                )

            # return _extends('parent.html', ctx, _blocks)
            body.append(
                ast.Return(
                    value=ast.Call(
                        func=ast.Name(id="_extends", ctx=ast.Load()),
                        args=[
                            self._compile_expr(extends_node.template),
                            ast.Name(id="ctx", ctx=ast.Load()),
                            ast.Name(id="_blocks", ctx=ast.Load()),
                        ],
                        keywords=[],
                    ),
                )
            )
        else:
            # No inheritance - render directly
            # Local function cache for hot-path operations
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
                args=[ast.arg(arg="ctx"), ast.arg(arg="_blocks")],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[ast.Constant(value=None)],  # _blocks=None
            ),
            body=body,
            decorator_list=[],
            returns=None,
        )

    # Node types that can cause runtime errors and should track line numbers
    _LINE_TRACKED_NODES = frozenset(
        {
            "Output",  # Expression evaluation
            "For",  # Iterator access, filter application
            "If",  # Boolean coercion, attribute access
            "Match",  # Pattern matching
            "Set",  # Expression evaluation
            "Let",  # Expression evaluation
            "CallBlock",  # Function calls
            "Do",  # Side-effect expressions
        }
    )

    def _make_line_marker(self, lineno: int) -> ast.stmt:
        """Generate ctx['_line'] = lineno statement for error tracking."""
        return ast.Assign(
            targets=[
                ast.Subscript(
                    value=ast.Name(id="ctx", ctx=ast.Load()),
                    slice=ast.Constant(value="_line"),
                    ctx=ast.Store(),
                )
            ],
            value=ast.Constant(value=lineno),
        )

    def _compile_node(self, node: Any) -> list[ast.stmt]:
        """Compile a single AST node to Python statements.

        Complexity: O(1) type dispatch using class name lookup.

        For nodes that can cause runtime errors, injects a line marker
        statement (ctx['_line'] = N) before the node's code. This enables
        rich error messages with source line numbers.
        """
        node_type = type(node).__name__

        # Inject line marker for risky nodes (only if they have lineno)
        stmts: list[ast.stmt] = []
        if node_type in self._LINE_TRACKED_NODES and hasattr(node, "lineno"):
            stmts.append(self._make_line_marker(node.lineno))

        # Dispatch table - O(1) lookup instead of isinstance chain
        dispatch = self._get_node_dispatch()
        handler = dispatch.get(node_type)
        if handler:
            stmts.extend(handler(node))

        return stmts

    def _get_node_dispatch(self) -> dict[str, Callable]:
        """Get node type dispatch table (cached on first call)."""
        if not hasattr(self, "_node_dispatch"):
            self._node_dispatch = {
                "Data": self._compile_data,
                "Output": self._compile_output,
                "If": self._compile_if,
                "For": self._compile_for,
                "Match": self._compile_match,
                "Set": self._compile_set,
                "Let": self._compile_let,
                "Export": self._compile_export,
                "Include": self._compile_include,
                "Block": self._compile_block,
                "Macro": self._compile_macro,
                "Def": self._compile_def,
                "CallBlock": self._compile_call_block,
                "Slot": self._compile_slot,
                "FromImport": self._compile_from_import,
                "With": self._compile_with,
                "WithHugo": self._compile_with_hugo,
                "Do": self._compile_do,
                "Raw": self._compile_raw,
                "Capture": self._compile_capture,
                "Cache": self._compile_cache,
                "FilterBlock": self._compile_filter_block,
                # RFC: kida-modern-syntax-features
                "Break": self._compile_break,
                "Continue": self._compile_continue,
                "Spaceless": self._compile_spaceless,
                "Embed": self._compile_embed,
            }
        return self._node_dispatch
