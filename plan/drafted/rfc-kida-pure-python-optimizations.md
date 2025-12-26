# RFC: Kida Pure Python Optimization Pass

**Status**: Draft  
**Created**: 2025-12-26  
**Revised**: 2025-12-26 (v1.1)  
**Priority**: Medium  
**Effort**: ~19 hours (~2.5 days)  
**Impact**: High - 10-30% faster template rendering, zero cold-start on warm cache  
**Category**: Compiler / Optimization / Performance  
**Scope**: `bengal/rendering/kida/`  
**Dependencies**: None (pure Python, no external packages)

---

## Executive Summary

This RFC proposes an **AST optimization pass** for Kida that operates entirely in pure Python with zero external dependencies. By analyzing and transforming the Kida AST before compilation to Python AST, we can achieve significant performance improvements without requiring Rust extensions or C modules.

**Key Insight**: Kida's AST-to-AST architecture (unique among Python template engines) makes sophisticated compile-time optimizations possible. Jinja2 generates Python source strings — Kida generates `ast.Module` objects directly, enabling structured manipulation.

**Proposed Optimizations**:

| Optimization | Phase | Effort | Impact | Complexity |
|--------------|-------|--------|--------|------------|
| Constant Folding | Compile | 4h | 5-15% | Low |
| Dead Code Elimination | Compile | 3h | 10-30% | Low |
| Static Data Coalescing | Compile | 2h | 5-10% | Low |
| Filter Inlining | Compile | 4h | 5-10% | Medium |
| Buffer Pre-allocation | Runtime | 2h | 5-10% | Low |
| Template Bytecode Cache | Startup | 4h | **90%+ cold-start** | Low |

> **Note**: Expression Deduplication (5h, 10-20% impact) deferred to Phase 2 RFC due to complexity of tracking expression identity across scopes.

**Total Effort**: ~19 hours (~2.5 days)

**Key Deliverables**:
1. `ASTOptimizer` class with pluggable optimization passes and stats tracking
2. `BytecodeCache` for persistent compiled template storage (version-aware)
3. `InlinedFilter` node type for direct method call generation
4. `OptimizationStats` for debugging and observability
5. Integration with existing `Environment.optimized` flag
6. Comprehensive test coverage (>90%) for each optimization

---

## Motivation

### Current State

Kida is already **5.6x faster** than Jinja2 (geometric mean 4.4x) due to:
- StringBuilder pattern (vs generator yields)
- LOAD_FAST caching (_e, _s, _append)
- O(1) dispatch tables
- Single-pass HTML escaping

However, the `COMPLEXITY.md` optimization checklist identifies gaps:

```markdown
### Compiler
- [x] Dispatch table for node types O(1)
- [x] AST-to-AST (no string manipulation)
- [x] Compile-time filter binding
- [ ] Constant folding optimization pass  ← THIS RFC

### Runtime
- [x] Single-pass HTML escape
- [ ] Pre-allocate buffer based on template size estimate  ← THIS RFC
```

### Why Pure Python?

1. **Zero deployment friction**: No compilation, no binary wheels, no platform issues
2. **Inspectable**: Users can debug and understand optimizations
3. **Modular**: Each optimization is independent and toggleable
4. **Maintainable**: Same language as rest of codebase
5. **Portable**: Works everywhere Python works (including PyPy, GraalPy)

### Impact by Use Case

| Use Case | Current Pain | After Optimization |
|----------|--------------|-------------------|
| **Serverless (Lambda)** | Cold-start recompilation | Bytecode cache eliminates |
| **Dev server** | Repeated recompilation | Faster iteration |
| **Large sites (1000+ pages)** | CPU-bound rendering | 10-30% faster |
| **Math-heavy templates** | Runtime evaluation | Constant folding |
| **Debug templates** | `{% if DEBUG %}` overhead | Dead code elimination |

---

## Design

### Architecture

```
Template Source
      ↓
   Lexer (existing)
      ↓
   Parser (existing)
      ↓
  Kida AST
      ↓
┌─────────────────────────────────┐
│     ASTOptimizer (NEW)          │
│  ├── ConstantFolder             │
│  ├── DeadCodeEliminator         │
│  ├── DataCoalescer              │
│  ├── FilterInliner              │
│  └── BufferEstimator            │
└─────────────────────────────────┘
      ↓
  Optimized Kida AST
      ↓
   Compiler (existing)
      ↓
  Python AST
      ↓
  compile() → code object
      ↓
┌─────────────────────────────────┐
│   BytecodeCache (NEW)           │
│   Persists code objects to disk │
└─────────────────────────────────┘
      ↓
   Template
```

### Design Principles

1. **Non-destructive**: Create new AST nodes, never mutate existing
2. **Composable**: Each pass is independent, order doesn't matter (mostly)
3. **Safe**: Never change observable behavior
4. **Traceable**: Log what optimizations were applied (debug mode)
5. **Toggleable**: Each optimization can be disabled individually

---

## Optimization 1: Constant Folding

### Problem

Expressions with only constant operands are evaluated at runtime:

```jinja
{{ 60 * 60 * 24 }}         {# Computed every render #}
{{ "Hello" ~ " " ~ "World" }}  {# String concat every render #}
{% if 1 + 1 == 2 %}...{% end %}  {# Always true, still evaluated #}
```

### Solution

Evaluate constant expressions at compile time:

```jinja
{{ 86400 }}           {# Pre-computed #}
{{ "Hello World" }}   {# Pre-concatenated #}
{% if true %}...{% end %}  {# Simplified, then dead-code eliminated #}
```

### Implementation

