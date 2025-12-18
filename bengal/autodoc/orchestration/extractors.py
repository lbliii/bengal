"""
Extraction wrappers for autodoc.

Provides facade functions for extracting documentation from Python, CLI, and OpenAPI sources.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.autodoc.base import DocElement
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


def extract_python(
    site: Site,
    python_config: dict,
) -> list[DocElement]:
    """Extract Python API documentation."""
    from bengal.autodoc.extractors.python import PythonExtractor

    source_dirs = python_config.get("source_dirs", [])
    exclude_patterns = python_config.get("exclude", [])

    extractor = PythonExtractor(exclude_patterns=exclude_patterns, config=python_config)
    all_elements = []

    for source_dir in source_dirs:
        source_path = Path(source_dir)
        # Treat relative paths as relative to the site root, not the current working directory.
        # This is critical for CI/public builds and for tests where the process CWD is not the
        # site root but the config uses relative paths (e.g., "src", "bengal").
        if not source_path.is_absolute():
            source_path = site.root_path / source_path
        if not source_path.exists():
            logger.warning(
                "autodoc_source_dir_not_found",
                path=str(source_path),
                type="python",
            )
            continue

        elements = extractor.extract(source_path)
        all_elements.extend(elements)

    logger.debug("autodoc_python_extracted", count=len(all_elements))
    return all_elements


def extract_cli(
    site: Site,
    cli_config: dict,
) -> list[DocElement]:
    """Extract CLI documentation."""
    from bengal.autodoc.extractors.cli import CLIExtractor

    app_module = cli_config.get("app_module")
    if not app_module:
        logger.warning("autodoc_cli_no_app_module")
        return []

    framework = cli_config.get("framework", "click")
    include_hidden = cli_config.get("include_hidden", False)

    # Load CLI app from module path (e.g., "bengal.cli:main")
    try:
        module_path, attr_name = app_module.split(":")
        module = importlib.import_module(module_path)
        cli_app = getattr(module, attr_name)
    except (ValueError, ImportError, AttributeError) as e:
        logger.warning("autodoc_cli_load_failed", app_module=app_module, error=str(e))
        return []

    # Extract documentation
    extractor = CLIExtractor(framework=framework, include_hidden=include_hidden)
    elements = extractor.extract(cli_app)

    logger.debug("autodoc_cli_extracted", count=len(elements))
    return elements


def extract_openapi(
    site: Site,
    openapi_config: dict,
) -> list[DocElement]:
    """Extract OpenAPI documentation."""
    from bengal.autodoc.extractors.openapi import OpenAPIExtractor

    spec_file = openapi_config.get("spec_file")
    if not spec_file:
        logger.warning("autodoc_openapi_no_spec_file")
        return []

    spec_path = Path(spec_file)
    # Treat relative paths as relative to the site root, not the current working directory.
    # This is critical for public/CI builds that run from a repo root while the site lives
    # in a subdirectory (e.g., <repo>/site).
    if not spec_path.is_absolute():
        spec_path = site.root_path / spec_path
    if not spec_path.exists():
        logger.warning("autodoc_openapi_spec_not_found", path=str(spec_path))
        return []

    # Extract documentation
    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)

    logger.debug("autodoc_openapi_extracted", count=len(elements))
    return elements
