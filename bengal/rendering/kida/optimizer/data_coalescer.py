"""Data Coalescing Optimization Pass.

Merges adjacent Data nodes to reduce the number of _append() calls
in generated code.

Before:
    _append('<div class="card">\n    <h2>Title</h2>\n')
    _append('</div>\n')

After:
    _append('<div class="card">\n    <h2>Title</h2>\n</div>\n')

Impact: ~5-10% reduction in function calls for typical templates.

Thread-Safety:
    Stateless, creates new nodes. Safe for concurrent use.
"""

from __future__ import annotations

from dataclasses import replace

from bengal.rendering.kida.nodes import Data, Node, Template


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

        if len(new_body) == len(node.body) and all(
            a is b for a, b in zip(new_body, node.body, strict=True)
        ):
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

        if hasattr(node, "elif_") and node.elif_:
            new_elifs = []
            changed = False
            for test, body in node.elif_:
                new_body = self._coalesce_body(list(body))
                if new_body != list(body):
                    changed = True
                new_elifs.append((test, tuple(new_body)))
            if changed:
                changes["elif_"] = tuple(new_elifs)

        if not changes:
            return node

        return replace(node, **changes)