```python
# bengal/rendering/kida/optimizer/constant_folder.py

from __future__ import annotations

import operator
from typing import Any

from bengal.rendering.kida.nodes import (
    BinOp, Const, UnaryOp, Compare, Node, Expr, Concat,
)


# Safe operators for compile-time evaluation
_BINOP_FUNCS: dict[str, Any] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "//": operator.floordiv,
    "%": operator.mod,
    "**": operator.pow,
    "~": lambda a, b: str(a) + str(b),  # String concatenation
}

_UNARYOP_FUNCS: dict[str, Any] = {
    "-": operator.neg,
    "+": operator.pos,
    "not": operator.not_,
}

_COMPARE_FUNCS: dict[str, Any] = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


class ConstantFolder:
    """Evaluate constant expressions at compile time.

    Thread-safe: Stateless, creates new nodes.

    Example:
        >>> folder = ConstantFolder()
        >>> folded, count = folder.fold(parse("{{ 1 + 2 * 3 }}"))
        >>> # Result: Output(expr=Const(value=7)), count=1
    """

    def __init__(self) -> None:
        self._fold_count = 0

    def fold(self, node: Node) -> tuple[Node, int]:
        """Recursively fold constants in AST.

        Returns:
            Tuple of (optimized AST, number of constants folded)
        """
        self._fold_count = 0
        result = self._fold_node(node)
        return result, self._fold_count

    def _fold_node(self, node: Node) -> Node:
        """Dispatch to appropriate folder based on node type."""
        node_type = type(node).__name__

        if node_type == "BinOp":
            return self._fold_binop(node)
        elif node_type == "UnaryOp":
            return self._fold_unaryop(node)
        elif node_type == "Compare":
            return self._fold_compare(node)
        elif node_type == "Concat":
            return self._fold_concat(node)
        elif hasattr(node, "body"):
            # Recurse into container nodes
            return self._fold_container(node)

        return node

    def _fold_binop(self, node: BinOp) -> Expr:
        """Fold binary operations on constants."""
        left = self._fold_node(node.left)
        right = self._fold_node(node.right)

        # Both operands are constants?
        if isinstance(left, Const) and isinstance(right, Const):
            op_func = _BINOP_FUNCS.get(node.op)
            if op_func is not None:
                try:
                    result = op_func(left.value, right.value)
                    self._fold_count += 1
                    return Const(
                        value=result,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                    )
                except (ZeroDivisionError, TypeError, ValueError):
                    pass  # Can't fold, keep original

        # Rebuild with potentially folded children
        if left is node.left and right is node.right:
            return node  # No change

        return BinOp(
            left=left,
            op=node.op,
            right=right,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    def _fold_unaryop(self, node: UnaryOp) -> Expr:
        """Fold unary operations on constants."""
        operand = self._fold_node(node.operand)

        if isinstance(operand, Const):
            op_func = _UNARYOP_FUNCS.get(node.op)
            if op_func is not None:
                try:
                    result = op_func(operand.value)
                    return Const(
                        value=result,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                    )
                except (TypeError, ValueError):
                    pass

        if operand is node.operand:
            return node

        return UnaryOp(
            op=node.op,
            operand=operand,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    def _fold_compare(self, node: Compare) -> Expr:
        """Fold comparison operations on constants."""
        left = self._fold_node(node.left)
        comparators = [self._fold_node(c) for c in node.comparators]

        # All operands are constants?
        if isinstance(left, Const) and all(isinstance(c, Const) for c in comparators):
            # Simple case: single comparison
            if len(node.ops) == 1 and len(comparators) == 1:
                op_func = _COMPARE_FUNCS.get(node.ops[0])
                if op_func is not None:
                    try:
                        result = op_func(left.value, comparators[0].value)
                        return Const(
                            value=result,
                            lineno=node.lineno,
                            col_offset=node.col_offset,
                        )
                    except (TypeError, ValueError):
                        pass

        # Rebuild with folded children if changed
        if left is node.left and comparators == list(node.comparators):
            return node

        return Compare(
            left=left,
            ops=node.ops,
            comparators=tuple(comparators),
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    def _fold_concat(self, node: Concat) -> Expr:
        """Fold string concatenation of constants."""
        # Concat node has sequence of expressions to join
        folded = [self._fold_node(e) for e in node.nodes]

        # All constants? Merge into single string
        if all(isinstance(e, Const) for e in folded):
            result = "".join(str(e.value) for e in folded)
            return Const(
                value=result,
                lineno=node.lineno,
                col_offset=node.col_offset,
            )

        # Merge adjacent constant sequences
        merged = []
        pending = []
        for expr in folded:
            if isinstance(expr, Const):
                pending.append(str(expr.value))
            else:
                if pending:
                    merged.append(Const(
                        value="".join(pending),
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                    ))
                    pending = []
                merged.append(expr)
        if pending:
            merged.append(Const(
                value="".join(pending),
                lineno=node.lineno,
                col_offset=node.col_offset,
            ))

        if len(merged) == 1:
            return merged[0]

        # Rebuild Concat with merged nodes
        return type(node)(
            nodes=tuple(merged),
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    def _fold_container(self, node: Node) -> Node:
        """Recursively fold constants in container nodes."""
        # Handle nodes with body (If, For, Block, etc.)
        changes = {}

        if hasattr(node, "body"):
            new_body = tuple(self._fold_node(n) for n in node.body)
            if new_body != tuple(node.body):
                changes["body"] = new_body

        if hasattr(node, "else_") and node.else_:
            new_else = tuple(self._fold_node(n) for n in node.else_)
            if new_else != tuple(node.else_):
                changes["else_"] = new_else

        if hasattr(node, "test"):
            new_test = self._fold_node(node.test)
            if new_test is not node.test:
                changes["test"] = new_test

        if hasattr(node, "expr"):
            new_expr = self._fold_node(node.expr)
            if new_expr is not node.expr:
                changes["expr"] = new_expr

        if not changes:
            return node

        # Reconstruct node with changes
        from dataclasses import fields, replace
        return replace(node, **changes)
```

### Test Cases

```python
# tests/rendering/kida/optimizer/test_constant_folder.py

import pytest
from bengal.rendering.kida.optimizer.constant_folder import ConstantFolder
from bengal.rendering.kida.lexer import tokenize
from bengal.rendering.kida.parser import Parser
from bengal.rendering.kida.nodes import Const, Output


class TestConstantFolder:
    """Tests for compile-time constant folding."""

    @pytest.fixture
    def folder(self):
        return ConstantFolder()

    def _parse(self, source: str):
        tokens = list(tokenize(source))
        return Parser(tokens, source=source).parse()

    def test_fold_arithmetic(self, folder):
        """Arithmetic operations on constants are folded."""
        ast = self._parse("{{ 1 + 2 * 3 }}")
        folded, count = folder.fold(ast)

        # Should have single Output with Const(7)
        output = folded.body[0]
        assert isinstance(output, Output)
        assert isinstance(output.expr, Const)
        assert output.expr.value == 7
        assert count >= 1  # At least one fold occurred

    def test_fold_string_concat(self, folder):
        """String concatenation of constants is folded."""
        ast = self._parse('{{ "Hello" ~ " " ~ "World" }}')
        folded, count = folder.fold(ast)

        output = folded.body[0]
        assert isinstance(output.expr, Const)
        assert output.expr.value == "Hello World"

    def test_fold_comparison(self, folder):
        """Comparison operations on constants are folded."""
        ast = self._parse("{% if 1 < 2 %}yes{% end %}")
        folded, count = folder.fold(ast)

        # If node test should now be Const(True)
        if_node = folded.body[0]
        assert isinstance(if_node.test, Const)
        assert if_node.test.value is True

    def test_no_fold_variables(self, folder):
        """Expressions with variables are not folded."""
        ast = self._parse("{{ x + 1 }}")
        folded, count = folder.fold(ast)

        # Should remain a BinOp, not a Const
        output = folded.body[0]
        assert type(output.expr).__name__ == "BinOp"
        assert count == 0  # Nothing folded

    def test_partial_fold(self, folder):
        """Partial constant expressions are folded where possible."""
        ast = self._parse("{{ x + (1 + 2) }}")
        folded, count = folder.fold(ast)

        # Inner (1 + 2) should be folded to 3
        output = folded.body[0]
        binop = output.expr
        assert type(binop).__name__ == "BinOp"
        assert isinstance(binop.right, Const)
        assert binop.right.value == 3
        assert count == 1

    def test_fold_division_by_zero_safe(self, folder):
        """Division by zero is not folded (would raise at runtime)."""
        ast = self._parse("{{ 1 / 0 }}")
        folded, count = folder.fold(ast)

        # Should remain a BinOp, not crash
        output = folded.body[0]
        assert type(output.expr).__name__ == "BinOp"
        assert count == 0  # Unsafe fold avoided

    def test_fold_nested_structures(self, folder):
        """Constants in nested structures are folded."""
        ast = self._parse("{% for x in items %}{{ 1 + 1 }}{% end %}")
        folded, count = folder.fold(ast)

        for_node = folded.body[0]
        output = for_node.body[0]
        assert isinstance(output.expr, Const)
        assert output.expr.value == 2

    def test_fold_chained_operators(self, folder):
        """Chained constant operations are fully folded."""
        ast = self._parse("{{ 2 ** 3 ** 2 }}")  # 2^9 = 512
        folded, count = folder.fold(ast)

        output = folded.body[0]
        assert isinstance(output.expr, Const)
        assert output.expr.value == 512

    def test_fold_unary_operators(self, folder):
        """Unary operators on constants are folded."""
        ast = self._parse("{{ -5 }}")
        folded, count = folder.fold(ast)

        output = folded.body[0]
        assert isinstance(output.expr, Const)
        assert output.expr.value == -5
```

