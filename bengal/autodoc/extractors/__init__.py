"""
Documentation extractors for the autodoc system.

This package contains extractors that convert various source types into
unified DocElement trees for rendering as API documentation.

Available Extractors:
    - PythonExtractor: Extracts from Python source via AST (no imports)
    - OpenAPIExtractor: Parses OpenAPI 3.x YAML/JSON specifications
    - CLIExtractor: Documents Click/Typer/argparse command-line interfaces

Architecture:
    All extractors implement the `Extractor` abstract base class from
    `bengal.autodoc.base`. Each produces a list of `DocElement` objects
    that can be rendered uniformly regardless of source type.

Performance:
    The Python extractor uses AST parsing (no code execution) for safety
    and speed. OpenAPI and CLI extractors are lazy-loaded to minimize
    import overhead when not used.

Example:
    >>> from bengal.autodoc.extractors import PythonExtractor
    >>> extractor = PythonExtractor(config={"source_dirs": ["src/"]})
    >>> elements = extractor.extract(Path("src/mypackage"))

Related:
    - bengal/autodoc/base.py: Extractor base class and DocElement model
    - bengal/autodoc/models/: Typed metadata for each extractor type
"""

from __future__ import annotations

from bengal.autodoc.extractors.openapi import OpenAPIExtractor
from bengal.autodoc.extractors.python import PythonExtractor

__all__ = ["OpenAPIExtractor", "PythonExtractor"]
