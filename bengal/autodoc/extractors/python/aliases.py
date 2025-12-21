"""
Alias detection and __all__ extraction for Python modules.

Provides utilities for detecting simple assignment aliases at module level
and extracting __all__ exports.
"""

from __future__ import annotations

import ast


def detect_aliases(
    tree: ast.Module,
    module_name: str,
    defined_names: set[str],
    expr_to_string: callable,
) -> dict[str, str]:
    """
    Detect simple assignment aliases at module level.

    Patterns detected:
    - alias = original (ast.Name)
    - alias = module.original (ast.Attribute)

    Args:
        tree: Module AST
        module_name: Current module qualified name
        defined_names: Set of names defined in this module
        expr_to_string: Function to convert AST expr to string

    Returns:
        Dict mapping alias_name -> qualified_original
    """
    aliases = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            # Only handle single-target simple assignments
            if len(node.targets) != 1:
                continue

            target = node.targets[0]

            # Target must be a simple name (not attribute or subscript)
            if not isinstance(target, ast.Name):
                continue

            alias_name = target.id

            # Value must be Name or Attribute
            if isinstance(node.value, ast.Name):
                # alias = original
                original = node.value.id
                if original in defined_names:
                    aliases[alias_name] = f"{module_name}.{original}"

            elif isinstance(node.value, ast.Attribute):
                # alias = module.original
                original_qualified = expr_to_string(node.value)
                # Only track if it looks like it's in our documented corpus
                if original_qualified and "." in original_qualified:
                    aliases[alias_name] = original_qualified

    return aliases


def extract_all_exports(tree: ast.Module) -> list[str] | None:
    """
    Extract __all__ exports if present in module.

    Args:
        tree: Module AST

    Returns:
        List of exported names, or None if __all__ not defined
    """
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "__all__"
                    and isinstance(node.value, ast.List | ast.Tuple)
                ):
                    # Try to extract the list
                    exports = []
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            exports.append(elt.value)
                    return exports
    return None
