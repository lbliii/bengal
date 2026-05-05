"""Fix command — auto-fix common health check issues."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def fix(
    source: Annotated[str, Description("Source directory path")] = "",
    validator: Annotated[
        str, Description("Only fix issues from specific validator (e.g. Directives, Links)")
    ] = "",
    dry_run: Annotated[bool, Description("Show what would be fixed without applying")] = False,
    confirm: Annotated[bool, Description("Ask for confirmation before applying fixes")] = False,
    all: Annotated[
        bool, Description("Apply all fixes including those requiring confirmation")
    ] = False,
    traceback: Annotated[
        str, Description("Traceback verbosity: full | compact | minimal | off")
    ] = "",
) -> dict:
    """Auto-fix common health check issues.

    Analyzes health check results and applies safe fixes automatically.
    By default, only applies SAFE fixes (reversible, no side effects).
    """
    from bengal.cli.utils import configure_traceback, load_site_from_cli
    from bengal.health import HealthCheck
    from bengal.health.remediation import AutoFixer, FixSafety
    from bengal.output import get_cli_output
    from bengal.utils.observability.profile import BuildProfile

    source = source or "."
    traceback_val = traceback or None
    validator_val = validator or None

    cli = get_cli_output()
    configure_traceback(debug=False, traceback=traceback_val, site=None)

    cli.header("Auto-Fix")
    cli.info("Loading site and running health checks...")

    site = load_site_from_cli(
        source=source, config=None, environment=None, profile=BuildProfile.WRITER, cli=cli
    )

    configure_traceback(debug=False, traceback=traceback_val, site=site)

    site.discover_content()
    site.discover_assets()

    health_check = HealthCheck(site)
    report = health_check.run(profile=BuildProfile.WRITER)

    fixer = AutoFixer(report, site_root=site.root_path)
    fixes = fixer.suggest_fixes()

    if validator_val:
        fixes = [f for f in fixes if f.check_result and f.check_result.validator == validator_val]

    if not fixes:
        cli.success("No fixes available - all checks passed!")
        return {
            "status": "ok",
            "message": "No fixes needed",
            "applied": 0,
            "failed": 0,
            "skipped": 0,
        }

    safe_fixes = [f for f in fixes if f.safety == FixSafety.SAFE]
    confirm_fixes = [f for f in fixes if f.safety == FixSafety.CONFIRM]
    unsafe_fixes = [f for f in fixes if f.safety == FixSafety.UNSAFE]

    cli.blank()
    cli.render_write(
        "kv_detail.kida",
        title="Fix Summary",
        items=[
            {"label": "Total fixes", "value": str(len(fixes))},
            {"label": "Safe", "value": f"{len(safe_fixes)} (auto-apply)"},
            *([{"label": "Confirm", "value": str(len(confirm_fixes))}] if confirm_fixes else []),
            *(
                [{"label": "Unsafe", "value": f"{len(unsafe_fixes)} (manual review)"}]
                if unsafe_fixes
                else []
            ),
        ],
    )

    if safe_fixes:
        cli.render_write(
            "item_list.kida",
            title="Safe Fixes",
            items=[{"name": f.description, "description": ""} for f in safe_fixes[:10]],
        )
        if len(safe_fixes) > 10:
            cli.info(f"  ... and {len(safe_fixes) - 10} more")

    if confirm_fixes and (all or confirm):
        cli.render_write(
            "item_list.kida",
            title="Fixes Requiring Confirmation",
            items=[{"name": f.description, "description": ""} for f in confirm_fixes[:10]],
        )

    if unsafe_fixes:
        cli.render_write(
            "validation_report.kida",
            issues=[{"level": "warning", "message": f.description} for f in unsafe_fixes[:5]],
        )

    if dry_run:
        cli.blank()
        cli.info("Dry run mode - no changes made")
        return {
            "status": "ok",
            "message": "Dry run complete",
            "dry_run": True,
            "fixes_available": len(fixes),
            "safe": len(safe_fixes),
            "confirm": len(confirm_fixes),
            "unsafe": len(unsafe_fixes),
        }

    cli.blank()
    fixes_to_apply = safe_fixes.copy()

    if (
        (all or confirm)
        and confirm_fixes
        and cli.confirm(f"Apply {len(confirm_fixes)} fix(es) requiring confirmation?")
    ):
        fixes_to_apply.extend(confirm_fixes)

    if not fixes_to_apply:
        cli.info("No fixes to apply")
        return {
            "status": "skipped",
            "message": "No fixes to apply",
            "applied": 0,
            "failed": 0,
            "skipped": 0,
        }

    cli.info(f"Applying {len(fixes_to_apply)} fix(es)...")
    results = fixer.apply_fixes(fixes_to_apply)

    cli.blank()
    cli.render_write(
        "kv_detail.kida",
        title="Results",
        items=[
            {"label": "Applied", "value": str(results["applied"])},
            {"label": "Failed", "value": str(results["failed"])},
            {"label": "Skipped", "value": str(results["skipped"])},
        ],
        badge={
            "level": "success" if results["failed"] == 0 else "warning",
            "text": "Done" if results["failed"] == 0 else "Partial",
        },
    )

    if results["applied"] > 0:
        cli.blank()
        cli.info("Re-running validation...")
        report_after = health_check.run(profile=BuildProfile.WRITER)
        cli.render_write(
            "validation_report.kida",
            **report_after.format_validation_report(verbose=False, show_suggestions=False),
        )

    return {
        "status": "ok" if results["failed"] == 0 else "error",
        "message": "All fixes applied"
        if results["failed"] == 0
        else f"{results['failed']} fix(es) failed",
        "applied": results["applied"],
        "failed": results["failed"],
        "skipped": results["skipped"],
    }
