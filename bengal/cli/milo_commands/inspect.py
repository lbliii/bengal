"""Inspect group — analyze and inspect your site."""

from __future__ import annotations

from typing import Annotated, Any

from milo import Description


def _render_debug_report(cli, report, *, title: str | None = None) -> None:
    """Render a DebugReport through Kida templates."""
    report_title = title or f"{getattr(report, 'tool_name', 'Debug')} Report"
    items = [
        {"label": "Summary", "value": getattr(report, "summary", "") or "No summary"},
        {"label": "Findings", "value": str(len(getattr(report, "findings", [])))},
    ]
    if getattr(report, "error_count", 0):
        items.append({"label": "Errors", "value": str(report.error_count)})
    if getattr(report, "warning_count", 0):
        items.append({"label": "Warnings", "value": str(report.warning_count)})
    if getattr(report, "execution_time_ms", 0):
        items.append({"label": "Execution time", "value": f"{report.execution_time_ms:.1f}ms"})
    for key, value in getattr(report, "statistics", {}).items():
        items.append({"label": str(key).replace("_", " ").title(), "value": str(value)})

    cli.render_write("kv_detail.kida", title=report_title, items=items)

    findings = getattr(report, "findings", [])
    if findings:
        cli.render_write(
            "item_list.kida",
            title="Findings",
            items=[{"name": finding.format_short(), "description": ""} for finding in findings],
        )


def inspect_page(
    page_path: Annotated[
        str, Description("Page path (relative to content dir, full, or partial match)")
    ],
    source: Annotated[str, Description("Source directory path")] = "",
    verbose: Annotated[
        bool, Description("Show additional details (timing, template variables)")
    ] = False,
    diagnose: Annotated[
        bool, Description("Check for issues (broken links, missing assets)")
    ] = False,
    output_format: Annotated[str, Description("Output format: console or json")] = "console",
) -> dict:
    """Explain how a page is built — source, template chain, dependencies, cache status."""
    import json
    from dataclasses import asdict

    from bengal.cli.utils import get_cli_output, load_site_from_cli
    from bengal.utils.observability.profile import BuildProfile

    source = source or "."
    cli = get_cli_output()
    cli.header("Page Explanation")
    cli.info("Loading site...")

    site = load_site_from_cli(
        source=source,
        config=None,
        environment=None,
        profile=BuildProfile.WRITER,
        cli=cli,
    )
    site.discover_content()
    cli.success(f"Loaded {len(site.pages)} pages")

    from bengal.cache import BuildCache

    cache_path = site.config_service.paths.build_cache
    cache = (
        BuildCache.load(cache_path)
        if cache_path.exists() or cache_path.with_suffix(".json.zst").exists()
        else None
    )

    template_engine = None
    try:
        from bengal.rendering.engines import create_engine

        template_engine = create_engine(site)
    except Exception as e:
        cli.warning(f"Could not initialize template engine: {e}")

    from bengal.debug import PageExplainer

    explainer = PageExplainer(site, cache=cache, template_engine=template_engine)

    try:
        explanation = explainer.explain(page_path=page_path, verbose=verbose, diagnose=diagnose)
    except ValueError as e:
        cli.error(str(e))
        matches = _find_similar_pages(page_path, site.pages)
        if matches:
            cli.render_write(
                "item_list.kida",
                title="Did you mean?",
                items=[{"name": match, "description": ""} for match in matches[:5]],
            )
        raise SystemExit(1) from e

    if output_format == "json":
        data = asdict(explanation)
        data = _convert_paths_to_strings(data)
        cli.render_write("json_output.kida", data=json.dumps(data, indent=2, default=str))
    else:
        from bengal.debug import ExplanationReporter

        reporter = ExplanationReporter(cli=cli)
        reporter.print(explanation, verbose=verbose)

        cli.blank()
        if explanation.issues:
            error_count = sum(1 for i in explanation.issues if i.severity == "error")
            warning_count = sum(1 for i in explanation.issues if i.severity == "warning")
            if error_count:
                cli.error(f"Found {error_count} error(s) and {warning_count} warning(s)")
                cli.tip("See the issue list above — each entry points to the file, line, and fix.")
            elif warning_count:
                cli.warning(f"Found {warning_count} warning(s)")
        else:
            cli.success("Page explanation complete")

    return {"page": page_path, "issues": len(explanation.issues)}


