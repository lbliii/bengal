"""Debug group — debug builds and dependencies."""

from __future__ import annotations

import json
from typing import Annotated

from milo import Description

from bengal.cli.helpers.debug_reports import render_debug_report


def debug_incremental(
    source: Annotated[str, Description("Source directory path")] = "",
    explain_page: Annotated[str, Description("Explain why a specific page was rebuilt")] = "",
    output_format: Annotated[str, Description("Output format: console or json")] = "console",
    output_file: Annotated[str, Description("Output file (for JSON format)")] = "",
) -> dict:
    """Debug incremental build issues — cache state, rebuild reasons, phantom rebuilds."""
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.cli.utils import load_site_from_cli
    from bengal.debug import IncrementalBuildDebugger
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()

    cli.header("Incremental Build Debugger")

    cli.info("Loading site...")
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    cache = BuildCache.load(site.config_service.paths.build_cache)
    cli.info(f"Loaded cache with {len(cache.file_fingerprints)} tracked files")

    debugger = IncrementalBuildDebugger(site=site, cache=cache, root_path=site.root_path)

    if explain_page:
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
                from bengal.utils.io.atomic_write import atomic_write_text

                atomic_write_text(Path(output_file), json.dumps(data, indent=2))
                cli.success(f"Saved to {output_file}")
            else:
                cli.render_write("json_output.kida", data=json.dumps(data, indent=2))
        else:
            cli.info(explanation.format_detailed())
        return {"page": explanation.page_path, "reasons": [r.value for r in explanation.reasons]}
    report = debugger.run()

    if output_format == "json":
        data = report.to_dict()
        if output_file:
            from bengal.utils.io.atomic_write import atomic_write_text

            atomic_write_text(Path(output_file), json.dumps(data, indent=2))
            cli.success(f"Saved report to {output_file}")
        else:
            cli.render_write("json_output.kida", data=json.dumps(data, indent=2))
    else:
        cli.blank()
        render_debug_report(cli, report)
    return {"findings": len(report.findings), "recommendations": len(report.recommendations)}


def debug_delta(
    source: Annotated[str, Description("Source directory path")] = "",
    baseline: Annotated[bool, Description("Compare against baseline (first) build")] = False,
    save_baseline: Annotated[bool, Description("Save current state as new baseline")] = False,
    output_format: Annotated[str, Description("Output format: console or json")] = "console",
    output_file: Annotated[str, Description("Output file (for JSON format)")] = "",
) -> dict:
    """Compare builds and identify changes — added/removed pages, timing, config diffs."""
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.cli.utils import load_site_from_cli
    from bengal.debug import BuildDeltaAnalyzer
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()

    cli.header("Build Delta Analyzer")

    cli.info("Loading site...")
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    cache = BuildCache.load(site.config_service.paths.build_cache)

    analyzer = BuildDeltaAnalyzer(site=site, cache=cache, root_path=site.root_path)

    if save_baseline:
        analyzer.save_baseline()
        cli.success("Saved current state as baseline")
        return {"saved_baseline": True}

    if baseline:
        delta_result = analyzer.compare_to_baseline()
        if not delta_result:
            cli.warning("No baseline found. Run with --save-baseline first.")
            return {"status": "skipped", "message": "No baseline found", "findings": []}
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
                from bengal.utils.io.atomic_write import atomic_write_text

                atomic_write_text(Path(output_file), json.dumps(data, indent=2))
                cli.success(f"Saved to {output_file}")
            else:
                cli.render_write("json_output.kida", data=json.dumps(data, indent=2))
        else:
            cli.info(delta_result.format_detailed())
        return {
            "added": len(delta_result.added_pages),
            "removed": len(delta_result.removed_pages),
            "time_change_ms": delta_result.time_change_ms,
            "config_changed": delta_result.config_changed,
        }
    report = analyzer.run()
    if output_format == "json":
        data = report.to_dict()
        if output_file:
            from bengal.utils.io.atomic_write import atomic_write_text

            atomic_write_text(Path(output_file), json.dumps(data, indent=2))
            cli.success(f"Saved report to {output_file}")
        else:
            cli.render_write("json_output.kida", data=json.dumps(data, indent=2))
    else:
        cli.blank()
        render_debug_report(cli, report)
    return {"findings": len(getattr(report, "findings", []))}


