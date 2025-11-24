"""
Health check commands for Bengal.

Commands:
    bengal health linkcheck - Check internal and external links
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import configure_traceback, load_site_from_cli
from bengal.core.site import Site
from bengal.health.linkcheck.orchestrator import LinkCheckOrchestrator
from bengal.utils.cli_output import CLIOutput
from bengal.utils.traceback_config import TracebackStyle


@click.group("health", cls=BengalGroup)
def health_cli():
    """Health check and validation commands."""
    pass


@health_cli.command("linkcheck")
@click.option(
    "--external-only",
    is_flag=True,
    help="Only check external links (skip internal validation)",
)
@click.option(
    "--internal-only",
    is_flag=True,
    help="Only check internal links (skip external validation)",
)
@click.option(
    "--max-concurrency",
    type=int,
    help="Maximum concurrent HTTP requests (default: 20)",
)
@click.option(
    "--per-host-limit",
    type=int,
    help="Maximum concurrent requests per host (default: 4)",
)
@click.option(
    "--timeout",
    type=float,
    help="Request timeout in seconds (default: 10.0)",
)
@click.option(
    "--retries",
    type=int,
    help="Number of retry attempts (default: 2)",
)
@click.option(
    "--retry-backoff",
    type=float,
    help="Base backoff time for exponential backoff in seconds (default: 0.5)",
)
@click.option(
    "--exclude",
    multiple=True,
    help="URL pattern to exclude (repeatable, regex supported)",
)
@click.option(
    "--exclude-domain",
    multiple=True,
    help="Domain to exclude (repeatable, e.g., 'localhost')",
)
@click.option(
    "--ignore-status",
    multiple=True,
    help="Status code or range to ignore (repeatable, e.g., '500-599', '403')",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["console", "json"]),
    default="console",
    help="Output format",
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(),
    help="Output file (for JSON format)",
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    help="Traceback verbosity: full | compact | minimal | off",
)
def linkcheck(
    external_only: bool,
    internal_only: bool,
    max_concurrency: int | None,
    per_host_limit: int | None,
    timeout: float | None,
    retries: int | None,
    retry_backoff: float | None,
    exclude: tuple[str, ...],
    exclude_domain: tuple[str, ...],
    ignore_status: tuple[str, ...],
    output_format: str,
    output_file: str | None,
    traceback: str | None,
) -> None:
    """
    Check internal and external links in the site.

    Validates that all links in your site work correctly:
    - Internal links point to existing pages and anchors
    - External links return successful HTTP status codes

    Examples:
        bengal health linkcheck
        bengal health linkcheck --external-only
        bengal health linkcheck --format json --output report.json
        bengal health linkcheck --exclude "^/api/preview/" --ignore-status "500-599"
    """
    cli = CLIOutput()

    # Configure traceback behavior
    configure_traceback(debug=False, traceback=traceback)

    # Load site
    cli.header("🔗 Link Checker")
    cli.info("Loading site...")

    site = load_site_from_cli(source=".", config=None, environment=None, profile=None, cli=cli)

    # Apply file-based traceback config after site is loaded
    configure_traceback(debug=False, traceback=traceback, site=site)

    site.discover_content()
    site.discover_assets()

    cli.success(f"Loaded {len(site.pages)} pages")

    # Determine what to check
    check_internal = not external_only
    check_external = not internal_only

    # Ensure site is built before checking internal links
    if check_internal:
        try:
            _ensure_site_built(site, cli)
        except Exception as e:
            cli.error(f"Failed to build site: {e}")
            # Traceback already configured, will be shown by error handler if needed
            raise click.Abort() from e

    # Build config from CLI flags and site config
    linkcheck_config = _build_config(
        site.config,
        max_concurrency,
        per_host_limit,
        timeout,
        retries,
        retry_backoff,
        exclude,
        exclude_domain,
        ignore_status,
    )

    # Run link checker
    try:
        cli.info(f"Checking links (internal: {check_internal}, external: {check_external})...")

        orchestrator = LinkCheckOrchestrator(
            site,
            check_internal=check_internal,
            check_external=check_external,
            config=linkcheck_config,
        )

        results, summary = orchestrator.check_all_links()

        # Output results
        if output_format == "json":
            report = orchestrator.format_json_report(results, summary)

            if output_file:
                output_path = Path(output_file)
                output_path.write_text(json.dumps(report, indent=2))
                cli.success(f"JSON report saved to {output_path}")
            else:
                print(json.dumps(report, indent=2))

        else:  # console format
            report = orchestrator.format_console_report(results, summary)
            print(report)

        # Exit with appropriate code
        if not summary.passed:
            raise click.Abort()

    except click.Abort:
        raise
    except Exception as e:
        cli.error(f"Link check failed: {e}")
        # Traceback already configured, will be shown if needed
        raise click.Abort() from e


def _ensure_site_built(site: Site, cli: CLIOutput) -> None:
    """
    Ensure the site is built before checking links.

    Checks if output directory exists and contains recent files.
    If not, automatically builds the site.

    Args:
        site: Site instance
        cli: CLI output helper
    """
    from bengal.orchestration.build import BuildOrchestrator

    output_dir = site.output_dir
    needs_build = False

    if not output_dir.exists():
        cli.warning(f"Output directory '{output_dir}' does not exist")
        needs_build = True
    else:
        # Check if output directory has any HTML files
        html_files = list(output_dir.rglob("*.html"))
        if not html_files:
            cli.warning("Output directory is empty")
            needs_build = True
        else:
            cli.info(f"Found {len(html_files)} HTML files in output directory")

    if needs_build:
        cli.info("Building site before checking links...")

        # Purge cache for clean build (link checking requires fresh output)
        from bengal.cache import clear_build_cache

        if clear_build_cache(site.root_path):
            cli.info("Purged build cache for clean build")

        orchestrator = BuildOrchestrator(site)
        orchestrator.build()
        cli.success("Site built successfully")


def _build_config(
    site_config: dict,
    max_concurrency: int | None,
    per_host_limit: int | None,
    timeout: float | None,
    retries: int | None,
    retry_backoff: float | None,
    exclude: tuple[str, ...],
    exclude_domain: tuple[str, ...],
    ignore_status: tuple[str, ...],
) -> dict:
    """Build linkcheck config from CLI flags and site config."""
    # Start with site config
    config = site_config.get("health", {}).get("linkcheck", {})

    # Override with CLI flags (if provided)
    if max_concurrency is not None:
        config["max_concurrency"] = max_concurrency
    if per_host_limit is not None:
        config["per_host_limit"] = per_host_limit
    if timeout is not None:
        config["timeout"] = timeout
    if retries is not None:
        config["retries"] = retries
    if retry_backoff is not None:
        config["retry_backoff"] = retry_backoff

    # Merge exclude patterns (CLI + config)
    all_exclude = list(exclude) + config.get("exclude", [])
    if all_exclude:
        config["exclude"] = all_exclude

    # Merge exclude domains (CLI + config)
    all_exclude_domain = list(exclude_domain) + config.get("exclude_domain", [])
    if all_exclude_domain:
        config["exclude_domain"] = all_exclude_domain

    # Merge ignore status (CLI + config)
    all_ignore_status = list(ignore_status) + config.get("ignore_status", [])
    if all_ignore_status:
        config["ignore_status"] = all_ignore_status

    return config


# Compatibility export
linkcheck_command = linkcheck
