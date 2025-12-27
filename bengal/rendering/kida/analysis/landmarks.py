"""Landmark detection for template introspection.

Detects HTML5 landmark elements (nav, main, header, footer, aside, etc.)
in template output for structural classification and role inference.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Node

# HTML5 landmark elements
_LANDMARK_ELEMENTS = frozenset(
    {
        "nav",
        "main",
        "header",
        "footer",
        "aside",
        "article",
        "section",
    }
)

# Regex to find HTML tags in Data nodes
_TAG_RE = re.compile(r"<\s*(\w+)", re.IGNORECASE)


class LandmarkDetector:
    """Detect HTML5 landmark elements in template output.

    Analyzes Data nodes to find landmark elements like <nav>, <main>, etc.
    Used for structural classification and role inference.

    Example:
        >>> detector = LandmarkDetector()
        >>> landmarks = detector.detect(block_node)
        >>> print(landmarks)
        frozenset({'nav', 'main'})

    Limitations:
        - Only detects landmarks in static HTML (Data nodes)
        - Cannot detect dynamically generated tags
        - May miss landmarks inside included templates
    """

    def detect(self, node: Node) -> frozenset[str]:
        """Detect landmark elements in a node tree.

        Args:
            node: AST node to analyze.

        Returns:
            Frozen set of landmark element names found.
        """
        landmarks: set[str] = set()
        self._visit(node, landmarks)
        return frozenset(landmarks)

    def _visit(self, node: Any, landmarks: set[str]) -> None:
        """Visit node and collect landmarks."""
        if node is None:
            return

        node_type = type(node).__name__

        if node_type == "Data":
            # Scan static content for HTML tags
            for match in _TAG_RE.finditer(node.value):
                tag = match.group(1).lower()
                if tag in _LANDMARK_ELEMENTS:
                    landmarks.add(tag)
            return

        # Recurse into children
        for attr in ("body", "else_", "empty"):
            if hasattr(node, attr):
                children = getattr(node, attr)
                if children:
                    for child in children:
                        if hasattr(child, "lineno"):
                            self._visit(child, landmarks)

        # Handle elif
        if hasattr(node, "elif_") and node.elif_:
            for _test, body in node.elif_:
                for child in body:
                    if hasattr(child, "lineno"):
                        self._visit(child, landmarks)

        # Handle match cases
        if hasattr(node, "cases") and node.cases:
            for _pattern, _guard, body in node.cases:
                for child in body:
                    if hasattr(child, "lineno"):
                        self._visit(child, landmarks)

        # Handle blocks in embed
        if hasattr(node, "blocks") and isinstance(node.blocks, dict):
            for block in node.blocks.values():
                if hasattr(block, "lineno"):
                    self._visit(block, landmarks)
