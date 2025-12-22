"""
Multi-style docstring parsing for Python documentation extraction.

This module provides parsers for the three major Python docstring conventions,
enabling autodoc to extract structured information from any docstring style.

Supported Styles:
    - **Google style**: Uses `Args:`, `Returns:`, `Raises:`, `Example:` sections
    - **NumPy style**: Uses underlined section headers (Parameters, Returns, etc.)
    - **Sphinx style**: Uses `:param:`, `:returns:`, `:raises:` field syntax

Auto-Detection:
    The `parse_docstring()` function can automatically detect the docstring style
    based on patterns in the text. This allows mixed-style codebases to be
    documented correctly without explicit configuration.

Architecture:
    Each parser class extracts the same structured data into a `ParsedDocstring`
    container, providing a uniform interface regardless of input style.

Example:
    >>> from bengal.autodoc.docstring_parser import parse_docstring
    >>> parsed = parse_docstring('''
    ...     Brief summary.
    ...
    ...     Args:
    ...         name: Parameter description
    ...
    ...     Returns:
    ...         str: Result description
    ... ''')
    >>> parsed.summary
    'Brief summary.'
    >>> parsed.args
    {'name': 'Parameter description'}

Related:
    - bengal/autodoc/extractors/python/: Uses these parsers for AST extraction
    - bengal/autodoc/models/python.py: ParsedDocstring frozen dataclass variant
"""

from __future__ import annotations

import re
import textwrap
from typing import Any


class ParsedDocstring:
    """
    Container for structured docstring data extracted by parsers.

    This class provides a uniform representation of docstring content regardless
    of the original style (Google, NumPy, or Sphinx). All parsers populate the
    same fields, enabling consistent template rendering.

    Attributes:
        summary: First line of the docstring (brief description)
        description: Full description including summary
        args: Parameter name → description mapping
        returns: Return value description
        return_type: Explicit return type (from Sphinx :rtype:)
        raises: List of exception dicts with 'type' and 'description'
        examples: Code examples extracted from docstring
        see_also: Cross-references to related items
        notes: Additional notes or caveats
        warnings: Warning messages for users
        deprecated: Deprecation notice if present
        version_added: Version when this API was added
        attributes: Class attribute name → description mapping
    """

    def __init__(self) -> None:
        self.summary: str = ""
        self.description: str = ""
        self.args: dict[str, str] = {}
        self.returns: str = ""
        self.return_type: str | None = None
        self.raises: list[dict[str, str]] = []
        self.examples: list[str] = []
        self.see_also: list[str] = []
        self.notes: list[str] = []
        self.warnings: list[str] = []
        self.deprecated: str | None = None
        self.version_added: str | None = None
        self.attributes: dict[str, str] = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "summary": self.summary,
            "description": self.description,
            "args": self.args,
            "returns": self.returns,
            "return_type": self.return_type,
            "raises": self.raises,
            "examples": self.examples,
            "see_also": self.see_also,
            "notes": self.notes,
            "warnings": self.warnings,
            "deprecated": self.deprecated,
            "version_added": self.version_added,
            "attributes": self.attributes,
        }


def parse_docstring(docstring: str | None, style: str = "auto") -> ParsedDocstring:
    """
    Parse docstring and extract structured information.

    Args:
        docstring: Raw docstring text
        style: Docstring style ('auto', 'google', 'numpy', 'sphinx')

    Returns:
        ParsedDocstring object with extracted information
    """
    if not docstring:
        return ParsedDocstring()

    # Auto-detect style
    if style == "auto":
        style = detect_docstring_style(docstring)

    # Parse based on detected style
    if style == "google":
        return GoogleDocstringParser().parse(docstring)
    elif style == "numpy":
        return NumpyDocstringParser().parse(docstring)
    elif style == "sphinx":
        return SphinxDocstringParser().parse(docstring)
    else:
        # Plain docstring - just summary
        result = ParsedDocstring()
        result.summary = docstring.strip().split("\n")[0]
        result.description = docstring.strip()
        return result


