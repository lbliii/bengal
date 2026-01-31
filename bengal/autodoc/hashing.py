"""
Hashing utilities for autodoc content.

Provides fine-grained hashing of documentation-relevant content to enable
selective rebuilds that skip code-only changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.utils.primitives.hashing import hash_str

if TYPE_CHECKING:
    from bengal.autodoc.base import DocElement


def compute_doc_content_hash(
    element: DocElement,
    *,
    include_signature: bool = True,
    include_decorators: bool = True,
) -> str:
    """
    Compute 16-character hash of documentation-relevant content only.

    Normalization Strategy:
    - Docstrings: strip(), skip empty lines.
    - Signatures: remove all whitespace.
    - Lists (decorators, bases): sorted() alphabetically.
    - Metadata: Deterministic JSON hashing of relevant fields.

    Args:
        element: DocElement to hash
        include_signature: Whether to include signatures in the hash
        include_decorators: Whether to include decorators in the hash

    Returns:
        16-character truncated SHA-256 hash
    """
    parts: list[str] = []

    # 1. Docstring / Description
    if element.description:
        # Normalize: strip each line and skip empty lines to ignore indentation/spacing changes
        normalized_lines = [
            line.strip() for line in element.description.strip().splitlines() if line.strip()
        ]
        if normalized_lines:
            parts.append("doc:" + "\n".join(normalized_lines))

    # 2. Type-specific metadata (Signatures, Bases, etc.)
    tm = element.typed_metadata

    # Python-specific
    # CLI-specific
    from bengal.autodoc.models.cli import CLICommandMetadata, CLIGroupMetadata, CLIOptionMetadata

    # OpenAPI-specific
    from bengal.autodoc.models.openapi import (
        OpenAPIEndpointMetadata,
        OpenAPISchemaMetadata,
    )
    from bengal.autodoc.models.python import PythonClassMetadata, PythonFunctionMetadata

    if isinstance(tm, PythonFunctionMetadata):
        if include_signature and tm.signature:
            parts.append("sig:" + tm.signature.replace(" ", ""))
        if include_decorators and tm.decorators:
            parts.append("dec:" + "|".join(sorted(tm.decorators)))

    elif isinstance(tm, PythonClassMetadata):
        if tm.bases:
            parts.append("bases:" + "|".join(sorted(tm.bases)))
        if include_decorators and tm.decorators:
            parts.append("dec:" + "|".join(sorted(tm.decorators)))

    elif isinstance(tm, (CLICommandMetadata, CLIGroupMetadata)):
        # CLI commands/groups are primarily defined by their help text (description)
        # but we also include callback name if it changes
        if tm.callback:
            parts.append("callback:" + tm.callback)

    elif isinstance(tm, CLIOptionMetadata):
        # Options have many relevant fields
        parts.append("opt:" + tm.name)
        parts.append("type:" + tm.type_name)
        parts.append("opts:" + "|".join(sorted(tm.opts)))
        if tm.envvar:
            parts.append("env:" + tm.envvar)
        if tm.default is not None:
            parts.append("def:" + str(tm.default))

    elif isinstance(tm, OpenAPIEndpointMetadata):
        parts.append("method:" + tm.method)
        parts.append("path:" + tm.path)
        if tm.operation_id:
            parts.append("opid:" + tm.operation_id)
        if tm.tags:
            parts.append("tags:" + "|".join(sorted(tm.tags)))
        # For parameters, request body, and responses, we use a simple summary hash
        # because these are complex nested objects.
        if tm.parameters:
            parts.append("params_count:" + str(len(tm.parameters)))
        if tm.responses:
            parts.append("resp_count:" + str(len(tm.responses)))

    elif isinstance(tm, OpenAPISchemaMetadata):
        if tm.schema_type:
            parts.append("type:" + tm.schema_type)
        if tm.required:
            parts.append("req:" + "|".join(sorted(tm.required)))
        if tm.enum:
            parts.append("enum:" + "|".join(sorted(str(e) for e in tm.enum)))
        # Properties affect schema docs significantly
        if tm.properties:
            parts.append("props:" + "|".join(sorted(tm.properties.keys())))

    # Fallback to metadata dict for other types or if typed_metadata missing
    else:
        # Signature fallback
        sig = element.metadata.get("signature")
        if include_signature and sig:
            parts.append("sig:" + str(sig).replace(" ", ""))

        # Decorators fallback
        decs = element.metadata.get("decorators")
        if include_decorators and decs and isinstance(decs, (list, tuple)):
            parts.append("dec:" + "|".join(sorted(str(d) for d in decs)))

        # Bases fallback
        bases = element.metadata.get("bases")
        if bases and isinstance(bases, (list, tuple)):
            parts.append("bases:" + "|".join(sorted(str(b) for b in bases)))

    # 3. Examples and See Also
    if element.examples:
        parts.append("examples:" + "|".join(sorted(element.examples)))
    if element.see_also:
        parts.append("see_also:" + "|".join(sorted(element.see_also)))
    if element.deprecated:
        parts.append("deprecated:" + element.deprecated)

    if not parts:
        # No documentation content found - return a hash of the qualified name
        # to ensure at least some stable identity.
        return hash_str(element.qualified_name, truncate=16)

    content = "\n".join(parts)
    return hash_str(content, truncate=16)
