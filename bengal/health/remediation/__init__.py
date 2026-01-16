"""
Automated remediation subsystem for health check issues.

This package provides automated fixes for common validation errors detected by
health checks. Fixes are categorized by safety level to prevent unintended
modifications.

Components:
AutoFixer: Framework for generating and applying fixes from HealthReport results
FixAction: Encapsulates a single fix with metadata and application logic
FixSafety: Safety classification (SAFE, CONFIRM, UNSAFE)

Architecture:
Remediation is separate from validation - validators detect issues, this
package provides the operational capability to fix them. This separation
enables validators to remain pure and side-effect free.

Related:
- bengal.health.report: HealthReport consumed by AutoFixer
- bengal.health.validators: Produce validation issues
- bengal.cli.commands.fix: CLI interface for autofix

Example:
    >>> from bengal.health.remediation import AutoFixer, FixSafety
    >>> fixer = AutoFixer(report, site_root=site.root_path)
    >>> fixes = fixer.suggest_fixes()
    >>> safe_fixes = [f for f in fixes if f.safety == FixSafety.SAFE]
    >>> results = fixer.apply_fixes(safe_fixes)
    >>> print(f"Applied {results['applied']} fixes")

"""

from __future__ import annotations

from bengal.health.remediation.autofix import AutoFixer, FixAction, FixSafety

__all__ = ["AutoFixer", "FixAction", "FixSafety"]