def detect_docstring_style(docstring: str) -> str:
    """
    Auto-detect docstring style.

    Args:
        docstring: Raw docstring text

    Returns:
        Style name ('google', 'numpy', 'sphinx', or 'plain')
    """
    # Google style markers
    if re.search(
        r"\n\s*(Args|Arguments|Parameters|Returns?|Yields?|Raises?|Note|Warning|Example|Examples|See Also|Attributes):\s*\n",
        docstring,
    ):
        return "google"

    # NumPy style markers (section with underline)
    if re.search(
        r"\n\s*(Parameters|Returns?|Yields?|Raises?|See Also|Notes?|Warnings?|Examples?|Attributes)\s*\n\s*-+\s*\n",
        docstring,
    ):
        return "numpy"

    # Sphinx style markers
    if re.search(r":param |:type |:returns?:|:rtype:|:raises?:", docstring):
        return "sphinx"

    return "plain"


class GoogleDocstringParser:
    """
    Parser for Google-style Python docstrings.

    Google style uses section headers followed by colons and indented content.
    This is the most common style in modern Python projects.

    Recognized Sections:
        - Args/Arguments/Parameters: Function parameters
        - Returns/Return: Return value description
        - Raises/Raise: Exceptions that may be raised
        - Example/Examples: Usage examples
        - Note/Notes: Additional information
        - Warning/Warnings: Cautions for users
        - See Also: Cross-references
        - Attributes: Class/module attributes
        - Deprecated: Deprecation notices

    Custom Sections:
        Unrecognized section headers (title-case phrases ending with colon)
        are preserved in the description field as markdown sections.

    Example Input:
        ```
        Brief summary line.

        Args:
            name (str): The name to greet
            loud (bool): Whether to shout

        Returns:
            str: The greeting message

        Raises:
            ValueError: If name is empty
        ```
    """

    def parse(self, docstring: str) -> ParsedDocstring:
        """Parse Google-style docstring."""
        result = ParsedDocstring()

        # Split into lines
        lines = docstring.split("\n")

        # Extract summary (first line)
        if lines:
            result.summary = lines[0].strip()

        # Split into sections
        sections = self._split_sections(docstring)

        # Known structured sections (we parse these specially)
        known_sections = {
            "Args",
            "Arguments",
            "Parameters",
            "Returns",
            "Return",
            "Raises",
            "Raise",
            "Example",
            "Examples",
            "See Also",
            "Note",
            "Notes",
            "Warning",
            "Warnings",
            "Deprecated",
            "Attributes",
            "Yields",
            "Yield",
            "description",
        }

        # Parse structured sections
        result.args = self._parse_args_section(sections.get("Args", ""))
        if not result.args:
            result.args = self._parse_args_section(sections.get("Arguments", ""))
        if not result.args:
            result.args = self._parse_args_section(sections.get("Parameters", ""))

        result.returns = sections.get("Returns", sections.get("Return", ""))
        result.raises = self._parse_raises_section(sections.get("Raises", ""))
        result.examples = self._parse_examples_section(
            sections.get("Example", sections.get("Examples", ""))
        )
        result.see_also = self._parse_see_also_section(sections.get("See Also", ""))
        result.notes = self._parse_note_section(sections.get("Note", sections.get("Notes", "")))
        result.warnings = self._parse_note_section(
            sections.get("Warning", sections.get("Warnings", ""))
        )
        result.deprecated = sections.get("Deprecated")
        result.attributes = self._parse_args_section(sections.get("Attributes", ""))

        # Build description: base description + custom sections (documentation prose)
        base_desc = sections.get("description", result.summary)
        # Dedent to prevent markdown treating indented content as code blocks
        description_parts = [textwrap.dedent(base_desc) if base_desc else ""]

        # Append custom sections to description (they're documentation, not structured data)
        for section_name, section_content in sections.items():
            if section_name not in known_sections and section_content:
                # Dedent the content to prevent markdown treating it as code block
                dedented = textwrap.dedent(section_content)
                # Format as markdown section
                description_parts.append(f"\n\n**{section_name}:**\n{dedented}")

        result.description = "\n".join(description_parts).strip()

        return result

    def _split_sections(self, docstring: str) -> dict[str, str]:
        """Split docstring into sections."""
        sections = {}
        lines = docstring.split("\n")

        # Known section markers (we care about extracting these)
        known_markers = [
            "Args",
            "Arguments",
            "Parameters",
            "Returns",
            "Return",
            "Yields",
            "Yield",
            "Raises",
            "Raise",
            "Note",
            "Notes",
            "Warning",
            "Warnings",
            "Example",
            "Examples",
            "See Also",
            "Deprecated",
            "Attributes",
        ]

        current_section = "description"
        section_buffer: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Check if this line is a section header
            is_section = False

            # First check known markers
            for marker in known_markers:
                if stripped == f"{marker}:":
                    # Save previous section
                    if section_buffer:
                        sections[current_section] = "\n".join(section_buffer).strip()
                        section_buffer = []
                    current_section = marker
                    is_section = True
                    break

            # Also detect custom section headers: unindented lines ending with ":"
            # but NOT argument patterns like "name (type): description"
            # Pattern: starts at column 0, is a title-like phrase ending with ":"
            # Custom section: "Cache File Format:", "Version Management:", etc.
            # Must be title-case words (not arg pattern which has lowercase or parens)
            if (
                not is_section
                and not line.startswith(" ")
                and not line.startswith("\t")
                and re.match(r"^[A-Z][A-Za-z\s]+:$", stripped)
            ):
                # Save previous section
                if section_buffer:
                    sections[current_section] = "\n".join(section_buffer).strip()
                    section_buffer = []
                current_section = stripped.rstrip(":")
                is_section = True

            if not is_section:
                section_buffer.append(line)

        # Save last section
        if section_buffer:
            sections[current_section] = "\n".join(section_buffer).strip()

        return sections

    def _parse_args_section(self, section: str) -> dict[str, str]:
        """
        Parse Args section.

        Format:
            name (type): description
            name: description
        """
        args: dict[str, str] = {}
        if not section:
            return args

        lines = section.split("\n")
        current_arg: str | None = None
        current_desc: list[str] = []

        for line in lines:
            # Check if this is a new argument
            # Pattern: "name (type): description" or "name: description"
            match = re.match(r"^\s*(\w+)\s*(?:\(([^)]+)\))?\s*:\s*(.+)?", line)
            if match:
                # Save previous arg
                if current_arg:
                    args[current_arg] = " ".join(current_desc).strip()

                # Start new arg
                current_arg = match.group(1)
                desc = match.group(3) or ""
                current_desc = [desc] if desc else []
            elif current_arg and line.strip():
                # Continuation of description
                current_desc.append(line.strip())

        # Save last arg
        if current_arg:
            args[current_arg] = " ".join(current_desc).strip()

        return args

    def _parse_raises_section(self, section: str) -> list[dict[str, str]]:
        """
        Parse Raises section.

        Format:
            ExceptionType: description
        """
        raises: list[dict[str, str]] = []
        if not section:
            return raises

        lines = section.split("\n")
        current_exc: str | None = None
        current_desc: list[str] = []

        for line in lines:
            match = re.match(r"^\s*(\w+)\s*:\s*(.+)?", line)
            if match:
                # Save previous exception
                if current_exc:
                    raises.append(
                        {"type": current_exc, "description": " ".join(current_desc).strip()}
                    )

                # Start new exception
                current_exc = match.group(1)
                desc = match.group(2) or ""
                current_desc = [desc] if desc else []
            elif current_exc and line.strip():
                current_desc.append(line.strip())

        # Save last exception
        if current_exc:
            raises.append({"type": current_exc, "description": " ".join(current_desc).strip()})

        return raises

    def _parse_examples_section(self, section: str) -> list[str]:
        """Extract code examples."""
        examples: list[str] = []
        if not section:
            return examples

        # Check if section contains explicit code block markers
        lines = section.split("\n")
        has_explicit_markers = any(
            ">>>" in line or line.strip().startswith("```") for line in lines
        )

        if not has_explicit_markers:
            # No explicit markers - treat entire section as one code example
            return [section.strip()]

        # Otherwise, look for >>> or explicit code blocks
        in_example = False
        current_example = []

        for line in lines:
            if ">>>" in line or line.strip().startswith("```"):
                in_example = True
                current_example.append(line)
            elif in_example:
                current_example.append(line)
                if line.strip().endswith("```") and len(current_example) > 1:
                    examples.append("\n".join(current_example))
                    current_example = []
                    in_example = False
            elif line.strip() and not in_example:
                # Non-code text, might be example description
                if not current_example:
                    current_example.append(line)

        if current_example:
            examples.append("\n".join(current_example))

        return examples

    def _parse_see_also_section(self, section: str) -> list[str]:
        """Extract cross-references."""
        see_also: list[str] = []
        if not section:
            return see_also

        for line in section.split("\n"):
            line = line.strip()
            if line:
                # Extract references (simple: just capture non-empty lines)
                see_also.append(line)

        return see_also

    def _parse_note_section(self, section: str) -> list[str]:
        """Extract notes or warnings."""
        notes: list[str] = []
        if not section:
            return notes

        # Split by paragraphs
        current_note = []
        for line in section.split("\n"):
            if line.strip():
                current_note.append(line.strip())
            elif current_note:
                notes.append(" ".join(current_note))
                current_note = []

        if current_note:
            notes.append(" ".join(current_note))

        return notes


