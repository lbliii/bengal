"""
Skeleton Schema Definition.

Defines the data structures for site skeletons using the Component Model pattern.
Skeletons describe site structure declaratively, enabling generation of sites
from YAML manifests or programmatic construction.

Component Model:
    - Identity (type): What is it? (blog, doc, landing, etc.)
    - Mode (variant): How does it look? (hero, minimal, grid, etc.)
    - Data (props): What data does it have? (title, date, etc.)

Classes:
    Component: A single page or section in the skeleton
    Skeleton: Root container with global cascade and structure

Example:
    skeleton = Skeleton.from_yaml('''
    name: My Blog
    structure:
      - path: posts
        type: blog
        pages:
          - path: first-post
            props:
              title: My First Post
    ''')
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class Component:
    """
    A component in the site structure (Page or Section).

    Implements the Component Model pattern:
    - Identity: type (blog, doc, landing) - determines behavior
    - Mode: variant (hero, minimal, grid) - determines appearance
    - Data: props (title, date, author) - content data

    Components can contain child pages, making them sections.
    Cascade values are inherited by all descendants.

    Attributes:
        path: File/directory path relative to parent
        type: Component identity (determines template family)
        variant: Component mode (determines visual style)
        props: Data passed to template as frontmatter
        content: Raw markdown body content
        pages: Child components (if present, this is a section)
        cascade: Values to inherit to all descendants
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
        """
        Check if this component represents a section.

        Returns:
            True if component has child pages (is a directory)
        """
        return bool(self.pages)


@dataclass
class Skeleton:
    """
    Root definition of a site skeleton.

    A skeleton describes the complete structure of a site, including
    global cascade values that apply to all components and the
    hierarchical structure of pages and sections.

    Attributes:
        name: Human-readable skeleton name
        description: Brief description of the skeleton's purpose
        version: Schema version for compatibility
        cascade: Global cascade applied to all components
        structure: Top-level components in the site
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
        """
        Parse a skeleton from a YAML string.

        Args:
            content: YAML content defining the skeleton

        Returns:
            Skeleton instance populated from the YAML
        """
        data = yaml.safe_load(content)
        return cls._parse_node(data)

    @classmethod
    def _parse_node(cls, data: dict[str, Any]) -> Skeleton:
        """
        Parse skeleton data from a dictionary.

        Args:
            data: Parsed YAML dictionary

        Returns:
            Populated Skeleton instance
        """
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
        """
        Parse a single component from dictionary data.

        Handles normalization of legacy fields (layout -> variant,
        metadata -> props) for backward compatibility.

        Args:
            data: Component dictionary (modified during parsing)

        Returns:
            Populated Component instance
        """
        # Extract children first
        pages_data = data.pop("pages", [])
        pages = [cls._parse_component(p) for p in pages_data]

        # Extract core fields
        path = data.pop("path")
        type_ = data.pop("type", None)
        variant = data.pop("variant", None)
        content = data.pop("content", None)
        cascade = data.pop("cascade", {})

        # Normalize layout/hero_style to variant
        if not variant:
            variant = data.pop("layout", None) or data.pop("hero_style", None)

        # Normalize metadata to props
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
