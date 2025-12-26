"""Compiler utilities for Kida.

Provides operator mapping utilities for AST generation.
"""

from __future__ import annotations

import ast


class OperatorUtilsMixin:
    """Mixin providing operator mapping utilities.

    Maps Kida operator strings to Python AST operator nodes.
    """

    def _get_binop(self, op: str) -> ast.operator:
        """Map operator string to AST operator."""
        ops = {
            "+": ast.Add(),
            "-": ast.Sub(),
            "*": ast.Mult(),
            "/": ast.Div(),
            "//": ast.FloorDiv(),
            "%": ast.Mod(),
            "**": ast.Pow(),
        }
        return ops.get(op, ast.Add())

    def _get_unaryop(self, op: str) -> ast.unaryop:
        """Map unary operator string to AST operator."""
        ops = {
            "-": ast.USub(),
            "+": ast.UAdd(),
            "not": ast.Not(),
        }
        return ops.get(op, ast.Not())

    def _get_cmpop(self, op: str) -> ast.cmpop:
        """Map comparison operator string to AST operator."""
        ops = {
            "==": ast.Eq(),
            "!=": ast.NotEq(),
            "<": ast.Lt(),
            "<=": ast.LtE(),
            ">": ast.Gt(),
            ">=": ast.GtE(),
            "in": ast.In(),
            "not in": ast.NotIn(),
            "is": ast.Is(),
            "is not": ast.IsNot(),
        }
        return ops.get(op, ast.Eq())