---

## Optimization 2: Dead Code Elimination

### Problem

Templates often contain debug blocks that are never executed in production:

```jinja
{% if false %}
    <div class="debug-panel">...</div>
{% end %}

{% if DEBUG %}  {# DEBUG is always False in prod #}
    {{ dump(context) }}
{% end %}
```

These still consume AST space and (minor) compilation time.

### Solution

Remove statically unreachable code:

```jinja
{# After optimization: completely removed #}
```

### Implementation

```python
# bengal/rendering/kida/optimizer/dead_code_eliminator.py

from __future__ import annotations

from bengal.rendering.kida.nodes import (
    Node, If, Const, Template, Block, For,
)


class DeadCodeEliminator:
    """Remove statically unreachable code from AST.

    Rules:
        - `{% if false %}...{% end %}` → removed entirely
        - `{% if true %}body{% end %}` → body inlined (no If node)
        - `{% if true %}body{% else %}unreachable{% end %}` → body only
        - Empty For loops with empty iterable literal → removed

    Thread-safe: Stateless, creates new nodes.
    """

    def __init__(self) -> None:
        self._eliminate_count = 0

    def eliminate(self, node: Node) -> tuple[Node, int]:
        """Remove dead code from AST.

        Returns:
            Tuple of (optimized AST, number of blocks eliminated)
        """
        self._eliminate_count = 0
        if isinstance(node, Template):
            result = self._eliminate_template(node)
        else:
            result = self._eliminate_node(node)
        return result, self._eliminate_count

    def _eliminate_template(self, node: Template) -> Template:
        """Process template root."""
        new_body = self._eliminate_body(list(node.body))

        if new_body == list(node.body):
            return node

        return Template(
            body=tuple(new_body),
            extends=node.extends,
            context_type=node.context_type,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    def _eliminate_body(self, nodes: list[Node]) -> list[Node]:
        """Process a sequence of nodes, removing dead code."""
        result = []

        for node in nodes:
            eliminated = self._eliminate_node(node)

            if eliminated is None:
                # Node was completely eliminated
                continue
            elif isinstance(eliminated, list):
                # Node was inlined (e.g., If with constant true test)
                result.extend(eliminated)
            else:
                result.append(eliminated)

        return result

    def _eliminate_node(self, node: Node) -> Node | list[Node] | None:
        """Eliminate dead code from a single node."""
        node_type = type(node).__name__

        if node_type == "If":
            return self._eliminate_if(node)
        elif node_type == "For":
            return self._eliminate_for(node)
        elif hasattr(node, "body"):
            return self._eliminate_container(node)

        return node

    def _eliminate_if(self, node: If) -> Node | list[Node] | None:
        """Eliminate dead code in If statements."""
        # Check if test is a constant
        if isinstance(node.test, Const):
            self._eliminate_count += 1
            if node.test.value:
                # Condition is always true → inline body
                return self._eliminate_body(list(node.body))
            else:
                # Condition is always false
                if node.elif_:
                    # Check first elif
                    first_elif_test, first_elif_body = node.elif_[0]
                    if isinstance(first_elif_test, Const) and first_elif_test.value:
                        return self._eliminate_body(list(first_elif_body))
                    # More complex elif chain - keep for now
                    # TODO: Full elif chain analysis
                if node.else_:
                    # Has else → inline else body
                    return self._eliminate_body(list(node.else_))
                else:
                    # No else → remove entirely
                    return None

        # Non-constant test - recurse into children
        return self._eliminate_container(node)

    def _eliminate_for(self, node: For) -> Node | None:
        """Eliminate empty For loops."""
        # Check for empty literal iterable
        if type(node.iter).__name__ == "List":
            if not node.iter.items:
                # Empty list literal → remove loop
                if node.empty:
                    # Has empty block → inline it
                    return self._eliminate_body(list(node.empty))
                return None

        # Recurse into body
        return self._eliminate_container(node)

    def _eliminate_container(self, node: Node) -> Node:
        """Recursively eliminate dead code in container nodes."""
        from dataclasses import replace

        changes = {}

        if hasattr(node, "body"):
            new_body = self._eliminate_body(list(node.body))
            if new_body != list(node.body):
                changes["body"] = tuple(new_body)

        if hasattr(node, "else_") and node.else_:
            new_else = self._eliminate_body(list(node.else_))
            if new_else != list(node.else_):
                changes["else_"] = tuple(new_else) if new_else else ()

        if hasattr(node, "empty") and node.empty:
            new_empty = self._eliminate_body(list(node.empty))
            if new_empty != list(node.empty):
                changes["empty"] = tuple(new_empty) if new_empty else ()

        if hasattr(node, "elif_") and node.elif_:
            new_elifs = []
            changed = False
            for test, body in node.elif_:
                new_body = self._eliminate_body(list(body))
                if new_body != list(body):
                    changed = True
                new_elifs.append((test, tuple(new_body)))
            if changed:
                changes["elif_"] = tuple(new_elifs)

        if not changes:
            return node

        return replace(node, **changes)
```

### Test Cases