def debug_deps(
    page_path: Annotated[str, Description("Page path to visualize dependencies for")] = "",
    source: Annotated[str, Description("Source directory path")] = "",
    blast_file: Annotated[str, Description("Show what rebuilds if this file changes")] = "",
    export_format: Annotated[str, Description("Export format: mermaid or dot")] = "",
    output_file: Annotated[str, Description("Output file for export")] = "",
    max_depth: Annotated[int, Description("Maximum depth for visualization")] = 3,
) -> dict:
    """Visualize dependency graph — what a page depends on, blast radius analysis."""
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.cli.utils import load_site_from_cli
    from bengal.debug import DependencyVisualizer
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()

    cli.header("Dependency Visualizer")

    cli.info("Loading build cache...")
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    cache = BuildCache.load(site.config_service.paths.build_cache)
    cli.info(f"Loaded {len(cache.dependencies)} pages with dependencies")

    visualizer = DependencyVisualizer(site=site, cache=cache, root_path=site.root_path)

    if blast_file:
        affected = visualizer.get_blast_radius(blast_file)
        items = [{"name": page, "description": ""} for page in sorted(affected)[:20]]
        cli.render_write(
            "item_list.kida",
            title=f"Blast Radius: {blast_file} ({len(affected)} pages)",
            items=items,
        )
        if len(affected) > 20:
            cli.info(f"  ... and {len(affected) - 20} more")
        return {"file": blast_file, "affected_count": len(affected), "affected": sorted(affected)}

    if export_format:
        output_path = Path(output_file) if output_file else None
        if export_format == "mermaid":
            result = visualizer.export_mermaid(output_path, root=page_path or None)
        else:
            result = visualizer.export_dot(output_path, root=page_path or None)

        if output_file:
            cli.success(f"Exported to {output_file}")
        else:
            cli.blank()
            cli.info(result)
        return {"format": export_format, "output_file": output_file or None}

    if page_path:
        tree = visualizer.visualize_page(page_path, max_depth)
        cli.blank()
        cli.info(tree)
        return {"page": page_path, "max_depth": max_depth}
    report = visualizer.run()
    cli.blank()
    render_debug_report(cli, report)
    return {"findings": len(report.findings)}


def debug_migrate(
    source: Annotated[str, Description("Source directory path")] = "",
    move_from: Annotated[str, Description("Source path for content move")] = "",
    move_to: Annotated[str, Description("Destination path for content move")] = "",
    execute: Annotated[
        bool, Description("Execute the move (requires move_from and move_to)")
    ] = False,
    dry_run: Annotated[bool, Description("Show what would be done without making changes")] = False,
) -> dict:
    """Preview or execute content migrations — move content while maintaining link integrity."""
    from bengal.cli.utils import load_site_from_cli
    from bengal.debug import ContentMigrator
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()

    cli.header("Content Migrator")

    cli.info("Loading site...")
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    site.discover_content()
    cli.info(f"Found {len(site.pages)} pages")

    migrator = ContentMigrator(site=site, root_path=site.root_path)

    if move_from and move_to:
        preview = migrator.preview_move(move_from, move_to)
        cli.blank()
        cli.info(preview.format_summary())

        if execute and preview.can_proceed:
            actions = migrator.execute_move(preview, dry_run=dry_run)
            cli.blank()
            cli.info("Actions:" if dry_run else "Executed:")
            for action in actions:
                prefix = "(dry run) " if dry_run else ""
                cli.info(f"  {prefix}{action}")
        elif execute and not preview.can_proceed:
            cli.error("Cannot proceed due to warnings")
            cli.tip(
                "Resolve the warnings shown above, or re-run without --execute to preview only."
            )

        return {
            "move_from": move_from,
            "move_to": move_to,
            "can_proceed": preview.can_proceed,
            "dry_run": dry_run,
        }

    if move_from or move_to:
        cli.error("Both --move-from and --move-to are required for a move operation")
        cli.tip(
            "Pass both flags together, e.g. `bengal debug structure --move-from old/ --move-to new/`."
        )
        raise SystemExit(1)

    report = migrator.run()
    cli.blank()
    render_debug_report(cli, report, title="Structure Issues")

    return {"findings": len(report.findings)}


