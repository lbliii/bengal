"""
Auto-fix framework for health check issues.

This module provides automated fixes for common validation errors detected by
health checks. Fixes are categorized by safety level to prevent unintended
modifications.

Safety Levels:
    SAFE: Can be applied automatically (reversible, no side effects)
    CONFIRM: Requires user confirmation (may have side effects)
    UNSAFE: Requires manual review (complex changes)

Supported Fixes:
    - Directive fence nesting: Adjusts fence depths for proper nesting hierarchy
    - Link fixes: (Future) Typo detection and moved page reference updates

Architecture:
    AutoFixer analyzes HealthReport results and generates FixAction objects.
    Each FixAction contains a callable that applies the fix. Fixes are designed
    to be atomic and file-local to minimize risk.

Related:
    - bengal.health.report: HealthReport consumed by AutoFixer
    - bengal.health.validators.directives: Produces directive issues

Example:
    >>> from bengal.health.autofix import AutoFixer, FixSafety
    >>> fixer = AutoFixer(report, site_root=site.root_path)
    >>> fixes = fixer.suggest_fixes()
    >>> safe_fixes = [f for f in fixes if f.safety == FixSafety.SAFE]
    >>> results = fixer.apply_fixes(safe_fixes)
    >>> print(f"Applied {results['applied']} fixes")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from bengal.health.report import CheckResult, HealthReport
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class FixSafety(Enum):
    """
    Safety classification for auto-fix actions.

    Determines how fixes are applied:
        SAFE: Apply automatically (reversible, file-local, no side effects)
        CONFIRM: Prompt user before applying (may affect multiple files)
        UNSAFE: Require manual review (complex structural changes)

    Usage:
        Use FixSafety.SAFE for well-tested, atomic fixes like fence depth
        adjustments. Use CONFIRM for fixes that modify cross-references.
        Use UNSAFE for experimental or risky fixes.
    """

    SAFE = "safe"
    CONFIRM = "confirm"
    UNSAFE = "unsafe"


@dataclass
class FixAction:
    """
    Single auto-fix action with metadata and application logic.

    FixAction encapsulates what needs to be fixed, where, and how. The apply
    callable performs the actual fix when invoked. Fixes are designed to be
    atomic and file-local to minimize risk.

    Attributes:
        description: Human-readable summary of the fix
        file_path: Absolute path to file requiring modification
        line_number: Starting line number (None if file-wide)
        fix_type: Category identifier (e.g., "directive_fence", "link_update")
        safety: FixSafety level determining application policy
        apply: Callable returning True on success, False on failure
        check_result: Original CheckResult that triggered this fix suggestion

    Example:
        >>> fix = FixAction(
        ...     description="Fix fence nesting in cards.md (3 directives)",
        ...     file_path=Path("/site/content/cards.md"),
        ...     line_number=24,
        ...     fix_type="directive_fence",
        ...     safety=FixSafety.SAFE,
        ...     apply=lambda: True,
        ... )
        >>> if fix.can_apply():
        ...     fix.apply()
    """

    description: str
    file_path: Path
    line_number: int | None = None
    fix_type: str = ""
    safety: FixSafety = FixSafety.SAFE
    apply: Any = None
    check_result: CheckResult | None = None

    def can_apply(self) -> bool:
        """
        Check if this fix can be applied automatically.

        Returns:
            True if safety is SAFE and apply callable is set.
        """
        return self.safety == FixSafety.SAFE and self.apply is not None


class AutoFixer:
    """
    Framework for automated fixes of health check issues.

    AutoFixer analyzes HealthReport results, identifies fixable issues, and
    generates FixAction objects. Currently supports directive fence nesting
    fixes with hierarchical depth calculation.

    Supported Fix Types:
        directive_fence: Adjusts fence depths for proper MyST directive nesting
        link_update: (Future) Fix broken internal links, update moved pages

    Design Principles:
        - Fixes are atomic and file-local (no cross-file dependencies)
        - Safety levels prevent accidental destructive changes
        - Full hierarchy analysis ensures child/parent consistency
        - Fixes are reversible via version control

    Attributes:
        report: HealthReport to analyze for fixable issues
        site_root: Absolute path to site root (required)
        fixes: List of suggested FixAction objects (populated by suggest_fixes)

    Example:
        >>> fixer = AutoFixer(report, site_root=site.root_path)
        >>> fixes = fixer.suggest_fixes()
        >>> safe = [f for f in fixes if f.safety == FixSafety.SAFE]
        >>> results = fixer.apply_fixes(safe)
        >>> print(f"Applied {results['applied']} fixes")

    See Also:
        - bengal.health.report.HealthReport: Input report format
        - bengal.health.validators.directives: Produces directive issues
    """

    def __init__(self, report: HealthReport, site_root: Path):
        """
        Initialize auto-fixer.

        Args:
            report: Health report to analyze for fixes
            site_root: Root path of the site (required, must be absolute)

        Raises:
            ValueError: If site_root is not provided or not absolute

        Note:
            site_root must be explicit - no fallback to Path.cwd() to ensure
            consistent behavior regardless of working directory.
            See: plan/implemented/rfc-path-resolution-architecture.md
        """
        from bengal.errors import BengalError

        if not site_root:
            raise BengalError(
                "site_root is required for AutoFixer",
                suggestion="Provide an absolute site root path",
            )
        if not site_root.is_absolute():
            site_root = site_root.resolve()
        self.report = report
        self.site_root = site_root
        self.fixes: list[FixAction] = []

    def suggest_fixes(self) -> list[FixAction]:
        """
        Analyze report and suggest fixes for all issues.

        Returns:
            List of FixAction objects representing possible fixes
        """
        fixes = []

        for validator_report in self.report.validator_reports:
            # Route to validator-specific fixers
            if validator_report.validator_name == "Directives":
                fixes.extend(self._suggest_directive_fixes(validator_report))
            elif validator_report.validator_name == "Links":
                fixes.extend(self._suggest_link_fixes(validator_report))
            # Add more validators as needed

        self.fixes = fixes
        return fixes

    def _suggest_directive_fixes(self, validator_report: Any) -> list[FixAction]:
        """
        Suggest fixes for directive fence nesting issues.

        Analyzes validation results for fence nesting errors/warnings and creates
        FixAction objects. Uses metadata (preferred) or falls back to detail parsing.

        Args:
            validator_report: ValidatorReport from Directives validator.

        Returns:
            List of FixAction objects for directive fence fixes.
        """
        fixes: list[FixAction] = []

        for result in validator_report.results:
            # Handle both errors and warnings (fence nesting is a warning)
            if result.status.value not in ("error", "warning"):
                continue

            # Check for fence nesting issues
            if (
                "fence nesting" in result.message.lower()
                or "never closed" in result.message.lower()
            ):
                # 1. Try metadata (Precise, Preferred)
                if result.metadata and "fence_warnings" in result.metadata:
                    fence_warnings = result.metadata["fence_warnings"]
                    files_to_fix: dict[str, list[int]] = {}

                    for w in fence_warnings:
                        file_path_str = w.get("page")
                        line = w.get("line")
                        if file_path_str and line is not None:
                            if file_path_str not in files_to_fix:
                                files_to_fix[file_path_str] = []
                            files_to_fix[file_path_str].append(line)

                    for file_path_str, line_numbers in files_to_fix.items():
                        file_path = Path(file_path_str)

                        # Avoid duplicates
                        if any(
                            f.file_path == file_path and f.fix_type == "directive_fence"
                            for f in fixes
                        ):
                            continue

                        # Resolve relative to site root if possible for display
                        try:
                            rel_path = file_path.relative_to(self.site_root)
                        except ValueError:
                            rel_path = file_path

                        fixes.append(
                            FixAction(
                                description=f"Fix fence nesting in {rel_path} ({len(line_numbers)} directive(s))",
                                file_path=file_path,
                                line_number=min(line_numbers) if line_numbers else None,
                                fix_type="directive_fence",
                                safety=FixSafety.SAFE,
                                apply=self._create_file_fix(file_path, line_numbers),
                                check_result=result,
                            )
                        )
                    continue

                # 2. Fallback to details parsing (Legacy/Fallback)
                if result.details:
                    # Extract file and line from details
                    for detail in result.details:
                        # Parse formats like:
                        # - "cards.md:24,43,51 - 3 issue(s)" (multiple lines)
                        # - "cards.md:24 - structure: Line 24: Directive 'cards'..." (single line)
                        if ":" in detail and ".md" in detail:
                            parts = detail.split(":", 1)
                            if len(parts) >= 2:
                                file_name = parts[0]
                                line_part = parts[1].split()[
                                    0
                                ]  # Get first part (may be "24" or "24,43,51")

                                # Handle multiple line numbers separated by commas
                                line_numbers = []
                                for line_str in line_part.split(","):
                                    try:
                                        line_num = int(line_str.strip())
                                        line_numbers.append(line_num)
                                    except ValueError:
                                        continue

                                if line_numbers:
                                    # Find the actual file path (file_name might be just the basename)
                                    # Search in site root and common content directories
                                    possible_paths = [
                                        self.site_root / file_name,
                                        self.site_root / "content" / file_name,
                                    ]
                                    # Also search recursively for the file
                                    found_files = list(self.site_root.rglob(file_name))

                                    # Use first found file, or first possible path if exists
                                    found_file_path: Path | None = None
                                    for path in found_files[:1] if found_files else possible_paths:
                                        if path.exists():
                                            found_file_path = path.resolve()
                                            break

                                    if (
                                        found_file_path
                                        and found_file_path.exists()
                                        and not any(
                                            f.file_path == found_file_path
                                            and f.fix_type == "directive_fence"
                                            for f in fixes
                                        )
                                    ):
                                        # Group fixes by file - create one fix action per file that fixes all directives
                                        # This ensures we fix the entire hierarchy in one pass
                                        # Create a single fix action for this file that handles all directives
                                        fixes.append(
                                            FixAction(
                                                description=f"Fix fence nesting in {found_file_path.relative_to(self.site_root)} ({len(line_numbers)} directive(s))",
                                                file_path=found_file_path,
                                                line_number=min(line_numbers)
                                                if line_numbers
                                                else None,  # Use first line for reference
                                                fix_type="directive_fence",
                                                safety=FixSafety.SAFE,
                                                apply=self._create_file_fix(
                                                    found_file_path, line_numbers
                                                ),
                                                check_result=result,
                                            )
                                        )

        return fixes

    def _create_file_fix(self, file_path: Path, line_numbers: list[int]) -> Any:
        """
        Create a fix callable for all directives in a file.

        The generated fix function analyzes the entire file's directive hierarchy
        and adjusts fence depths to ensure proper nesting. Fixes are applied in
        a single pass covering all nested children and grandchildren.

        Args:
            file_path: Absolute path to the markdown file.
            line_numbers: Line numbers of directives with nesting issues.

        Returns:
            Callable that returns True on success, False on failure.

        Algorithm:
            1. Parse directive hierarchy from file
            2. Mark affected directives and their ancestors/descendants
            3. Calculate required depths (baseline=3, +1 per nesting level)
            4. Apply fixes deepest-first to preserve hierarchy
        """

        def apply_fix() -> bool:
            """Apply fixes to all directives in the file."""
            try:
                if not file_path.exists():
                    return False

                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                # Parse directive hierarchy
                directives = self._parse_directive_hierarchy(lines)

                # Find all directives that need fixing (those at reported line numbers or their parents/children)
                directives_to_fix = set()
                baseline_depth = 3

                # For each reported line number, find the directive and mark it + all its hierarchy for fixing
                for line_num in line_numbers:
                    # Find directive at this line (or corresponding opening fence)
                    target_directive = None
                    for directive in directives:
                        if directive["line"] == line_num:
                            target_directive = directive
                            break

                    # If not found, might be a closing fence - find corresponding opening
                    if not target_directive and line_num <= len(lines):
                        line = lines[line_num - 1]
                        closing_colon = re.match(r"^(\s*)(:{3,})\s*$", line)
                        closing_backtick = re.match(r"^(\s*)(`{3,})\s*$", line)

                        if closing_colon or closing_backtick:
                            if closing_colon:
                                closing_depth = len(closing_colon.group(2))
                                fence_type = "colon"
                            else:
                                assert closing_backtick is not None  # Type narrowing
                                closing_depth = len(closing_backtick.group(2))
                                fence_type = "backtick"

                            for directive in reversed(directives):
                                if (
                                    directive["fence_type"] == fence_type
                                    and directive["current_depth"] == closing_depth
                                    and directive["line"] < line_num
                                ):
                                    target_directive = directive
                                    break

                    if not target_directive:
                        continue

                    # Mark this directive and all its ancestors and descendants for fixing
                    directives_to_fix.add(target_directive["line"])

                    # Add ancestors
                    current = target_directive
                    while current.get("parent"):
                        parent_line = current["parent"]
                        parent = next((d for d in directives if d["line"] == parent_line), None)
                        if parent:
                            directives_to_fix.add(parent["line"])
                            current = parent
                        else:
                            break

                    # Add descendants (children, grandchildren, etc.)
                    for directive in directives:
                        current = directive
                        while current.get("parent"):
                            parent_line = current["parent"]
                            if (
                                parent_line == target_directive["line"]
                                or parent_line in directives_to_fix
                            ):
                                directives_to_fix.add(directive["line"])
                                break
                            parent = next((d for d in directives if d["line"] == parent_line), None)
                            if parent:
                                current = parent
                            else:
                                break

                # Calculate required depths for all directives to fix
                directives_list = [d for d in directives if d["line"] in directives_to_fix]

                # Build hierarchy and calculate depths
                for directive in directives_list:
                    # Find ancestors
                    ancestors = []
                    current = directive
                    while current.get("parent"):
                        parent_line = current["parent"]
                        parent = next((d for d in directives if d["line"] == parent_line), None)
                        if parent:
                            ancestors.append(parent)
                            current = parent
                        else:
                            break

                    # Find deepest nested descendant
                    descendants = [
                        d for d in directives if self._is_descendant(d, directive, directives)
                    ]
                    if descendants:
                        deepest = max(descendants, key=lambda d: self._get_depth(d, directives))
                        depth_from_deepest = self._get_depth(
                            directive, directives
                        ) - self._get_depth(deepest, directives)
                        directive["required_depth"] = baseline_depth + abs(depth_from_deepest)
                    else:
                        # No descendants, use ancestor count
                        directive["required_depth"] = baseline_depth + len(ancestors)

                # Apply fixes (deepest first, then parents)
                directives_list.sort(key=lambda d: d["required_depth"], reverse=True)
                for directive in directives_list:
                    if directive["current_depth"] < directive["required_depth"]:
                        self._apply_single_fix(lines, directive)

                # Write file
                file_path.write_text("\n".join(lines), encoding="utf-8")
                return True

            except Exception as e:
                import traceback

                logger.error(
                    "autofix_apply_failed",
                    file_path=str(file_path),
                    error=str(e),
                    error_type=type(e).__name__,
                )
                traceback.print_exc()
                return False

        return apply_fix

    def _is_descendant(
        self,
        directive: dict[str, Any],
        ancestor: dict[str, Any],
        all_directives: list[dict[str, Any]],
    ) -> bool:
        """
        Check if directive is a descendant of ancestor in the hierarchy.

        Args:
            directive: Candidate descendant directive dict.
            ancestor: Potential ancestor directive dict.
            all_directives: Complete list of parsed directives.

        Returns:
            True if directive is nested within ancestor.
        """
        current: dict[str, Any] | None = directive
        while current and current.get("parent"):
            if current["parent"] == ancestor["line"]:
                return True
            current = next((d for d in all_directives if d["line"] == current["parent"]), None)
            if not current:
                break
        return False

    def _get_depth(self, directive: dict[str, Any], all_directives: list[dict[str, Any]]) -> int:
        """
        Get nesting depth of a directive in the hierarchy.

        Args:
            directive: Directive dict to measure.
            all_directives: Complete list of parsed directives.

        Returns:
            Nesting depth (0=root level, 1=child of root, etc.).
        """
        depth = 0
        current: dict[str, Any] | None = directive
        while current and current.get("parent"):
            depth += 1
            current = next((d for d in all_directives if d["line"] == current["parent"]), None)
            if not current:
                break
        return depth

    def _create_fence_fix(self, file_path: Path, line_number: int) -> Any:
        """
        Create a fix function for fence nesting issues.

        Implements hierarchical fix: increments all parents +1 based on deepest nested directive.
        Example: tab-set (grandparent) > tab-item (parent) > note (child, baseline 3)
        Result: grandparent=5, parent=4, child=3

        The fix analyzes the entire file to understand directive hierarchy and fixes
        from bottom-up (deepest first, then parents).
        """

        def apply_fix() -> bool:
            """
            Apply hierarchical fix: increment all parents +1 based on deepest nested directive.

            Strategy:
            1. Parse entire file to build directive hierarchy tree
            2. Find deepest nested directive (baseline depth, usually 3)
            3. Work backwards up the tree, incrementing each parent by 1
            4. Fix from bottom-up (deepest first, then parents)
            """
            try:
                if not file_path.exists():
                    return False

                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                if line_number <= 0 or line_number > len(lines):
                    return False

                # Step 1: Build directive hierarchy
                directives = self._parse_directive_hierarchy(lines)

                # Step 2: Find the directive at line_number and its ancestors
                # Handle case where line_number might be a closing fence instead of opening fence
                target_directive = None
                for directive in directives:
                    if directive["line"] == line_number:
                        target_directive = directive
                        break

                # If no directive found, check if this line is a closing fence
                # and find the corresponding opening fence
                if not target_directive and line_number <= len(lines):
                    line = lines[line_number - 1]
                    closing_colon = re.match(r"^(\s*)(:{3,})\s*$", line)
                    closing_backtick = re.match(r"^(\s*)(`{3,})\s*$", line)

                    if closing_colon or closing_backtick:
                        if closing_colon:
                            closing_depth = len(closing_colon.group(2))
                            fence_type = "colon"
                        else:
                            assert closing_backtick is not None  # Type narrowing
                            closing_depth = len(closing_backtick.group(2))
                            fence_type = "backtick"

                        # Find most recent opening fence before this line with matching type and depth
                        for directive in reversed(directives):
                            if (
                                directive["fence_type"] == fence_type
                                and directive["current_depth"] == closing_depth
                                and directive["line"] < line_number
                            ):
                                target_directive = directive
                                break

                if not target_directive:
                    return False

                # Step 3: Build ancestor chain (parent -> grandparent -> ...)
                # Build from child to root (deepest first)
                ancestors = []
                current = target_directive
                while current.get("parent"):
                    parent_line = current["parent"]
                    parent = next((d for d in directives if d["line"] == parent_line), None)
                    if parent:
                        ancestors.append(parent)
                        current = parent
                    else:
                        break

                # ancestors is now [parent, grandparent, ...] (child to root order)
                # Step 4: Determine required depths (deepest = baseline 3, each parent +1)
                baseline_depth = 3
                target_directive["required_depth"] = baseline_depth
                # Reverse ancestors so we process from root to child (top to bottom)
                # Root needs baseline + len(ancestors), each child needs baseline + distance_from_deepest
                ancestors_reversed = list(
                    reversed(ancestors)
                )  # [grandparent, parent] (root to child)
                for i, ancestor in enumerate(ancestors_reversed):
                    # Root (i=0) needs baseline + len(ancestors), next needs baseline + len(ancestors) - 1, etc.
                    ancestor["required_depth"] = baseline_depth + len(ancestors) - i

                # Step 5: Find all descendants that need fixing
                # When we fix a directive, we also need to fix all its nested children
                descendants = []
                for directive in directives:
                    # Check if this directive is a descendant of target_directive
                    current = directive
                    depth_from_target = 0
                    found_target = False

                    # Walk up the parent chain to see if target_directive is an ancestor
                    while current.get("parent"):
                        parent_line = current["parent"]
                        if parent_line == target_directive["line"]:
                            # This directive is a direct child of target_directive
                            found_target = True
                            break
                        parent = next((d for d in directives if d["line"] == parent_line), None)
                        if parent:
                            depth_from_target += 1
                            current = parent
                        else:
                            break

                    if found_target:
                        # Calculate required depth: baseline + distance from target + ancestors
                        directive["required_depth"] = (
                            baseline_depth + depth_from_target + len(ancestors)
                        )
                        descendants.append(directive)

                # Step 6: Apply fixes from bottom-up (deepest first, then parents)
                # Fix target directive first (deepest nested)
                if target_directive["current_depth"] < target_directive["required_depth"]:
                    self._apply_single_fix(lines, target_directive)

                # Fix descendants (children, grandchildren, etc.) - deepest first
                descendants.sort(key=lambda d: d["required_depth"], reverse=True)
                for descendant in descendants:
                    if descendant["current_depth"] < descendant["required_depth"]:
                        self._apply_single_fix(lines, descendant)

                # Fix ancestors from root to child (top to bottom) so we don't break parent references
                for ancestor in ancestors_reversed:
                    if ancestor["current_depth"] < ancestor["required_depth"]:
                        self._apply_single_fix(lines, ancestor)

                # Write file
                file_path.write_text("\n".join(lines), encoding="utf-8")
                return True

            except Exception as e:
                import traceback

                logger.error(
                    "autofix_apply_failed",
                    file_path=str(file_path),
                    error=str(e),
                    error_type=type(e).__name__,
                )
                traceback.print_exc()
                return False

        return apply_fix

    def _parse_directive_hierarchy(self, lines: list[str]) -> list[dict[str, Any]]:
        """
        Parse directive hierarchy from file lines.

        Scans file content for MyST directive fences (backtick and colon style)
        and builds a parent-child hierarchy using a stack-based approach.

        Args:
            lines: List of file lines (newline-stripped).

        Returns:
            List of directive dicts with keys:
                line: 1-based line number of opening fence
                type: Directive name (e.g., "note", "tab-set")
                fence_type: "backtick" or "colon"
                current_depth: Number of fence characters
                indent: Leading whitespace count
                parent: Line number of parent directive (None if root)
                fence_marker: Actual fence string (e.g., "```", ":::")
                line_content: Full line text
        """
        directives = []
        stack: list[dict[str, Any]] = []  # Stack of open directives

        for line_num, line in enumerate(lines, 1):
            # Check for backtick fences
            backtick_match = re.match(r"^(\s*)(`{3,})\{(\w+(?:-\w+)?)\}", line)
            if backtick_match:
                indent = len(backtick_match.group(1))
                fence_marker = backtick_match.group(2)
                directive_type = backtick_match.group(3)
                depth = len(fence_marker)

                # Find parent: most recent directive on stack that's still open
                # (backtick fences can nest, parent is whatever is currently open)
                parent = stack[-1] if stack else None

                directive = {
                    "line": line_num,
                    "type": directive_type,
                    "fence_type": "backtick",
                    "current_depth": depth,
                    "indent": indent,
                    "parent": parent["line"] if parent else None,
                    "fence_marker": fence_marker,
                    "line_content": line,
                }
                directives.append(directive)
                stack.append(directive)
                continue

            # Check for colon fences
            colon_match = re.match(r"^(\s*)(:{3,})\{(\w+(?:-\w+)?)\}", line)
            if colon_match:
                indent = len(colon_match.group(1))
                fence_marker = colon_match.group(2)
                directive_type = colon_match.group(3)
                depth = len(fence_marker)

                # Find parent: most recent directive on stack that's still open
                # (not just by indentation - colon fences can nest without indentation)
                parent = stack[-1] if stack else None

                directive = {
                    "line": line_num,
                    "type": directive_type,
                    "fence_type": "colon",
                    "current_depth": depth,
                    "indent": indent,
                    "parent": parent["line"] if parent else None,
                    "fence_marker": fence_marker,
                    "line_content": line,
                }
                directives.append(directive)
                stack.append(directive)
                continue

            # Check for closing fences (remove from stack)
            closing_backtick = re.match(r"^(\s*)(`{3,})\s*$", line)
            closing_colon = re.match(r"^(\s*)(:{3,})\s*$", line)

            if (closing_backtick or closing_colon) and stack:
                # Pop matching directive from stack
                # Match by fence type and depth
                if closing_backtick:
                    fence_type = "backtick"
                    closing_depth = len(closing_backtick.group(2))
                else:
                    assert closing_colon is not None  # Type narrowing
                    fence_type = "colon"
                    closing_depth = len(closing_colon.group(2))

                # Find matching directive on stack (most recent with same type and depth)
                for i in range(len(stack) - 1, -1, -1):
                    if (
                        stack[i]["fence_type"] == fence_type
                        and stack[i]["current_depth"] == closing_depth
                    ):
                        stack.pop(i)
                        break

        return directives

    def _apply_single_fix(self, lines: list[str], directive: dict[str, Any]) -> None:
        """
        Apply fix to a single directive by increasing fence depth.

        Modifies lines in-place. Finds and updates both opening and closing
        fences to match the required depth.

        Args:
            lines: File lines list (modified in-place).
            directive: Directive dict with current_depth and required_depth.
        """
        line_idx = directive["line"] - 1
        if line_idx < 0 or line_idx >= len(lines):
            return

        line = lines[line_idx]
        current_depth = directive["current_depth"]
        required_depth = directive["required_depth"]

        if current_depth >= required_depth:
            return  # Already correct

        if directive["fence_type"] == "backtick":
            # Replace opening fence
            old_fence = "`" * current_depth
            new_fence = "`" * required_depth
            lines[line_idx] = line.replace(f"{old_fence}{{", f"{new_fence}{{", 1)

            # Find and replace closing fence
            for i in range(line_idx + 1, min(line_idx + 200, len(lines))):
                if lines[i].strip() == old_fence:
                    lines[i] = lines[i].replace(old_fence, new_fence, 1)
                    break

        elif directive["fence_type"] == "colon":
            # Replace opening fence
            old_fence = ":" * current_depth
            new_fence = ":" * required_depth
            lines[line_idx] = line.replace(f"{old_fence}{{", f"{new_fence}{{", 1)

            # Find matching closing fence (accounting for nesting)
            nesting_depth = 0
            for i in range(line_idx + 1, min(line_idx + 200, len(lines))):
                # Check for opening fences
                opening_match = re.match(r"^(\s*)(:{3,})\{", lines[i])
                if opening_match:
                    nesting_depth += 1
                    continue

                # Check for closing fences
                closing_match = re.match(r"^(\s*)(:{3,})\s*$", lines[i])
                if closing_match:
                    closing_depth = len(closing_match.group(2))
                    if closing_depth == current_depth and nesting_depth == 0:
                        lines[i] = lines[i].replace(old_fence, new_fence, 1)
                        break
                    elif closing_depth == current_depth:
                        nesting_depth -= 1

    def _suggest_link_fixes(self, validator_report: Any) -> list[FixAction]:
        """
        Suggest fixes for link validation errors.

        Future implementation will support:
            - Typo detection for broken internal links
            - Automatic updates for moved page references
            - Anchor fixes for renamed headings

        Args:
            validator_report: ValidatorReport from Links validator.

        Returns:
            List of FixAction objects (currently empty, future implementation).
        """
        return []

    def apply_fixes(self, fixes: list[FixAction] | None = None) -> dict[str, Any]:
        """
        Apply specified fixes to files.

        Iterates through fixes and invokes their apply callables. Tracks success,
        failure, and skip counts. Fixes that cannot be applied (wrong safety
        level or missing callable) are skipped.

        Args:
            fixes: List of FixAction to apply. If None, uses self.fixes.

        Returns:
            Dict with counts: {"applied": N, "failed": M, "skipped": K}
        """
        if fixes is None:
            fixes = self.fixes

        applied = 0
        failed = 0
        skipped = 0

        for fix in fixes:
            if not fix.can_apply():
                skipped += 1
                continue

            try:
                if fix.apply():
                    applied += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(
                    "autofix_apply_failed",
                    fix_type=type(fix).__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                failed += 1

        return {"applied": applied, "failed": failed, "skipped": skipped}

    def apply_safe_fixes(self) -> dict[str, Any]:
        """
        Apply only SAFE fixes automatically.

        Convenience method that filters self.fixes to FixSafety.SAFE and applies
        them. Use this for unattended/automated fix application.

        Returns:
            Dict with counts: {"applied": N, "failed": M, "skipped": K}
        """
        safe_fixes = [f for f in self.fixes if f.safety == FixSafety.SAFE]
        return self.apply_fixes(safe_fixes)
