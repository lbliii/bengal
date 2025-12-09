"""
Pre-parse validation for directives.

Validates directive syntax before parsing to catch errors early with
helpful messages.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class DirectiveSyntaxValidator:
    """
    Validates directive syntax before parsing.

    Catches common errors early with helpful messages before expensive
    parsing and recursive markdown processing.
    """

    # Known directive types
    KNOWN_DIRECTIVES = {
        "tabs",
        "note",
        "tip",
        "warning",
        "danger",
        "error",
        "info",
        "example",
        "success",
        "caution",
        "dropdown",
        "details",
        "code-tabs",
        "code_tabs",
    }

    # Admonition types (subset of known directives)
    ADMONITION_TYPES = {
        "note",
        "tip",
        "warning",
        "danger",
        "error",
        "info",
        "example",
        "success",
        "caution",
    }

    @staticmethod
    def validate_tabs_directive(
        content: str, file_path: Path | None = None, line_number: int | None = None
    ) -> list[str]:
        """
        Validate tabs directive content.

        Args:
            content: Directive content (between opening and closing backticks)
            file_path: Optional file path for error messages
            line_number: Optional line number for error messages

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not content or not content.strip():
            errors.append("Tabs directive has no content")
            return errors

        # Check for tab markers: ### Tab: Title
        tab_markers = re.findall(r"^### Tab: (.+)$", content, re.MULTILINE)

        if len(tab_markers) == 0:
            # Check for common typos
            bad_markers = re.findall(r"^###\s*Ta[^b]", content, re.MULTILINE)
            if bad_markers:
                errors.append(
                    "Malformed tab marker found. "
                    "Use format: ### Tab: Title (note the space after colon)"
                )
            else:
                errors.append(
                    "Tabs directive has no tab markers. Use ### Tab: Title to create tabs"
                )

        elif len(tab_markers) == 1:
            errors.append(
                "Tabs directive has only 1 tab. "
                "For single items, use an admonition (note, tip, etc.) instead"
            )

        # Check for excessive tabs (performance warning)
        if len(tab_markers) > 10:
            errors.append(
                f"Tabs directive has {len(tab_markers)} tabs (>10). "
                "Consider splitting into multiple tabs blocks or separate pages for better performance"
            )

        return errors

    @staticmethod
    def validate_code_tabs_directive(
        content: str, file_path: Path | None = None, line_number: int | None = None
    ) -> list[str]:
        """
        Validate code-tabs directive content.

        Args:
            content: Directive content
            file_path: Optional file path
            line_number: Optional line number

        Returns:
            List of validation errors
        """
        errors = []

        if not content or not content.strip():
            errors.append("Code-tabs directive has no content")
            return errors

        # Check for tab markers
        tab_markers = re.findall(r"^### Tab: (.+)$", content, re.MULTILINE)

        if len(tab_markers) == 0:
            errors.append(
                "Code-tabs directive has no tab markers. Use ### Tab: Language to create code tabs"
            )

        return errors

    @staticmethod
    def validate_dropdown_directive(
        content: str, title: str = "", file_path: Path | None = None, line_number: int | None = None
    ) -> list[str]:
        """
        Validate dropdown directive content.

        Args:
            content: Directive content
            title: Directive title
            file_path: Optional file path
            line_number: Optional line number

        Returns:
            List of validation errors
        """
        errors = []

        if not content or not content.strip():
            errors.append("Dropdown directive has no content")

        # Title is optional but recommended
        if not title:
            # This is a warning, not an error
            pass

        return errors

    @staticmethod
    def validate_admonition_directive(
        admon_type: str, content: str, file_path: Path | None = None, line_number: int | None = None
    ) -> list[str]:
        """
        Validate admonition directive content.

        Args:
            admon_type: Type of admonition (note, tip, warning, etc.)
            content: Directive content
            file_path: Optional file path
            line_number: Optional line number

        Returns:
            List of validation errors
        """
        errors = []

        if not content or not content.strip():
            errors.append(f"{admon_type.capitalize()} admonition has no content")

        return errors

    @staticmethod
    def validate_nested_fences(content: str, file_path: Path | None = None) -> list[str]:
        """
        Validate nested fence usage (colon fences).

        Checks for:
        1. Unclosed fences
        2. Mismatched closing fence lengths
        3. Nested directives using same fence length as parent (ambiguous)

        Args:
            content: Markdown content
            file_path: Optional file path

        Returns:
            List of error/warning messages
        """
        errors = []
        lines = content.split("\n")

        # Stack of (line_number, colon_count, directive_type, is_indented)
        stack: list[tuple[int, int, str, bool]] = []

        # Regex for fence start: ^(\s*)(:{3,})\{([^}]+)\}
        # Regex for fence end: ^(\s*)(:{3,})\s*$
        start_pattern = re.compile(r"^(\s*)(:{3,})\{([^}]+)\}")
        end_pattern = re.compile(r"^(\s*)(:{3,})\s*$")

        for i, line in enumerate(lines):
            line_num = i + 1

            # Check for start block
            start_match = start_pattern.match(line)
            if start_match:
                indent = start_match.group(1)
                colons = start_match.group(2)
                dtype = start_match.group(3).strip()
                count = len(colons)
                is_indented = len(indent) >= 4

                # Check nesting against parent
                if stack:
                    parent_line, parent_count, parent_type, parent_indented = stack[-1]

                    # Warning: Nested with same length and no indentation
                    if count == parent_count and not is_indented:
                        errors.append(
                            f"Line {line_num}: Nested directive '{dtype}' uses same fence length ({count}) "
                            f"as parent '{parent_type}' (line {parent_line}). "
                            "This causes parsing ambiguity. Use variable fence lengths (e.g. ::::) "
                            "for the parent or indent the child."
                        )

                stack.append((line_num, count, dtype, is_indented))
                continue

            # Check for end block
            end_match = end_pattern.match(line)
            if end_match:
                colons = end_match.group(2)
                count = len(colons)

                if not stack:
                    errors.append(
                        f"Line {line_num}: Orphaned closing fence (length {count}) found without matching opening fence."
                    )
                    continue

                # Check against top of stack
                top_line, top_count, top_type, _ = stack[-1]

                if count == top_count:
                    # Perfect match
                    stack.pop()
                elif count > top_count:
                    # Closing fence is LONGER than opening - strictly usually treated as content
                    # but in this context likely a mistake by user trying to close a parent?
                    # Actually, standard says end fence must be >= start fence.
                    # So :::: can close :::. But usually you match exact.
                    # Let's warn if they differ significantly or if multiple items on stack

                    # Check if it matches any parent
                    found = False
                    for idx in range(len(stack) - 1, -1, -1):
                        if stack[idx][1] == count:
                            # It closes a parent, leaving children unclosed
                            unclosed = stack[idx + 1 :]
                            unclosed_desc = ", ".join(f"'{x[2]}'" for x in unclosed)
                            errors.append(
                                f"Line {line_num}: Closing fence (length {count}) matches parent '{stack[idx][2]}' "
                                f"but leaves inner directives unclosed: {unclosed_desc}."
                            )
                            # Pop everything down to that parent
                            del stack[idx:]
                            found = True
                            break

                    if not found:
                        # It's just longer than the current top.
                        # Technically valid in CommonMark (closes the block), but bad style.
                        pass  # Warning? Nah, maybe explicit match is better.

                else:  # count < top_count
                    # Closing fence is SHORTER. Cannot close the block.
                    errors.append(
                        f"Line {line_num}: Closing fence (length {count}) is too short to close "
                        f"directive '{top_type}' (requires {top_count} colons)."
                    )

        # End of file: check for unclosed blocks
        if stack:
            for unclosed_line, unclosed_count, unclosed_dtype, _marker in stack:
                if unclosed_count == 3:
                    errors.append(
                        f"Line {unclosed_line}: Directive '{unclosed_dtype}' opened with ````` but never closed. "
                        f"Add closing ````` or use 4+ backticks (````) if content contains code blocks."
                    )
                else:
                    errors.append(
                        f"Line {unclosed_line}: Directive '{unclosed_dtype}' opened with {unclosed_count} backticks but never closed. "
                        f"Add matching closing fence."
                    )

        return errors

    @classmethod
    def validate_directive(
        cls,
        directive_type: str,
        content: str,
        title: str = "",
        options: dict[str, Any] | None = None,
        file_path: Path | None = None,
        line_number: int | None = None,
    ) -> list[str]:
        """
        Validate any directive type.

        Args:
            directive_type: Type of directive (tabs, note, dropdown, etc.)
            content: Directive content
            title: Directive title (if any)
            options: Directive options dictionary
            file_path: Optional file path
            line_number: Optional line number

        Returns:
            List of validation errors (empty if valid)
        """
        options = options or {}
        errors = []

        # Check if directive type is known
        if directive_type not in cls.KNOWN_DIRECTIVES:
            errors.append(
                f"Unknown directive type: {directive_type}. "
                f"Known directives: {', '.join(sorted(cls.KNOWN_DIRECTIVES))}"
            )
            return errors  # Don't validate further if type is unknown

        # Validate based on type
        if directive_type == "tabs":
            errors.extend(cls.validate_tabs_directive(content, file_path, line_number))

        elif directive_type in ("code-tabs", "code_tabs"):
            errors.extend(cls.validate_code_tabs_directive(content, file_path, line_number))

        elif directive_type in ("dropdown", "details"):
            errors.extend(cls.validate_dropdown_directive(content, title, file_path, line_number))

        elif directive_type in cls.ADMONITION_TYPES:
            errors.extend(
                cls.validate_admonition_directive(directive_type, content, file_path, line_number)
            )

        return errors

    @classmethod
    def validate_directive_block(
        cls, directive_block: str, file_path: Path | None = None, start_line: int | None = None
    ) -> dict[str, Any]:
        """
        Validate a complete directive block from markdown.

        Args:
            directive_block: Full directive block including opening/closing backticks
            file_path: Optional file path
            start_line: Optional starting line number

        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'errors': List[str],
                'directive_type': str,
                'content': str,
                'title': str,
                'options': Dict[str, Any]
            }
        """
        result: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "directive_type": None,
            "content": "",
            "title": "",
            "options": {},
        }

        # Parse directive block
        # Pattern: ```{directive_type} title
        #          :option: value
        #
        #          content
        #          ```
        pattern = r"```\{(\w+(?:-\w+)?)\}([^\n]*)\n(.*?)```"
        match = re.search(pattern, directive_block, re.DOTALL)

        if not match:
            result["valid"] = False
            result["errors"].append("Malformed directive block: could not parse")
            return result

        directive_type = match.group(1)
        title = match.group(2).strip()
        content = match.group(3)

        result["directive_type"] = directive_type
        result["title"] = title
        result["content"] = content

        # Parse options (lines starting with :key:)
        options = {}
        option_pattern = r"^:(\w+):\s*(.*)$"
        for line in content.split("\n"):
            opt_match = re.match(option_pattern, line.strip())
            if opt_match:
                key = opt_match.group(1)
                value = opt_match.group(2).strip()
                options[key] = value
        result["options"] = options

        # Validate the directive
        errors = cls.validate_directive(
            directive_type=directive_type,
            content=content,
            title=title,
            options=options,
            file_path=file_path,
            line_number=start_line,
        )

        if errors:
            result["valid"] = False
            result["errors"] = errors

        return result


