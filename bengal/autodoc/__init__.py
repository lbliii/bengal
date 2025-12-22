"""
Autodoc - Automatic API documentation generation system.

This package generates API documentation as virtual pages during site build,
rendered directly via theme templates without intermediate markdown files.

Supported Documentation Types:
    - **Python API**: Extracts from source files via AST parsing (no imports)
    - **OpenAPI/REST API**: Parses OpenAPI 3.x YAML/JSON specifications
    - **CLI**: Documents Click, Typer, and argparse command-line interfaces

Key Components:
    - DocElement: Unified data model for all documented elements
    - Extractor: Base class for all documentation extractors
    - VirtualAutodocOrchestrator: Coordinates extraction and page generation
    - AutodocRunResult: Summary of generated pages and sections

Architecture:
    Autodoc follows Bengal's passive models pattern. Extractors produce
    DocElement trees, which the orchestrator converts to virtual Page
    and Section objects during the build phase.

Configuration:
    Configure via `config/_default/autodoc.yaml` or `bengal.toml`:

    ```yaml
    autodoc:
      python:
        enabled: true
        source_dirs: ["src/mypackage"]
      cli:
        enabled: true
        app_module: "mypackage.cli:main"
    ```

Example:
    >>> from bengal.autodoc import PythonExtractor, VirtualAutodocOrchestrator
    >>> extractor = PythonExtractor(config)
    >>> elements = extractor.extract(Path("src/mypackage"))

Related:
    - bengal/autodoc/extractors/: Documentation extractors
    - bengal/autodoc/models/: Typed metadata dataclasses
    - bengal/autodoc/orchestration/: Virtual page generation
    - architecture/autodoc.md: Full architecture documentation
"""

from __future__ import annotations

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.extractors.cli import CLIExtractor
from bengal.autodoc.extractors.openapi import OpenAPIExtractor
from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.orchestration import AutodocRunResult, VirtualAutodocOrchestrator

__all__ = [
    "AutodocRunResult",
    "CLIExtractor",
    "DocElement",
    "Extractor",
    "OpenAPIExtractor",
    "PythonExtractor",
    "VirtualAutodocOrchestrator",
]
