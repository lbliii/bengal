"""Dead Code Elimination Optimization Pass.

Removes statically unreachable code from the AST, including:
- `{% if false %}...{% end %}` → removed entirely
- `{% if true %}body{% end %}` → body inlined (no If node)
- `{% if true %}body{% else %}unreachable{% end %}` → body only
- Empty For loops with empty iterable literal → removed

Thread-Safety:
    Stateless, creates new nodes. Safe for concurrent use.
"""

from __future__ import annotations

from dataclasses import replace

from bengal.rendering.kida.nodes import (
    Const,
    For,
    If,
    Node,
    Template,
)
from bengal.rendering.kida.nodes import (
    List as ListNode,
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
                    if isinstance(first_elif_test, Const):
                        if first_elif_test.value:
                            # First elif is true → inline its body
                            return self._eliminate_body(list(first_elif_body))
                        else:
                            # First elif is false, check remaining elifs
                            remaining_elifs = node.elif_[1:]
                            if remaining_elifs:
                                # Recurse with remaining elifs
                                new_if = If(
                                    test=remaining_elifs[0][0],
                                    body=remaining_elifs[0][1],
                                    elif_=remaining_elifs[1:],
                                    else_=node.else_,
                                    lineno=node.lineno,
                                    col_offset=node.col_offset,
                                )
                                return self._eliminate_if(new_if)
                            elif node.else_:
                                return self._eliminate_body(list(node.else_))
                            else:
                                return None
                    # Non-constant elif - keep as new If
                    new_if = If(
                        test=first_elif_test,
                        body=first_elif_body,
                        elif_=node.elif_[1:],
                        else_=node.else_,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                    )
                    return self._eliminate_container(new_if)
                if node.else_:
                    # Has else → inline else body
                    return self._eliminate_body(list(node.else_))
                else:
                    # No else → remove entirely
                    return None

        # Non-constant test - recurse into children
        return self._eliminate_container(node)

    def _eliminate_for(self, node: For) -> Node | list[Node] | None:
        """Eliminate empty For loops."""
        # Check for empty literal iterable
        if isinstance(node.iter, ListNode) and not node.iter.items:
            self._eliminate_count += 1
            # Empty list literal → remove loop
            if node.empty:
                # Has empty block → inline it
                return self._eliminate_body(list(node.empty))
            return None

        # Recurse into body
        return self._eliminate_container(node)

    def _eliminate_container(self, node: Node) -> Node:
        """Recursively eliminate dead code in container nodes."""
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
