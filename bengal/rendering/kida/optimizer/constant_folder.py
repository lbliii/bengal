"""Constant Folding Optimization Pass.

Evaluates constant expressions at compile time, eliminating runtime computation
for operations on literals.

Examples:
    {{ 60 * 60 * 24 }}         → {{ 86400 }}
    {{ "Hello" ~ " " ~ "World" }} → {{ "Hello World" }}
    {% if 1 + 1 == 2 %}...{% end %} → {% if true %}...{% end %}

Thread-Safety:
    Stateless, creates new nodes. Safe for concurrent use.
"""

from __future__ import annotations

import operator
from dataclasses import replace
from typing import Any

from bengal.rendering.kida.nodes import (
    BinOp,
    BoolOp,
    Compare,
    Concat,
    Const,
    Expr,
    Node,
    Template,
    UnaryOp,
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
        >>> # Result: Template with Output(expr=Const(value=7)), count=1
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
        elif node_type == "BoolOp":
            return self._fold_boolop(node)
        elif node_type == "Template":
            return self._fold_template(node)
        elif hasattr(node, "body"):
            # Recurse into container nodes
            return self._fold_container(node)
        elif hasattr(node, "expr"):
            # Nodes with expr attribute (Output, etc.)
            return self._fold_expr_container(node)

        return node

    def _fold_template(self, node: Template) -> Template:
        """Process template root."""
        new_body = tuple(self._fold_node(n) for n in node.body)

        if all(a is b for a, b in zip(new_body, node.body, strict=True)):
            return node

        return Template(
            body=new_body,
            extends=node.extends,
            context_type=node.context_type,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

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
                except (ZeroDivisionError, TypeError, ValueError, OverflowError):
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
                    self._fold_count += 1
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

        # All operands are constants? Single comparison only
        if (
            isinstance(left, Const)
            and all(isinstance(c, Const) for c in comparators)
            and len(node.ops) == 1
            and len(comparators) == 1
        ):
            op_func = _COMPARE_FUNCS.get(node.ops[0])
            if op_func is not None:
                try:
                    result = op_func(left.value, comparators[0].value)
                    self._fold_count += 1
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

    def _fold_boolop(self, node: BoolOp) -> Expr:
        """Fold boolean operations on constants.

        Applies short-circuit evaluation rules ONLY when safe:
        - `true or x` → `true` (only at start, before any non-constants)
        - `false and x` → `false` (only at start, before any non-constants)
        - `true and x` → `x` (removes the constant True)
        - `false or x` → `x` (removes the constant False)

        When a non-constant precedes a constant, we cannot short-circuit
        because the non-constant could evaluate to a value that determines
        the result.
        """
        values = [self._fold_node(v) for v in node.values]

        # Try to simplify based on short-circuit evaluation
        new_values = []
        saw_non_const = False

        for v in values:
            if isinstance(v, Const):
                if node.op == "or":
                    if v.value:  # True (truthy constant)
                        if not saw_non_const:
                            # `true or ...` at start → True
                            self._fold_count += 1
                            return v
                        else:
                            # Non-const before: `x or true` → keep both
                            # (x might be truthy, short-circuiting)
                            new_values.append(v)
                    else:
                        # `false or x` → skip False
                        self._fold_count += 1
                        continue
                else:  # and
                    if not v.value:  # False (falsy constant)
                        if not saw_non_const:
                            # `false and ...` at start → False
                            self._fold_count += 1
                            return v
                        else:
                            # Non-const before: `x and false` → keep both
                            new_values.append(v)
                    else:
                        # `true and x` → skip True
                        self._fold_count += 1
                        continue
            else:
                saw_non_const = True
                new_values.append(v)

        # If all values were folded away
        if not new_values:
            # Default result based on operation
            self._fold_count += 1
            return Const(
                value=node.op == "and",  # and → True, or → False
                lineno=node.lineno,
                col_offset=node.col_offset,
            )

        # If only one value remains, return it directly
        if len(new_values) == 1:
            return new_values[0]

        # Rebuild with simplified values
        if len(new_values) == len(node.values) and all(
            a is b for a, b in zip(new_values, node.values, strict=True)
        ):
            return node

        return BoolOp(
            op=node.op,
            values=tuple(new_values),
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    def _fold_concat(self, node: Concat) -> Expr:
        """Fold string concatenation of constants."""
        # Concat node has sequence of expressions to join
        folded = [self._fold_node(e) for e in node.nodes]

        # All constants? Merge into single string
        if all(isinstance(e, Const) for e in folded):
            self._fold_count += 1
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
                    merged.append(
                        Const(
                            value="".join(pending),
                            lineno=node.lineno,
                            col_offset=node.col_offset,
                        )
                    )
                    pending = []
                merged.append(expr)
        if pending:
            merged.append(
                Const(
                    value="".join(pending),
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                )
            )

        # Check if we merged any adjacent constants
        if len(merged) < len(folded):
            self._fold_count += 1

        if len(merged) == 1:
            return merged[0]

        # Rebuild Concat with merged nodes
        return Concat(
            nodes=tuple(merged),
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    def _fold_container(self, node: Node) -> Node:
        """Recursively fold constants in container nodes."""
        changes = {}

        if hasattr(node, "body"):
            new_body = tuple(self._fold_node(n) for n in node.body)
            if any(a is not b for a, b in zip(new_body, node.body, strict=True)):
                changes["body"] = new_body

        if hasattr(node, "else_") and node.else_:
            new_else = tuple(self._fold_node(n) for n in node.else_)
            if any(a is not b for a, b in zip(new_else, node.else_, strict=True)):
                changes["else_"] = new_else

        if hasattr(node, "empty") and node.empty:
            new_empty = tuple(self._fold_node(n) for n in node.empty)
            if any(a is not b for a, b in zip(new_empty, node.empty, strict=True)):
                changes["empty"] = new_empty

        if hasattr(node, "test"):
            new_test = self._fold_node(node.test)
            if new_test is not node.test:
                changes["test"] = new_test

        if hasattr(node, "elif_") and node.elif_:
            new_elifs = []
            changed = False
            for test, body in node.elif_:
                new_test = self._fold_node(test)
                new_body = tuple(self._fold_node(n) for n in body)
                if new_test is not test or any(
                    a is not b for a, b in zip(new_body, body, strict=True)
                ):
                    changed = True
                new_elifs.append((new_test, new_body))
            if changed:
                changes["elif_"] = tuple(new_elifs)

        if not changes:
            return node

        # Reconstruct node with changes
        return replace(node, **changes)

    def _fold_expr_container(self, node: Node) -> Node:
        """Fold constants in nodes with expr attribute."""
        new_expr = self._fold_node(node.expr)
        if new_expr is node.expr:
            return node
        return replace(node, expr=new_expr)
