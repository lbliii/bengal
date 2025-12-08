"""
Bengal Autodoc - Virtual page documentation generation system.

Supports:
- Python API documentation (via AST)
- OpenAPI/REST API documentation
- CLI documentation (Click/argparse/typer)

Documentation is generated as virtual pages during site build,
rendered directly via theme templates without intermediate markdown files.
"""

from __future__ import annotations

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.extractors.cli import CLIExtractor
from bengal.autodoc.extractors.openapi import OpenAPIExtractor
from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.virtual_orchestrator import AutodocRunResult, VirtualAutodocOrchestrator

__all__ = [
    "AutodocRunResult",
    "CLIExtractor",
    "DocElement",
    "Extractor",
    "OpenAPIExtractor",
    "PythonExtractor",
    "VirtualAutodocOrchestrator",
]
