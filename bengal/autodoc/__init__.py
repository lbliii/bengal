"""
Bengal Autodoc - Unified documentation generation system.

Supports:
- Python API documentation (via AST)
- OpenAPI/REST API documentation
- CLI documentation (Click/argparse/typer)

All with shared templates, cross-references, and incremental builds.
"""


from __future__ import annotations

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.extractors.cli import CLIExtractor
from bengal.autodoc.generator import DocumentationGenerator

__all__ = [
    "CLIExtractor",
    "DocElement",
    "DocumentationGenerator",
    "Extractor",
]
