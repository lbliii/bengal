"""
Auto-fix commands for Bengal.

Commands:
    bengal fix - Auto-fix common health check issues
"""

from __future__ import annotations

import click

from bengal.cli.helpers import (
    configure_traceback,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.errors.traceback import TracebackStyle
from bengal.health import HealthCheck
from bengal.health.autofix import AutoFixer, FixSafety
from bengal.utils.profile import BuildProfile


@click.command("fix")
@handle_cli_errors(show_art=False)
@click.option(
    "--validator",
    help="Only fix issues from specific validator (e.g., 'Directives', 'Links')",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be fixed without actually applying fixes",
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Ask for confirmation before applying fixes",
)
@click.option(
    "--all",
    "fix_all",
    is_flag=True,
    help="Apply all fixes including those requiring confirmation",
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    help="Traceback verbosity: full | compact | minimal | off",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def fix(
    validator: str | None,
    dry_run: bool,
    confirm: bool,
    fix_all: bool,
    traceback: str | None,
    source: str,
) -> None:
    """
    Auto-fix common health check issues.

    Analyzes health check results and applies safe fixes automatically.
    By default, only applies SAFE fixes (reversible, no side effects).

    Examples:
        bengal fix
        bengal fix --validator Directives
        bengal fix --dry-run  # See what would be fixed
        bengal fix --all  # Apply all fixes including confirmations

    See also:
        bengal validate - Run health checks
    """
    cli = get_cli_output()

    # Configure traceback behavior
    configure_traceback(debug=False, traceback=traceback, site=None)

    # Load site
    cli.header("🔧 Auto-Fix")
    cli.info("Loading site and running health checks...")

    site = load_site_from_cli(
        source=source, config=None, environment=None, profile=BuildProfile.WRITER, cli=cli
    )

    # Apply file-based traceback config after site is loaded
    configure_traceback(debug=False, traceback=traceback, site=site)

    # Discover content (required for validation)
    site.discover_content()
    site.discover_assets()

    # Run health checks
    health_check = HealthCheck(site)
    report = health_check.run(profile=BuildProfile.WRITER)

    # Analyze report and suggest fixes
    fixer = AutoFixer(report, site_root=site.root_path)
    fixes = fixer.suggest_fixes()

    # Filter by validator if specified
    if validator:
        fixes = [f for f in fixes if f.check_result and f.check_result.validator == validator]

    if not fixes:
        cli.success("No fixes available - all checks passed!")
        return

    # Group fixes by safety level
    safe_fixes = [f for f in fixes if f.safety == FixSafety.SAFE]
    confirm_fixes = [f for f in fixes if f.safety == FixSafety.CONFIRM]
    unsafe_fixes = [f for f in fixes if f.safety == FixSafety.UNSAFE]

    # Show summary
    cli.blank()
    cli.info(f"Found {len(fixes)} fix(es):")
    cli.info(f"  • {len(safe_fixes)} safe (can be applied automatically)")
    if confirm_fixes:
        cli.info(f"  • {len(confirm_fixes)} require confirmation")
    if unsafe_fixes:
        cli.warning(f"  • {len(unsafe_fixes)} unsafe (manual review required)")

    # Show what would be fixed
    cli.blank()
    if safe_fixes:
        cli.info("[bold]Safe fixes:[/bold]")
        for fix in safe_fixes[:10]:  # Show first 10
            cli.info(f"  • {fix.description}")
        if len(safe_fixes) > 10:
            cli.info(f"  ... and {len(safe_fixes) - 10} more")

    if confirm_fixes and (fix_all or confirm):
        cli.blank()
        cli.info("[bold]Fixes requiring confirmation:[/bold]")
        for fix in confirm_fixes[:10]:
            cli.info(f"  • {fix.description}")

    if unsafe_fixes:
        cli.blank()
        cli.warning("[bold]Unsafe fixes (manual review required):[/bold]")
        for fix in unsafe_fixes[:5]:
            cli.warning(f"  • {fix.description}")

    # Apply fixes
    if dry_run:
        cli.blank()
        cli.info("Dry run mode - no changes made")
        return

    cli.blank()
    fixes_to_apply = safe_fixes.copy()

    # Ask for confirmation for CONFIRM fixes
    if (
        (fix_all or confirm)
        and confirm_fixes
        and click.confirm(f"Apply {len(confirm_fixes)} fix(es) requiring confirmation?")
    ):
        fixes_to_apply.extend(confirm_fixes)

    if not fixes_to_apply:
        cli.info("No fixes to apply")
        return

    # Apply fixes
    cli.info(f"Applying {len(fixes_to_apply)} fix(es)...")
    results = fixer.apply_fixes(fixes_to_apply)

    cli.blank()
    if results["applied"] > 0:
        cli.success(f"✅ Applied {results['applied']} fix(es)")
    if results["failed"] > 0:
        cli.warning(f"⚠️  {results['failed']} fix(es) failed")
    if results["skipped"] > 0:
        cli.info(f"ℹ️  Skipped {results['skipped']} fix(es)")

    # Re-run validation to show updated status
    if results["applied"] > 0:
        cli.blank()
        cli.info("Re-running validation...")
        report_after = health_check.run(profile=BuildProfile.WRITER)
        cli.info(report_after.format_console(verbose=False, show_suggestions=False))
