"""Check command — validate site health and content quality."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def _check_display_context(
    report,
    *,
    focus: str = "",
    style: str = "dense",
    limit: int = 10,
    verbose: bool = False,
    suggestions: bool = False,
) -> dict:
    """Build template context for source health check output."""
    from bengal.cli.milo_commands._reports import bar, palette

    glyphs = palette(style)
    envelope = report.format_envelope(command="check")
    raw_findings = []
    for index, finding in enumerate(envelope["findings"], 1):
        code = finding.get("code") or "CHK"
        raw_findings.append({**finding, "display_code": f"{code}-{index:03d}"})

    filtered = [
        finding
        for finding in raw_findings
        if (verbose or finding["severity"] != "info")
        and (suggestions or finding["severity"] != "suggestion")
    ]
    findings = []
    for finding in filtered:
        details = finding.get("details") or []
        severity = finding["severity"]
        findings.append(
            {
                **finding,
                "glyph": glyphs.get(severity, glyphs["warning"]),
                "location": details[0] if details else finding.get("validator", "health"),
                "target": details[1] if len(details) > 1 else finding.get("validator", "health"),
                "recommendation": finding.get("recommendation")
                or "Review the source health finding.",
            }
        )

    total_findings = len(findings)
    actionable_count = sum(
        1 for finding in findings if finding["severity"] in {"error", "warning", "suggestion"}
    )
    visible = findings if limit <= 0 else findings[:limit]
    hidden_count = 0 if limit <= 0 else max(0, total_findings - len(visible))
    focus_value = focus.strip().lower()
    focused = None
    if focus_value:
        focused = next(
            (
                item
                for item in findings
                if item["display_code"].lower() == focus_value
                or str(item.get("code") or "").lower() == focus_value
            ),
            None,
        )

    summary = envelope["summary"]
    errors = int(summary.get("errors", 0))
    warnings = int(summary.get("warnings", 0))
    suggestion_count = int(summary.get("suggestions", 0))
    total_checks = max(int(summary.get("total_checks", 0)), errors + warnings + suggestion_count, 1)
    if errors:
        verdict = "Validation failed"
    elif warnings:
        verdict = "Validation passed with warnings"
    else:
        verdict = "Validation passed"
    if actionable_count or total_findings:
        detail = f"{errors} error(s), {warnings} warning(s), {suggestion_count} suggestion(s)"
    else:
        detail = f"{summary.get('passed', 0)} check(s) passed"
    steps = (
        [
            "Re-run with --suggestions for actionable fixes.",
            "Use --focus CODE to inspect one finding.",
            "Fix source content or config, then re-run `bengal check`.",
        ]
        if actionable_count
        else ["Source content and configuration passed health checks."]
    )
    return {
        "title": "Health Check",
        "ascii": style in {"ascii", "ci"},
        "verdict": verdict,
        "detail": detail,
        "findings": visible,
        "finding_heading": "Findings" if actionable_count else "Details",
        "focused_finding": focused,
        "focus": focus,
        "hidden_count": hidden_count,
        "next_focus": findings[len(visible)]["display_code"] if hidden_count else "",
        "meters": [
            {
                "glyph": glyphs["error"] if errors else glyphs["ok"],
                "label": "errors",
                "padding": " " * 9,
                "bar": bar(errors, total_checks, fill=glyphs["fill"], empty=glyphs["empty"]),
                "value": errors,
            },
            {
                "glyph": glyphs["warning"] if warnings else glyphs["ok"],
                "label": "warnings",
                "padding": " " * 7,
                "bar": bar(warnings, total_checks, fill=glyphs["fill"], empty=glyphs["empty"]),
                "value": warnings,
            },
            {
                "glyph": glyphs["suggestion"] if suggestion_count else glyphs["ok"],
                "label": "suggestions",
                "padding": " " * 4,
                "bar": bar(
                    suggestion_count, total_checks, fill=glyphs["fill"], empty=glyphs["empty"]
                ),
                "value": suggestion_count,
            },
        ],
        "steps": steps,
    }


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
    templates_security: Annotated[
        bool, Description("Run static escape/privacy checks on templates (Kida only)")
    ] = False,
    templates_pattern: Annotated[str, Description("Glob pattern for templates")] = "",
    fix: Annotated[bool, Description("Show migration hints for template errors")] = False,
    focus: Annotated[str, Description("Show one health finding by code, e.g. H101-001")] = "",
    style: Annotated[str, Description("Output style: dense, ascii, or ci")] = "dense",
    limit: Annotated[int, Description("Maximum findings to show in human output (0 = all)")] = 10,
) -> dict:
    """Validate site health and content quality.

    Runs health checks to find errors, warnings, and issues.
    By default shows only problems (errors and warnings).
    """
    from pathlib import Path

    from bengal.cli.utils import configure_traceback, load_site_from_cli
    from bengal.health import HealthCheck
    from bengal.output import get_cli_output
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
    if style not in {"dense", "ascii", "ci"}:
        cli.error(f"--style must be one of dense, ascii, or ci (got: {style!r})")
        cli.tip("Use --style ci for stable ASCII-safe output in automation logs.")
        raise SystemExit(2)
    if limit < 0:
        cli.error("--limit must be zero or greater")
        cli.tip("Use --limit 0 to show all findings.")
        raise SystemExit(2)

    with cli.output_mode(style):
        configure_traceback(debug=False, traceback=traceback_val, site=None)

        if style in {"ascii", "ci"}:
            cli.raw("Bengal Health Check Validation", level=None)
            cli.blank()
        else:
            cli.header("Health Check Validation")

        build_profile = (
            BuildProfile.from_string(profile_val) if profile_val else BuildProfile.WRITER
        )

        site = load_site_from_cli(
            source=source, config=None, environment=None, profile=build_profile, cli=cli
        )

        configure_traceback(debug=False, traceback=traceback_val, site=site)

        site.discover_content()
        site.discover_assets()

        cli.success(f"Loaded {len(site.pages)} pages")

        if templates or templates_context or templates_security:
            _validate_templates(
                site,
                templates_pattern_val,
                fix,
                cli,
                templates,
                templates_context,
                templates_security,
            )
            return {"status": "ok", "message": "Template validation complete"}

        context: list[Path] | None = None
        cache = None

        if files:
            context = files
        elif changed:
            from bengal.cache import BuildCache

            cache = BuildCache.load(site.config_service.paths.build_cache)
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

            cache = BuildCache.load(site.config_service.paths.build_cache)

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
        report_context = _check_display_context(
            report,
            focus=focus,
            style=style,
            limit=limit,
            verbose=verbose,
            suggestions=suggestions,
        )
        if focus:
            focused = report_context["focused_finding"]
            if focused is None:
                cli.error(f"Health finding not found: {focus}")
                cli.tip("Use a finding code from `bengal check`, such as H101-001.")
                raise SystemExit(2)
            cli.render_write("check_report_focus.kida", **{**report_context, "finding": focused})
        else:
            cli.render_write("check_report.kida", **report_context)

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
            raise SystemExit(1)

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

            cache = BuildCache.load(site.config_service.paths.build_cache)

        health_check = HealthCheck(site)
        report = health_check.run(
            profile=build_profile,
            verbose=verbose,
            incremental=incremental,
            context=files_to_validate,
            cache=cache,
        )

        cli.blank()
        cli.render_write(
            "validation_report.kida",
            **report.format_validation_report(verbose=verbose, show_suggestions=suggestions),
        )

        if report.has_errors():
            cli.error(f"{report.total_errors} error(s) found")
            cli.tip("Fix the issues above — watcher will re-run on save.")
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


def _validate_templates(
    site,
    pattern,
    show_hints,
    cli,
    templates,
    validate_context,
    validate_security,
):
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

    if validate_security:
        if hasattr(engine, "validate_security"):
            errors.extend(engine.validate_security(patterns))
        else:
            cli.info("Template security analysis is only available for Kida templates.")

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
        diagnostic_code = getattr(error, "diagnostic_code", None)
        if diagnostic_code:
            detail_parts.append(diagnostic_code)
        if error.line:
            detail_parts.append(f"Line {error.line}: {error.message}")
        else:
            detail_parts.append(error.message)
        if show_hints:
            suggestion = getattr(error, "suggestion", None)
            if suggestion:
                detail_parts.append(f"Hint: {suggestion}")
        level = "warning" if getattr(error, "severity", "error") == "warning" else "error"
        issues.append(
            {"level": level, "message": error.template, "detail": " — ".join(detail_parts[1:])}
        )

    error_count = sum(1 for issue in issues if issue["level"] == "error")
    warning_count = sum(1 for issue in issues if issue["level"] == "warning")
    cli.render_write(
        "validation_report.kida",
        title="Template Validation",
        issues=issues,
        summary={"errors": error_count, "warnings": warning_count, "passed": 0},
    )
    if error_count:
        cli.error(f"Template validation failed: {error_count} error(s)")
        cli.tip(
            "See the validation report above — each issue includes a suggestion for how to fix it."
        )
        raise SystemExit(1)
