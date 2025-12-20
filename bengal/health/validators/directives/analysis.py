"""
Directive analysis module.

Extracts and analyzes directive blocks from markdown content.

Build-Integrated Validation:
    When a BuildContext with cached content is provided, the analyzer uses
    cached content instead of re-reading files from disk. This eliminates
    ~4 seconds of redundant disk I/O during health checks (773 files).

    See: plan/active/rfc-build-integrated-validation.md
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.directives.validator import DirectiveSyntaxValidator
from bengal.utils.autodoc import is_autodoc_page
from bengal.utils.logger import get_logger

from .constants import (
    KNOWN_DIRECTIVES,
    MAX_DIRECTIVES_PER_PAGE,
    MAX_TABS_PER_BLOCK,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class DirectiveAnalyzer:
    """
    Analyzes directive usage across a site.

    Extracts directives from markdown content, validates their structure,
    and collects statistics for reporting.

    Build-Integrated Validation:
        When analyze_from_context() is used with cached content, the analyzer
        avoids disk I/O entirely, reducing health check time from ~4.6s to <100ms.
    """

    def analyze(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> dict[str, Any]:
        """
        Analyze all directives in site source files.

        Uses cached content from build_context when available to avoid
        redundant disk I/O (~4 seconds saved for 773-page sites).

        Args:
            site: Site instance to analyze
            build_context: Optional BuildContext with cached page contents.
                          When provided, uses cached content instead of
                          reading from disk (build-integrated validation).

        Returns:
            Dictionary with directive statistics and issues
        """
        data: dict[str, Any] = {
            "total_directives": 0,
            "by_type": defaultdict(int),
            "by_page": defaultdict(list),
            "syntax_errors": [],
            "completeness_errors": [],
            "performance_warnings": [],
            "fence_nesting_warnings": [],
        }

        # Use cached content if available (build-integrated validation)
        use_cache = (
            build_context is not None
            and hasattr(build_context, "has_cached_content")
            and build_context.has_cached_content
        )

        # Observability: Track processing stats
        pages_total = len(site.pages)
        pages_processed = 0
        skip_no_path = 0
        skip_generated = 0
        skip_autodoc = 0
        skip_no_changes = 0
        cache_hits = 0
        disk_reads = 0

        # Analyze each page's source content
        for page in site.pages:
            if not page.source_path or not page.source_path.exists():
                skip_no_path += 1
                continue

            # Skip generated pages (they don't have markdown source)
            if page.metadata.get("_generated"):
                skip_generated += 1
                continue

            # Skip autodoc-generated pages (API/CLI docs)
            if is_autodoc_page(page):
                skip_autodoc += 1
                continue

            # Incremental fast path: when build context provides changed pages, only analyze those.
            # This keeps dev-server rebuilds fast when only templates/assets changed.
            if (
                build_context is not None
                and getattr(build_context, "incremental", False)
                and hasattr(build_context, "changed_page_paths")
            ):
                changed_page_paths = getattr(build_context, "changed_page_paths", None)
                if (
                    isinstance(changed_page_paths, set)
                    and page.source_path not in changed_page_paths
                ):
                    skip_no_changes += 1
                    continue

            pages_processed += 1

            try:
                # Use cached content if available (eliminates disk I/O)
                if use_cache and build_context is not None:
                    content = build_context.get_content(page.source_path)
                    if content is None:
                        # Fallback to disk if not cached (shouldn't happen normally)
                        content = page.source_path.read_text(encoding="utf-8")
                        disk_reads += 1
                    else:
                        cache_hits += 1
                else:
                    # Read from disk (no cache or no build_context)
                    content = page.source_path.read_text(encoding="utf-8")
                    disk_reads += 1

                # Check for fence nesting structure using the shared validator
                fence_errors = DirectiveSyntaxValidator.validate_nested_fences(
                    content, page.source_path
                )
                for error in fence_errors:
                    # Extract line number if present
                    line_match = re.match(r"Line (\d+):", error)
                    line_num = int(line_match.group(1)) if line_match else 0

                    data["fence_nesting_warnings"].append(
                        {
                            "page": page.source_path,
                            "line": line_num,
                            "type": "structure",
                            "warning": error,
                        }
                    )

                # Check for markdown code blocks with nested code blocks (same fence length)
                code_block_warnings = self._check_code_block_nesting(content, page.source_path)
                for warning in code_block_warnings:
                    data["fence_nesting_warnings"].append(warning)

                page_directives = self._extract_directives(content, page.source_path)

                for directive in page_directives:
                    data["total_directives"] += 1
                    data["by_type"][directive["type"]] += 1
                    data["by_page"][str(page.source_path)].append(directive)

                    # Check for syntax errors
                    if directive.get("syntax_error"):
                        data["syntax_errors"].append(
                            {
                                "page": page.source_path,
                                "line": directive["line_number"],
                                "type": directive["type"],
                                "error": directive["syntax_error"],
                            }
                        )

                    # Check for completeness errors
                    if directive.get("completeness_error"):
                        data["completeness_errors"].append(
                            {
                                "page": page.source_path,
                                "line": directive["line_number"],
                                "type": directive["type"],
                                "error": directive["completeness_error"],
                            }
                        )

                    # Check for fence nesting warnings
                    if directive.get("fence_nesting_warning"):
                        warning_data = {
                            "page": page.source_path,
                            "line": directive["line_number"],
                            "type": directive["type"],
                            "warning": directive["fence_nesting_warning"],
                        }
                        if directive.get("inner_conflict_line"):
                            warning_data["inner_line"] = directive["inner_conflict_line"]
                        data["fence_nesting_warnings"].append(warning_data)

                    # Check for fence style warnings (backtick vs colon)
                    if directive.get("fence_style_warning"):
                        data["fence_nesting_warnings"].append(
                            {
                                "page": page.source_path,
                                "line": directive["line_number"],
                                "type": directive["type"],
                                "warning": directive["fence_style_warning"],
                            }
                        )

            except Exception as e:
                # Skip files we can't read
                logger.debug(
                    "directive_analysis_file_skip",
                    page=str(page.source_path),
                    error=str(e),
                    error_type=type(e).__name__,
                )
                pass

        # Check for performance issues
        for page_path, directives in data["by_page"].items():
            # Too many directives on one page?
            if len(directives) > MAX_DIRECTIVES_PER_PAGE:
                data["performance_warnings"].append(
                    {
                        "page": Path(page_path),
                        "issue": "heavy_directive_usage",
                        "count": len(directives),
                        "message": f"{len(directives)} directives on one page (>{MAX_DIRECTIVES_PER_PAGE})",
                    }
                )

            # Check individual directive issues
            for directive in directives:
                # Too many tabs in a tabs block?
                if (
                    directive["type"] == "tabs"
                    and directive.get("tab_count", 0) > MAX_TABS_PER_BLOCK
                ):
                    data["performance_warnings"].append(
                        {
                            "page": Path(page_path),
                            "issue": "too_many_tabs",
                            "line": directive["line_number"],
                            "count": directive["tab_count"],
                            "message": f"Tabs block has {directive['tab_count']} tabs (>{MAX_TABS_PER_BLOCK})",
                        }
                    )

        # Store observability stats in data for the validator
        data["_stats"] = {
            "pages_total": pages_total,
            "pages_processed": pages_processed,
            "pages_skipped": {
                "no_path": skip_no_path,
                "generated": skip_generated,
                "autodoc": skip_autodoc,
                "no_changes": skip_no_changes,
            },
            "cache_hits": cache_hits,
            "cache_misses": disk_reads,
        }

        return data

    def _is_inside_code_block(self, content: str, position: int) -> bool:
        """
        Check if a position in content is inside a markdown code block.

        Args:
            content: Full markdown content
            position: Character position to check

        Returns:
            True if position is inside a code block (```...```, ~~~...~~~, or indented 4+ spaces)
        """
        # Find all code block boundaries
        code_block_pattern = r"^(`{3,}|~{3,})[^\n]*$"
        lines = content[:position].split("\n")

        # Track if we're inside a fenced code block
        in_fenced_block = False
        code_block_marker = None

        # Track if we're in an indented code block (4+ spaces)
        in_indented_block = False

        for i, line in enumerate(lines):
            # Check if this line is a code block fence
            match = re.match(code_block_pattern, line)
            if match:
                marker = match.group(1)
                # If we're in a code block and this matches the opening marker, close it
                if in_fenced_block and marker == code_block_marker:
                    in_fenced_block = False
                    code_block_marker = None
                # Otherwise, open a new code block
                else:
                    in_fenced_block = True
                    code_block_marker = marker
                in_indented_block = False  # Fenced blocks override indented
            else:
                # Check for indented code blocks (4+ spaces, not a list item)
                stripped = line.lstrip()
                indent = len(line) - len(stripped)
                if indent >= 4 and stripped:
                    if (
                        i == 0
                        or (
                            lines[i - 1].strip()
                            and len(lines[i - 1]) - len(lines[i - 1].lstrip()) >= 4
                        )
                        or in_indented_block
                    ):
                        in_indented_block = True
                    else:
                        in_indented_block = False
                else:
                    if in_indented_block and not stripped:
                        continue
                    else:
                        in_indented_block = False

        return in_fenced_block or in_indented_block

    def _check_code_block_nesting(self, content: str, file_path: Path) -> list[dict[str, Any]]:
        """
        Check for markdown code blocks that contain nested code blocks with the same fence length.

        Returns:
            List of warning dictionaries
        """
        warnings = []
        lines = content.split("\n")

        code_block_pattern = re.compile(r"^(\s*)(`{3,})(\w*)(?::[^\s]*)?\s*$")
        directive_pattern = re.compile(r"^(\s*)(`{3,})\{([^}]+)\}")
        stack: list[tuple[int, int, str]] = []
        directive_stack: list[int] = []

        for i, line in enumerate(lines, 1):
            directive_match = directive_pattern.match(line)
            if directive_match:
                directive_fence_length = len(directive_match.group(2))
                directive_stack.append(directive_fence_length)
                continue

            match = code_block_pattern.match(line)
            if match:
                indent = len(match.group(1))
                fence_marker = match.group(2)
                language = match.group(3)
                fence_length = len(fence_marker)

                if not language and directive_stack and fence_length == directive_stack[-1]:
                    directive_stack.pop()
                    continue

                if indent >= 4:
                    continue

                char_pos = len("\n".join(lines[: i - 1]))
                if self._is_inside_colon_directive(content, char_pos):
                    continue

                if not language:
                    if stack:
                        top_line, top_length, top_lang = stack[-1]
                        if fence_length == top_length or fence_length > top_length:
                            stack.pop()
                            continue
                    continue

                if stack:
                    top_line, top_length, top_lang = stack[-1]
                    if language and fence_length == top_length:
                        warnings.append(
                            {
                                "page": file_path,
                                "line": top_line,  # Outer directive line (for context display)
                                "inner_line": i,  # Inner conflicting line
                                "type": "structure",
                                "warning": (
                                    f"Outer directive at line {top_line} uses {fence_length} backticks but "
                                    f"inner code block at line {i} also uses {fence_length}. "
                                    f"Use {fence_length + 1}+ backticks for outer (e.g., ````{top_lang or 'markdown'}`)."
                                ),
                            }
                        )
                        stack.append((i, fence_length, language))
                    elif fence_length < top_length:
                        stack.append((i, fence_length, language))
                    else:
                        stack.append((i, fence_length, language))
                else:
                    stack.append((i, fence_length, language))

        return warnings

    def _is_inside_colon_directive(self, content: str, position: int) -> bool:
        """Check if a position is inside a colon directive (:::{name})."""
        lines = content[:position].split("\n")
        colon_pattern = re.compile(r"^(\s*)(:{3,})\{([^}]+)\}")
        closing_pattern = re.compile(r"^(\s*)(:{3,})\s*$")

        in_directive = False
        directive_depth = 0

        for line in lines:
            if colon_pattern.match(line):
                directive_depth += 1
                in_directive = True
            elif closing_pattern.match(line):
                directive_depth -= 1
                if directive_depth == 0:
                    in_directive = False

        return in_directive and directive_depth > 0

    def _is_inside_inline_code(self, content: str, position: int) -> bool:
        """Check if a position in content is inside inline code (single backticks)."""
        lines_before = content[:position].split("\n")
        if not lines_before:
            return False

        current_line = lines_before[-1]
        char_pos_in_line = len(current_line)
        backticks_before = current_line[:char_pos_in_line].count("`")

        if self._is_inside_code_block(content, position):
            return True

        return backticks_before % 2 == 1

    def _extract_directives(self, content: str, file_path: Path) -> list[dict[str, Any]]:
        """
        Extract all directive blocks from markdown content (colon fences only).

        Args:
            content: Markdown content
            file_path: Path to file (for error reporting)

        Returns:
            List of directive dictionaries with metadata
        """
        directives = []

        colon_start_pattern = r"^(\s*)(:{3,})\{(\w+(?:-\w+)?)\}([^\n]*)"
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            match = re.match(colon_start_pattern, lines[i])
            if match:
                indent = len(match.group(1))
                if indent >= 4:
                    i += 1
                    continue

                char_pos = len("\n".join(lines[:i]))
                if self._is_inside_code_block(content, char_pos) or self._is_inside_inline_code(
                    content, char_pos
                ):
                    i += 1
                    continue

                fence_marker = match.group(2)
                directive_type = match.group(3)
                title = match.group(4).strip()
                fence_depth = len(fence_marker)

                directive_content_lines = []
                j = i + 1
                found_closing = False
                while j < len(lines):
                    closing_pattern = rf"^\s*:{{{fence_depth}}}\s*$"
                    if re.match(closing_pattern, lines[j]):
                        found_closing = True
                        break
                    directive_content_lines.append(lines[j])
                    j += 1

                if not found_closing:
                    i += 1
                    continue

                directive_content = "\n".join(directive_content_lines)
                line_number = i + 1

                directive_info = {
                    "type": directive_type,
                    "title": title,
                    "content": directive_content,
                    "line_number": line_number,
                    "file_path": file_path,
                    "fence_depth": fence_depth,
                    "fence_type": "colon",
                }

                self._check_fence_nesting(directive_info)

                if directive_type not in KNOWN_DIRECTIVES:
                    directive_info["syntax_error"] = f"Unknown directive type: {directive_type}"

                if directive_type == "tabs":
                    self._validate_tabs_directive(directive_info)
                elif directive_type in ("code-tabs", "code_tabs"):
                    self._validate_code_tabs_directive(directive_info)
                elif directive_type in ("dropdown", "details"):
                    self._validate_dropdown_directive(directive_info)

                directives.append(directive_info)
                i = j + 1
            else:
                i += 1

        return directives

    def _validate_tabs_directive(self, directive: dict[str, Any]) -> None:
        """Validate tabs directive content."""
        content = directive["content"]

        tab_markers = re.findall(r"^### Tab: (.+)$", content, re.MULTILINE)
        directive["tab_count"] = len(tab_markers)

        if len(tab_markers) == 0:
            bad_markers = re.findall(r"^###\s*Ta[^b]", content, re.MULTILINE)
            if bad_markers:
                directive["syntax_error"] = 'Malformed tab marker (use "### Tab: Title")'
            else:
                directive["completeness_error"] = (
                    "Tabs directive has no tab markers (### Tab: Title)"
                )
        elif len(tab_markers) == 1:
            directive["completeness_error"] = (
                "Tabs directive has only 1 tab (consider using admonition instead)"
            )

        if not content.strip():
            directive["completeness_error"] = "Tabs directive has no content"

    def _validate_code_tabs_directive(self, directive: dict[str, Any]) -> None:
        """Validate code-tabs directive content."""
        content = directive["content"]

        tab_markers = re.findall(r"^### Tab: (.+)$", content, re.MULTILINE)
        directive["tab_count"] = len(tab_markers)

        if len(tab_markers) == 0:
            directive["completeness_error"] = (
                "Code-tabs directive has no tab markers (### Tab: Language)"
            )

        if not content.strip():
            directive["completeness_error"] = "Code-tabs directive has no content"

    def _validate_dropdown_directive(self, directive: dict[str, Any]) -> None:
        """Validate dropdown directive content."""
        content = directive["content"]

        if not content.strip():
            directive["completeness_error"] = "Dropdown directive has no content"

    def _check_fence_nesting(self, directive: dict[str, Any]) -> None:
        """Check for fence nesting issues."""
        content = directive["content"]
        fence_depth = directive["fence_depth"]
        fence_type = directive.get("fence_type", "colon")
        directive_line = directive["line_number"]

        if fence_type == "colon":
            return

        if fence_type == "backtick" and fence_depth == 3:
            code_block_pattern = r"^(`{3,}|~{3,})[a-zA-Z0-9_-]*\s*$"
            lines = content.split("\n")
            inner_line_offset = None
            for idx, line in enumerate(lines):
                match = re.match(code_block_pattern, line.strip())
                if match:
                    fence_marker = match.group(1)
                    if fence_marker.startswith("`") and len(fence_marker) == 3:
                        inner_line_offset = idx
                        break

            if inner_line_offset is not None:
                # Calculate actual line number in source file
                # directive_line is where the directive starts, content starts after opening fence
                inner_line = directive_line + inner_line_offset + 1  # +1 for the opening fence line
                directive["fence_nesting_warning"] = (
                    f"Outer directive at line {directive_line} uses ``` but inner code block "
                    f"at line {inner_line} also uses ```. Use 4+ backticks for outer."
                )
                directive["inner_conflict_line"] = inner_line
                return

        directive_type = directive["type"]
        if directive_type in ("tabs", "code-tabs", "code_tabs"):
            tab_count = len(re.findall(r"^### Tab:", content, re.MULTILINE))
            content_lines = len([line for line in content.split("\n") if line.strip()])

            if tab_count > 0 and content_lines < (tab_count * 3):
                directive["fence_nesting_warning"] = (
                    f"Directive content appears incomplete ({content_lines} lines, {tab_count} tabs). "
                    f"If tabs contain code blocks, use 4+ backticks (````) for the directive fence."
                )