```python
# tests/rendering/kida/optimizer/test_dead_code_eliminator.py

import pytest
from bengal.rendering.kida.optimizer.dead_code_eliminator import DeadCodeEliminator


class TestDeadCodeEliminator:
    """Tests for dead code elimination."""

    @pytest.fixture
    def eliminator(self):
        return DeadCodeEliminator()

    def _parse(self, source: str):
        from bengal.rendering.kida.lexer import tokenize
        from bengal.rendering.kida.parser import Parser
        tokens = list(tokenize(source))
        return Parser(tokens, source=source).parse()

    def test_eliminate_if_false(self, eliminator):
        """{% if false %}...{% end %} is completely removed."""
        ast = self._parse("before{% if false %}removed{% end %}after")
        result, count = eliminator.eliminate(ast)

        # Should have only 2 Data nodes (before, after)
        assert len(result.body) == 2
        assert result.body[0].value == "before"
        assert result.body[1].value == "after"
        assert count == 1  # One block eliminated

    def test_inline_if_true(self, eliminator):
        """{% if true %}body{% end %} inlines the body."""
        ast = self._parse("{% if true %}content{% end %}")
        result, count = eliminator.eliminate(ast)

        # Should have single Data node
        assert len(result.body) == 1
        assert result.body[0].value == "content"
        assert count == 1

    def test_if_false_with_else(self, eliminator):
        """{% if false %}...{% else %}kept{% end %} keeps else."""
        ast = self._parse("{% if false %}removed{% else %}kept{% end %}")
        result, count = eliminator.eliminate(ast)

        assert len(result.body) == 1
        assert result.body[0].value == "kept"
        assert count == 1

    def test_nested_dead_code(self, eliminator):
        """Dead code in nested structures is eliminated."""
        ast = self._parse("""
            {% for x in items %}
                {% if false %}never{% end %}
                {{ x }}
            {% end %}
        """)
        result, count = eliminator.eliminate(ast)

        for_node = result.body[0]
        # Body should not contain the dead If node
        if_nodes = [n for n in for_node.body if type(n).__name__ == "If"]
        assert len(if_nodes) == 0
        assert count == 1

    def test_preserve_dynamic_conditions(self, eliminator):
        """Non-constant conditions are preserved."""
        ast = self._parse("{% if x %}content{% end %}")
        result, count = eliminator.eliminate(ast)

        # If node should still exist
        assert type(result.body[0]).__name__ == "If"
        assert count == 0  # Nothing eliminated

    def test_eliminate_multiple_dead_blocks(self, eliminator):
        """Multiple dead code blocks are all eliminated."""
        ast = self._parse("""
            {% if false %}dead1{% end %}
            live
            {% if false %}dead2{% end %}
        """)
        result, count = eliminator.eliminate(ast)

        # Only the "live" Data node should remain
        data_nodes = [n for n in result.body if type(n).__name__ == "Data"]
        assert any("live" in n.value for n in data_nodes)
        assert count == 2  # Two blocks eliminated
```

---

## Optimization 3: Static Data Coalescing

### Problem

Adjacent `Data` nodes create multiple `_append()` calls:

```jinja
<div class="card">
    <h2>Title</h2>      {# Data node 1 #}
</div>                  {# Data node 2 #}
```

Generates:

```python
_append('<div class="card">\n    <h2>Title</h2>\n')
_append('</div>\n')
```

### Solution

Merge adjacent `Data` nodes into single nodes:

```python
_append('<div class="card">\n    <h2>Title</h2>\n</div>\n')
```

### Implementation

```python
# bengal/rendering/kida/optimizer/data_coalescer.py

from __future__ import annotations

from bengal.rendering.kida.nodes import Node, Template, Data


class DataCoalescer:
    """Merge adjacent Data nodes to reduce _append() calls.

    Thread-safe: Stateless, creates new nodes.

    Impact: ~5-10% reduction in function calls for typical templates.
    """

    def __init__(self) -> None:
        self._coalesce_count = 0

    def coalesce(self, node: Node) -> tuple[Node, int]:
        """Merge adjacent Data nodes in AST.

        Returns:
            Tuple of (optimized AST, number of merge operations)
        """
        self._coalesce_count = 0
        if isinstance(node, Template):
            result = self._coalesce_template(node)
        else:
            result = self._coalesce_node(node)
        return result, self._coalesce_count

    def _coalesce_template(self, node: Template) -> Template:
        """Process template root."""
        new_body = self._coalesce_body(list(node.body))

        if len(new_body) == len(node.body):
            # Check if actually changed
            if all(a is b for a, b in zip(new_body, node.body)):
                return node

        return Template(
            body=tuple(new_body),
            extends=node.extends,
            context_type=node.context_type,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    def _coalesce_body(self, nodes: list[Node]) -> list[Node]:
        """Merge adjacent Data nodes in a body."""
        if not nodes:
            return nodes

        result = []
        pending_data: list[Data] = []

        for node in nodes:
            # Recurse into container nodes first
            if hasattr(node, "body"):
                node = self._coalesce_node(node)

            if isinstance(node, Data):
                pending_data.append(node)
            else:
                # Flush pending data
                if pending_data:
                    result.append(self._merge_data(pending_data))
                    pending_data = []
                result.append(node)

        # Flush remaining data
        if pending_data:
            result.append(self._merge_data(pending_data))

        return result

    def _merge_data(self, nodes: list[Data]) -> Data:
        """Merge multiple Data nodes into one."""
        if len(nodes) == 1:
            return nodes[0]

        self._coalesce_count += len(nodes) - 1  # N nodes merged = N-1 eliminations
        merged_value = "".join(n.value for n in nodes)
        return Data(
            value=merged_value,
            lineno=nodes[0].lineno,
            col_offset=nodes[0].col_offset,
        )

    def _coalesce_node(self, node: Node) -> Node:
        """Recursively coalesce Data in container nodes."""
        from dataclasses import replace

        changes = {}

        if hasattr(node, "body"):
            new_body = self._coalesce_body(list(node.body))
            if new_body != list(node.body):
                changes["body"] = tuple(new_body)

        if hasattr(node, "else_") and node.else_:
            new_else = self._coalesce_body(list(node.else_))
            if new_else != list(node.else_):
                changes["else_"] = tuple(new_else)

        if hasattr(node, "empty") and node.empty:
            new_empty = self._coalesce_body(list(node.empty))
            if new_empty != list(node.empty):
                changes["empty"] = tuple(new_empty)

        if not changes:
            return node

        return replace(node, **changes)
```

---

## Optimization 4: Filter Inlining

### Problem

Common filters like `upper`, `lower`, `strip` go through the filter dispatch system:

```python
# Generated code for {{ name | upper }}
_append(_e(_filter_upper(ctx["name"])))
```

This involves:
1. Filter name lookup
2. Function call overhead
3. Argument passing

### Solution

Inline simple, pure filters directly:

```python
# Generated code for {{ name | upper }}
_append(_e(str(ctx["name"]).upper()))
```

### Implementation

