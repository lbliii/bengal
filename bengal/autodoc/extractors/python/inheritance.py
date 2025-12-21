"""
Inherited member synthesis for Python classes.

Provides utilities for synthesizing inherited members from base classes
when include_inherited is enabled.
"""

from __future__ import annotations

from typing import Any

from bengal.autodoc.base import DocElement
from bengal.autodoc.utils import get_python_class_bases, get_python_function_is_property


def should_include_inherited(config: dict[str, Any], element_type: str = "class") -> bool:
    """
    Check if inherited members should be included for element type.

    Args:
        config: Extractor configuration
        element_type: Type of element ("class" or "exception")

    Returns:
        True if inherited members should be included
    """
    # Global toggle
    if config.get("include_inherited", False):
        return True

    # Per-type override
    by_type = config.get("include_inherited_by_type", {})
    return bool(by_type.get(element_type, False))


def synthesize_inherited_members(
    class_elem: DocElement,
    class_index: dict[str, DocElement],
    config: dict[str, Any],
) -> None:
    """
    Add inherited members to a class element.

    Modifies class_elem in place by appending inherited members
    from base classes found in class_index.

    Args:
        class_elem: Class DocElement to augment with inherited members
        class_index: Index mapping qualified class names to DocElements
        config: Extractor configuration
    """
    # Get base classes using typed accessor
    bases = get_python_class_bases(class_elem)
    if not bases:
        return

    # Track existing member names to avoid duplicates
    existing_members = {child.name for child in class_elem.children}

    # For each base class, look up in index and copy members
    for base_name in bases:
        # Try to find the base class in our index
        # Handle both simple names and qualified names
        base_elem = None

        # Try as-is first
        if base_name in class_index:
            base_elem = class_index[base_name]
        else:
            # Try to find by simple name match
            simple_base = base_name.split(".")[-1]
            for qualified, elem in class_index.items():
                if qualified.endswith(f".{simple_base}"):
                    base_elem = elem
                    break

        if not base_elem:
            continue

        # Copy methods and properties from base class
        include_private = config.get("include_private", False)

        for member in base_elem.children:
            # Skip if derived class overrides this member
            if member.name in existing_members:
                continue

            # Skip private members unless configured to include them
            if (
                member.name.startswith("_")
                and not member.name.startswith("__")
                and not include_private
            ):
                continue

            # Only inherit methods and properties
            if member.element_type not in (
                "method",
                "function",
            ) and not get_python_function_is_property(member):
                continue

            # Create inherited member entry
            inherited_member = DocElement(
                name=member.name,
                qualified_name=f"{class_elem.qualified_name}.{member.name}",
                description=f"Inherited from `{base_elem.qualified_name}`",
                element_type=member.element_type,
                source_file=member.source_file,
                line_number=member.line_number,
                metadata={
                    **member.metadata,
                    "inherited_from": base_elem.qualified_name,
                    "synthetic": True,
                },
            )
            class_elem.children.append(inherited_member)
            existing_members.add(member.name)
