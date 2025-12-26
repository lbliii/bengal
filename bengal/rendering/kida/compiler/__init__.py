"""Kida Compiler — transforms AST into Python code.

The `compiler` package provides the core logic for compiling Kida template
AST nodes into Python AST, then into executable code objects.

Public API:
    Compiler: Main compiler class for Kida templates
"""

from __future__ import annotations

from bengal.rendering.kida.compiler.core import Compiler

__all__ = [
    "Compiler",
]
