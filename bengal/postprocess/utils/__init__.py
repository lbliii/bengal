"""
Shared utilities for postprocess generators.

This package provides common functions used across all postprocess generators
to ensure consistent behavior and reduce code duplication.

Modules:
    xml: XML formatting utilities (indent_xml)
    page_data: Page data extraction utilities (get_section_name, tags_to_list)

Example:
    >>> from bengal.postprocess.utils import indent_xml, get_section_name, tags_to_list
    >>>
    >>> # Format XML element
    >>> indent_xml(root_element)
    >>>
    >>> # Extract section name from page
    >>> section = get_section_name(page)
    >>>
    >>> # Convert tags to list safely
    >>> tag_list = tags_to_list(page.tags)

"""

from __future__ import annotations

from bengal.postprocess.utils.page_data import get_section_name, tags_to_list
from bengal.postprocess.utils.xml import indent_xml

__all__ = [
    "get_section_name",
    "indent_xml",
    "tags_to_list",
]
