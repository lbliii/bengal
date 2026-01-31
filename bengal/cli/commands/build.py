"""Build command for generating the static site."""

from __future__ import annotations

from pathlib import Path

import click

from bengal.cli.base import BengalCommand
from bengal.cli.helpers import command_metadata, handle_cli_errors
from bengal.cli.utils import (
    configure_cli_logging,
    configure_traceback,
    get_cli_output,
    load_site_from_cli,
    truncate_path,
    validate_flag_conflicts,
    validate_mutually_exclusive,
)
from bengal.config.build_options_resolver import CLIFlags, resolve_build_options
from bengal.errors.traceback import TracebackStyle
from bengal.orchestration.stats import (
    display_build_stats,
    show_building_indicator,
)
from bengal.utils.observability.logger import close_all_loggers, print_all_summaries


@click.command(cls=BengalCommand)
@command_metadata(
    category="build",
    description="Build the static site from content and templates",
    examples=[
        "bengal build",
        "bengal build --incremental",
        "bengal build --profile dev",
    ],
    requires_site=True,
    tags=["build", "production", "core"],
)
@handle_cli_errors(show_art=True)
@validate_flag_conflicts(
    {"fast": ["use_dev", "use_theme_dev"], "quiet": ["use_dev", "use_theme_dev"]}
)
@validate_mutually_exclusive(("quiet", "verbose"))
@click.option(
    "--no-parallel",
    is_flag=True,
    default=False,
    help="Force sequential processing (bypasses auto-detection). Use for debugging or benchmarking.",
)
@click.option(
    "--incremental/--no-incremental",
    default=None,
    help="Incremental mode: auto when omitted (uses cache if present).",
)
@click.option(
    "--memory-optimized",
    is_flag=True,
    help="Use streaming build for memory efficiency (best for 5K+ pages)",
)
@click.option(
    "--environment",
    "-e",
    type=click.Choice(["local", "preview", "production"], case_sensitive=False),
    help="Environment name (auto-detects if not specified)",
)
@click.option(
    "--profile",
    type=click.Choice(["writer", "theme-dev", "dev"]),
    help="Build profile: writer (fast/clean), theme-dev (templates), dev (full debug)",
)
@click.option(
    "--perf-profile",
    type=click.Path(),
    help="Enable performance profiling and save to file (default: .bengal/profiles/profile.stats)",
)
@click.option(
    "--profile-templates",
    is_flag=True,
    help="Profile template rendering times (shows which templates and functions are slow)",
)
@click.option(
    "--clean-output/--no-clean-output",
    default=False,
    help="Delete the output directory before building (useful for CI cache-busting).",
)
@click.option(
    "--theme-dev",
    "use_theme_dev",
    is_flag=True,
    help="Use theme developer profile (shorthand for --profile theme-dev)",
)
@click.option(
    "--dev",
    "use_dev",
    is_flag=True,
    help="Use developer profile with full observability (shorthand for --profile dev)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed build output (phase timing, build stats). Does NOT change profile.",
)
@click.option("--strict", is_flag=True, help="Fail on template errors (recommended for CI/CD)")
@click.option(
    "--debug", is_flag=True, help="Show debug output and full tracebacks (maps to dev profile)"
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    help="Traceback verbosity: full | compact | minimal | off",
)
@click.option(
    "--validate", is_flag=True, help="Validate templates before building (catch errors early)"
)
@click.option(
    "--assets-pipeline/--no-assets-pipeline",
    default=None,
    help="Enable/disable Node-based assets pipeline (overrides config)",
)
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.option("--quiet", "-q", is_flag=True, help="Minimal output - only show errors and summary")
@click.option(
    "--fast/--no-fast",
    default=None,
    help="Fast mode: quiet output, guaranteed parallel, max speed (overrides config)",
)
@click.option(
    "--full-output",
    is_flag=True,
    help="Show full traditional output instead of live progress (useful for debugging)",
)
@click.option(
    "--dashboard",
    is_flag=True,
    help="Launch interactive Textual dashboard (experimental)",
)
@click.option(
    "--explain",
    is_flag=True,
    help="Show detailed incremental build decision breakdown (why pages are rebuilt/skipped)",
)
@click.option(
    "--explain-json",
    is_flag=True,
    help="Output --explain results as JSON (for tooling integration)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview build without writing files (shows what WOULD happen)",
)
@click.option(
    "--log-file",
    type=click.Path(),
    help="Write detailed logs to file (default: .bengal/logs/build.log)",
)
@click.option(
    "--version",
    "build_version",
    type=str,
    help="Build only a specific version (git mode only, e.g., 0.1.6)",
)
@click.option(
    "--all-versions",
    is_flag=True,
    help="Build all versions in parallel (git mode only)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def build(
    no_parallel: bool,
    incremental: bool | None,
    memory_optimized: bool,
    environment: str | None,
    profile: str,
    perf_profile: str,
    profile_templates: bool,
    clean_output: bool,
    use_theme_dev: bool,
    use_dev: bool,
    verbose: bool,
    strict: bool,
    debug: bool,
    traceback: str | None,
    validate: bool,
    assets_pipeline: bool,
    config: str,
    quiet: bool,
    fast: bool,
    full_output: bool,
    dashboard: bool,
    explain: bool,
    explain_json: bool,
    dry_run: bool,
    log_file: str,
    build_version: str | None,
    all_versions: bool,
    source: str,
) -> None:
    """
    Build the static site.

    Generates HTML files from your content, applies templates,
    processes assets, and outputs a production-ready site.

    """

    # Import profile system
    from bengal.utils.observability.profile import BuildProfile, set_current_profile

    # Handle fast mode (CLI flag takes precedence, then check config later)
    # For now, determine from CLI flag only - config will be checked after Site.from_config
    fast_mode_enabled = fast if fast is not None else False

    # Apply fast mode settings if enabled
    if fast_mode_enabled:
        # Force quiet mode for minimal output
        quiet = True
        # Fast mode doesn't force sequential (still auto-detects via should_parallelize)
        # But --no-parallel can override it

    # New validations for build flag combinations
    if memory_optimized and perf_profile:
        raise click.UsageError(
            "--memory-optimized and --perf-profile cannot be used together (profiler doesn't work with streaming)"
        )

    if memory_optimized and incremental is True:
        cli = get_cli_output(quiet=quiet, verbose=verbose)
        cli.warning(
            "--memory-optimized with --incremental may not fully utilize cache (streaming limits incremental benefits)"
        )
        cli.blank()

    # Determine build profile with proper precedence.
    build_profile = BuildProfile.from_cli_args(
        profile=profile, dev=use_dev, theme_dev=use_theme_dev, debug=debug
    )

    # Set global profile for helper functions
    set_current_profile(build_profile)

    # Get profile configuration
    profile_config = build_profile.get_config()

    # Configure logging using consolidated helper
    log_path = configure_cli_logging(
        source=source,
        profile=build_profile,
        log_file=log_file,
        debug=debug,
        verbose=verbose,
        track_memory=profile_config.get("track_memory", False),
    )

    # Configure traceback behavior BEFORE site loading so errors show properly
    configure_traceback(debug=debug, traceback=traceback)

    # Create CLIOutput once at the start with quiet/verbose flags
    cli = get_cli_output(quiet=quiet, verbose=verbose)

    try:
        # Load site using helper
        site = load_site_from_cli(
            source=source,
            config=config,
            environment=environment,
            profile=profile,
        )

        if clean_output:
            cli.info("Cleaning output directory before build (--clean-output).")
            site.clean()
            # Internal hint for build phases: on a clean output directory, we do not
            # need to run stale-fingerprint cleanup (there cannot be any).
            site.config["_clean_output_this_run"] = True

        # Apply file-based traceback config after site is loaded (lowest precedence)
        configure_traceback(debug=debug, traceback=traceback, site=site)

        # Resolve build options with unified precedence: CLI > config > DEFAULTS
        cli_flags = CLIFlags(
            force_sequential=no_parallel,
            incremental=incremental,
            quiet=quiet,
            verbose=verbose,
            strict=strict,
            fast=fast,
            memory_optimized=memory_optimized,
            profile_templates=profile_templates,
        )
        build_options = resolve_build_options(site.config, cli_flags)

        # Extract resolved values for backward compatibility with existing code
        incremental = build_options.incremental
        quiet = build_options.quiet
        verbose = build_options.verbose
        strict = build_options.strict
        memory_optimized = build_options.memory_optimized
        profile_templates = build_options.profile_templates

        # Check if fast mode was enabled (from config or CLI)
        fast_mode_enabled = fast is True or (fast is None and build_options.quiet)

        # Override config with CLI flags (update nested structure)
        # Support both Config and dict - use raw dict for mutations
        if strict:
            if "build" not in site.config:
                site.config["build"] = {}
            site.config["build"]["strict_mode"] = True
        if debug:
            if "build" not in site.config:
                site.config["build"] = {}
            site.config["build"]["debug"] = True

        # Override asset pipeline toggle if provided
        if assets_pipeline is not None:
            if "assets" not in site.config:
                site.config["assets"] = {}
            site.config["assets"]["pipeline"] = bool(assets_pipeline)

        # Launch interactive dashboard if requested
        if dashboard:
            from bengal.cli.dashboard.build import run_build_dashboard

            run_build_dashboard(
                site=site,
                parallel=not build_options.force_sequential,
                incremental=incremental,
                memory_optimized=memory_optimized,
                strict=strict,
                profile=build_profile,
            )
            return  # Dashboard handles its own exit

        # Handle git version mode
        if build_version or all_versions:
            # Check if versioning is enabled in git mode
            if not getattr(site, "versioning_enabled", False):
                cli.error("Versioning is not enabled (add versioning config to bengal.yaml)")
                raise click.Abort()

            version_config = getattr(site, "version_config", None)
            if not version_config or not version_config.is_git_mode:
                cli.error(
                    "--version and --all-versions require git mode versioning (set mode: git)"
                )
                raise click.Abort()

            # Import git adapter
            from bengal.content.versioning import GitVersionAdapter

            git_adapter = GitVersionAdapter(
                Path(source).resolve(),
                version_config.git_config,
            )

            if all_versions:
                # Discover and build all versions
                cli.info("Discovering versions from git...")
                discovered_versions = git_adapter.discover_versions()

                if not discovered_versions:
                    cli.warning("No versions found matching git patterns")
                    raise click.Abort()

                cli.info(
                    f"Found {len(discovered_versions)} versions: {', '.join(v.id for v in discovered_versions)}"
                )

                # Build each version (sequential for now, parallel in future)
                for version in discovered_versions:
                    cli.blank()
                    cli.info(f"{cli.icons.info} Building version {version.id}...")

                    # Extract ref from source (e.g., "git:release/0.1.6" → "release/0.1.6")
                    ref = (
                        version.source.replace("git:", "")
                        if version.source.startswith("git:")
                        else version.id
                    )

                    worktree = git_adapter.get_or_create_worktree(version.id, ref)

                    # Load site from worktree
                    worktree_site = load_site_from_cli(
                        source=str(worktree.path),
                        config=config,
                        environment=environment,
                        profile=profile,
                    )

                    # Set version-specific output directory
                    if version.latest:
                        # Latest version goes to main output
                        pass
                    else:
                        # Older versions go to versioned subdirectory
                        # Update nested config structure - use raw dict for mutations
                        if "build" not in worktree_site.config:
                            worktree_site.config["build"] = {}
                        worktree_site.config["build"]["output_dir"] = str(
                            Path(site.output_dir) / version.id
                        )

                    # Build this version
                    from bengal.orchestration.build.options import BuildOptions

                    worktree_build_opts = BuildOptions(
                        force_sequential=False,  # Auto-detect via should_parallelize()
                        incremental=incremental,
                        verbose=profile_config["verbose_build_stats"],
                        quiet=quiet,
                        profile=build_profile,
                        memory_optimized=memory_optimized,
                        strict=strict,
                        full_output=full_output,
                    )
                    worktree_site.build(worktree_build_opts)

                # Cleanup worktrees
                git_adapter.cleanup_worktrees(keep_cached=True)

                cli.blank()
                cli.success(f"Built {len(discovered_versions)} versions")
                return

            elif build_version:
                # Build specific version
                cli.info(f"Looking for version {build_version}...")

                # Check if it matches any pattern
                discovered = git_adapter.discover_versions()
                matching = [v for v in discovered if v.id == build_version]

                if not matching:
                    cli.error(f"Version {build_version} not found")
                    cli.info(f"Available: {', '.join(v.id for v in discovered[:10])}")
                    raise click.Abort()

                version = matching[0]
                ref = (
                    version.source.replace("git:", "")
                    if version.source.startswith("git:")
                    else version.id
                )

                worktree = git_adapter.get_or_create_worktree(version.id, ref)

                cli.info(f"{cli.icons.info} Building version {version.id} from {ref}")

                # Load site from worktree
                site = load_site_from_cli(
                    source=str(worktree.path),
                    config=config,
                    environment=environment,
                    profile=profile,
                )

                # Continue with normal build below

        # Validate templates if requested (via service)
        if validate:
            from bengal.services.validation import DefaultTemplateValidationService

            error_count = DefaultTemplateValidationService().validate(site)

            if error_count > 0:
                cli.blank()
                cli.error(f"Validation failed with {error_count} error(s) - fix errors above")
                raise click.Abort()

            cli.blank()  # Blank line before build

        # Determine if we should use rich status spinner
        try:
            from bengal.utils.observability.rich_console import should_use_rich

            use_rich_spinner = should_use_rich() and not quiet
        except ImportError:
            use_rich_spinner = False

        if use_rich_spinner:
            # Show building indicator using themed CLIOutput
            show_building_indicator("Building site")
        else:
            # Fallback (shouldn't happen since Rich is required)
            show_building_indicator("Building site")

        # (Validation already done above when validate is True)

        # Enable performance profiling if requested
        if perf_profile:
            import cProfile
            import pstats
            from io import StringIO

            profiler = cProfile.Profile()
            profiler.enable()

            # Pass profile to build using BuildOptions
            from bengal.orchestration.build.options import BuildOptions as PerfBuildOptions

            perf_build_opts = PerfBuildOptions(
                force_sequential=build_options.force_sequential,
                incremental=incremental,
                verbose=profile_config["verbose_build_stats"],
                quiet=quiet,
                profile=build_profile,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output,
            )
            stats = site.build(options=perf_build_opts)

            profiler.disable()

            # Determine profile output path (use organized directory structure)
            if perf_profile is True:
                # Flag set without path - use default organized location
                paths.profiles_dir.mkdir(parents=True, exist_ok=True)
                perf_profile_path = paths.profiles_dir / "profile.stats"
            else:
                # User specified custom path
                perf_profile_path = Path(perf_profile)

            profiler.dump_stats(str(perf_profile_path))

            # Display summary
            if not quiet:
                s = StringIO()
                ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
                ps.print_stats(20)  # Top 20 functions

                cli.blank()
                cli.header("Performance Profile (Top 20 by cumulative time)")
                for line in s.getvalue().splitlines():
                    cli.info(line)
                cli.success(
                    f"Profile saved to: {perf_profile_path} (analyze with: python -m pstats)"
                )
        else:
            # Enable template profiling if requested
            if profile_templates:
                from bengal.rendering.template_profiler import enable_profiling

                enable_profiling()

            # Pass profile to build
            # When --full-output is used, enable console logs for debugging
            # Use BuildOptions directly - parallel is auto-detected via should_parallelize() unless force_sequential=True
            from bengal.orchestration.build.options import BuildOptions

            # If --explain-json is set, imply --explain
            if explain_json:
                explain = True

            build_opts = BuildOptions(
                force_sequential=build_options.force_sequential,
                incremental=incremental,
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

            # Display explain output if requested (RFC: rfc-incremental-build-observability Phase 2)
            if explain:
                if explain_json:
                    _print_explain_json(stats, dry_run=dry_run)
                else:
                    _print_explain_output(stats, cli, dry_run=dry_run)

            # Display template profiling report if enabled
            if profile_templates and not quiet:
                from bengal.rendering.template_profiler import (
                    format_profile_report,
                    get_profiler,
                )

                template_profiler = get_profiler()
                if template_profiler:
                    report = template_profiler.get_report()
                    cli.blank()
                    cli.header("Template Profiling Report")
                    for line in format_profile_report(report, top_n=20).splitlines():
                        cli.info(line)

        # Display template errors first if we're in theme-dev or dev mode
        if stats.template_errors and build_profile != BuildProfile.WRITER:
            from bengal.orchestration.stats import display_template_errors

            display_template_errors(stats)

        # Store output directory in stats for display
        stats.output_dir = str(site.output_dir)

        # Display build stats based on profile (unless quiet mode)
        if not quiet:
            if build_profile == BuildProfile.WRITER:
                # Simple, clean output for writers
                from bengal.orchestration.stats import display_simple_build_stats

                display_simple_build_stats(stats, output_dir=str(site.output_dir))
            elif build_profile == BuildProfile.DEVELOPER:
                # Rich intelligent summary with performance insights (Phase 2)
                from bengal.orchestration.summary import display_build_summary
                from bengal.utils.observability.rich_console import detect_environment

                console_env = detect_environment()
                display_build_summary(stats, environment=console_env)
            else:
                # Theme-dev: Use existing detailed display
                display_build_stats(stats, show_art=True, output_dir=str(site.output_dir))
        else:
            cli.console.print(f"{cli.icons.success} [success]Build complete![/success]")
            cli.path(str(site.output_dir), label="")

        # Print phase timing summary in dev mode only
        if build_profile == BuildProfile.DEVELOPER and not quiet:
            print_all_summaries()

        # Show GIL tip for performance (only if not quiet and GIL could be disabled)
        if not quiet and not explain:
            from bengal.utils.concurrency.gil import format_gil_tip_for_cli

            gil_tip = format_gil_tip_for_cli()
            if gil_tip:
                cli.tip(gil_tip)
    finally:
        # Always close log file handles
        close_all_loggers()


def _print_explain_output(stats, cli, *, dry_run: bool = False) -> None:
    """
    Print detailed incremental build decision breakdown.

    RFC: rfc-incremental-build-observability Phase 2

    Displays a human-readable breakdown of why pages were rebuilt or skipped,
    grouped by rebuild reason. Useful for debugging cache issues.

    Args:
        stats: BuildStats object containing incremental_decision
        cli: CLIOutput instance for formatted output
        dry_run: Whether this was a dry-run (preview) build
    """
    from bengal.orchestration.build.results import IncrementalDecision

    decision: IncrementalDecision | None = getattr(stats, "incremental_decision", None)
    if decision is None:
        cli.warning("No incremental decision data available (try running with --incremental)")
        return

    # Header
    cli.blank()
    if dry_run:
        cli.header("📊 Incremental Build Preview (--dry-run)")
        verb = "Would rebuild"
    else:
        cli.header("📊 Incremental Build Decision")
        verb = "Rebuilt"

    total_pages = len(decision.pages_to_build) + decision.pages_skipped_count
    cli.info(
        f"  {verb} {len(decision.pages_to_build)} pages ({decision.pages_skipped_count} skipped)"
    )
    cli.blank()

    # Group pages by rebuild reason
    reason_groups: dict[str, list[str]] = {}
    for page_path, reason in decision.rebuild_reasons.items():
        key = reason.code.value
        if key not in reason_groups:
            reason_groups[key] = []
        reason_groups[key].append(page_path)

    # Display rebuild reasons table
    if reason_groups:
        cli.info("  REBUILD:")
        cli.info(
            "  ┌───────────────────────────────────┬───────┬─────────────────────────────────┐"
        )
        cli.info(
            "  │ Reason                            │ Count │ Pages                           │"
        )
        cli.info(
            "  ├───────────────────────────────────┼───────┼─────────────────────────────────┤"
        )

        for reason_code, pages in sorted(reason_groups.items(), key=lambda x: -len(x[1])):
            # Format pages list (show first 2, truncate if more)
            if len(pages) <= 2:
                pages_str = ", ".join(truncate_path(p) for p in pages)
            else:
                pages_str = f"{truncate_path(pages[0])}, ... +{len(pages) - 1} more"

            # Truncate to fit column
            if len(pages_str) > 31:
                pages_str = pages_str[:28] + "..."

            # Format reason code for display
            reason_display = reason_code.replace("_", " ").title()
            if len(reason_display) > 33:
                reason_display = reason_display[:30] + "..."

            cli.info(f"  │ {reason_display:<33} │ {len(pages):>5} │ {pages_str:<31} │")

        cli.info(
            "  └───────────────────────────────────┴───────┴─────────────────────────────────┘"
        )
        cli.blank()

    # Asset changes section
    if decision.fingerprint_changes or decision.asset_changes:
        cli.info("  ASSETS:")
        for asset in decision.asset_changes:
            cli.info(f"    • {asset} → CHANGED")
        if decision.fingerprint_changes:
            cli.detail(
                "    (fingerprint changed, all pages using these assets were rebuilt)", indent=0
            )
        cli.blank()

    # Skip summary
    if decision.pages_skipped_count > 0:
        cli.info(f"  SKIP ({decision.pages_skipped_count} pages): no_changes")
        cli.blank()

    # Detailed skip reasons (only shown in verbose mode / when data available)
    if decision.skip_reasons:
        cli.blank()
        cli.detail(f"  Skipped pages (first 10):", indent=0)
        for i, (page_path, skip_reason) in enumerate(list(decision.skip_reasons.items())[:10]):
            cli.detail(f"    • {truncate_path(page_path)}: {skip_reason.value}", indent=0)
        if len(decision.skip_reasons) > 10:
            cli.detail(f"    ... and {len(decision.skip_reasons) - 10} more", indent=0)

    # RFC: rfc-incremental-build-observability - Layer trace output
    filter_log = getattr(stats, "filter_decision_log", None)
    if filter_log is not None:
        cli.info(filter_log.to_trace_output())

    # Footer
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


def truncate_path(path: str, max_len: int = 25) -> str:
    """Truncate path for display, keeping the filename visible."""
    if len(path) <= max_len:
        return path
    # Keep the last part (filename) and truncate from the start
    parts = path.split("/")
    if len(parts) == 1:
        return path[: max_len - 3] + "..."
    # Try to keep at least the filename
    filename = parts[-1]
    if len(filename) >= max_len - 3:
        return "..." + filename[-(max_len - 3) :]
    remaining = max_len - len(filename) - 4  # 4 for ".../"
    if remaining > 0:
        return ".../" + filename
    return "..." + filename[-(max_len - 3) :]


def _print_explain_json(stats, *, dry_run: bool = False) -> None:
    """
    Print incremental build decision as JSON.

    RFC: rfc-incremental-build-observability Phase 2

    Outputs machine-readable JSON for tooling integration.

    Args:
        stats: BuildStats object containing incremental_decision
        dry_run: Whether this was a dry-run (preview) build
    """
    import json

    from bengal.orchestration.build.results import IncrementalDecision

    decision: IncrementalDecision | None = getattr(stats, "incremental_decision", None)

    if decision is None:
        output = {
            "error": "No incremental decision data available",
            "hint": "Try running with --incremental",
        }
    else:
        # Build JSON-serializable output
        rebuild_reasons = {}
        for page_path, reason in decision.rebuild_reasons.items():
            rebuild_reasons[page_path] = {
                "code": reason.code.value,
                "details": reason.details if reason.details else None,
            }

        skip_reasons = {}
        for page_path, skip_reason in decision.skip_reasons.items():
            skip_reasons[page_path] = skip_reason.value

        # RFC: rfc-incremental-build-observability - Include layer trace
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

    print(json.dumps(output, indent=2))
