"""
Typed metadata models for autodoc system.

This package provides type-safe metadata dataclasses that replace
the untyped `metadata: dict[str, Any]` field on DocElement.

Usage:
    from bengal.autodoc.models import PythonClassMetadata, DocMetadata

    if isinstance(element.typed_metadata, PythonClassMetadata):
        bases = element.typed_metadata.bases  # Type-safe!

Architecture:
    - common.py: Shared types (SourceLocation, QualifiedName)
    - python.py: Python-specific metadata (module, class, function)
    - cli.py: CLI-specific metadata (command, group, option)
    - openapi.py: OpenAPI-specific metadata (endpoint, schema, overview)
"""

from __future__ import annotations

from bengal.autodoc.models.cli import (
    CLICommandMetadata,
    CLIGroupMetadata,
    CLIOptionMetadata,
)
from bengal.autodoc.models.common import QualifiedName, SourceLocation
from bengal.autodoc.models.openapi import (
    OpenAPIEndpointMetadata,
    OpenAPIOverviewMetadata,
    OpenAPIParameterMetadata,
    OpenAPIRequestBodyMetadata,
    OpenAPIResponseMetadata,
    OpenAPISchemaMetadata,
)
from bengal.autodoc.models.python import (
    ParameterInfo,
    ParsedDocstring,
    PythonAliasMetadata,
    PythonAttributeMetadata,
    PythonClassMetadata,
    PythonFunctionMetadata,
    PythonModuleMetadata,
)

# Union type for all metadata
type DocMetadata = (
    PythonModuleMetadata
    | PythonClassMetadata
    | PythonFunctionMetadata
    | PythonAttributeMetadata
    | PythonAliasMetadata
    | CLICommandMetadata
    | CLIGroupMetadata
    | CLIOptionMetadata
    | OpenAPIEndpointMetadata
    | OpenAPIOverviewMetadata
    | OpenAPISchemaMetadata
)

__all__ = [
    # Common
    "QualifiedName",
    "SourceLocation",
    # Python
    "ParameterInfo",
    "ParsedDocstring",
    "PythonAliasMetadata",
    "PythonAttributeMetadata",
    "PythonClassMetadata",
    "PythonFunctionMetadata",
    "PythonModuleMetadata",
    # CLI
    "CLICommandMetadata",
    "CLIGroupMetadata",
    "CLIOptionMetadata",
    # OpenAPI
    "OpenAPIEndpointMetadata",
    "OpenAPIOverviewMetadata",
    "OpenAPIParameterMetadata",
    "OpenAPIRequestBodyMetadata",
    "OpenAPIResponseMetadata",
    "OpenAPISchemaMetadata",
    # Union
    "DocMetadata",
]
