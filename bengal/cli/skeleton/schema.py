"""
Skeleton Schema Definition.

This module defines the data structures for site skeletons, implementing the
Component Model (Identity/Mode/Data).

Key Concepts:
    - Component: Represents a page or section with Identity (type), Mode (variant), and Data (props)
    - Skeleton: The root container for the site structure
    - Cascade: Inheritance rules for nested components
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class Component:
    """
    A component in the site structure (Page or Section).

    Implements the Component Model:
    - Identity: type (what is it?)
    - Mode: variant (how does it look?)
    - Data: props (what data does it have?)
    """

    # Identity (Required for sections, inferred for pages)
    path: str

    # 1. Identity (Type)
    # Determines logic (sorting, validation) and template family
    type: str | None = None

    # 2. Mode (Variant)
    # Determines visual style (CSS, Hero, Layout)
    variant: str | None = None

    # 3. Data (Props)
    # Content passed to the template (frontmatter)
    props: dict[str, Any] = field(default_factory=dict)

    # 4. Content
    # Raw markdown content body
    content: str | None = None

    # 5. Children (Makes this a Section)
    pages: list[Component] = field(default_factory=list)

    # 6. Cascade (Inheritance)
    # Fields to apply to all children
    cascade: dict[str, Any] = field(default_factory=dict)

    def is_section(self) -> bool:
        """Check if this component represents a section."""
        return bool(self.pages)


@dataclass
class Skeleton:
    """
    Root definition of a site skeleton.
    """

    # Metadata about the skeleton itself
    name: str | None = None
    description: str | None = None
    version: str = "1.0"

    # Global cascade (applies to everything)
    cascade: dict[str, Any] = field(default_factory=dict)

    # The structure
    structure: list[Component] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, content: str) -> Skeleton:
        """Parse skeleton from YAML string."""
        data = yaml.safe_load(content)
        return cls._parse_node(data)

    @classmethod
    def _parse_node(cls, data: dict[str, Any]) -> Skeleton:
        """Recursive parser."""
        # Parse structure
        structure_data = data.get("structure", [])
        structure = [cls._parse_component(item) for item in structure_data]

        return cls(
            name=data.get("name"),
            description=data.get("description"),
            version=data.get("version", "1.0"),
            cascade=data.get("cascade", {}),
            structure=structure,
        )

    @classmethod
    def _parse_component(cls, data: dict[str, Any]) -> Component:
        """Parse a single component."""
        # Extract children first
        pages_data = data.pop("pages", [])
        pages = [cls._parse_component(p) for p in pages_data]

        # Extract core fields
        path = data.pop("path")
        type_ = data.pop("type", None)
        variant = data.pop("variant", None)
        content = data.pop("content", None)
        cascade = data.pop("cascade", {})

        # Legacy normalization (layout/hero_style -> variant)
        if not variant:
            variant = data.pop("layout", None) or data.pop("hero_style", None)

        # Legacy normalization (metadata -> props)
        props = data.pop("props", {})
        metadata = data.pop("metadata", {})
        if metadata:
            props.update(metadata)

        # Everything else remaining in 'data' is implicit props (flat frontmatter)
        # Merge them into props
        props.update(data)

        return Component(
            path=path,
            type=type_,
            variant=variant,
            props=props,
            content=content,
            pages=pages,
            cascade=cascade,
        )
