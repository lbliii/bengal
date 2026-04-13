"""Check command — validate site health and content quality."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def check(
    source: Annotated[str, Description("Source directory path")] = "",
    file: Annotated[str, Description("Validate specific file(s), comma-separated")] = "",
    changed: Annotated[
        bool, Description("Only validate changed files (requires build cache)")
    ] = False,
    watch: Annotated[bool, Description("Watch mode: validate on file changes")] = False,
    profile: Annotated[str, Description("Build profile: writer, theme-dev, developer")] = "",
    verbose: Annotated[bool, Description("Show all checks, not just problems")] = False,
    suggestions: Annotated[bool, Description("Show quality suggestions")] = False,
    incremental: Annotated[bool, Description("Use incremental validation")] = False,
    ignore: Annotated[
        str, Description("Health check codes to ignore (comma-separated, e.g. H101,H202)")
    ] = "",
    traceback: Annotated[
        str, Description("Traceback verbosity: full | compact | minimal | off")
    ] = "",
    templates: Annotated[bool, Description("Validate template syntax")] = False,
    templates_context: Annotated[
        bool, Description("Validate template context (Kida only)")
    ] = False,
    templates_pattern: Annotated[str, Description("Glob pattern for templates")] = "",
    fix: Annotated[bool, Description("Show migration hints for template errors")] = False,
) -> dict:
    """Validate site health and content quality.

    Runs health checks to find errors, warnings, and issues.
    By default shows only problems (errors and warnings).
    """
    from pathlib import Path

    from bengal.cli.utils import configure_traceback, get_cli_output, load_site_from_cli
    from bengal.health import HealthCheck
    from bengal.utils.observability.profile import BuildProfile

    source = source or "."
    traceback_val = traceback or None
    profile_val = profile or None
    templates_pattern_val = templates_pattern or None

    # Parse ignore codes
    ignore_codes = (
        {code.strip().upper() for code in ignore.split(",") if code.strip()} if ignore else None
    )

    # Parse file paths
    files: list[Path] = []
    if file:
        for f in file.split(","):
            f = f.strip()
            if f:
                files.append(Path(f))

    cli = get_cli_output()
    configure_traceback(debug=False, traceback=traceback_val, site=None)

    cli.header("Health Check Validation")

    build_profile = BuildProfile.from_string(profile_val) if profile_val else BuildProfile.WRITER

    site = load_site_from_cli(
        source=source, config=None, environment=None, profile=build_profile, cli=cli
    )

    configure_traceback(debug=False, traceback=traceback_val, site=site)

    site.discover_content()
    site.discover_assets()

    cli.success(f"Loaded {len(site.pages)} pages")

    if templates or templates_context:
        _validate_templates(site, templates_pattern_val, fix, cli, templates, templates_context)
        return {"status": "ok", "message": "Template validation complete"}

    context: list[Path] | None = None
    cache = None

    if files:
        context = files
    elif changed:
        from bengal.cache import BuildCache

        cache = BuildCache.load(site.paths.build_cache)
        context = []
        for page in site.pages:
            if page.source_path and cache.is_changed(page.source_path):
                context.append(page.source_path)

        if not context:
            cli.info("No changed files found - all files are up to date")
            return {
                "status": "skipped",
                "message": "No changed files found",
                "errors": 0,
                "warnings": 0,
            }
        cli.info(f"Found {len(context)} changed file(s)")

    if (incremental or changed) and cache is None:
        from bengal.cache import BuildCache

        cache = BuildCache.load(site.paths.build_cache)

    cli.blank()
    health_check = HealthCheck(site)

    report = health_check.run(
        profile=build_profile,
        verbose=verbose,
        incremental=incremental or changed,
        context=context,
        cache=cache,
        ignore_codes=ignore_codes,
    )

    cli.blank()
    cli.info(report.format_console(verbose=verbose, show_suggestions=suggestions))

    if watch:
        _run_watch_mode(
            site=site,
            build_profile=build_profile,
            verbose=verbose,
            suggestions=suggestions,
            incremental=incremental or changed,
            cli=cli,
        )
        return {"status": "ok", "message": "Watch mode ended"}

    errors = report.total_errors if hasattr(report, "total_errors") else 0
    warnings = report.total_warnings if hasattr(report, "total_warnings") else 0

    if report.has_errors():
        cli.error(f"Validation failed: {errors} error(s) found")
        raise SystemExit(1)
    if report.has_warnings():
        cli.warning(f"Validation completed with {warnings} warning(s)")
    else:
        cli.success("Validation passed - no issues found")

    return {
        "status": "ok" if not report.has_errors() else "error",
        "message": "Validation passed"
        if not report.has_errors()
        else f"Validation failed: {errors} error(s)",
        "errors": errors,
        "warnings": warnings,
        "passed": not report.has_errors(),
    }


def _run_watch_mode(site, build_profile, verbose, suggestions, incremental, cli):
    """Run validation in watch mode."""
    import signal
    import threading
    from pathlib import Path

    import watchfiles

    from bengal.cache.paths import STATE_DIR_NAME
    from bengal.health import HealthCheck
    from bengal.utils.concurrency.async_compat import run_async

    cli.blank()
    cli.info("Watch mode: Validating on file changes (Ctrl+C to stop)")
    cli.blank()

    stop_event = threading.Event()

    def _should_validate(file_path: Path) -> bool:
        valid_extensions = {".md", ".toml", ".yaml", ".yml", ".html", ".jinja2", ".jinja"}
        if file_path.suffix.lower() not in valid_extensions:
            return False
        if "public" in str(file_path) or STATE_DIR_NAME in str(file_path):
            return False
        return not (file_path.name.startswith(".") or file_path.name.endswith("~"))

    def watch_filter(change, path: str) -> bool:
        return _should_validate(Path(path))

    def _run_validation(files_to_validate):
        cli.blank()
        cli.info(f"Files changed: {len(files_to_validate)}")
        for fp in files_to_validate[:5]:
            cli.info(f"   * {fp}")
        if len(files_to_validate) > 5:
            cli.info(f"   ... and {len(files_to_validate) - 5} more")

        site.discover_content()
        site.discover_assets()

        cache = None
        if incremental:
            from bengal.cache import BuildCache

            cache = BuildCache.load(site.paths.build_cache)

        health_check = HealthCheck(site)
        report = health_check.run(
            profile=build_profile,
            verbose=verbose,
            incremental=incremental,
            context=files_to_validate,
            cache=cache,
        )

        cli.blank()
        cli.info(report.format_console(verbose=verbose, show_suggestions=suggestions))

        if report.has_errors():
            cli.error(f"{report.total_errors} error(s) found")
        elif report.has_warnings():
            cli.warning(f"{report.total_warnings} warning(s)")
        else:
            cli.success("Validation passed")
        cli.blank()
        cli.info("Watching for changes...")

    async def _watch_loop():
        watch_dirs = [site.root_path / "content", site.root_path / "templates", site.root_path]
        watch_paths = [d for d in watch_dirs if d.exists()]
        async for changes in watchfiles.awatch(
            *watch_paths,
            watch_filter=watch_filter,
            debounce=500,
            stop_event=stop_event,
        ):
            if stop_event.is_set():
                break
            files_to_validate = [Path(path) for (_, path) in changes]
            if files_to_validate:
                _run_validation(files_to_validate)

    def signal_handler(sig, frame):
        cli.blank()
        cli.info("Stopping watch mode...")
        stop_event.set()
        cli.success("Watch mode stopped")

    signal.signal(signal.SIGINT, signal_handler)

    try:
        run_async(_watch_loop())
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


def _validate_templates(site, pattern, show_hints, cli, templates, validate_context):
    """Validate template syntax and context."""
    from fnmatch import fnmatch

    from bengal.rendering.engines import create_engine
    from bengal.rendering.template_context_validation import (
        context_errors_to_template_errors,
        validate_template_contexts,
    )

    cli.blank()
    cli.info("Validating templates...")

    engine = create_engine(site)
    patterns = [pattern] if pattern else None

    errors = list(engine.validate(patterns)) if templates else []

    if validate_context:
        template_names = engine.list_templates() if hasattr(engine, "list_templates") else []
        if patterns:
            template_names = [n for n in template_names if any(fnmatch(n, p) for p in patterns)]
        context_errors = validate_template_contexts(engine, site, template_names)
        errors.extend(context_errors_to_template_errors(context_errors))

    if not errors:
        cli.render_write(
            "validation_report.kida",
            issues=[{"level": "success", "message": "All templates valid"}],
            summary={"errors": 0, "warnings": 0, "passed": 1},
        )
        return

    issues = []
    for error in errors:
        detail_parts = [f"Template: {error.template}"]
        if error.line:
            detail_parts.append(f"Line {error.line}: {error.message}")
        else:
            detail_parts.append(error.message)
        if show_hints:
            suggestion = getattr(error, "suggestion", None)
            if suggestion:
                detail_parts.append(f"Hint: {suggestion}")
        issues.append(
            {"level": "error", "message": error.template, "detail": " — ".join(detail_parts[1:])}
        )

    cli.render_write(
        "validation_report.kida",
        title="Template Validation",
        issues=issues,
        summary={"errors": len(errors), "warnings": 0, "passed": 0},
    )
    cli.error(f"Template validation failed: {len(errors)} error(s)")
    raise SystemExit(1)