def inspect_links(
    source: Annotated[str, Description("Source directory path")] = "",
    external_only: Annotated[bool, Description("Only check external links")] = False,
    internal_only: Annotated[bool, Description("Only check internal links")] = False,
    exclude: Annotated[
        str, Description("URL patterns to exclude, comma-separated (regex supported)")
    ] = "",
    output_format: Annotated[str, Description("Output format: console or json")] = "console",
    output_file: Annotated[str, Description("Output file (for JSON format)")] = "",
    max_concurrency: Annotated[int, Description("Maximum concurrent HTTP requests")] = 0,
    per_host_limit: Annotated[int, Description("Maximum concurrent requests per host")] = 0,
    timeout: Annotated[float, Description("Request timeout in seconds")] = 0.0,
    retries: Annotated[int, Description("Number of retry attempts")] = 0,
    retry_backoff: Annotated[float, Description("Base backoff time for exponential backoff")] = 0.0,
    exclude_domain: Annotated[str, Description("Domains to exclude, comma-separated")] = "",
    ignore_status: Annotated[
        str, Description("Status codes/ranges to ignore, comma-separated")
    ] = "",
) -> dict:
    """Check internal and external links in the site."""
    import json
    from pathlib import Path

    from bengal.cli.utils import get_cli_output, load_site_from_cli
    from bengal.health.linkcheck.orchestrator import LinkCheckOrchestrator

    source = source or "."
    cli = get_cli_output()

    cli.header("Link Checker")
    cli.info("Loading site...")

    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    site.discover_content()
    site.discover_assets()
    cli.success(f"Loaded {len(site.pages)} pages")

    check_internal = not external_only
    check_external = not internal_only

    if check_internal:
        _ensure_site_built(site, cli)

    # Parse comma-separated lists
    exclude_list = [e.strip() for e in exclude.split(",") if e.strip()] if exclude else []
    exclude_domain_list = (
        [d.strip() for d in exclude_domain.split(",") if d.strip()] if exclude_domain else []
    )
    ignore_status_list = (
        [s.strip() for s in ignore_status.split(",") if s.strip()] if ignore_status else []
    )

    linkcheck_config = _build_linkcheck_config(
        site.config,
        max_concurrency,
        per_host_limit,
        timeout,
        retries,
        retry_backoff,
        tuple(exclude_list),
        tuple(exclude_domain_list),
        tuple(ignore_status_list),
    )

    try:
        orchestrator = LinkCheckOrchestrator(
            site,
            check_internal=check_internal,
            check_external=check_external,
            config=linkcheck_config,
        )
        results, summary = orchestrator.check_all_links()

        if output_format == "json":
            report = orchestrator.format_json_report(results, summary)
            if output_file:
                Path(output_file).write_text(json.dumps(report, indent=2))
                cli.success(f"JSON report saved to {output_file}")
            else:
                cli.render_write("json_output.kida", data=json.dumps(report, indent=2))
        else:
            cli.render_write(
                "validation_report.kida",
                **orchestrator.format_validation_report(results, summary),
            )

        if not summary.passed:
            raise SystemExit(1)

        return {"passed": summary.passed, "total": getattr(summary, "total", None)}
    except SystemExit:
        raise
    except Exception as e:
        cli.error(f"Link check failed: {e}")
        cli.tip("Re-run with --traceback to see the full error, or narrow scope with --path.")
        raise SystemExit(1) from e


def inspect_graph(
    source: Annotated[str, Description("Source directory path")] = "",
    output_format: Annotated[
        str, Description("Output format: console, json, or mermaid")
    ] = "console",
    output_file: Annotated[str, Description("Output file for export")] = "",
) -> dict:
    """Analyze site structure and link graph."""
    import json
    from pathlib import Path

    from bengal.cli.utils import get_cli_output, load_site_from_cli

    source = source or "."
    cli = get_cli_output()

    cli.header("Site Graph Analysis")
    cli.info("Loading site...")

    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    site.discover_content()

    cli.success(f"Loaded {len(site.pages)} pages")

    from bengal.cache.build_cache import BuildCache
    from bengal.debug import DependencyVisualizer

    cache = BuildCache.load(site.config_service.paths.build_cache)
    visualizer = DependencyVisualizer(site=site, cache=cache, root_path=site.root_path)

    report = visualizer.run()

    if output_format == "json":
        data = report.to_dict()
        if output_file:
            Path(output_file).write_text(json.dumps(data, indent=2))
            cli.success(f"Saved to {output_file}")
        else:
            cli.render_write("json_output.kida", data=json.dumps(data, indent=2))
    elif output_format == "mermaid":
        result = visualizer.export_mermaid(Path(output_file) if output_file else None)
        if output_file:
            cli.success(f"Exported to {output_file}")
        else:
            cli.info(result)
    else:
        cli.blank()
        _render_debug_report(cli, report, title="Dependency Report")

    return {"pages": len(site.pages), "findings": len(report.findings)}


