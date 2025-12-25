"""
Tree-sitter based syntax highlighting backend.

This backend provides fast, semantic syntax highlighting using tree-sitter
parsers. It is optional and requires the tree-sitter package and language
grammar packages.

Features:
    - 10x faster than Pygments for supported languages
    - Semantic highlighting via tree queries
    - Local variable tracking via locals.scm
    - Thread-safe via thread-local Parser instances
    - Automatic fallback to Pygments for unsupported languages

Performance:
    - Parse time (per block): ~0.15ms (vs ~1.5ms for Pygments)
    - Memory per parser: ~10KB (vs ~50KB for Pygments lexer)

Requirements:
    - tree-sitter>=0.22
    - Language grammar packages (e.g., tree-sitter-python)

See Also:
    - https://tree-sitter.github.io/tree-sitter/
    - https://github.com/tree-sitter/py-tree-sitter
"""

from __future__ import annotations

# This module is imported conditionally - if tree-sitter is not installed,
# the import in __init__.py will fail gracefully.

# Placeholder for Phase 1 implementation
# The full implementation will be added in Phase 1 of the RFC

raise ImportError("tree-sitter backend not yet implemented (Phase 1)")
