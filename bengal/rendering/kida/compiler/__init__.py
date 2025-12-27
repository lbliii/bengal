"""Kida Compiler — transforms Kida AST into executable Python code.

The compiler takes an immutable Kida AST (Template node) and generates a
Python `ast.Module` containing a `render(ctx, _blocks=None)` function.
This is then compiled to a code object via `compile()`.

Architecture:
    Kida AST → Python AST → Code Object

    Unlike Jinja2 which generates Python source strings, Kida generates
    `ast.Module` objects directly. This enables:
    - Structured manipulation (no regex, no string parsing)
    - Compile-time optimizations (constant folding, dead code elimination)
    - Precise source mapping for error messages
    - No eval() security concerns

Generated Code Pattern:
    ```python
    def render(ctx, _blocks=None):
        if _blocks is None: _blocks = {}
        _e = _escape          # Cache for LOAD_FAST
        _s = _str
        buf = []
        _append = buf.append  # Cached method lookup

        # Template body...
        _append("Hello, ")
        _append(_e(_s(ctx.get("name", ""))))

        return ''.join(buf)
    ```

Mixin Architecture:
    - `OperatorUtilsMixin`: Binary/unary operator AST generation
    - `ExpressionCompilationMixin`: Expressions, filters, tests, function calls
    - `StatementCompilationMixin`: Control flow, blocks, macros, includes

Thread-Safety:
    Compiler instances are single-use and not thread-safe. Create one per
    compilation. The resulting code object is immutable and thread-safe.

Public API:
    Compiler: Main compiler class combining all compilation mixins
"""

from __future__ import annotations

from bengal.rendering.kida.compiler.core import Compiler

__all__ = [
    "Compiler",
]