def debug_sandbox(
    content: Annotated[str, Description("Directive markdown content")] = "",
    file_path: Annotated[str, Description("Read content from file")] = "",
    validate_only: Annotated[bool, Description("Only validate syntax, don't render")] = False,
    list_directives: Annotated[bool, Description("List all available directives")] = False,
    help_directive: Annotated[str, Description("Get detailed help for a directive")] = "",
    output_format: Annotated[str, Description("Output format: console, html, or json")] = "console",
) -> dict:
    """Test directives in isolation without building the entire site."""
    from pathlib import Path

    from bengal.debug import ShortcodeSandbox
    from bengal.output import get_cli_output

    cli = get_cli_output()
    cli.header("Shortcode Sandbox")

    sandbox = ShortcodeSandbox()

    if list_directives:
        directives = sandbox.list_directives()
        cli.render_write(
            "item_list.kida",
            title=f"Available Directives ({len(directives)} types)",
            items=[
                {
                    "name": ", ".join(d["names"]),
                    "description": d["description"].split("\n")[0].strip()
                    if d["description"]
                    else "",
                }
                for d in directives
            ],
        )
        return {"directives": directives, "count": len(directives)}

    if help_directive:
        help_text = sandbox.get_directive_help(help_directive)
        cli.blank()
        if help_text:
            cli.info(help_text)
        else:
            cli.warning(f"Unknown directive: {help_directive}")
            cli.info("Use --list-directives to see available directives")
        return {"directive": help_directive, "found": help_text is not None}

    if file_path:
        content = Path(file_path).read_text(encoding="utf-8")
    elif content:
        content = content.replace("\\n", "\n")
    else:
        cli.warning("No content provided")
        cli.info("Usage: bengal debug sandbox '<content>' or --file-path <path>")
        cli.info("       bengal debug sandbox --list-directives")
        return {"status": "skipped", "message": "No content provided"}

    if validate_only:
        validation = sandbox.validate(content)
        cli.blank()
        if output_format == "json":
            cli.render_write(
                "json_output.kida",
                data=json.dumps(
                    {
                        "valid": validation.valid,
                        "directive": validation.directive_name,
                        "errors": validation.errors,
                        "suggestions": validation.suggestions,
                    },
                    indent=2,
                ),
            )
        elif validation.valid:
            cli.success(f"Valid syntax: {validation.directive_name or 'no directive'}")
        else:
            issues = [{"level": "error", "message": err} for err in validation.errors]
            issues.extend({"level": "info", "message": sug} for sug in validation.suggestions)
            cli.render_write(
                "validation_report.kida",
                issues=issues,
                summary={"errors": len(validation.errors), "warnings": 0, "passed": 0},
            )
        return {
            "valid": validation.valid,
            "directive": validation.directive_name,
            "errors": validation.errors,
        }

    result = sandbox.render(content)
    cli.blank()

    if output_format == "json":
        cli.render_write(
            "json_output.kida",
            data=json.dumps(
                {
                    "success": result.success,
                    "directive": result.directive_name,
                    "html": result.html,
                    "parse_time_ms": result.parse_time_ms,
                    "render_time_ms": result.render_time_ms,
                    "errors": result.errors,
                },
                indent=2,
            ),
        )
    elif output_format == "html":
        cli.info(result.html)
    elif result.success:
        cli.render_write(
            "kv_detail.kida",
            title=f"Rendered: {result.directive_name or 'none'}",
            items=[
                {"label": "Parse", "value": f"{result.parse_time_ms:.2f}ms"},
                {"label": "Render", "value": f"{result.render_time_ms:.2f}ms"},
            ],
        )
        cli.blank()
        cli.info(result.html)
    else:
        cli.render_write(
            "validation_report.kida",
            issues=[{"level": "error", "message": err} for err in result.errors],
            summary={"errors": len(result.errors), "warnings": 0, "passed": 0},
        )

    return {
        "success": result.success,
        "directive": result.directive_name,
        "parse_time_ms": result.parse_time_ms,
        "render_time_ms": result.render_time_ms,
    }