class NumpyDocstringParser:
    """
    Parser for NumPy-style Python docstrings.

    NumPy style uses section headers underlined with dashes. This style is
    common in scientific Python packages (NumPy, SciPy, pandas, etc.).

    Recognized Sections:
        - Parameters: Function parameters with type on separate line
        - Returns: Return value with type on separate line
        - Yields: Generator yield values
        - Raises: Exceptions that may be raised
        - See Also: Cross-references to related items
        - Notes: Extended discussion and implementation details
        - Warnings: Cautions for users
        - Examples: Usage examples (often with doctest format)
        - Attributes: Class attributes
        - Methods: Class method summaries

    Example Input:
        ```
        Brief summary line.

        Parameters
        ----------
        name : str
            The name to greet.
        loud : bool, optional
            Whether to shout (default: False).

        Returns
        -------
        str
            The greeting message.
        ```
    """

    def parse(self, docstring: str) -> ParsedDocstring:
        """Parse NumPy-style docstring."""
        result = ParsedDocstring()

        # Extract summary
        lines = docstring.split("\n")
        if lines:
            result.summary = lines[0].strip()

        # Split into sections
        sections = self._split_sections(docstring)

        # Parse sections
        result.description = sections.get("description", result.summary)
        result.args = self._parse_parameters_section(sections.get("Parameters", ""))
        result.returns = sections.get("Returns", "")
        result.raises = self._parse_raises_section(sections.get("Raises", ""))
        result.examples = self._parse_examples_section(sections.get("Examples", ""))
        result.see_also = self._parse_see_also_section(sections.get("See Also", ""))
        result.notes = self._parse_note_section(sections.get("Notes", ""))
        result.warnings = self._parse_note_section(sections.get("Warnings", ""))
        result.attributes = self._parse_parameters_section(sections.get("Attributes", ""))

        return result

    def _split_sections(self, docstring: str) -> dict[str, str]:
        """Split NumPy docstring into sections."""
        sections = {}
        lines = docstring.split("\n")

        section_markers = [
            "Parameters",
            "Returns",
            "Yields",
            "Raises",
            "See Also",
            "Notes",
            "Warnings",
            "Examples",
            "Attributes",
            "Methods",
        ]

        current_section = "description"
        section_buffer: list[str] = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Check if this is a section header (followed by -----)
            if stripped in section_markers and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and all(c == "-" for c in next_line):
                    # Save previous section
                    if section_buffer:
                        sections[current_section] = "\n".join(section_buffer).strip()
                        section_buffer = []

                    current_section = stripped
                    i += 2  # Skip header and underline
                    continue

            section_buffer.append(line)
            i += 1

        # Save last section
        if section_buffer:
            sections[current_section] = "\n".join(section_buffer).strip()

        return sections

    def _parse_parameters_section(self, section: str) -> dict[str, str]:
        """
        Parse Parameters section.

        Format:
            name : type
                description
        """
        params: dict[str, str] = {}
        if not section:
            return params

        lines = section.split("\n")
        current_param: str | None = None
        current_desc: list[str] = []

        for line in lines:
            # Check for parameter definition: "name : type"
            if ":" in line and not line.startswith(" "):
                # Save previous param
                if current_param:
                    params[current_param] = " ".join(current_desc).strip()

                # Parse new param
                parts = line.split(":", 1)
                current_param = parts[0].strip()
                current_desc = []
            elif current_param and line.strip():
                # Description line (indented)
                current_desc.append(line.strip())

        # Save last param
        if current_param:
            params[current_param] = " ".join(current_desc).strip()

        return params

    def _parse_raises_section(self, section: str) -> list[dict[str, str]]:
        """Parse Raises section (similar to Parameters)."""
        raises: list[dict[str, str]] = []
        if not section:
            return raises

        lines = section.split("\n")
        current_exc: str | None = None
        current_desc: list[str] = []

        for line in lines:
            if not line.startswith(" ") and line.strip():
                # Save previous exception
                if current_exc:
                    raises.append(
                        {"type": current_exc, "description": " ".join(current_desc).strip()}
                    )

                # New exception type
                current_exc = line.strip()
                current_desc = []
            elif current_exc and line.strip():
                current_desc.append(line.strip())

        # Save last exception
        if current_exc:
            raises.append({"type": current_exc, "description": " ".join(current_desc).strip()})

        return raises

    def _parse_examples_section(self, section: str) -> list[str]:
        """Extract examples (usually code blocks)."""
        if not section:
            return []
        return [section.strip()]

    def _parse_see_also_section(self, section: str) -> list[str]:
        """Extract cross-references."""
        if not section:
            return []
        return [line.strip() for line in section.split("\n") if line.strip()]

    def _parse_note_section(self, section: str) -> list[str]:
        """Extract notes."""
        if not section:
            return []
        return [section.strip()]


