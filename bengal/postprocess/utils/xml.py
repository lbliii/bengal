"""
XML formatting utilities for postprocess generators.

Provides shared XML manipulation functions used by RSS, Sitemap, and other
XML-based output generators.

Functions:
    indent_xml: Add indentation to XML elements for readability

Example:
    >>> import xml.etree.ElementTree as ET
    >>> from bengal.postprocess.utils.xml import indent_xml
    >>>
    >>> root = ET.Element("root")
    >>> child = ET.SubElement(root, "child")
    >>> child.text = "content"
    >>> indent_xml(root)
    >>> ET.tostring(root, encoding="unicode")
    '<root>\\n  <child>content</child>\\n</root>'

"""

from __future__ import annotations

import xml.etree.ElementTree as ET


def indent_xml(elem: ET.Element, level: int = 0) -> None:
    """
    Add indentation to XML element tree for readability.

    Recursively adds newlines and indentation to XML elements to produce
    human-readable output. Modifies the element tree in place.

    Args:
        elem: XML element to indent (modified in place)
        level: Current indentation level (default: 0 for root)

    Example:
        >>> import xml.etree.ElementTree as ET
        >>> root = ET.Element("rss")
        >>> channel = ET.SubElement(root, "channel")
        >>> title = ET.SubElement(channel, "title")
        >>> title.text = "My Feed"
        >>> indent_xml(root)
        >>> # Now root has proper indentation for pretty printing

    Note:
        This function modifies the element's `text` and `tail` attributes
        to add whitespace. It preserves existing text content.

    """
    indent = "\n" + "  " * level

    if len(elem):
        # Element has children
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent

        last_child: ET.Element | None = None
        for child in elem:
            indent_xml(child, level + 1)
            last_child = child

        # Set tail on last child (guaranteed non-None when len(elem) > 0)
        if last_child is not None and (not last_child.tail or not last_child.tail.strip()):
            last_child.tail = indent
    elif level and (not elem.tail or not elem.tail.strip()):
        # Leaf element (no children) - just set tail
        elem.tail = indent