```python
# bengal/rendering/kida/optimizer/filter_inliner.py

from __future__ import annotations

from bengal.rendering.kida.nodes import Node, Filter, Const, FuncCall, Output


# Filters that can be safely inlined
# Maps filter_name -> (method_name, takes_args)
_INLINABLE_FILTERS: dict[str, tuple[str, bool]] = {
    "upper": ("upper", False),
    "lower": ("lower", False),
    "strip": ("strip", False),
    "lstrip": ("lstrip", False),
    "rstrip": ("rstrip", False),
    "title": ("title", False),
    "capitalize": ("capitalize", False),
    "swapcase": ("swapcase", False),
}


class FilterInliner:
    """Inline common pure filters as direct method calls.

    This converts filter calls like `{{ name | upper }}` from:
        _filter_upper(value)
    To:
        str(value).upper()

    Benefits:
        - Eliminates filter dispatch overhead
        - Enables further optimization by Python
        - ~5-10% speedup for filter-heavy templates

    Only pure, side-effect-free filters are inlined.
    """

    def __init__(self) -> None:
        self._inline_count = 0

    def inline(self, node: Node) -> tuple[Node, int]:
        """Inline eligible filters in AST.

        Returns:
            Tuple of (optimized AST, number of filters inlined)
        """
        self._inline_count = 0
        result = self._inline_node(node)
        return result, self._inline_count

    def _inline_node(self, node: Node) -> Node:
        """Process a single node."""
        node_type = type(node).__name__

        if node_type == "Filter":
            return self._inline_filter(node)
        elif node_type == "Output":
            return self._inline_output(node)
        elif hasattr(node, "body"):
            return self._inline_container(node)

        return node

    def _inline_filter(self, node: Filter) -> Node:
        """Attempt to inline a filter call."""
        # Check if filter is inlinable
        if node.name not in _INLINABLE_FILTERS:
            # Recurse into nested filters
            if isinstance(node.value, Filter):
                new_value = self._inline_filter(node.value)
                if new_value is not node.value:
                    from dataclasses import replace
                    return replace(node, value=new_value)
            return node

        method_name, takes_args = _INLINABLE_FILTERS[node.name]

        # Don't inline if filter has arguments and it doesn't expect them
        if node.args and not takes_args:
            return node

        # Create InlinedFilter node (new node type for code generation)
        from bengal.rendering.kida.nodes import InlinedFilter

        # First, inline any nested filters
        inner_value = node.value
        if isinstance(inner_value, Filter):
            inner_value = self._inline_filter(inner_value)

        self._inline_count += 1
        return InlinedFilter(
            value=inner_value,
            method=method_name,
            args=node.args,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    def _inline_output(self, node: Output) -> Node:
        """Inline filters in Output expressions."""
        if isinstance(node.expr, Filter):
            new_expr = self._inline_filter(node.expr)
            if new_expr is not node.expr:
                from dataclasses import replace
                return replace(node, expr=new_expr)
        return node

    def _inline_container(self, node: Node) -> Node:
        """Recursively inline in container nodes."""
        from dataclasses import replace

        changes = {}

        if hasattr(node, "body"):
            new_body = tuple(self._inline_node(n) for n in node.body)
            if any(a is not b for a, b in zip(new_body, node.body)):
                changes["body"] = new_body

        if hasattr(node, "else_") and node.else_:
            new_else = tuple(self._inline_node(n) for n in node.else_)
            if any(a is not b for a, b in zip(new_else, node.else_)):
                changes["else_"] = new_else

        if not changes:
            return node

        return replace(node, **changes)
```

### Required Node Addition

Add to `bengal/rendering/kida/nodes.py`:

```python
@dataclass(frozen=True, slots=True)
class InlinedFilter(Expr):
    """Inlined filter as direct method call (optimization).

    Generated by FilterInliner for common pure filters like upper, lower, strip.
    The compiler generates `str(value).method()` instead of filter dispatch.

    Example:
        `{{ name | upper }}` compiles to `str(ctx["name"]).upper()`
        instead of `_filter_upper(ctx["name"])`
    """

    value: Expr      # The expression being filtered
    method: str      # The str method to call (e.g., "upper", "lower")
    args: Sequence[Expr] = ()  # Optional method arguments
```

### Required Compiler Update

Add handler in `bengal/rendering/kida/compiler/expressions.py`:

```python
def _compile_inlined_filter(self, node: InlinedFilter) -> ast.Call:
    """Compile inlined filter to direct method call.

    Generates: str(value).method(*args)
    """
    # str(value)
    str_call = ast.Call(
        func=ast.Name(id="str", ctx=ast.Load()),
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
```

---

## Optimization 5: Template Bytecode Cache

### Problem

Every process start recompiles templates from source:

```
Process Start → Load Source → Lexer → Parser → AST → Compiler → Python AST → compile() → exec()
                              ↑________________________________________________↑
                                         ~10-50ms per template
```

For serverless (Lambda, Cloud Functions), this is the **primary cold-start cost**.

### Solution

Persist compiled `code` objects to disk using `marshal`:

```
Cold Start:
  Check cache → marshal.load() → exec() → render
                 ↑_________________↑
                     ~0.5ms per template

Warm Cache:
  Check cache (hit) → return cached
                        ~0.01ms
```

### Implementation

```python
# bengal/rendering/kida/bytecode_cache.py

from __future__ import annotations

import hashlib
import marshal
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import CodeType

# Python version tag for cache invalidation across Python upgrades
_PY_VERSION_TAG = f"py{sys.version_info.major}{sys.version_info.minor}"


class BytecodeCache:
    """Persist compiled template bytecode to disk.

    Uses marshal for code object serialization (Python stdlib).

    Thread-Safety:
        File writes use atomic rename pattern to prevent corruption.
        Multiple processes can safely share the cache directory.

    Cache Invalidation:
        Uses source hash in filename. When source changes, hash changes,
        and old cache entry becomes orphan (cleaned up lazily).

    Example:
        >>> cache = BytecodeCache(Path(".bengal-cache/kida"))
        >>>
        >>> # Miss: compile and cache
        >>> code = cache.get("base.html", source_hash)
        >>> if code is None:
        ...     code = compile_template(source)
        ...     cache.set("base.html", source_hash, code)
        >>>
        >>> # Hit: instant load
        >>> code = cache.get("base.html", source_hash)
    """

    def __init__(
        self,
        directory: Path,
        pattern: str = "__kida_{version}_{name}_{hash}.pyc",
    ):
        """Initialize bytecode cache.

        Args:
            directory: Cache directory (created if missing)
            pattern: Filename pattern with {version}, {name}, {hash} placeholders
        """
        self._dir = directory
        self._pattern = pattern
        self._dir.mkdir(parents=True, exist_ok=True)

    def _make_path(self, name: str, source_hash: str) -> Path:
        """Generate cache file path.

        Includes Python version in filename to prevent cross-version
        bytecode incompatibility (marshal format is version-specific).
        """
        # Sanitize name for filesystem
        safe_name = name.replace("/", "_").replace("\\", "_")
        filename = self._pattern.format(
            version=_PY_VERSION_TAG,
            name=safe_name,
            hash=source_hash[:16],
        )
        return self._dir / filename

    def get(self, name: str, source_hash: str) -> CodeType | None:
        """Load cached bytecode if available.

        Args:
            name: Template name
            source_hash: Hash of template source (for invalidation)

        Returns:
            Compiled code object, or None if not cached
        """
        path = self._make_path(name, source_hash)

        if not path.exists():
            return None

        try:
            with open(path, "rb") as f:
                return marshal.load(f)
        except (OSError, ValueError, EOFError):
            # Corrupted or incompatible cache file
            path.unlink(missing_ok=True)
            return None

    def set(self, name: str, source_hash: str, code: CodeType) -> None:
        """Cache compiled bytecode.

        Args:
            name: Template name
            source_hash: Hash of template source
            code: Compiled code object
        """
        path = self._make_path(name, source_hash)
        tmp_path = path.with_suffix(".tmp")

        try:
            # Write to temp file first (atomic pattern)
            with open(tmp_path, "wb") as f:
                marshal.dump(code, f)

            # Atomic rename
            tmp_path.rename(path)
        except OSError:
            # Best effort - caching failure shouldn't break compilation
            tmp_path.unlink(missing_ok=True)

    def clear(self, current_version_only: bool = False) -> int:
        """Remove cached bytecode.

        Args:
            current_version_only: If True, only clear current Python version's cache

        Returns:
            Number of files removed
        """
        count = 0
        pattern = f"__kida_{_PY_VERSION_TAG}_*.pyc" if current_version_only else "__kida_*.pyc"
        for path in self._dir.glob(pattern):
            path.unlink(missing_ok=True)
            count += 1
        return count

    def stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with size, file_count, total_bytes
        """
        files = list(self._dir.glob("__kida_*.pyc"))
        total_bytes = sum(f.stat().st_size for f in files)

        return {
            "file_count": len(files),
            "total_bytes": total_bytes,
        }


def hash_source(source: str) -> str:
    """Generate hash of template source for cache key."""
    return hashlib.sha256(source.encode()).hexdigest()
```

