"""
Debug and diagnostic commands for Bengal.

Commands:
    bengal debug incremental - Debug incremental build issues
    bengal debug delta - Compare builds and explain changes
    bengal debug deps - Visualize build dependencies
    bengal debug migrate - Preview content migrations
    bengal debug sandbox - Test shortcodes/directives in isolation
    bengal debug config-inspect - Advanced configuration inspection
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
from bengal.errors.traceback import TracebackStyle


@click.group("debug", cls=BengalGroup)
def debug_cli() -> None:
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
    cache = BuildCache.load(site.paths.build_cache)

    cli.info(f"Loaded cache with {len(cache.file_fingerprints)} tracked files")

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

    cache = BuildCache.load(site.paths.build_cache)

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

    cache = BuildCache.load(site.paths.build_cache)

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
    _redirect_format: str | None,  # TODO: implement redirect generation
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


@debug_cli.command("sandbox")
@handle_cli_errors(show_art=False)
@click.argument("content", required=False)
@click.option(
    "--file",
    "file_path",
    type=click.Path(exists=True),
    help="Read content from file",
)
@click.option(
    "--validate-only",
    is_flag=True,
    help="Only validate syntax, don't render",
)
@click.option(
    "--list-directives",
    is_flag=True,
    help="List all available directives",
)
@click.option(
    "--help-directive",
    type=str,
    help="Get detailed help for a directive",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["console", "html", "json"]),
    default="console",
    help="Output format",
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    hidden=True,
    help="Traceback verbosity",
)
def sandbox(
    content: str | None,
    file_path: str | None,
    validate_only: bool,
    list_directives: bool,
    help_directive: str | None,
    output_format: str,
    traceback: str | None,
) -> None:
    """
    Test shortcodes/directives in isolation.

    Renders directives without building the entire site, useful for
    testing and debugging directive syntax before adding to content.

    Examples:
        bengal debug sandbox '```{note}\\nThis is a note.\\n```'
        bengal debug sandbox --file test-directive.md
        bengal debug sandbox --list-directives
        bengal debug sandbox --help-directive tabs
        bengal debug sandbox --validate-only '```{note}\\nTest\\n```'
    """
    from bengal.debug import ShortcodeSandbox

    cli = get_cli_output()
    configure_traceback(debug=False, traceback=traceback)

    cli.header("🧪 Shortcode Sandbox")

    # Create sandbox (no site needed for basic testing)
    sandbox_tool = ShortcodeSandbox()

    if list_directives:
        directives = sandbox_tool.list_directives()
        cli.blank()
        cli.info(f"Available directives ({len(directives)} types):")
        cli.blank()
        for directive in directives:
            names = ", ".join(directive["names"])
            cli.console.print(f"  {names}")
            cli.console.print(f"    {directive['description']}")
        return

    if help_directive:
        help_text = sandbox_tool.get_directive_help(help_directive)
        cli.blank()
        if help_text:
            cli.console.print(help_text)
        else:
            cli.warning(f"Unknown directive: {help_directive}")
            cli.info("Use --list-directives to see available directives")
        return

    # Get content
    if file_path:
        content = Path(file_path).read_text()
    elif not content:
        cli.warning("No content provided")
        cli.info("Usage: bengal debug sandbox '<content>' or --file <path>")
        cli.info("       bengal debug sandbox --list-directives")
        return

    # Handle escaped newlines from CLI
    content = content.replace("\\n", "\n")

    if validate_only:
        validation = sandbox_tool.validate(content)
        cli.blank()
        if validation.valid:
            cli.success("✅ Valid syntax")
            if validation.directive_name:
                cli.info(f"   Directive: {validation.directive_name}")
        else:
            cli.error("❌ Invalid syntax")
            for error in validation.errors:
                cli.console.print(f"   {error}")
            for suggestion in validation.suggestions:
                cli.info(f"   💡 {suggestion}")
        return

    # Render
    result = sandbox_tool.render(content)
    cli.blank()

    if result.success:
        cli.success("✅ Rendered successfully")
        cli.info(f"   Directive: {result.directive_name or 'none'}")
        cli.info(f"   Time: {result.parse_time_ms + result.render_time_ms:.2f}ms")
        cli.blank()

        if output_format == "html":
            cli.console.print(result.html)
        elif output_format == "json":
            data = {
                "success": True,
                "directive": result.directive_name,
                "html": result.html,
                "parse_time_ms": result.parse_time_ms,
                "render_time_ms": result.render_time_ms,
            }
            cli.console.print(json.dumps(data, indent=2))
        else:
            cli.info("Output HTML:")
            cli.console.print(f"[dim]{result.html}[/dim]")
    else:
        cli.error("❌ Render failed")
        for error in result.errors:
            cli.console.print(f"   {error}")


@debug_cli.command("config-inspect")
@handle_cli_errors(show_art=False)
@click.option(
    "--compare-to",
    type=str,
    help="Compare to environment or profile (e.g., 'production', 'profile:dev')",
)
@click.option(
    "--explain-key",
    type=str,
    help="Explain how a specific key got its value (e.g., 'site.title')",
)
@click.option(
    "--list-sources",
    is_flag=True,
    help="List available configuration sources",
)
@click.option(
    "--find-issues",
    is_flag=True,
    help="Find potential configuration issues",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["console", "json"]),
    default="console",
    help="Output format",
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    hidden=True,
    help="Traceback verbosity",
)
def config_inspect(
    compare_to: str | None,
    explain_key: str | None,
    list_sources: bool,
    find_issues: bool,
    output_format: str,
    traceback: str | None,
) -> None:
    """
    Advanced configuration inspection and comparison.

    Goes beyond 'bengal config diff' with origin tracking, impact analysis,
    and key-level value resolution explanations.

    Examples:
        bengal debug config-inspect --list-sources
        bengal debug config-inspect --compare-to production
        bengal debug config-inspect --explain-key site.baseurl
        bengal debug config-inspect --find-issues
    """
    from bengal.debug import ConfigInspector

    cli = get_cli_output()
    configure_traceback(debug=False, traceback=traceback)

    cli.header("🔬 Config Inspector")

    # Load site
    cli.info("Loading site...")
    site = load_site_from_cli(source=".", config=None, environment=None, profile=None, cli=cli)
    configure_traceback(debug=False, traceback=traceback, site=site)

    # Create inspector
    inspector = ConfigInspector(site=site)

    if list_sources:
        sources = inspector._list_available_sources()
        cli.blank()
        cli.info("Available configuration sources:")
        for source in sources:
            cli.console.print(f"   • {source}")
        return

    if explain_key:
        explanation = inspector.explain_key(explain_key)
        cli.blank()
        if explanation:
            cli.console.print(explanation.format())
        else:
            cli.warning(f"Key not found: {explain_key}")
        return

    if compare_to:
        from bengal.config.environment import detect_environment

        current_env = detect_environment()
        comparison = inspector.compare(current_env, compare_to)

        cli.blank()
        if output_format == "json":
            data = {
                "source1": comparison.source1,
                "source2": comparison.source2,
                "diffs": [
                    {
                        "path": d.path,
                        "type": d.type,
                        "old_value": d.old_value,
                        "new_value": d.new_value,
                        "old_origin": d.old_origin,
                        "new_origin": d.new_origin,
                        "impact": d.impact,
                    }
                    for d in comparison.diffs
                ],
            }
            cli.console.print(json.dumps(data, indent=2))
        else:
            cli.console.print(comparison.format_detailed())
        return

    if find_issues:
        findings = inspector.find_issues()
        cli.blank()
        if findings:
            cli.info(f"Found {len(findings)} potential issue(s):")
            for finding in findings:
                icon = (
                    "❌"
                    if finding.severity.value == "error"
                    else "⚠️"
                    if finding.severity.value == "warning"
                    else "ℹ️"
                )
                cli.console.print(f"   {icon} {finding.title}")
                if finding.suggestion:
                    cli.console.print(f"      💡 {finding.suggestion}")
        else:
            cli.success("✅ No issues found")
        return

    # Default: show usage
    cli.blank()
    cli.info("Usage:")
    cli.info("   --list-sources    List available config sources")
    cli.info("   --compare-to      Compare current config to another source")
    cli.info("   --explain-key     Explain how a key got its value")
    cli.info("   --find-issues     Find potential configuration issues")


# Compatibility export
debug_command = debug_cli