def inspect_perf(
    last: Annotated[int, Description("Show last N builds")] = 10,
    output_format: Annotated[str, Description("Output format: table, json, or summary")] = "table",
    compare: Annotated[bool, Description("Compare last two builds")] = False,
) -> dict:
    """Show build performance metrics."""
    from pathlib import Path

    from bengal.cache.paths import BengalPaths
    from bengal.utils.observability.performance_report import PerformanceReport

    paths = BengalPaths(Path.cwd())
    report = PerformanceReport(metrics_dir=paths.metrics_dir)

    if compare:
        report.compare()
    else:
        report.show(last=last, format=output_format)

    return {"last": last, "compare": compare}


# --- Helpers ---


def _find_similar_pages(query: str, pages) -> list[str]:
    """Find pages with similar paths."""
    query_lower = query.lower()
    matches = []
    for page in pages:
        path_str = str(page.source_path).lower()
        if query_lower in path_str:
            matches.append(str(page.source_path))
            continue
        if (
            page.source_path.stem.lower() in query_lower
            or query_lower in page.source_path.stem.lower()
        ):
            matches.append(str(page.source_path))
    matches.sort(key=lambda x: (len(x), x))
    return matches


def _convert_paths_to_strings(obj: Any) -> Any:
    """Recursively convert Path objects to strings for JSON serialization."""
    from pathlib import Path

    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _convert_paths_to_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_paths_to_strings(item) for item in obj]
    return obj


def _ensure_site_built(site, cli) -> None:
    """Ensure the site is built before checking links."""
    output_dir = site.output_dir
    needs_build = False

    if not output_dir.exists():
        cli.warning(f"Output directory '{output_dir}' does not exist")
        needs_build = True
    else:
        html_files = list(output_dir.rglob("*.html"))
        if not html_files:
            cli.warning("Output directory is empty")
            needs_build = True
        else:
            cli.info(f"Found {len(html_files)} HTML files in output directory")

    if needs_build:
        cli.info("Building site before checking links...")
        from bengal.cache import clear_build_cache
        from bengal.orchestration.build import BuildOptions, BuildOrchestrator

        if clear_build_cache(site.root_path):
            cli.info("Purged build cache for clean build")

        orchestrator = BuildOrchestrator(site)
        orchestrator.build(BuildOptions(quiet=True))
        cli.success("Site built successfully")


def _build_linkcheck_config(
    site_config: dict[str, Any],
    max_concurrency: int,
    per_host_limit: int,
    timeout: float,
    retries: int,
    retry_backoff: float,
    exclude: tuple[str, ...],
    exclude_domain: tuple[str, ...],
    ignore_status: tuple[str, ...],
) -> dict[str, Any]:
    """Build linkcheck config from CLI flags and site config."""
    config = site_config.get("health", {}).get("linkcheck", {})

    if max_concurrency:
        config["max_concurrency"] = max_concurrency
    if per_host_limit:
        config["per_host_limit"] = per_host_limit
    if timeout:
        config["timeout"] = timeout
    if retries:
        config["retries"] = retries
    if retry_backoff:
        config["retry_backoff"] = retry_backoff

    all_exclude = list(exclude) + config.get("exclude", [])
    if all_exclude:
        config["exclude"] = all_exclude

    all_exclude_domain = list(exclude_domain) + config.get("exclude_domain", [])
    if all_exclude_domain:
        config["exclude_domain"] = all_exclude_domain

    all_ignore_status = list(ignore_status) + config.get("ignore_status", [])
    if all_ignore_status:
        config["ignore_status"] = all_ignore_status

    return config