### Integration with Environment

```python
# In Environment._compile() - update bengal/rendering/kida/environment/core.py

from bengal.rendering.kida.bytecode_cache import BytecodeCache, hash_source

def _compile(
    self,
    source: str,
    name: str | None,
    filename: str | None,
) -> Template:
    """Compile template with optional bytecode caching."""
    source_hash = hash_source(source)

    # Check bytecode cache
    if self._bytecode_cache is not None and name is not None:
        cached_code = self._bytecode_cache.get(name, source_hash)
        if cached_code is not None:
            return Template(self, cached_code, name, filename)

    # Full compilation pipeline
    tokens = list(Lexer(source, self._lexer_config).tokenize())
    ast = Parser(tokens, source=source).parse()

    # Apply optimizations
    if self.optimized:
        ast = self._optimizer.optimize(ast)

    code = Compiler(self).compile(ast, name, filename)

    # Cache bytecode
    if self._bytecode_cache is not None and name is not None:
        self._bytecode_cache.set(name, source_hash, code)

    return Template(self, code, name, filename)
```

---

## Optimization 6: Buffer Pre-Allocation

### Problem

The render buffer grows dynamically:

```python
buf = []  # Empty list, grows via append
```

For large templates, this causes multiple reallocations.

### Solution

Estimate output size based on Data node sizes and pre-allocate:

```python
# During AST optimization, calculate:
estimated_size = sum(len(data.value) for data in all_data_nodes)
estimated_size *= 1.5  # Buffer for dynamic content

# Generated code:
buf = io.StringIO(estimated_size)
```

### Implementation

```python
# bengal/rendering/kida/optimizer/buffer_estimator.py

from __future__ import annotations

from bengal.rendering.kida.nodes import Node, Data, Template


class BufferEstimator:
    """Estimate output buffer size from AST.

    Calculates total static content size plus headroom for dynamic content.
    Used to pre-allocate StringIO buffer in generated code.
    """

    def estimate(self, node: Template) -> int:
        """Estimate output size in bytes.

        Returns conservative estimate (may be larger than actual).
        """
        static_size = self._count_static_bytes(node)

        # Add headroom for dynamic content
        # Heuristic: dynamic content typically adds 50-100% overhead
        estimated = int(static_size * 1.5)

        # Minimum useful buffer size
        return max(estimated, 256)

    def _count_static_bytes(self, node: Node) -> int:
        """Count bytes of static Data content."""
        total = 0

        if isinstance(node, Data):
            total += len(node.value.encode("utf-8"))

        if hasattr(node, "body"):
            for child in node.body:
                total += self._count_static_bytes(child)

        if hasattr(node, "else_") and node.else_:
            for child in node.else_:
                total += self._count_static_bytes(child)

        if hasattr(node, "empty") and node.empty:
            for child in node.empty:
                total += self._count_static_bytes(child)

        return total
```

Then modify code generation to use `io.StringIO`:

```python
# In Compiler._make_render_function():

# Import io at module level
import_io = ast.Import(names=[ast.alias(name="io")])

# buf = io.StringIO(estimated_size)
buf_init = ast.Assign(
    targets=[ast.Name(id="buf", ctx=ast.Store())],
    value=ast.Call(
        func=ast.Attribute(
            value=ast.Name(id="io", ctx=ast.Load()),
            attr="StringIO",
            ctx=ast.Load(),
        ),
        args=[],  # Python auto-handles initial capacity
        keywords=[],
    ),
)

# _write = buf.write (instead of _append = buf.append)
write_cache = ast.Assign(
    targets=[ast.Name(id="_write", ctx=ast.Store())],
    value=ast.Attribute(
        value=ast.Name(id="buf", ctx=ast.Load()),
        attr="write",
        ctx=ast.Load(),
    ),
)

# return buf.getvalue()
return_stmt = ast.Return(
    value=ast.Call(
        func=ast.Attribute(
            value=ast.Name(id="buf", ctx=ast.Load()),
            attr="getvalue",
            ctx=ast.Load(),
        ),
        args=[],
        keywords=[],
    ),
)
```

---

## Unified Optimizer

### Implementation

