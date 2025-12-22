"""Pre-parse validation for directive syntax.

This module provides ``DirectiveSyntaxValidator`` for catching common directive
syntax errors early, before expensive parsing and recursive markdown processing.
Validation runs at the text level and produces helpful error messages.

Key Classes:
    - ``DirectiveSyntaxValidator``: Validates directive syntax by type.

Functions:
    - ``validate_markdown_directives()``: Validate all directives in a file.
    - ``get_directive_validation_summary()``: Summarize validation results.

Validation Checks:
    - **Tabs**: Requires ``### Tab:`` markers, minimum 2 tabs, warns on >10.
    - **Code-tabs**: Requires ``### Tab:`` markers for language tabs.
    - **Dropdown**: Requires non-empty content.
    - **Admonitions**: Requires non-empty content.
    - **Nesting**: Detects unclosed fences, mismatched lengths, ambiguous nesting.

Example:
    Validate a markdown file::

        from bengal.directives.validator import validate_markdown_directives

        results = validate_markdown_directives(markdown_content, Path("guide.md"))
        for result in results:
            if not result["valid"]:
                print(f"Errors in {result['directive_type']}: {result['errors']}")

See Also:
    - ``bengal.directives.errors``: ``DirectiveError`` for runtime errors.
    - ``bengal.directives.contracts``: Contract validation for nesting rules.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class DirectiveSyntaxValidator:
    """Validate directive syntax before parsing.

    Catches common errors early with helpful messages, avoiding expensive
    parsing and recursive markdown processing for malformed content.

    Class Attributes:
        KNOWN_DIRECTIVES: Set of recognized directive type names.
        ADMONITION_TYPES: Subset of directives that are admonitions.

    Example:
        Validate a specific directive::

            errors = DirectiveSyntaxValidator.validate_directive(
                directive_type="tabs",
                content=directive_content,
                file_path=Path("guide.md"),
                line_number=42,
            )
            if errors:
                for error in errors:
                    print(f"Validation error: {error}")
    """

    KNOWN_DIRECTIVES: set[str] = {
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
    """Set of recognized directive type names for validation."""

    ADMONITION_TYPES: set[str] = {
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
    """Subset of KNOWN_DIRECTIVES that are admonition types."""

    @staticmethod
    def validate_tabs_directive(
        content: str, file_path: Path | None = None, line_number: int | None = None
    ) -> list[str]:
        """Validate tabs directive content.

        Checks for:
            - Presence of ``### Tab:`` markers.
            - Minimum of 2 tabs (suggests admonition for single items).
            - Maximum of 10 tabs (performance warning).

        Args:
            content: Directive content between opening and closing fences.
            file_path: Optional file path for error context.
            line_number: Optional line number for error context.

        Returns:
            List of validation error messages (empty if valid).
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
        """Validate code-tabs directive content.

        Checks for ``### Tab:`` markers for language tabs.

        Args:
            content: Directive content between opening and closing fences.
            file_path: Optional file path for error context.
            line_number: Optional line number for error context.

        Returns:
            List of validation error messages (empty if valid).
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
        """Validate dropdown directive content.

        Checks for non-empty content. Title is optional but recommended.

        Args:
            content: Directive content between opening and closing fences.
            title: Directive title (text after directive name).
            file_path: Optional file path for error context.
            line_number: Optional line number for error context.

        Returns:
            List of validation error messages (empty if valid).
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
        """Validate admonition directive content.

        Checks for non-empty content in admonition blocks.

        Args:
            admon_type: Type of admonition (note, tip, warning, etc.).
            content: Directive content between opening and closing fences.
            file_path: Optional file path for error context.
            line_number: Optional line number for error context.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not content or not content.strip():
            errors.append(f"{admon_type.capitalize()} admonition has no content")

        return errors

    @staticmethod
    def validate_nested_fences(content: str, file_path: Path | None = None) -> list[str]:
        """Validate nested colon fence structure in markdown content.

        Performs structural validation of directive nesting, checking for:
            1. Unclosed fences (missing closing ``:::``).
            2. Mismatched closing fence lengths.
            3. Ambiguous nesting (same fence length without named closers).

        This is a global check on the entire document, not per-directive.

        Args:
            content: Full markdown content to validate.
            file_path: Optional file path for error context.

        Returns:
            List of error/warning messages with line numbers.
        """
        errors = []
        lines = content.split("\n")

        # Stack of (line_number, colon_count, directive_type, is_indented, uses_named_closer)
        stack: list[tuple[int, int, str, bool, bool]] = []

        # Regex for fence start: ^(\s*)(:{3,})\{([^}]+)\}
        # Regex for fence end: ^(\s*)(:{3,})\s*$
        # Regex for named closer: ^(\s*)(:{3,})\{/([^}]+)\}
        start_pattern = re.compile(r"^(\s*)(:{3,})\{([^}]+)\}")
        end_pattern = re.compile(r"^(\s*)(:{3,})\s*$")
        named_closer_pattern = re.compile(r"^(\s*)(:{3,})\{/([^}]+)\}", re.MULTILINE)

        # Code block tracking (``` or ~~~)
        code_block_pattern = re.compile(r"^(\s*)(`{3,}|~{3,})")
        in_code_block = False
        code_block_fence: str | None = None

        # First pass: check if content uses named closers (enables same-fence-length)
        uses_named_closers = bool(named_closer_pattern.search(content))

        for i, line in enumerate(lines):
            line_num = i + 1

            # Track code block state (skip directive analysis inside code blocks)
            code_match = code_block_pattern.match(line)
            if code_match:
                fence = code_match.group(2)
                if not in_code_block:
                    in_code_block = True
                    code_block_fence = fence
                elif fence.startswith(code_block_fence[0]) and len(fence) >= len(code_block_fence):
                    # Closing fence (same or longer)
                    in_code_block = False
                    code_block_fence = None
                continue

            # Skip directive analysis inside code blocks
            if in_code_block:
                continue

            # Check for named closer first (:::{/name})
            closer_match = named_closer_pattern.match(line)
            if closer_match:
                closer_type = closer_match.group(3).strip()
                # Find matching opener in stack and pop
                for idx in range(len(stack) - 1, -1, -1):
                    if stack[idx][2] == closer_type:
                        stack.pop(idx)
                        break
                continue

            # Check for start block
            start_match = start_pattern.match(line)
            if start_match:
                indent = start_match.group(1)
                colons = start_match.group(2)
                dtype = start_match.group(3).strip()
                count = len(colons)
                is_indented = len(indent) >= 4

                # Check nesting against parent (only warn if NOT using named closers)
                if stack and not uses_named_closers:
                    parent_line, parent_count, parent_type, parent_indented, _ = stack[-1]

                    # Warning: Nested with same length and no indentation
                    if count == parent_count and not is_indented:
                        errors.append(
                            f"Line {line_num}: Nested directive '{dtype}' uses same fence length ({count}) "
                            f"as parent '{parent_type}' (line {parent_line}). "
                            f"Recommended: Use named closers for clarity: :::{{{dtype}}} ... :::{{{'/' + dtype}}}. "
                            "Alternative: Use variable fence lengths (e.g. :::: for parent)."
                        )

                stack.append((line_num, count, dtype, is_indented, uses_named_closers))
                continue

            # Check for end block (fence-depth closing)
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
                top_line, top_count, top_type, _, _ = stack[-1]

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
            for unclosed_line, unclosed_count, unclosed_dtype, _is_indented, _uses_named in stack:
                if unclosed_count == 3:
                    errors.append(
                        f"Line {unclosed_line}: Directive '{unclosed_dtype}' opened with ::: but never closed. "
                        f"Add closing ::: fence."
                    )
                else:
                    errors.append(
                        f"Line {unclosed_line}: Directive '{unclosed_dtype}' opened with {unclosed_count} colons but never closed. "
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
        """Validate a directive by type.

        Routes validation to the appropriate type-specific validator based on
        the directive type. Unknown types return an error immediately.

        Args:
            directive_type: Type of directive (tabs, note, dropdown, etc.).
            content: Directive content between opening and closing fences.
            title: Directive title (text after directive name).
            options: Directive options dictionary (parsed ``:key: value`` lines).
            file_path: Optional file path for error context.
            line_number: Optional line number for error context.

        Returns:
            List of validation error messages (empty if valid).
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
        """Validate a complete directive block extracted from markdown.

        Parses the block to extract type, title, options, and content, then
        runs type-specific validation.

        Args:
            directive_block: Full directive block including opening/closing fences.
            file_path: Optional file path for error context.
            start_line: Optional starting line number for error context.

        Returns:
            Dictionary with validation results::

                {
                    "valid": bool,
                    "errors": list[str],
                    "directive_type": str | None,
                    "content": str,
                    "title": str,
                    "options": dict[str, Any]
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
    """Validate all directive blocks in a markdown file.

    Performs both structural validation (nesting, fence matching) and
    per-directive content validation.

    Args:
        markdown_content: Full markdown content to validate.
        file_path: Optional file path for error reporting.

    Returns:
        List of validation result dictionaries, one per directive block plus
        any structural issues. Each result has ``valid``, ``errors``,
        ``directive_type``, ``content``, ``title``, and ``options`` keys.

    Example:
        >>> results = validate_markdown_directives(content, Path("guide.md"))
        >>> for r in results:
        ...     if not r["valid"]:
        ...         print(f"{r['directive_type']}: {r['errors']}")
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
    """Summarize directive validation results.

    Aggregates validation results into counts and a consolidated error list.

    Args:
        validation_results: List of validation result dictionaries from
            ``validate_markdown_directives()``.

    Returns:
        Summary dictionary::

            {
                "total_directives": int,
                "valid": int,
                "invalid": int,
                "errors": list[{"directive_type": str, "error": str}],
                "has_errors": bool
            }

    Example:
        >>> results = validate_markdown_directives(content)
        >>> summary = get_directive_validation_summary(results)
        >>> if summary["has_errors"]:
        ...     print(f"{summary['invalid']} directives have errors")
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
