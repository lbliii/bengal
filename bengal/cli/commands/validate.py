"""
Validation commands for Bengal.

Commands:
    bengal validate - Run health checks on the site
"""

from __future__ import annotations

from pathlib import Path

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import (
    configure_traceback,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.health import HealthCheck
from bengal.utils.profile import BuildProfile
from bengal.utils.traceback_config import TracebackStyle


@click.group("validate", cls=BengalGroup)
def validate_cli():
    """Validation and health check commands."""
    pass


@validate_cli.command()
@handle_cli_errors(show_art=False)
@click.option(
    "--file",
    "files",
    multiple=True,
    type=click.Path(exists=True, path_type=Path),
    help="Validate specific files (can be specified multiple times)",
)
@click.option(
    "--changed",
    is_flag=True,
    help="Only validate changed files (requires incremental build cache)",
)
@click.option(
    "--watch",
    is_flag=True,
    help="Watch mode: validate on file changes (experimental)",
)
@click.option(
    "--profile",
    type=click.Choice(["writer", "theme-dev", "developer"], case_sensitive=False),
    help="Build profile to use (writer, theme-dev, developer)",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show verbose output (all checks, not just problems)",
)
@click.option(
    "--incremental",
    is_flag=True,
    help="Use incremental validation (only check changed files)",
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    help="Traceback verbosity: full | compact | minimal | off",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def validate(
    files: tuple[Path, ...],
    changed: bool,
    watch: bool,
    profile: str | None,
    verbose: bool,
    incremental: bool,
    traceback: str | None,
    source: str,
) -> None:
    """
    🔍 Validate site health and content quality.

    Runs health checks on your site to find errors, warnings, and issues.
    By default, shows only problems (errors and warnings).

    Examples:
        bengal validate
        bengal validate --file content/page.md
        bengal validate --changed
        bengal validate --profile writer
        bengal validate --verbose

    See also:
        bengal site build - Build the site
        bengal health linkcheck - Check links specifically
    """
    cli = get_cli_output()

    # Configure traceback behavior
    configure_traceback(debug=False, traceback=traceback, site=None)

    # Load site
    cli.header("🔍 Health Check Validation")
    cli.info("Loading site...")

    # Determine profile (default to WRITER for fast validation)
    build_profile = BuildProfile.from_string(profile) if profile else BuildProfile.WRITER

    site = load_site_from_cli(
        source=source, config=None, environment=None, profile=build_profile, cli=cli
    )

    # Apply file-based traceback config after site is loaded
    configure_traceback(debug=False, traceback=traceback, site=site)

    # Discover content (required for validation)
    site.discover_content()
    site.discover_assets()

    cli.success(f"Loaded {len(site.pages)} pages")

    # Determine context for validation
    context: list[Path] | None = None
    if files:
        context = list(files)
    elif changed:
        # Find changed files using build cache
        from bengal.cache import BuildCache

        cache_dir = site.root_path / ".bengal"
        cache_path = cache_dir / "cache.json"
        cache = BuildCache.load(cache_path)

        context = []
        for page in site.pages:
            if page.source_path and cache.is_changed(page.source_path):
                context.append(page.source_path)

        if not context:
            cli.info("No changed files found - all files are up to date")
            return
        else:
            cli.info(f"Found {len(context)} changed file(s)")

    # Load cache for incremental validation
    cache = None
    if incremental or changed:
        from bengal.cache import BuildCache

        cache_dir = site.root_path / ".bengal"
        cache_path = cache_dir / "cache.json"
        cache = BuildCache.load(cache_path)

    # Run health checks
    cli.blank()
    health_check = HealthCheck(site)
    report = health_check.run(
        profile=build_profile,
        verbose=verbose,
        incremental=incremental or changed,
        context=context,
        cache=cache,
    )

    # Print report
    cli.blank()
    cli.info(report.format_console(verbose=verbose))

    # Exit with error code if there are errors
    if report.has_errors():
        raise click.ClickException(f"Validation failed: {report.error_count} error(s) found")
    elif report.has_warnings():
        cli.warning(f"Validation completed with {report.warning_count} warning(s)")
    else:
        cli.success("Validation passed - no issues found")