```python
# bengal/rendering/kida/optimizer/__init__.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bengal.rendering.kida.optimizer.constant_folder import ConstantFolder
from bengal.rendering.kida.optimizer.dead_code_eliminator import DeadCodeEliminator
from bengal.rendering.kida.optimizer.data_coalescer import DataCoalescer
from bengal.rendering.kida.optimizer.filter_inliner import FilterInliner
from bengal.rendering.kida.optimizer.buffer_estimator import BufferEstimator

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Template


@dataclass
class OptimizationConfig:
    """Configuration for AST optimization passes."""

    constant_folding: bool = True
    dead_code_elimination: bool = True
    data_coalescing: bool = True
    filter_inlining: bool = True
    estimate_buffer: bool = True


@dataclass
class OptimizationStats:
    """Statistics from optimization passes."""

    constants_folded: int = 0
    dead_blocks_removed: int = 0
    data_nodes_coalesced: int = 0
    filters_inlined: int = 0
    estimated_buffer_size: int = 256
    passes_applied: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable summary of optimizations applied."""
        parts = []
        if self.constants_folded:
            parts.append(f"{self.constants_folded} constants folded")
        if self.dead_blocks_removed:
            parts.append(f"{self.dead_blocks_removed} dead blocks removed")
        if self.data_nodes_coalesced:
            parts.append(f"{self.data_nodes_coalesced} data nodes merged")
        if self.filters_inlined:
            parts.append(f"{self.filters_inlined} filters inlined")
        return "; ".join(parts) if parts else "no optimizations applied"


@dataclass
class OptimizationResult:
    """Result of optimization pass."""

    ast: Template
    stats: OptimizationStats = field(default_factory=OptimizationStats)


class ASTOptimizer:
    """Unified AST optimization pass.

    Applies a sequence of pure-Python optimizations to the Kida AST
    before compilation to Python AST.

    Thread-safe: Stateless, creates new nodes.

    Example:
        >>> optimizer = ASTOptimizer()
        >>> result = optimizer.optimize(ast)
        >>> optimized_ast = result.ast
        >>> buffer_size = result.estimated_buffer_size
    """

    def __init__(self, config: OptimizationConfig | None = None):
        self._config = config or OptimizationConfig()

        # Initialize passes
        self._constant_folder = ConstantFolder()
        self._dead_code_eliminator = DeadCodeEliminator()
        self._data_coalescer = DataCoalescer()
        self._filter_inliner = FilterInliner()
        self._buffer_estimator = BufferEstimator()

    def optimize(self, ast: Template) -> OptimizationResult:
        """Apply all enabled optimization passes.

        Pass order:
            1. Constant folding (enables dead code detection)
            2. Dead code elimination (reduces AST size)
            3. Data coalescing (merges adjacent static content)
            4. Filter inlining (simplifies filter calls)
            5. Buffer estimation (calculates pre-allocation size)
        """
        stats = OptimizationStats()

        # Pass 1: Constant folding
        if self._config.constant_folding:
            ast, count = self._constant_folder.fold(ast)
            stats.constants_folded = count
            stats.passes_applied.append("constant_folding")

        # Pass 2: Dead code elimination
        if self._config.dead_code_elimination:
            ast, count = self._dead_code_eliminator.eliminate(ast)
            stats.dead_blocks_removed = count
            stats.passes_applied.append("dead_code_elimination")

        # Pass 3: Data coalescing
        if self._config.data_coalescing:
            ast, count = self._data_coalescer.coalesce(ast)
            stats.data_nodes_coalesced = count
            stats.passes_applied.append("data_coalescing")

        # Pass 4: Filter inlining
        if self._config.filter_inlining:
            ast, count = self._filter_inliner.inline(ast)
            stats.filters_inlined = count
            stats.passes_applied.append("filter_inlining")

        # Pass 5: Buffer estimation
        if self._config.estimate_buffer:
            stats.estimated_buffer_size = self._buffer_estimator.estimate(ast)
            stats.passes_applied.append("buffer_estimation")

        return OptimizationResult(ast=ast, stats=stats)


__all__ = [
    "ASTOptimizer",
    "OptimizationConfig",
    "OptimizationResult",
    "OptimizationStats",
    "ConstantFolder",
    "DeadCodeEliminator",
    "DataCoalescer",
    "FilterInliner",
    "BufferEstimator",
]
```

---

### Unified Optimizer Test Cases

```python
# tests/rendering/kida/optimizer/test_ast_optimizer.py

import pytest
from bengal.rendering.kida.optimizer import (
    ASTOptimizer,
    OptimizationConfig,
    OptimizationStats,
)
from bengal.rendering.kida.lexer import tokenize
from bengal.rendering.kida.parser import Parser


class TestASTOptimizer:
    """Integration tests for the unified optimizer."""

    def _parse(self, source: str):
        tokens = list(tokenize(source))
        return Parser(tokens, source=source).parse()

    def test_all_passes_applied(self):
        """All enabled passes are applied in order."""
        source = """
            {% if false %}dead{% end %}
            {{ 1 + 2 }}
            <div>A</div><div>B</div>
            {{ name | upper }}
        """
        ast = self._parse(source)
        optimizer = ASTOptimizer()

        result = optimizer.optimize(ast)

        assert result.stats.dead_blocks_removed >= 1
        assert result.stats.constants_folded >= 1
        assert result.stats.data_nodes_coalesced >= 1
        assert result.stats.filters_inlined >= 1
        assert result.stats.estimated_buffer_size > 0

    def test_selective_passes(self):
        """Only enabled passes are applied."""
        config = OptimizationConfig(
            constant_folding=True,
            dead_code_elimination=False,
            data_coalescing=False,
            filter_inlining=False,
            estimate_buffer=False,
        )
        optimizer = ASTOptimizer(config)

        source = "{% if false %}dead{% end %}{{ 1 + 1 }}"
        ast = self._parse(source)
        result = optimizer.optimize(ast)

        assert "constant_folding" in result.stats.passes_applied
        assert "dead_code_elimination" not in result.stats.passes_applied
        assert result.stats.constants_folded >= 1

    def test_stats_summary(self):
        """Stats summary produces readable output."""
        stats = OptimizationStats(
            constants_folded=3,
            dead_blocks_removed=1,
            data_nodes_coalesced=5,
            filters_inlined=2,
        )

        summary = stats.summary()
        assert "3 constants folded" in summary
        assert "1 dead blocks removed" in summary
        assert "5 data nodes merged" in summary
        assert "2 filters inlined" in summary

    def test_no_optimizations(self):
        """Templates with nothing to optimize return unchanged."""
        source = "{{ name }}"
        ast = self._parse(source)
        optimizer = ASTOptimizer()

        result = optimizer.optimize(ast)

        # Only buffer estimation should have any effect
        assert result.stats.constants_folded == 0
        assert result.stats.dead_blocks_removed == 0
        assert result.stats.data_nodes_coalesced == 0
        assert result.stats.filters_inlined == 0
```

---

## Performance Analysis

### Expected Impact

| Optimization | Template Type | Impact | Measurement |
|--------------|---------------|--------|-------------|
| Constant Folding | Math-heavy | 5-15% | Time to render |
| Dead Code Elimination | Debug templates | 10-30% | Time to render |
| Data Coalescing | HTML-heavy | 5-10% | Function call count |
| Filter Inlining | Filter-heavy | 5-10% | Time to render |
| Buffer Pre-allocation | Large output | 5-10% | Memory allocations |
| Bytecode Cache | All templates | 90%+ cold-start | Startup time |

### Benchmark Plan

