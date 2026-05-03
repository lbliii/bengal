"""Compatibility imports for rendering-owned reference registries."""

from __future__ import annotations

from bengal.rendering.reference_registry import (
    InternalReferenceResolver,
    LinkRegistry,
    build_link_registry,
    build_link_registry_from_artifacts,
    build_reference_resolver,
)

__all__ = [
    "InternalReferenceResolver",
    "LinkRegistry",
    "build_link_registry",
    "build_link_registry_from_artifacts",
    "build_reference_resolver",
]
