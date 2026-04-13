"""Build command — generate the static site."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def build(
    source: Annotated[str, Description("Source directory path")] = "",
    no_parallel: Annotated[
        bool, Description("Force sequential processing (bypasses auto-detection)")
    ] = False,
    incremental: Annotated[bool, Description("Incremental mode (uses cache if present)")] = False,
    no_incremental: Annotated[bool, Description("Force full rebuild (ignore cache)")] = False,
    memory_optimized: Annotated[
        bool, Description("Streaming build for memory efficiency (5K+ pages)")
    ] = False,
    environment: Annotated[str, Description("Environment: local, preview, production")] = "",
    profile: Annotated[str, Description("Build profile: writer, theme-dev, dev")] = "",
    perf_profile: Annotated[str, Description("Enable performance profiling, save to file")] = "",
    profile_templates: Annotated[bool, Description("Profile template rendering times")] = False,
    clean_output: Annotated[bool, Description("Delete output directory before building")] = False,
    theme_dev: Annotated[bool, Description("Use theme developer profile")] = False,
    dev: Annotated[bool, Description("Use developer profile with full observability")] = False,
    verbose: Annotated[bool, Description("Show detailed build output")] = False,
    strict: Annotated[bool, Description("Fail on template errors (recommended for CI)")] = False,
    debug: Annotated[bool, Description("Show debug output and full tracebacks")] = False,
    traceback: Annotated[
        str, Description("Traceback verbosity: full | compact | minimal | off")
    ] = "",
    validate: Annotated[bool, Description("Validate templates before building")] = False,
    assets_pipeline: Annotated[bool, Description("Enable Node-based assets pipeline")] = False,
    no_assets_pipeline: Annotated[bool, Description("Disable Node-based assets pipeline")] = False,
    config: Annotated[str, Description("Path to config file (default: bengal.toml)")] = "",
    quiet: Annotated[bool, Description("Minimal output — only errors and summary")] = False,
    fast: Annotated[bool, Description("Fast mode: quiet output, max speed")] = False,
    full_output: Annotated[
        bool, Description("Full traditional output instead of live progress")
    ] = False,
    dashboard: Annotated[bool, Description("Launch interactive Textual dashboard")] = False,
    explain: Annotated[bool, Description("Show incremental build decision breakdown")] = False,
    explain_json: Annotated[bool, Description("Output --explain results as JSON")] = False,
    dry_run: Annotated[bool, Description("Preview build without writing files")] = False,
    log_file: Annotated[str, Description("Write detailed logs to file")] = "",
    build_version: Annotated[str, Description("Build only a specific version (git mode)")] = "",
    all_versions: Annotated[bool, Description("Build all versions in parallel (git mode)")] = False,
) -> dict:
    """Build the static site.

    Generates HTML from content, applies templates, processes assets,
    and outputs a production-ready site.
    """

    from bengal.cli.utils import (
        configure_cli_logging,
        configure_traceback,
        get_cli_output,
        load_site_from_cli,
    )
    from bengal.config.build_options_resolver import CLIFlags, resolve_build_options
    from bengal.orchestration.stats import display_build_stats, show_building_indicator
    from bengal.utils.observability.logger import close_all_loggers, print_all_summaries
    from bengal.utils.observability.profile import BuildProfile, set_current_profile

    source = source or "."
    config_path = config or None
    environment_val = environment or None
    profile_val = profile or None
    traceback_val = traceback or None
    perf_profile_path = perf_profile or None
    log_file_path = log_file or None
    build_version_val = build_version or None

    # Resolve tri-state flags
    incremental_val: bool | None = None
    if incremental:
        incremental_val = True
    elif no_incremental:
        incremental_val = False

    assets_pipeline_val: bool | None = None
    if assets_pipeline:
        assets_pipeline_val = True
    elif no_assets_pipeline:
        assets_pipeline_val = False

    fast_val: bool | None = True if fast else None

    # Apply fast mode
    if fast:
        quiet = True

    cli = get_cli_output(quiet=quiet, verbose=verbose)

    if memory_optimized and perf_profile_path:
        cli.error("--memory-optimized and --perf-profile cannot be used together")
        raise SystemExit(2)

    # Determine build profile
    build_profile = BuildProfile.from_cli_args(
        profile=profile_val, dev=dev, theme_dev=theme_dev, debug=debug
    )
    set_current_profile(build_profile)
    profile_config = build_profile.get_config()

    # Configure logging and traceback
    configure_cli_logging(
        source=source,
        profile=build_profile,
        log_file=log_file_path,
        debug=debug,
        verbose=verbose,
        track_memory=profile_config.get("track_memory", False),
    )
    configure_traceback(debug=debug, traceback=traceback_val)

    if memory_optimized and incremental_val is True:
        cli.warning("--memory-optimized with --incremental may not fully utilize cache")
        cli.blank()

    try:
        site = load_site_from_cli(
            source=source,
            config=config_path,
            environment=environment_val,
            profile=profile_val,
        )

        if clean_output:
            cli.info("Cleaning output directory before build (--clean-output).")
            site.clean()
            site.config["_clean_output_this_run"] = True

        configure_traceback(debug=debug, traceback=traceback_val, site=site)

        # Resolve build options with unified precedence
        cli_flags = CLIFlags(
            force_sequential=no_parallel,
            incremental=incremental_val,
            quiet=quiet,
            verbose=verbose,
            strict=strict,
            fast=fast_val,
            memory_optimized=memory_optimized,
            profile_templates=profile_templates,
        )
        build_options = resolve_build_options(site.config, cli_flags)

        incremental_resolved = build_options.incremental
        quiet = build_options.quiet
        verbose = build_options.verbose
        strict = build_options.strict
        memory_optimized = build_options.memory_optimized
        profile_templates = build_options.profile_templates

        if strict:
            if "build" not in site.config:
                site.config["build"] = {}
            site.config["build"]["strict_mode"] = True
        if debug:
            if "build" not in site.config:
                site.config["build"] = {}
            site.config["build"]["debug"] = True

        if assets_pipeline_val is not None:
            if "assets" not in site.config:
                site.config["assets"] = {}
            site.config["assets"]["pipeline"] = bool(assets_pipeline_val)

        # Dashboard mode
        if dashboard:
            from bengal.cli.dashboard.build import run_build_dashboard

            run_build_dashboard(
                site=site,
                parallel=not build_options.force_sequential,
                incremental=incremental_resolved,
                memory_optimized=memory_optimized,
                strict=strict,
                profile=build_profile,
            )
            return None

        # Git version mode
        if build_version_val or all_versions:
            _build_versions(
                site=site,
                source=source,
                config_path=config_path,
                environment_val=environment_val,
                profile_val=profile_val,
                build_version=build_version_val,
                all_versions=all_versions,
                incremental=incremental_resolved,
                quiet=quiet,
                build_profile=build_profile,
                profile_config=profile_config,
                build_options=build_options,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output,
                cli=cli,
            )
            return None

        # Template validation
        if validate:
            from bengal.services.validation import DefaultTemplateValidationService

            error_count = DefaultTemplateValidationService().validate(site)
            if error_count > 0:
                cli.blank()
                cli.error(f"Validation failed with {error_count} error(s)")
                raise SystemExit(1)
            cli.blank()

        show_building_indicator("Building site")

        if explain_json:
            explain = True

        # Performance profiling mode
        if perf_profile_path:
            stats = _build_with_profiling(
                site=site,
                perf_profile_path=perf_profile_path,
                source=source,
                build_options=build_options,
                incremental=incremental_resolved,
                quiet=quiet,
                build_profile=build_profile,
                profile_config=profile_config,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output,
                cli=cli,
            )
        else:
            if profile_templates:
                from bengal.rendering.template_profiler import enable_profiling

                enable_profiling()

            from bengal.orchestration.build.options import BuildOptions

            build_opts = BuildOptions(
                force_sequential=build_options.force_sequential,
                incremental=incremental_resolved,
                verbose=profile_config.get("verbose_console_logs", False) or full_output or explain,
                quiet=quiet,
                profile=build_profile,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output,
                profile_templates=profile_templates,
                explain=explain,
                dry_run=dry_run,
                explain_json=explain_json,
            )
            stats = site.build(options=build_opts)

            if explain:
                if explain_json:
                    _print_explain_json(stats, dry_run=dry_run)
                else:
                    _print_explain_output(stats, cli, dry_run=dry_run)

            if profile_templates and not quiet:
                from bengal.rendering.template_profiler import format_profile_report, get_profiler

                template_profiler = get_profiler()
                if template_profiler:
                    report = template_profiler.get_report()
                    cli.blank()
                    cli.header("Template Profiling Report")
                    for line in format_profile_report(report, top_n=20).splitlines():
                        cli.info(line)

        # Display results
        if stats.template_errors and build_profile != BuildProfile.WRITER:
            from bengal.orchestration.stats import display_template_errors

            display_template_errors(stats)

        stats.output_dir = str(site.output_dir)

        if not quiet:
            if build_profile == BuildProfile.WRITER:
                from bengal.orchestration.stats import display_simple_build_stats

                if stats.regression_pct is None:
                    try:
                        from bengal.utils.observability.performance_collector import (
                            PerformanceCollector,
                        )

                        _reader = PerformanceCollector(metrics_dir=site.paths.metrics_dir)
                        _prev = _reader.load_previous()
                        if _prev and _prev.build_time_ms > 0 and stats.build_time_ms > 0:
                            stats.regression_pct = (
                                (stats.build_time_ms - _prev.build_time_ms)
                                / _prev.build_time_ms
                                * 100
                            )
                    except Exception:
                        pass
                display_simple_build_stats(stats, output_dir=str(site.output_dir))
            elif build_profile == BuildProfile.DEVELOPER:
                from bengal.orchestration.summary import display_build_summary
                from bengal.utils.observability.terminal import detect_environment

                console_env = detect_environment()
                display_build_summary(stats, environment=console_env, cli=cli)
            else:
                display_build_stats(stats, show_art=True, output_dir=str(site.output_dir))
        else:
            cli.success("Build complete!")
            cli.path(str(site.output_dir), label="")

        if build_profile == BuildProfile.DEVELOPER and not quiet:
            print_all_summaries()

        if not quiet and not explain:
            from bengal.utils.dx import collect_hints

            site_cfg = site.config.get("site") or {}
            baseurl = str(site_cfg.get("baseurl", "") or "") if isinstance(site_cfg, dict) else ""
            hints = collect_hints("build", baseurl=baseurl, max_hints=1)
            if hints:
                cli.tip(hints[0].message)

        return {
            "output_dir": str(site.output_dir),
            "pages": getattr(stats, "pages_built", None),
            "build_time_ms": getattr(stats, "build_time_ms", None),
            "incremental": incremental_resolved,
            "errors": len(getattr(stats, "template_errors", [])),
        }
    finally:
        close_all_loggers()


def _build_versions(
    *,
    site,
    source,
    config_path,
    environment_val,
    profile_val,
    build_version,
    all_versions,
    incremental,
    quiet,
    build_profile,
    profile_config,
    build_options,
    memory_optimized,
    strict,
    full_output,
    cli,
) -> dict:
    """Handle --version and --all-versions git mode builds."""
    from pathlib import Path

    from bengal.cli.utils import load_site_from_cli

    if not getattr(site, "versioning_enabled", False):
        cli.error("Versioning is not enabled (add versioning config to bengal.yaml)")
        raise SystemExit(1)

    version_config = getattr(site, "version_config", None)
    if not version_config or not version_config.is_git_mode:
        cli.error("--version and --all-versions require git mode versioning")
        raise SystemExit(1)

    from bengal.content.versioning import GitVersionAdapter

    git_adapter = GitVersionAdapter(
        Path(source).resolve(),
        version_config.git_config,
    )

    if all_versions:
        cli.info("Discovering versions from git...")
        discovered_versions = git_adapter.discover_versions()

        if not discovered_versions:
            cli.warning("No versions found matching git patterns")
            raise SystemExit(1)

        cli.info(
            f"Found {len(discovered_versions)} versions: {', '.join(v.id for v in discovered_versions)}"
        )

        from bengal.orchestration.build.options import BuildOptions

        for v in discovered_versions:
            cli.blank()
            cli.info(f"{cli.icons.info} Building version {v.id}...")

            ref = v.source.replace("git:", "") if v.source.startswith("git:") else v.id
            worktree = git_adapter.get_or_create_worktree(v.id, ref)

            worktree_site = load_site_from_cli(
                source=str(worktree.path),
                config=config_path,
                environment=environment_val,
                profile=profile_val,
            )

            if not v.latest:
                if "build" not in worktree_site.config:
                    worktree_site.config["build"] = {}
                worktree_site.config["build"]["output_dir"] = str(Path(site.output_dir) / v.id)

            worktree_build_opts = BuildOptions(
                force_sequential=False,
                incremental=incremental,
                verbose=profile_config["verbose_build_stats"],
                quiet=quiet,
                profile=build_profile,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output,
            )
            worktree_site.build(worktree_build_opts)

        git_adapter.cleanup_worktrees(keep_cached=True)
        cli.blank()
        cli.success(f"Built {len(discovered_versions)} versions")
        return {"versions": [v.id for v in discovered_versions], "count": len(discovered_versions)}

    # Build specific version
    cli.info(f"Looking for version {build_version}...")
    discovered = git_adapter.discover_versions()
    matching = [v for v in discovered if v.id == build_version]

    if not matching:
        cli.error(f"Version {build_version} not found")
        cli.info(f"Available: {', '.join(v.id for v in discovered[:10])}")
        raise SystemExit(1)

    v = matching[0]
    ref = v.source.replace("git:", "") if v.source.startswith("git:") else v.id
    worktree = git_adapter.get_or_create_worktree(v.id, ref)
    cli.info(f"{cli.icons.info} Building version {v.id} from {ref}")

    # Continue with normal build using worktree site
    return {"version": v.id, "ref": ref}


def _build_with_profiling(
    *,
    site,
    perf_profile_path,
    source,
    build_options,
    incremental,
    quiet,
    build_profile,
    profile_config,
    memory_optimized,
    strict,
    full_output,
    cli,
):
    """Run build with cProfile performance profiling."""
    import cProfile
    import pstats
    from io import StringIO
    from pathlib import Path

    from bengal.orchestration.build.options import BuildOptions

    profiler = cProfile.Profile()
    profiler.enable()

    build_opts = BuildOptions(
        force_sequential=build_options.force_sequential,
        incremental=incremental,
        verbose=profile_config["verbose_build_stats"],
        quiet=quiet,
        profile=build_profile,
        memory_optimized=memory_optimized,
        strict=strict,
        full_output=full_output,
    )
    stats = site.build(options=build_opts)

    profiler.disable()

    if perf_profile_path is True or perf_profile_path == "true":
        from bengal.cache.paths import BengalPaths

        perf_paths = BengalPaths(Path(source))
        perf_paths.profiles_dir.mkdir(parents=True, exist_ok=True)
        profile_output = perf_paths.profiles_dir / "profile.stats"
    else:
        profile_output = Path(perf_profile_path)

    profiler.dump_stats(str(profile_output))

    if not quiet:
        s = StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(20)
        cli.blank()
        cli.header("Performance Profile (Top 20 by cumulative time)")
        for line in s.getvalue().splitlines():
            cli.info(line)
        cli.success(f"Profile saved to: {profile_output}")

    return stats


def _print_explain_output(stats, cli, *, dry_run: bool = False) -> None:
    """Print detailed incremental build decision breakdown."""
    from bengal.cli.utils import truncate_path

    decision = getattr(stats, "incremental_decision", None)
    if decision is None:
        cli.warning("No incremental decision data available (try running with --incremental)")
        return

    cli.blank()
    if dry_run:
        cli.header("Incremental Build Preview (--dry-run)")
        verb = "Would rebuild"
    else:
        cli.header("Incremental Build Decision")
        verb = "Rebuilt"

    cli.info(
        f"  {verb} {len(decision.pages_to_build)} pages ({decision.pages_skipped_count} skipped)"
    )
    cli.blank()

    reason_groups: dict[str, list[str]] = {}
    for page_path, reason in decision.rebuild_reasons.items():
        key = reason.code.value
        if key not in reason_groups:
            reason_groups[key] = []
        reason_groups[key].append(page_path)

    if reason_groups:
        cli.info("  REBUILD:")
        cli.info(
            "  +-------------------------------------+-------+---------------------------------+"
        )
        cli.info(
            "  | Reason                              | Count | Pages                           |"
        )
        cli.info(
            "  +-------------------------------------+-------+---------------------------------+"
        )

        for reason_code, pages in sorted(reason_groups.items(), key=lambda x: -len(x[1])):
            if len(pages) <= 2:
                pages_str = ", ".join(truncate_path(p) for p in pages)
            else:
                pages_str = f"{truncate_path(pages[0])}, ... +{len(pages) - 1} more"
            if len(pages_str) > 31:
                pages_str = pages_str[:28] + "..."
            reason_display = reason_code.replace("_", " ").title()
            if len(reason_display) > 35:
                reason_display = reason_display[:32] + "..."
            cli.info(f"  | {reason_display:<35} | {len(pages):>5} | {pages_str:<31} |")

        cli.info(
            "  +-------------------------------------+-------+---------------------------------+"
        )
        cli.blank()

    if decision.fingerprint_changes or decision.asset_changes:
        cli.info("  ASSETS:")
        for asset in decision.asset_changes:
            cli.info(f"    * {asset} -> CHANGED")
        if decision.fingerprint_changes:
            cli.detail(
                "    (fingerprint changed, all pages using these assets were rebuilt)", indent=0
            )
        cli.blank()

    if decision.pages_skipped_count > 0:
        cli.info(f"  SKIP ({decision.pages_skipped_count} pages): no_changes")
        cli.blank()

    if decision.skip_reasons:
        cli.blank()
        cli.detail("  Skipped pages (first 10):", indent=0)
        for page_path, skip_reason in list(decision.skip_reasons.items())[:10]:
            cli.detail(f"    * {truncate_path(page_path)}: {skip_reason.value}", indent=0)
        if len(decision.skip_reasons) > 10:
            cli.detail(f"    ... and {len(decision.skip_reasons) - 10} more", indent=0)

    filter_log = getattr(stats, "filter_decision_log", None)
    if filter_log is not None:
        cli.info(filter_log.to_trace_output())

    cli.blank()
    if dry_run:
        cli.info("  Run without --dry-run to execute build.")
    else:
        reason_summary = decision.get_reason_summary()
        if reason_summary:
            summary_parts = [
                f"{count} {reason}"
                for reason, count in sorted(reason_summary.items(), key=lambda x: -x[1])[:3]
            ]
            cli.detail(f"  Reason summary: {', '.join(summary_parts)}", indent=0)


def _print_explain_json(stats, *, dry_run: bool = False) -> None:
    """Print incremental build decision as JSON."""
    import json

    from bengal.cli.utils import get_cli_output

    decision = getattr(stats, "incremental_decision", None)

    if decision is None:
        output = {"error": "No incremental decision data available", "hint": "Try --incremental"}
    else:
        rebuild_reasons = {}
        for page_path, reason in decision.rebuild_reasons.items():
            rebuild_reasons[page_path] = {
                "code": reason.code.value,
                "details": reason.details if reason.details else None,
            }

        skip_reasons = {
            page_path: skip_reason.value for page_path, skip_reason in decision.skip_reasons.items()
        }

        filter_log = getattr(stats, "filter_decision_log", None)
        layer_trace = filter_log.to_dict().get("layer_trace") if filter_log else None

        output = {
            "decision_type": filter_log.decision_type.value if filter_log else "unknown",
            "pages_to_build": len(decision.pages_to_build),
            "pages_skipped": decision.pages_skipped_count,
            "fingerprint_changes": decision.fingerprint_changes,
            "asset_changes": decision.asset_changes if decision.asset_changes else [],
            "rebuild_reasons": rebuild_reasons,
            "skip_reasons": skip_reasons if skip_reasons else None,
            "reason_summary": decision.get_reason_summary(),
            "layer_trace": layer_trace,
            "dry_run": dry_run,
        }

    cli = get_cli_output()
    cli.render_write("json_output.kida", data=json.dumps(output, indent=2))