class SphinxDocstringParser:
    """
    Parser for Sphinx/reStructuredText-style Python docstrings.

    Sphinx style uses inline field syntax with colons. This is the traditional
    style used by Sphinx autodoc and older Python projects.

    Recognized Fields:
        - :param name: Parameter description
        - :type name: Parameter type annotation
        - :returns: / :return: Return value description
        - :rtype: Return type annotation
        - :raises ExceptionType: Exception description

    Note:
        This parser handles the most common Sphinx field patterns. Some
        advanced Sphinx directives are not fully supported.

    Example Input:
        ```
        Brief summary line.

        :param name: The name to greet
        :type name: str
        :param loud: Whether to shout
        :type loud: bool
        :returns: The greeting message
        :rtype: str
        :raises ValueError: If name is empty
        ```
    """

    def parse(self, docstring: str) -> ParsedDocstring:
        """Parse Sphinx-style docstring."""
        result = ParsedDocstring()

        lines = docstring.split("\n")

        # Extract summary (first non-field line)
        summary_lines = []
        for line in lines:
            if not line.strip().startswith(":"):
                summary_lines.append(line)
            else:
                break

        if summary_lines:
            result.summary = summary_lines[0].strip()
            result.description = "\n".join(summary_lines).strip()

        # Parse field lists
        for line in lines:
            line = line.strip()

            # :param name: description
            match = re.match(r":param\s+(\w+):\s*(.+)", line)
            if match:
                param_name = match.group(1)
                param_desc = match.group(2)
                result.args[param_name] = param_desc
                continue

            # :returns: or :return: description
            match = re.match(r":returns?:\s*(.+)", line)
            if match:
                result.returns = match.group(1)
                continue

            # :rtype: type
            match = re.match(r":rtype:\s*(.+)", line)
            if match:
                result.return_type = match.group(1)
                continue

            # :raises Exception: description
            match = re.match(r":raises?\s+(\w+):\s*(.+)?", line)
            if match:
                exc_type = match.group(1)
                exc_desc = match.group(2) or ""
                result.raises.append({"type": exc_type, "description": exc_desc})
                continue

        return result
