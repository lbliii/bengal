"""
Signature building and argument extraction for Python functions/methods.

Provides utilities for building signature strings from AST nodes and
extracting structured argument information.
"""

from __future__ import annotations

import ast
from typing import Any

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


def build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """
    Build function signature string from AST node.

    Args:
        node: Function definition AST node

    Returns:
        Signature string like "def foo(x: int, y: str = 'default') -> bool"

    """
    args_parts: list[str] = []

    # 1. Positional-only arguments
    if hasattr(node.args, "posonlyargs") and node.args.posonlyargs:
        num_posonly = len(node.args.posonlyargs)
        num_args = len(node.args.args)
        num_defaults = len(node.args.defaults)
        posonly_defaults_count = max(0, num_defaults - num_args)

        for i, arg in enumerate(node.args.posonlyargs):
            part = arg.arg
            if arg.annotation:
                part += f": {annotation_to_string(arg.annotation)}"

            # Check for defaults in posonlyargs (applied from right to left)
            if i >= num_posonly - posonly_defaults_count:
                default_idx = i - (num_posonly - posonly_defaults_count)
                part += f" = {expr_to_string(node.args.defaults[default_idx])}"

            args_parts.append(part)
        args_parts.append("/")

    # 2. Regular arguments
    num_args = len(node.args.args)
    num_defaults = len(node.args.defaults)
    args_defaults_count = min(num_args, num_defaults)

    for i, arg in enumerate(node.args.args):
        part = arg.arg
        if arg.annotation:
            part += f": {annotation_to_string(arg.annotation)}"

        # Check for defaults in args (applied from right to left)
        if i >= num_args - args_defaults_count:
            default_idx = i - (num_args - args_defaults_count) + max(0, num_defaults - num_args)
            part += f" = {expr_to_string(node.args.defaults[default_idx])}"

        args_parts.append(part)

    # 3. *args
    if node.args.vararg:
        part = f"*{node.args.vararg.arg}"
        if node.args.vararg.annotation:
            part += f": {annotation_to_string(node.args.vararg.annotation)}"
        args_parts.append(part)
    elif hasattr(node.args, "kwonlyargs") and node.args.kwonlyargs:
        # Bare * if we have kwonlyargs but no vararg
        args_parts.append("*")

    # 4. Keyword-only arguments
    if hasattr(node.args, "kwonlyargs"):
        for i, arg in enumerate(node.args.kwonlyargs):
            part = arg.arg
            if arg.annotation:
                part += f": {annotation_to_string(arg.annotation)}"

            # kw_defaults is 1:1 with kwonlyargs
            if node.args.kw_defaults[i] is not None:
                part += f" = {expr_to_string(node.args.kw_defaults[i])}"

            args_parts.append(part)

    # 5. **kwargs
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
        List of argument dicts with 'name', 'type', 'default', 'kind' keys

    """
    args = []

    # 1. Positional-only
    if hasattr(node.args, "posonlyargs"):
        num_posonly = len(node.args.posonlyargs)
        num_args = len(node.args.args)
        num_defaults = len(node.args.defaults)
        posonly_defaults_count = max(0, num_defaults - num_args)

        for i, arg in enumerate(node.args.posonlyargs):
            default = None
            if i >= num_posonly - posonly_defaults_count:
                default_idx = i - (num_posonly - posonly_defaults_count)
                default = expr_to_string(node.args.defaults[default_idx])

            args.append(
                {
                    "name": arg.arg,
                    "type": annotation_to_string(arg.annotation) if arg.annotation else None,
                    "default": default,
                    "kind": "positional_only",
                }
            )

    # 2. Regular arguments
    num_args = len(node.args.args)
    num_defaults = len(node.args.defaults)
    args_defaults_count = min(num_args, num_defaults)

    for i, arg in enumerate(node.args.args):
        default = None
        if i >= num_args - args_defaults_count:
            default_idx = i - (num_args - args_defaults_count) + max(0, num_defaults - num_args)
            default = expr_to_string(node.args.defaults[default_idx])

        args.append(
            {
                "name": arg.arg,
                "type": annotation_to_string(arg.annotation) if arg.annotation else None,
                "default": default,
                "kind": "positional_or_keyword",
            }
        )

    # 3. *args
    if node.args.vararg:
        args.append(
            {
                "name": f"*{node.args.vararg.arg}",
                "type": annotation_to_string(node.args.vararg.annotation)
                if node.args.vararg.annotation
                else None,
                "default": None,
                "kind": "var_positional",
            }
        )

    # 4. Keyword-only
    if hasattr(node.args, "kwonlyargs"):
        for i, arg in enumerate(node.args.kwonlyargs):
            default = None
            if node.args.kw_defaults[i] is not None:
                default = expr_to_string(node.args.kw_defaults[i])

            args.append(
                {
                    "name": arg.arg,
                    "type": annotation_to_string(arg.annotation) if arg.annotation else None,
                    "default": default,
                    "kind": "keyword_only",
                }
            )

    # 5. **kwargs
    if node.args.kwarg:
        args.append(
            {
                "name": f"**{node.args.kwarg.arg}",
                "type": annotation_to_string(node.args.kwarg.annotation)
                if node.args.kwarg.annotation
                else None,
                "default": None,
                "kind": "var_keyword",
            }
        )

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
