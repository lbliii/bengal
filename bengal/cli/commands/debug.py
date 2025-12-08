"""
Debug and diagnostic commands for Bengal.

Commands:
    bengal debug incremental - Debug incremental build issues
    bengal debug delta - Compare builds and explain changes
    bengal debug deps - Visualize build dependencies
    bengal debug migrate - Preview content migrations
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import (
    configure_traceback,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.utils.traceback_config import TracebackStyle


@click.group("debug", cls=BengalGroup)
def debug_cli():
    """Debug and diagnostic commands for builds."""
    pass


@debug_cli.command("incremental")
@handle_cli_errors(show_art=False)
@click.option(
    "--explain",
    "explain_page",
    type=str,
    help="Explain why a specific page was rebuilt",
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
    hidden=True,
    help="Traceback verbosity",
)
def incremental(
    explain_page: str | None,
    output_format: str,
    output_file: str | None,
    traceback: str | None,
) -> None:
    """
    Debug incremental build issues.

    Analyzes cache state, explains why pages rebuild, identifies phantom
    rebuilds, and validates cache consistency.

    Examples:
        bengal debug incremental
        bengal debug incremental --explain content/posts/my-post.md
        bengal debug incremental --format json --output debug-report.json
    """
    from bengal.cache.build_cache import BuildCache
    from bengal.debug import IncrementalBuildDebugger

    cli = get_cli_output()
    configure_traceback(debug=False, traceback=traceback)

    cli.header("🔍 Incremental Build Debugger")

    # Load site
    cli.info("Loading site...")
    site = load_site_from_cli(source=".", config=None, environment=None, profile=None, cli=cli)
    configure_traceback(debug=False, traceback=traceback, site=site)

    # Load cache
    cache_path = site.root_path / ".bengal" / "cache.json"
    cache = BuildCache.load(cache_path)

    cli.info(f"Loaded cache with {len(cache.file_hashes)} tracked files")

    # Create debugger
    debugger = IncrementalBuildDebugger(site=site, cache=cache, root_path=site.root_path)

    if explain_page:
        # Explain specific page
        explanation = debugger.explain_rebuild(explain_page)
        cli.blank()

        if output_format == "json":
            data = {
                "page": explanation.page_path,
                "reasons": [r.value for r in explanation.reasons],
                "changed_dependencies": explanation.changed_dependencies,
                "cache_status": explanation.cache_status,
                "dependency_chain": explanation.dependency_chain,
                "suggestions": explanation.suggestions,
            }
            if output_file:
                Path(output_file).write_text(json.dumps(data, indent=2))
                cli.success(f"Saved to {output_file}")
            else:
                cli.console.print(json.dumps(data, indent=2))
        else:
            cli.console.print(explanation.format_detailed())
    else:
        # Full analysis
        report = debugger.run()

        if output_format == "json":
            data = report.to_dict()
            if output_file:
                Path(output_file).write_text(json.dumps(data, indent=2))
                cli.success(f"Saved report to {output_file}")
            else:
                cli.console.print(json.dumps(data, indent=2))
        else:
            cli.blank()
            cli.console.print(report.format_summary())

            if report.findings:
                cli.blank()
                cli.info("Findings:")
                for finding in report.findings:
                    cli.console.print(f"   {finding.format_short()}")

            if report.recommendations:
                cli.blank()
                cli.info("Recommendations:")
                for rec in report.recommendations:
                    cli.console.print(f"   💡 {rec}")


@debug_cli.command("delta")
@handle_cli_errors(show_art=False)
@click.option(
    "--baseline",
    is_flag=True,
    help="Compare against baseline (first) build",
)
@click.option(
    "--save-baseline",
    is_flag=True,
    help="Save current state as new baseline",
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
    hidden=True,
    help="Traceback verbosity",
)
def delta(
    baseline: bool,
    save_baseline: bool,
    output_format: str,
    output_file: str | None,
    traceback: str | None,
) -> None:
    """
    Compare builds and explain changes.

    Shows what changed between builds including added/removed pages,
    timing changes, and configuration differences.

    Examples:
        bengal debug delta
        bengal debug delta --baseline
        bengal debug delta --save-baseline
        bengal debug delta --format json --output delta-report.json
    """
    from bengal.cache.build_cache import BuildCache
    from bengal.debug import BuildDeltaAnalyzer

    cli = get_cli_output()
    configure_traceback(debug=False, traceback=traceback)

    cli.header("📊 Build Delta Analyzer")

    # Load site and cache
    cli.info("Loading site...")
    site = load_site_from_cli(source=".", config=None, environment=None, profile=None, cli=cli)
    configure_traceback(debug=False, traceback=traceback, site=site)

    cache_path = site.root_path / ".bengal" / "cache.json"
    cache = BuildCache.load(cache_path)

    # Create analyzer
    analyzer = BuildDeltaAnalyzer(site=site, cache=cache, root_path=site.root_path)

    if save_baseline:
        analyzer.save_baseline()
        cli.success("Saved current state as baseline")
        return

    # Get comparison
    if baseline:
        delta_result = analyzer.compare_to_baseline()
        if not delta_result:
            cli.warning("No baseline found. Run with --save-baseline first.")
            return
    else:
        delta_result = analyzer.compare_to_previous()

    if delta_result:
        cli.blank()
        if output_format == "json":
            data = {
                "before": delta_result.before.to_dict(),
                "after": delta_result.after.to_dict(),
                "added_pages": list(delta_result.added_pages),
                "removed_pages": list(delta_result.removed_pages),
                "time_change_ms": delta_result.time_change_ms,
                "time_change_pct": delta_result.time_change_pct,
                "config_changed": delta_result.config_changed,
            }
            if output_file:
                Path(output_file).write_text(json.dumps(data, indent=2))
                cli.success(f"Saved to {output_file}")
            else:
                cli.console.print(json.dumps(data, indent=2))
        else:
            cli.console.print(delta_result.format_detailed())
    else:
        # Run full analysis
        report = analyzer.run()

        if output_format == "json":
            data = report.to_dict()
            if output_file:
                Path(output_file).write_text(json.dumps(data, indent=2))
                cli.success(f"Saved report to {output_file}")
            else:
                cli.console.print(json.dumps(data, indent=2))
        else:
            cli.blank()
            cli.console.print(report.format_summary())


@debug_cli.command("deps")
@handle_cli_errors(show_art=False)
@click.argument("page_path", required=False)
@click.option(
    "--blast-radius",
    "blast_file",
    type=str,
    help="Show what rebuilds if this file changes",
)
@click.option(
    "--export",
    "export_format",
    type=click.Choice(["mermaid", "dot"]),
    help="Export format for graph",
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(),
    help="Output file for export",
)
@click.option(
    "--max-depth",
    type=int,
    default=3,
    help="Maximum depth for visualization (default: 3)",
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    hidden=True,
    help="Traceback verbosity",
)
def deps(
    page_path: str | None,
    blast_file: str | None,
    export_format: str | None,
    output_file: str | None,
    max_depth: int,
    traceback: str | None,
) -> None:
    """
    Visualize build dependencies.

    Shows what a page depends on (templates, partials, data files) and
    what would rebuild if a file changed.

    Examples:
        bengal debug deps content/posts/my-post.md
        bengal debug deps --blast-radius themes/default/layouts/base.html
        bengal debug deps --export mermaid --output deps.md
    """
    from bengal.cache.build_cache import BuildCache
    from bengal.debug import DependencyVisualizer

    cli = get_cli_output()
    configure_traceback(debug=False, traceback=traceback)

    cli.header("🕸️ Dependency Visualizer")

    # Load cache
    cli.info("Loading build cache...")
    site = load_site_from_cli(source=".", config=None, environment=None, profile=None, cli=cli)
    configure_traceback(debug=False, traceback=traceback, site=site)

    cache_path = site.root_path / ".bengal" / "cache.json"
    cache = BuildCache.load(cache_path)

    cli.info(f"Loaded {len(cache.dependencies)} pages with dependencies")

    # Create visualizer
    visualizer = DependencyVisualizer(site=site, cache=cache, root_path=site.root_path)

    if blast_file:
        # Show blast radius
        affected = visualizer.get_blast_radius(blast_file)
        cli.blank()
        cli.info(f"If {blast_file} changes, {len(affected)} page(s) would rebuild:")
        for page in sorted(affected)[:20]:
            cli.console.print(f"   • {page}")
        if len(affected) > 20:
            cli.console.print(f"   ... and {len(affected) - 20} more")
        return

    if export_format:
        # Export graph
        output_path = Path(output_file) if output_file else None

        if export_format == "mermaid":
            result = visualizer.export_mermaid(output_path, root=page_path)
        else:
            result = visualizer.export_dot(output_path, root=page_path)

        if output_file:
            cli.success(f"Exported to {output_file}")
        else:
            cli.blank()
            cli.console.print(result)
        return

    if page_path:
        # Show dependencies for specific page
        tree = visualizer.visualize_page(page_path, max_depth)
        cli.blank()
        cli.console.print(tree)
    else:
        # Run analysis
        report = visualizer.run()
        cli.blank()
        cli.console.print(report.format_summary())

        if report.findings:
            cli.blank()
            cli.info("Findings:")
            for finding in report.findings:
                cli.console.print(f"   {finding.format_short()}")


@debug_cli.command("migrate")
@handle_cli_errors(show_art=False)
@click.option(
    "--move",
    nargs=2,
    type=str,
    help="Preview moving SOURCE to DESTINATION",
)
@click.option(
    "--execute",
    is_flag=True,
    help="Execute the move (requires --move)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without making changes",
)
@click.option(
    "--generate-redirects",
    "redirect_format",
    type=click.Choice(["netlify", "nginx", "apache"]),
    help="Generate redirect rules for moves",
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    hidden=True,
    help="Traceback verbosity",
)
def migrate(
    move: tuple[str, str] | None,
    execute: bool,
    dry_run: bool,
    redirect_format: str | None,
    traceback: str | None,
) -> None:
    """
    Preview and execute content migrations.

    Safely move, split, or merge content while maintaining link integrity
    and generating redirect rules.

    Examples:
        bengal debug migrate
        bengal debug migrate --move docs/old.md guides/new.md
        bengal debug migrate --move docs/old.md guides/new.md --execute
        bengal debug migrate --move docs/old.md guides/new.md --dry-run
    """
    from bengal.debug import ContentMigrator

    cli = get_cli_output()
    configure_traceback(debug=False, traceback=traceback)

    cli.header("📦 Content Migrator")

    # Load site
    cli.info("Loading site...")
    site = load_site_from_cli(source=".", config=None, environment=None, profile=None, cli=cli)
    configure_traceback(debug=False, traceback=traceback, site=site)

    site.discover_content()

    cli.info(f"Found {len(site.pages)} pages")

    # Create migrator
    migrator = ContentMigrator(site=site, root_path=site.root_path)

    if move:
        source, destination = move
        preview = migrator.preview_move(source, destination)

        cli.blank()
        cli.console.print(preview.format_summary())

        if execute and preview.can_proceed:
            if not dry_run:
                actions = migrator.execute_move(preview, dry_run=dry_run)
            else:
                actions = migrator.execute_move(preview, dry_run=True)

            cli.blank()
            cli.info("Actions:" if dry_run else "Executed:")
            for action in actions:
                cli.console.print(f"   {'(dry run) ' if dry_run else ''}✓ {action}")
        elif execute and not preview.can_proceed:
            cli.error("Cannot proceed due to warnings")
    else:
        # Run analysis
        report = migrator.run()
        cli.blank()
        cli.console.print(report.format_summary())

        if report.findings:
            cli.blank()
            cli.info("Structure Issues:")
            for finding in report.findings:
                cli.console.print(f"   {finding.format_short()}")


# Compatibility export
debug_command = debug_cli

