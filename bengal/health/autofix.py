"""
Auto-fix framework for health check issues.

Provides safe, automated fixes for common validation errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from bengal.health.report import CheckResult, HealthReport


class FixSafety(Enum):
    """Safety level for auto-fixes."""

    SAFE = "safe"  # Can be applied automatically (reversible, no side effects)
    CONFIRM = "confirm"  # Should ask for confirmation (may have side effects)
    UNSAFE = "unsafe"  # Should not be auto-applied (requires manual review)


@dataclass
class FixAction:
    """
    Represents a single fix action.

    Attributes:
        description: Human-readable description of what will be fixed
        file_path: Path to file that needs fixing
        line_number: Line number (if applicable)
        fix_type: Type of fix (e.g., "directive_fence", "link_update")
        safety: Safety level (SAFE, CONFIRM, UNSAFE)
        apply: Function to apply the fix (returns True if successful)
        check_result: Original CheckResult that triggered this fix
    """

    description: str
    file_path: Path
    line_number: int | None = None
    fix_type: str = ""
    safety: FixSafety = FixSafety.SAFE
    apply: Any = None  # Callable that applies the fix
    check_result: CheckResult | None = None

    def can_apply(self) -> bool:
        """Check if this fix can be applied automatically."""
        return self.safety == FixSafety.SAFE and self.apply is not None


class AutoFixer:
    """
    Auto-fix framework for health check issues.

    Analyzes health check reports and suggests fixes for common errors.
    Provides safe fixes that can be applied automatically.

    Example:
        fixer = AutoFixer(report)
        fixes = fixer.suggest_fixes()
        safe_fixes = [f for f in fixes if f.safety == FixSafety.SAFE]
        fixer.apply_fixes(safe_fixes)
    """

    def __init__(self, report: HealthReport):
        """
        Initialize auto-fixer.

        Args:
            report: Health report to analyze for fixes
        """
        self.report = report
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
        """Suggest fixes for directive validation errors."""
        fixes = []

        for result in validator_report.results:
            if result.status.value != "error":
                continue

            # Check for fence nesting issues
            if (
                "fence nesting" in result.message.lower()
                or "never closed" in result.message.lower()
            ) and result.details:
                # Extract file and line from details
                for detail in result.details:
                    # Parse "cards.md:24 - structure: Line 24: Directive 'cards'..."
                    if ":" in detail and ".md" in detail:
                        parts = detail.split(":")
                        if len(parts) >= 2:
                            file_name = parts[0]
                            try:
                                line_num = int(parts[1].split()[0])
                                file_path = Path(file_name)

                                # Create fix action
                                fixes.append(
                                    FixAction(
                                        description=f"Fix fence nesting in {file_name}:{line_num}",
                                        file_path=file_path,
                                        line_number=line_num,
                                        fix_type="directive_fence",
                                        safety=FixSafety.SAFE,
                                        apply=self._create_fence_fix(file_path, line_num),
                                        check_result=result,
                                    )
                                )
                            except (ValueError, IndexError):
                                pass

        return fixes

    def _create_fence_fix(self, file_path: Path, line_number: int) -> Any:
        """Create a fix function for fence nesting issues."""

        def apply_fix() -> bool:
            """Apply fix: change ``` to ```` for directive fences."""
            try:
                if not file_path.exists():
                    return False

                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                if line_number <= 0 or line_number > len(lines):
                    return False

                # Find directive fence on or near this line
                target_line_idx = line_number - 1
                line = lines[target_line_idx]

                # Check if this is a directive fence (```{name} or :::{name})
                if "```{" in line or "::{" in line:
                    # Change 3 backticks to 4, or 3 colons to 4
                    if line.strip().startswith("```"):
                        # Backtick fence
                        fixed_line = line.replace("```{", "````{", 1)
                    elif line.strip().startswith(":::"):
                        # Colon fence
                        fixed_line = line.replace(":::{", "::::{", 1)
                    else:
                        return False

                    lines[target_line_idx] = fixed_line
                    file_path.write_text("\n".join(lines), encoding="utf-8")
                    return True

                return False
            except Exception:
                return False

        return apply_fix

    def _suggest_link_fixes(self, validator_report: Any) -> list[FixAction]:
        """Suggest fixes for link validation errors."""
        # Future: Implement link fixes
        # - Fix broken internal links (typo detection)
        # - Update moved page references
        return []

    def apply_fixes(self, fixes: list[FixAction] | None = None) -> dict[str, Any]:
        """
        Apply fixes to files.

        Args:
            fixes: List of fixes to apply (if None, uses self.fixes)

        Returns:
            Dictionary with results: {"applied": N, "failed": M, "skipped": K}
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
            except Exception:
                failed += 1

        return {"applied": applied, "failed": failed, "skipped": skipped}

    def apply_safe_fixes(self) -> dict[str, Any]:
        """
        Apply only safe fixes automatically.

        Returns:
            Dictionary with results
        """
        safe_fixes = [f for f in self.fixes if f.safety == FixSafety.SAFE]
        return self.apply_fixes(safe_fixes)
