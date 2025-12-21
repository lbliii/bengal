"""
Section builders for autodoc.

Creates virtual Section hierarchies for Python, CLI, and OpenAPI documentation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.autodoc.base import DocElement
from bengal.autodoc.utils import get_openapi_tags, resolve_cli_url_path
from bengal.core.section import Section
from bengal.utils.logger import get_logger
from bengal.utils.url_normalization import join_url_paths

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


def create_python_sections(
    elements: list[DocElement],
    site: Site,
    resolve_output_prefix: callable,
) -> dict[str, Section]:
    """
    Create virtual section hierarchy from doc elements.

    Creates sections for:
    - /{prefix}/ (root Python API section, e.g., /api/python/)
    - /{prefix}/<package>/ (for each top-level package)
    - /{prefix}/<package>/<subpackage>/ (nested packages)

    Args:
        elements: List of DocElements (modules) to process
        site: Site instance
        resolve_output_prefix: Function to resolve output prefix for doc type

    Returns:
        Dictionary mapping section path to Section object
    """
    sections: dict[str, Section] = {}

    # Resolve output prefix for Python docs
    prefix = resolve_output_prefix("python")
    prefix_parts = prefix.split("/") if prefix else []
    root_name = prefix_parts[-1] if prefix_parts else "python"

    # Build lookup of package descriptions from __init__.py modules
    # Key: qualified_name (e.g., "bengal.core"), Value: description
    package_descriptions: dict[str, str] = {}
    for element in elements:
        if element.element_type == "module" and element.description:
            # This module's description can describe its package
            package_descriptions[element.qualified_name] = element.description

    # Create root Python API section
    api_section = Section.create_virtual(
        name=root_name,
        relative_url=join_url_paths(prefix),
        title="Python API Reference",
        metadata={
            "type": "autodoc-python",
            "weight": 100,
            "icon": "book",
            "description": "Browse Python API documentation by package.",
            "nav_root": True,  # Act as navigation root (don't show parent in sidebar)
        },
    )
    sections[prefix] = api_section

    # Track package hierarchy
    for element in elements:
        if element.element_type != "module":
            continue

        # Parse module qualified name (e.g., "bengal.core.page")
        parts = element.qualified_name.split(".")

        # Create sections for package hierarchy
        current_section = api_section
        section_path = prefix

        for i, part in enumerate(parts[:-1]):  # Skip the final module
            section_path = f"{section_path}/{part}"

            if section_path not in sections:
                # Create new package section
                relative_url = join_url_paths(prefix, *parts[: i + 1])
                qualified_name = ".".join(parts[: i + 1])

                # Try to find description from the package's __init__.py
                description = package_descriptions.get(qualified_name, "")

                package_section = Section.create_virtual(
                    name=part,
                    relative_url=relative_url,
                    title=part.replace("_", " ").title(),
                    metadata={
                        "type": "autodoc-python",
                        "qualified_name": qualified_name,
                        "description": description,
                    },
                )
                current_section.add_subsection(package_section)
                sections[section_path] = package_section
                current_section = package_section
            else:
                current_section = sections[section_path]

    logger.debug(
        "autodoc_sections_created",
        count=len(sections),
        paths=list(sections.keys()),
    )

    return sections


def create_cli_sections(
    elements: list[DocElement],
    site: Site,
    resolve_output_prefix: callable,
) -> dict[str, Section]:
    """
    Create CLI section hierarchy.

    Creates sections for:
    - /{prefix}/ (root CLI section, e.g., /cli/)
    - /{prefix}/<group>/ (for each command group)
    - /{prefix}/<group>/<subgroup>/ (nested command groups)

    This mirrors the hierarchical approach used by create_python_sections(),
    ensuring proper NavTree navigation with nested subsections.

    Args:
        elements: List of DocElements (commands and command-groups) to process
        site: Site instance
        resolve_output_prefix: Function to resolve output prefix for doc type

    Returns:
        Dictionary mapping section path to Section object
    """
    sections: dict[str, Section] = {}

    # Resolve output prefix for CLI docs
    prefix = resolve_output_prefix("cli")
    prefix_parts = prefix.split("/") if prefix else []
    root_name = prefix_parts[-1] if prefix_parts else "cli"

    # Create root CLI section
    cli_section = Section.create_virtual(
        name=root_name,
        relative_url=join_url_paths(prefix),
        title="CLI Reference",
        metadata={
            "type": "autodoc-cli",
            "weight": 100,
            "icon": "terminal",
            "description": "Command-line interface documentation.",
            "nav_root": True,  # Act as navigation root (don't show parent in sidebar)
        },
    )
    sections[prefix] = cli_section

    # Group commands by command-group
    command_groups: dict[str, list[DocElement]] = {}
    standalone_commands: list[DocElement] = []

    for element in elements:
        if element.element_type == "command-group":
            command_groups[element.qualified_name] = []
        elif element.element_type == "command":
            # Check if command has a parent group
            parts = element.qualified_name.split(".")
            if len(parts) > 1:
                parent_group = ".".join(parts[:-1])
                if parent_group not in command_groups:
                    command_groups[parent_group] = []
                command_groups[parent_group].append(element)
            else:
                standalone_commands.append(element)

    # Create sections for ALL command groups with proper hierarchy
    # Empty groups still need sections for navigation and index pages
    for group_name in command_groups:
        # Build URL path components (drops root command, e.g., "bengal.utils" → "utils")
        group_path = resolve_cli_url_path(group_name)

        # Skip the root command group (e.g., "bengal") - its section is already
        # created above as cli_section. Otherwise we'd overwrite it and lose subsections.
        if not group_path:
            continue

        # Split into path parts for hierarchical section creation
        # e.g., "utils/assets" → ["utils", "assets"]
        group_parts = group_path.split("/")

        # Walk down the hierarchy, creating intermediate sections as needed
        # This ensures e.g., /cli/utils/ exists before /cli/utils/assets/
        current_section = cli_section
        section_path = prefix

        for i, part in enumerate(group_parts):
            section_path = f"{section_path}/{part}"

            if section_path not in sections:
                # Build qualified name for this level
                # Original qualified_name is like "bengal.utils.assets"
                # We need to reconstruct partial qualified names for intermediate levels
                group_name_parts = group_name.split(".")
                # Find how many parts from the original name correspond to this level
                # group_path has i+1 parts at this point, plus 1 for the root we skipped
                partial_qualified_name = ".".join(group_name_parts[: i + 2])

                group_section = Section.create_virtual(
                    name=part,
                    relative_url=join_url_paths(prefix, *group_parts[: i + 1]),
                    title=part.replace("_", " ").title(),
                    metadata={
                        "type": "autodoc-cli",
                        "qualified_name": partial_qualified_name,
                    },
                )
                current_section.add_subsection(group_section)
                sections[section_path] = group_section
                current_section = group_section
            else:
                current_section = sections[section_path]

    logger.debug(
        "autodoc_sections_created",
        count=len(sections),
        type="cli",
        subsection_count=len(cli_section.subsections),
    )
    return sections


def create_openapi_sections(
    elements: list[DocElement],
    site: Site,
    resolve_output_prefix: callable,
    _existing_sections: dict[str, Section] | None = None,
) -> dict[str, Section]:
    """Create OpenAPI section hierarchy."""
    sections: dict[str, Section] = {}
    # Note: _existing_sections parameter kept for API compatibility but no longer used
    # Each autodoc type now creates its own distinct section tree

    # Resolve output prefix for OpenAPI docs
    prefix = resolve_output_prefix("openapi")
    prefix_parts = prefix.split("/") if prefix else []
    root_name = prefix_parts[-1] if prefix_parts else "rest"

    # Create root OpenAPI section (always new, never reuse)
    api_section = Section.create_virtual(
        name=root_name,
        relative_url=join_url_paths(prefix),
        title="REST API Reference",
        metadata={
            "type": "autodoc-rest",
            "weight": 100,
            "icon": "book",
            "description": "REST API documentation.",
            "nav_root": True,  # Act as navigation root (don't show parent in sidebar)
        },
    )
    sections[prefix] = api_section

    # Group endpoints by tags
    tagged_endpoints: dict[str, list[DocElement]] = {}
    untagged_endpoints: list[DocElement] = []

    for element in elements:
        if element.element_type == "openapi_endpoint":
            tags = get_openapi_tags(element)
            if tags:
                for tag in tags:
                    if tag not in tagged_endpoints:
                        tagged_endpoints[tag] = []
                    tagged_endpoints[tag].append(element)
            else:
                untagged_endpoints.append(element)
        elif element.element_type == "openapi_overview":
            # Overview goes at root
            pass
        elif element.element_type == "openapi_schema":
            # Schemas go in a schemas section
            schemas_key = f"{prefix}/schemas"
            if schemas_key not in sections:
                schemas_section = Section.create_virtual(
                    name="schemas",
                    relative_url=join_url_paths(prefix, "schemas"),
                    title="Schemas",
                    metadata={
                        "type": "autodoc-rest",
                        "description": "API data schemas and models.",
                    },
                )
                api_section.add_subsection(schemas_section)
                sections[schemas_key] = schemas_section

    # Create sections for tags
    for tag, _endpoints in tagged_endpoints.items():
        tag_section = Section.create_virtual(
            name=tag,
            relative_url=join_url_paths(prefix, "tags", tag),
            title=tag.replace("-", " ").title(),
            metadata={
                "type": "autodoc-rest",
                "tag": tag,
            },
        )
        api_section.add_subsection(tag_section)
        sections[f"{prefix}/tags/{tag}"] = tag_section

    logger.debug("autodoc_sections_created", count=len(sections), type="openapi")
    return sections


def create_aggregating_parent_sections(
    sections: dict[str, Section],
) -> dict[str, Section]:
    """
    Create aggregating parent sections for shared prefixes.

    When multiple autodoc types share a common prefix (e.g., api/python and
    api/openapi), this creates a parent section (e.g., api/) that aggregates
    them. This enables:
    - A navigable /api/ page showing all API documentation types
    - Correct Dev dropdown detection (finds 'api' section)

    The aggregating section uses 'api-hub' type which renders an agnostic
    landing page showing all child API documentation types (Python, REST, etc.)
    instead of using a type-specific template.

    Args:
        sections: Existing section dictionary

    Returns:
        Dictionary of newly created parent sections
    """
    parent_sections: dict[str, Section] = {}

    # Find all unique parent paths that have multiple IMMEDIATE children
    # e.g., "api" is parent of "api/python" and "api/bengal-demo-commerce"
    # but NOT "api/python/analysis" (that's a grandchild, child of "api/python")
    parent_counts: dict[str, list[str]] = {}
    for section_path in sections:
        parts = section_path.split("/")
        # Only count IMMEDIATE children (exactly one level deep from top-level)
        # "api/python" → 2 parts, parent "api" ✓
        # "api/python/analysis" → 3 parts (skip for top-level parent aggregation)
        if len(parts) == 2:
            parent = parts[0]
            parent_counts.setdefault(parent, []).append(section_path)

    # Create parent sections for paths with at least 1 immediate child
    # (even with 1 child, we need the parent for menu detection - e.g., /api/ for dev dropdown)
    for parent_path, child_paths in parent_counts.items():
        # Skip if parent already exists
        if parent_path in sections:
            continue

        # Collect child types for template to display appropriate icons/labels
        child_types = list(
            set(sections[cp].metadata.get("type", "autodoc-python") for cp in child_paths)
        )

        # Create the parent section with 'api-hub' type for agnostic landing page
        # This uses a dedicated template that shows all child API types
        parent_section = Section.create_virtual(
            name=parent_path,
            relative_url=join_url_paths(parent_path),
            title=f"{parent_path.replace('-', ' ').title()} Documentation",
            metadata={
                "type": "autodoc-hub",  # Dedicated type for aggregating API sections
                "weight": 50,
                "icon": "book-open",
                "description": f"Browse all {parent_path} documentation.",
                "is_aggregating_section": True,
                "child_types": child_types,  # Track aggregated types for template
            },
        )

        # Link only immediate child sections as subsections
        # (nested sections like api/python/analysis are already children of api/python)
        for child_path in child_paths:
            child_section = sections[child_path]
            parent_section.add_subsection(child_section)

        parent_sections[parent_path] = parent_section
        logger.debug(
            "autodoc_aggregating_section_created",
            parent=parent_path,
            children=child_paths,
            child_types=child_types,
        )

    return parent_sections
