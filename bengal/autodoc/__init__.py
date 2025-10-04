"""
Bengal Autodoc - Unified documentation generation system.

Supports:
- Python API documentation (via AST)
- OpenAPI/REST API documentation
- CLI documentation (Click/argparse/typer)

All with shared templates, cross-references, and incremental builds.
"""

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.generator import DocumentationGenerator
from bengal.autodoc.extractors.cli import CLIExtractor

__all__ = [
    'DocElement',
    'Extractor',
    'DocumentationGenerator',
    'CLIExtractor',
]

