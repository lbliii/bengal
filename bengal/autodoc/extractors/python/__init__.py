"""
Python API documentation extractor package.

Extracts documentation from Python source files via AST parsing.
No imports required - fast and reliable.

Organization:
    - PythonExtractor: Main extractor class (this file, re-exported)
    - signature.py: Signature building and argument extraction
    - module_info.py: Module name inference and path resolution
    - inheritance.py: Inherited member synthesis
    - skip_logic.py: File/path filtering logic
    - aliases.py: Alias detection and __all__ extraction

Architecture:
    The extractor is intentionally single-pass for performance:
    1. Parse AST once per file
    2. Extract all elements in a single traversal
    3. Build class index for inheritance synthesis
    4. Apply grouping/output path logic

Related:
    - bengal/autodoc/docstring_parser.py: Docstring parsing (Google/NumPy/Sphinx)
    - bengal/autodoc/models/python.py: Typed metadata models
    - bengal/autodoc/utils.py: Shared utilities (grouping, sanitization)
"""

from __future__ import annotations

from bengal.autodoc.extractors.python.extractor import PythonExtractor

__all__ = ["PythonExtractor"]