```python
# benchmarks/test_optimizer.py

import pytest
from bengal.rendering.kida import Environment


@pytest.fixture
def env_optimized():
    return Environment(optimized=True)


@pytest.fixture
def env_unoptimized():
    return Environment(optimized=False)


class TestOptimizerBenchmarks:
    """Benchmarks for AST optimization passes."""

    def test_constant_folding_benchmark(self, benchmark, env_optimized, env_unoptimized):
        """Measure constant folding impact."""
        source = """
            {% for i in range(100) %}
                {{ 60 * 60 * 24 * 365 }}
                {{ 1 + 2 + 3 + 4 + 5 }}
                {{ "Hello" ~ " " ~ "World" }}
            {% end %}
        """

        # Compile both versions
        opt_template = env_optimized.from_string(source)
        unopt_template = env_unoptimized.from_string(source)

        ctx = {}

        # Benchmark optimized
        opt_time = benchmark(lambda: opt_template.render(ctx))

        # Compare
        # (Use benchmark fixture for proper comparison)

    def test_dead_code_benchmark(self, benchmark, env_optimized, env_unoptimized):
        """Measure dead code elimination impact."""
        source = """
            {% if false %}
                <div class="debug">
                    {{ dump(context) }}
                    {{ expensive_operation() }}
                </div>
            {% end %}
            <main>Content</main>
        """

        opt_template = env_optimized.from_string(source)
        unopt_template = env_unoptimized.from_string(source)

        ctx = {}

        opt_time = benchmark(lambda: opt_template.render(ctx))

    def test_bytecode_cache_cold_start(self, benchmark, tmp_path):
        """Measure bytecode cache cold-start improvement."""
        from bengal.rendering.kida.cache.bytecode import BytecodeCache

        cache = BytecodeCache(tmp_path / "cache")
        env = Environment(bytecode_cache=cache)

        # Simulate cold start: load 50 templates
        sources = {f"template_{i}.html": f"<div>Content {i}</div>" for i in range(50)}

        def cold_start():
            for name, source in sources.items():
                env.from_string(source, name=name)

        # First run: populate cache
        cold_start()

        # Second run: cache hits
        warm_time = benchmark(cold_start)
```

---

## Rollout Plan

### Phase 1: Core Optimizations (Week 1)

- [ ] Create `bengal/rendering/kida/optimizer/` package structure
- [ ] Add `InlinedFilter` node to `nodes.py`
- [ ] Implement `ConstantFolder` with stats tracking
- [ ] Implement `DeadCodeEliminator` with stats tracking
- [ ] Implement `DataCoalescer` with stats tracking
- [ ] Unit tests for each pass (>90% coverage)
- [ ] Integration with `Environment.optimized` flag

### Phase 2: Advanced Optimizations (Week 2)

- [ ] Implement `FilterInliner` with stats tracking
- [ ] Update Compiler to handle `InlinedFilter` node
- [ ] Implement `BufferEstimator`
- [ ] Implement `BytecodeCache` with version tagging
- [ ] Add `bytecode_cache` option to Environment
- [ ] Add debug logging for optimization passes

### Phase 3: Testing & Benchmarks (Week 3)

- [ ] End-to-end integration tests
- [ ] Benchmark suite comparing optimized vs unoptimized
- [ ] Real-world template testing (use `benchmarks/scenarios/`)
- [ ] Memory profiling (no significant increase)
- [ ] Edge case testing (empty templates, deeply nested, etc.)

### Phase 4: Release

- [ ] Verify `optimized=True` activates all passes
- [ ] Bytecode cache disabled by default (opt-in via `bytecode_cache=`)
- [ ] Add to changelog with before/after benchmarks
- [ ] Update `COMPLEXITY.md` checklist items
- [ ] Add usage examples to docstrings

---

## Configuration

### Environment Options

```python
from pathlib import Path
from bengal.rendering.kida import Environment
from bengal.rendering.kida.bytecode_cache import BytecodeCache

env = Environment(
    # Enable/disable optimization pass (default: True)
    optimized=True,

    # Optional: bytecode cache for persistent compilation
    bytecode_cache=BytecodeCache(Path(".bengal-cache/kida")),
)
```

### Fine-Grained Control

```python
from bengal.rendering.kida.optimizer import ASTOptimizer, OptimizationConfig

config = OptimizationConfig(
    constant_folding=True,
    dead_code_elimination=True,
    data_coalescing=True,
    filter_inlining=False,  # Disable if causing issues
    estimate_buffer=True,
)

optimizer = ASTOptimizer(config)
```

### Debugging Optimizations

```python
from bengal.rendering.kida.optimizer import ASTOptimizer
from bengal.rendering.kida.lexer import tokenize
from bengal.rendering.kida.parser import Parser

# Parse template
source = """
{% if false %}debug{% end %}
{{ 60 * 60 * 24 }}
<div>Hello</div>
<div>World</div>
"""
tokens = list(tokenize(source))
ast = Parser(tokens, source=source).parse()

# Optimize and inspect stats
optimizer = ASTOptimizer()
result = optimizer.optimize(ast)

print(result.stats.summary())
# Output: "1 constants folded; 1 dead blocks removed; 1 data nodes merged"

print(f"Buffer size estimate: {result.stats.estimated_buffer_size} bytes")
print(f"Passes applied: {', '.join(result.stats.passes_applied)}")
```

### Bytecode Cache Statistics

```python
cache = BytecodeCache(Path(".bengal-cache/kida"))

# Check cache state
stats = cache.stats()
print(f"Cached templates: {stats['file_count']}")
print(f"Total cache size: {stats['total_bytes'] / 1024:.1f} KB")

# Clear cache for current Python version only
removed = cache.clear(current_version_only=True)
print(f"Cleared {removed} cached templates")
```

---

## Alternatives Considered

### 1. Rust Extension for Lexer

**Rejected for this RFC**: Adds deployment complexity, platform issues, compilation requirements. Separate RFC if needed.

### 2. Cython Compilation

**Rejected**: Adds build complexity, not pure Python, harder to debug.

### 3. PyPy JIT Hints

**Rejected**: PyPy-specific, not portable to CPython majority.

### 4. Profile-Guided Optimization

**Deferred**: Requires runtime profiling infrastructure. Could be future enhancement.

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Constant folding speedup | 5-15% on math templates | Benchmark |
| Dead code elimination | 10-30% on debug templates | Benchmark |
| Cold-start reduction | 90%+ with bytecode cache | Startup time |
| Test coverage | >90% for optimizer package | pytest-cov |
| No regressions | 0 failing tests | CI |
| Memory neutral | ±5% memory usage | Memory profiling |
| Stats tracking works | All counts accurate | Integration tests |
| Cross-version safety | Cache invalidates on Python upgrade | Manual test |

---

## References

- `bengal/rendering/kida/COMPLEXITY.md` — Current optimization status
- `bengal/rendering/kida/compiler/__init__.py` — AST-to-AST design rationale
- `bengal/rendering/kida/nodes.py` — AST node definitions
- Python `ast` module documentation
- Python `marshal` module documentation
- Jinja2 `BytecodeCache` implementation (reference)

---

## Revision History

### v1.1 (2025-12-26)

**Corrections**:
- Fixed `Filter.node` → `Filter.value` to match actual node structure
- Fixed `For.iterable` → `For.iter` to match actual node structure
- Added `Concat` to ConstantFolder imports
- Added `Output` to FilterInliner imports
- Updated file path from `cache/bytecode.py` → `bytecode_cache.py` (flat structure)

**Additions**:
- Added `InlinedFilter` node definition and compiler handler
- Added `OptimizationStats` class for tracking optimization metrics
- Added Python version tag to bytecode cache for cross-version safety
- Added `clear(current_version_only=)` option to BytecodeCache
- Added debug/logging examples to Configuration section
- Added unified optimizer integration tests
- Expanded test cases with count verification

**Changes**:
- Deferred Expression Deduplication to Phase 2 RFC (complexity)
- Updated effort estimate to ~19 hours
- All optimizer methods now return `(ast, count)` tuples for observability
- Updated rollout plan with more specific tasks