def validate_markdown_directives(
    markdown_content: str, file_path: Path | None = None
) -> list[dict[str, Any]]:
    """
    Validate all directive blocks in a markdown file.

    Args:
        markdown_content: Full markdown content
        file_path: Optional file path for error reporting

    Returns:
        List of validation results, one per directive block
    """
    results = []
    validator = DirectiveSyntaxValidator()

    # 1. Check nesting structure (Global check)
    fence_errors = validator.validate_nested_fences(markdown_content, file_path)
    for error in fence_errors:
        results.append(
            {
                "valid": False,
                "errors": [error],
                "directive_type": "structure",
                "content": "",
                "title": "Nesting Structure",
                "options": {},
            }
        )

    # 2. Find and validate individual directive blocks
    pattern = r"```\{(\w+(?:-\w+)?)\}[^\n]*\n.*?```"

    for match in re.finditer(pattern, markdown_content, re.DOTALL):
        directive_block = match.group(0)
        start_pos = match.start()

        # Calculate line number
        line_number = markdown_content[:start_pos].count("\n") + 1

        # Validate the block
        result = validator.validate_directive_block(
            directive_block=directive_block, file_path=file_path, start_line=line_number
        )

        results.append(result)

    return results


def get_directive_validation_summary(validation_results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Get a summary of directive validation results.

    Args:
        validation_results: List of validation result dictionaries

    Returns:
        Summary dictionary with counts and error lists
    """
    total = len(validation_results)
    valid = sum(1 for r in validation_results if r["valid"])
    invalid = total - valid

    all_errors = []
    for result in validation_results:
        if not result["valid"]:
            for error in result["errors"]:
                all_errors.append({"directive_type": result["directive_type"], "error": error})

    return {
        "total_directives": total,
        "valid": valid,
        "invalid": invalid,
        "errors": all_errors,
        "has_errors": invalid > 0,
    }
