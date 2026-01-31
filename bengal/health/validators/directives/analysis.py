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
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.autodoc import is_autodoc_page
from bengal.utils.observability.logger import get_logger

from .constants import (
    KNOWN_DIRECTIVES,
    MAX_TABS_PER_BLOCK,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CodeBlockRange:
    """
    Represents a fenced code block's line range for O(1) containment checks.

    Used by DirectiveAnalyzer to pre-compute code block boundaries in a single
    O(L) pass, enabling O(R) lookups instead of O(L) per-position checks.

    Attributes:
        start_line: Opening fence line number (1-indexed)
        end_line: Closing fence line number (1-indexed)
            fence_type: "backtick" (```) or "tilde" (~~~)
            fence_depth: Number of fence characters (3+)

    """

    start_line: int
    end_line: int
    fence_type: str  # "backtick" or "tilde"
    fence_depth: int


@dataclass(frozen=True, slots=True)
class ColonDirectiveRange:
    """
    Represents a colon directive's line range for O(1) containment checks.

    Used by DirectiveAnalyzer to pre-compute colon directive boundaries in a
    single O(L) pass, enabling O(R) lookups instead of O(L) per-position checks.

    Attributes:
        start_line: Opening fence line number (1-indexed)
        end_line: Closing fence line number (1-indexed)
        fence_depth: Number of colon characters (3+)
        directive_type: Directive name (e.g., "note", "warning")

    """

    start_line: int
    end_line: int
    fence_depth: int
    directive_type: str


if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import SiteLike


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
        self, site: SiteLike, build_context: BuildContext | Any | None = None
    ) -> dict[str, Any]:
        """
        Analyze all directives in site source files.

        Uses cached content from build_context when available to avoid
        redundant disk I/O (~4 seconds saved for 773-page sites).

        Args:
            site: SiteLike instance to analyze
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

                # NOTE: DirectiveSyntaxValidator.validate_nested_fences and _check_code_block_nesting
                # removed — both produce false positives for valid MyST colon-fence syntax.
                # Patitas lexer handles fence nesting correctly. See: rfc-patitas-structural-validation.md

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

                    # NOTE: fence_nesting_warning and fence_style_warning checks removed.
                    # These produced false positives. Patitas handles fence validation correctly.
                    # See: rfc-patitas-structural-validation.md

            except Exception as e:
                # Skip files we can't read
                logger.debug(
                    "directive_analysis_file_skip",
                    page=str(page.source_path),
                    error=str(e),
                    error_type=type(e).__name__,
                )

        # Check for performance issues
        for page_path, directives in data["by_page"].items():
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

    def _build_code_block_index(self, lines: list[str]) -> list[CodeBlockRange]:
        """
        Build index of fenced code block ranges in single O(L) pass.

        Scans all lines once, tracking fence opens/closes with a stack.
        Resulting ranges enable O(R) containment checks instead of O(L) per-position.

        Args:
            lines: List of content lines (from content.split("\\n"))

        Returns:
            List of CodeBlockRange objects sorted by start_line.

        Complexity:
            Time: O(L) where L = number of lines
            Space: O(R) where R = number of code blocks (typically << L)
        """
        ranges: list[CodeBlockRange] = []
        # Stack: (start_line, fence_type, fence_depth)
        stack: list[tuple[int, str, int]] = []

        # Patterns for fenced code blocks
        fence_open_pattern = re.compile(r"^(\s*)(`{3,}|~{3,})(\w*)")
        fence_close_pattern = re.compile(r"^(\s*)(`{3,}|~{3,})\s*$")

        for i, line in enumerate(lines, 1):
            # Check indent - skip if 4+ spaces (indented code block, not fence)
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if indent >= 4:
                continue

            # Check for opening fence (has language tag or at start)
            open_match = fence_open_pattern.match(line)
            if open_match:
                fence_chars = open_match.group(2)
                fence_type = "backtick" if fence_chars[0] == "`" else "tilde"
                fence_depth = len(fence_chars)
                language = open_match.group(3)

                # Check if this is a closing fence (no language, matches stack top)
                close_match = fence_close_pattern.match(line)
                if close_match and stack:
                    close_chars = close_match.group(2)
                    close_type = "backtick" if close_chars[0] == "`" else "tilde"
                    close_depth = len(close_chars)

                    # Find matching opener (same type, same or lesser depth)
                    for j in range(len(stack) - 1, -1, -1):
                        start, s_type, s_depth = stack[j]
                        if s_type == close_type and close_depth >= s_depth:
                            stack.pop(j)
                            ranges.append(CodeBlockRange(start, i, s_type, s_depth))
                            break
                elif language or not stack:
                    # Opening fence (has language or no open blocks)
                    stack.append((i, fence_type, fence_depth))
                else:
                    # No language but might still be opening if different type/depth
                    # Check if it could close something first
                    closed = False
                    for j in range(len(stack) - 1, -1, -1):
                        start, s_type, s_depth = stack[j]
                        if s_type == fence_type and fence_depth >= s_depth:
                            stack.pop(j)
                            ranges.append(CodeBlockRange(start, i, s_type, s_depth))
                            closed = True
                            break
                    if not closed:
                        stack.append((i, fence_type, fence_depth))

        return sorted(ranges, key=lambda r: r.start_line)

    def _build_colon_directive_index(self, lines: list[str]) -> list[ColonDirectiveRange]:
        """
        Build index of colon directive ranges in single O(L) pass.

        Scans all lines once, tracking directive opens/closes with a stack.
        Resulting ranges enable O(R) containment checks instead of O(L) per-position.

        Args:
            lines: List of content lines (from content.split("\\n"))

        Returns:
            List of ColonDirectiveRange objects sorted by start_line.

        Complexity:
            Time: O(L) where L = number of lines
            Space: O(R) where R = number of directives (typically << L)
        """
        ranges: list[ColonDirectiveRange] = []
        # Stack: (start_line, fence_depth, directive_type)
        stack: list[tuple[int, int, str]] = []

        colon_open_pattern = re.compile(r"^(\s*)(:{3,})\{(\w+(?:-\w+)?)\}")
        colon_close_pattern = re.compile(r"^(\s*)(:{3,})\s*$")

        for i, line in enumerate(lines, 1):
            # Check indent - skip if 4+ spaces
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if indent >= 4:
                continue

            # Check for opening directive
            open_match = colon_open_pattern.match(line)
            if open_match:
                fence_depth = len(open_match.group(2))
                directive_type = open_match.group(3)
                stack.append((i, fence_depth, directive_type))
                continue

            # Check for closing fence
            close_match = colon_close_pattern.match(line)
            if close_match and stack:
                close_depth = len(close_match.group(2))
                # Find matching opener with same depth
                for j in range(len(stack) - 1, -1, -1):
                    start, s_depth, s_type = stack[j]
                    if s_depth == close_depth:
                        stack.pop(j)
                        ranges.append(ColonDirectiveRange(start, i, s_depth, s_type))
                        break

        return sorted(ranges, key=lambda r: r.start_line)

    def _is_line_inside_ranges(
        self, line_number: int, ranges: list[CodeBlockRange] | list[ColonDirectiveRange]
    ) -> bool:
        """
        Check if a line is inside any of the given ranges.

        Simple O(R) linear scan - efficient when R (range count) is small,
        which is typical (< 20 code blocks per file).

        Args:
            line_number: Line to check (1-indexed)
            ranges: Pre-computed ranges from _build_*_index()

        Returns:
            True if line is inside any range (exclusive of boundaries).

        Complexity:
            Time: O(R) where R = number of ranges
        """
        return any(r.start_line < line_number < r.end_line for r in ranges)

    def _check_code_block_nesting(self, content: str, file_path: Path) -> list[dict[str, Any]]:
        """
        Check for markdown code blocks that contain nested code blocks with the same fence length.

        Optimized: Pre-computes colon directive ranges in O(L), then uses O(R) lookups
        instead of O(L) per-line checks. Total complexity: O(L) instead of O(L²).

        Returns:
            List of warning dictionaries
        """
        warnings = []
        lines = content.split("\n")

        # Pre-compute colon directive ranges once: O(L)
        colon_ranges = self._build_colon_directive_index(lines)

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

                # O(R) lookup via pre-computed ranges
                if self._is_line_inside_ranges(i, colon_ranges):
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

    def _is_inside_inline_code_fast(self, line: str) -> bool:
        """
        Fast O(1) check if a directive pattern at line start is inside inline code.

        For directive extraction, we only need to check if the line itself starts
        with an odd number of backticks (indicating we're mid-inline-code).
        This is sufficient because directive patterns like :::{note} cannot appear
        inside inline code spans that started on the same line.

        Args:
            line: The line to check

        Returns:
            True if the line starts inside an inline code span.

        Complexity:
            Time: O(1) - just counts characters before directive pattern
        """
        # Find where the directive pattern starts (after leading whitespace)
        stripped = line.lstrip()
        prefix = line[: len(line) - len(stripped)]

        # Count backticks in the prefix (before directive pattern)
        backticks_before = prefix.count("`")
        return backticks_before % 2 == 1

    def _extract_directives(self, content: str, file_path: Path) -> list[dict[str, Any]]:
        """
        Extract all directive blocks from markdown content (colon fences only).

        Optimized: Pre-computes code block ranges in O(L), then uses O(R) lookups
        instead of O(L) per-line checks. Total complexity: O(L) instead of O(L²).

        Args:
            content: Markdown content
            file_path: Path to file (for error reporting)

        Returns:
            List of directive dictionaries with metadata
        """
        directives = []

        colon_start_pattern = r"^(\s*)(:{3,})\{(\w+(?:-\w+)?)\}([^\n]*)"
        lines = content.split("\n")

        # Pre-compute code block ranges once: O(L)
        code_block_ranges = self._build_code_block_index(lines)

        i = 0
        while i < len(lines):
            match = re.match(colon_start_pattern, lines[i])
            if match:
                indent = len(match.group(1))
                if indent >= 4:
                    i += 1
                    continue

                line_num = i + 1  # 1-indexed
                # O(R) lookup via pre-computed ranges
                if self._is_line_inside_ranges(line_num, code_block_ranges):
                    i += 1
                    continue

                # Inline code check is O(1) per line (just counts backticks on current line)
                if self._is_inside_inline_code_fast(lines[i]):
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

                # NOTE: _check_fence_nesting call removed — produces false positives.
                # Patitas lexer handles this correctly. See: rfc-patitas-structural-validation.md

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

        # Accept both "### Tab: Title" and "### Title" formats
        tab_markers = re.findall(r"^### (?:Tab: )?(.+)$", content, re.MULTILINE)
        directive["tab_count"] = len(tab_markers)

        if len(tab_markers) == 0:
            bad_markers = re.findall(r"^###\s*Ta[^b]", content, re.MULTILINE)
            if bad_markers:
                directive["syntax_error"] = (
                    'Malformed tab marker (use "### Tab: Title" or "### Title")'
                )
            else:
                directive["completeness_error"] = (
                    "Tabs directive has no tab markers (### Tab: Title or ### Title)"
                )
        elif len(tab_markers) == 1:
            directive["completeness_error"] = (
                "Tabs directive has only 1 tab (consider using admonition instead)"
            )

        if not content.strip():
            directive["completeness_error"] = "Tabs directive has no content"

    def _validate_code_tabs_directive(self, directive: dict[str, Any]) -> None:
        """Validate code-tabs directive content.

        Supports both legacy and v2 syntax:
        - Legacy: ### Tab: Language or ### Language markers
        - V2 (RFC: Simplified Code Tabs Syntax): Code fences with language tags
        """
        content = directive["content"]

        if not content.strip():
            directive["completeness_error"] = "Code-tabs directive has no content"
            return

        # V2 syntax: count code blocks with language tags
        # Pattern matches: ```python, ```javascript, etc.
        code_blocks = re.findall(r"^```(\w+)", content, re.MULTILINE)
        directive["tab_count"] = len(code_blocks)

        # Legacy syntax: ### Tab: Language or ### Language markers
        tab_markers = re.findall(r"^### (?:Tab: )?(.+)$", content, re.MULTILINE)

        # Accept either format - v2 code blocks or legacy tab markers
        if len(code_blocks) == 0 and len(tab_markers) == 0:
            directive["completeness_error"] = (
                "Code-tabs directive has no code blocks or tab markers"
            )

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
            # Count tabs - for tabs directive use markers, for code-tabs use code blocks
            if directive_type in ("code-tabs", "code_tabs"):
                # V2 syntax: count code blocks with language tags
                tab_count = len(re.findall(r"^```\w+", content, re.MULTILINE))
            else:
                # Regular tabs: Accept both "### Tab: Title" and "### Title" formats
                tab_count = len(re.findall(r"^### (?:Tab: )?", content, re.MULTILINE))

            content_lines = len([line for line in content.split("\n") if line.strip()])

            if tab_count > 0 and content_lines < (tab_count * 3):
                directive["fence_nesting_warning"] = (
                    f"Directive content appears incomplete ({content_lines} lines, {tab_count} tabs). "
                    f"If tabs contain code blocks, use 4+ backticks (````) for the directive fence."
                )
