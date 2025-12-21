"""
Signature building and argument extraction for Python functions/methods.

Provides utilities for building signature strings from AST nodes and
extracting structured argument information.
"""

from __future__ import annotations

import ast
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """
    Build function signature string from AST node.

    Args:
        node: Function definition AST node

    Returns:
        Signature string like "def foo(x: int, y: str = 'default') -> bool"
    """
    args_parts = []

    # Regular arguments
    for arg in node.args.args:
        part = arg.arg
        if arg.annotation:
            part += f": {annotation_to_string(arg.annotation)}"
        args_parts.append(part)

    # Add defaults
    defaults = node.args.defaults
    if defaults:
        for i, default in enumerate(defaults):
            idx = len(args_parts) - len(defaults) + i
            if idx >= 0:
                args_parts[idx] += f" = {expr_to_string(default)}"

    # *args
    if node.args.vararg:
        part = f"*{node.args.vararg.arg}"
        if node.args.vararg.annotation:
            part += f": {annotation_to_string(node.args.vararg.annotation)}"
        args_parts.append(part)

    # **kwargs
    if node.args.kwarg:
        part = f"**{node.args.kwarg.arg}"
        if node.args.kwarg.annotation:
            part += f": {annotation_to_string(node.args.kwarg.annotation)}"
        args_parts.append(part)

    # Build full signature
    async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    signature = f"{async_prefix}def {node.name}({', '.join(args_parts)})"

    # Add return annotation
    if node.returns:
        signature += f" -> {annotation_to_string(node.returns)}"

    return signature


def extract_arguments(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict[str, Any]]:
    """
    Extract argument information from function AST node.

    Args:
        node: Function definition AST node

    Returns:
        List of argument dicts with 'name', 'type', 'default' keys
    """
    args = []

    for arg in node.args.args:
        args.append(
            {
                "name": arg.arg,
                "type": annotation_to_string(arg.annotation) if arg.annotation else None,
                "default": None,  # Will be filled in with defaults
            }
        )

    # Add defaults
    defaults = node.args.defaults
    if defaults:
        for i, default in enumerate(defaults):
            idx = len(args) - len(defaults) + i
            if idx >= 0:
                args[idx]["default"] = expr_to_string(default)

    return args


def annotation_to_string(annotation: ast.expr | None) -> str | None:
    """
    Convert AST type annotation to string representation.

    Args:
        annotation: AST annotation expression

    Returns:
        String representation of the type annotation, or None
    """
    if annotation is None:
        return None

    try:
        return ast.unparse(annotation)
    except Exception as e:
        # Fallback for complex annotations
        logger.debug(
            "ast_unparse_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="using_ast_dump_fallback",
        )
        return ast.dump(annotation)


def expr_to_string(expr: ast.expr) -> str:
    """
    Convert AST expression to string representation.

    Args:
        expr: AST expression

    Returns:
        String representation of the expression
    """
    try:
        return ast.unparse(expr)
    except Exception as e:
        logger.debug(
            "ast_expr_unparse_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="using_ast_dump_fallback",
        )
        return ast.dump(expr)


def has_yield(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """
    Check if function contains yield statement (is a generator).

    Args:
        node: Function AST node

    Returns:
        True if function is a generator
    """
    return any(isinstance(child, ast.Yield | ast.YieldFrom) for child in ast.walk(node))
