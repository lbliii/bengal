"""Build command for generating the static site."""

from __future__ import annotations

from pathlib import Path

import click

from bengal.cli.base import BengalCommand
from bengal.cli.helpers import (
    command_metadata,
    configure_traceback,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
    run_autodoc_before_build,
    should_regenerate_autodoc,
    validate_flag_conflicts,
    validate_mutually_exclusive,
)
from bengal.utils.build_stats import (
    display_build_stats,
    show_building_indicator,
)
from bengal.utils.logger import (
    LogLevel,
    close_all_loggers,
    configure_logging,
    print_all_summaries,
)
from bengal.utils.traceback_config import TracebackStyle


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
    "--parallel/--no-parallel",
    default=True,
    help="Enable parallel processing for faster builds (default: enabled)",
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
    "--autodoc/--no-autodoc",
    default=None,
    help="Force regenerate autodoc before building (overrides config)",
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
    "--log-file", type=click.Path(), help="Write detailed logs to file (default: .bengal-build.log)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
def build(
    parallel: bool,
    incremental: bool,
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
    autodoc: bool,
    config: str,
    quiet: bool,
    fast: bool,
    full_output: bool,
    log_file: str,
    source: str,
) -> None:
    """
    🔨 Build the static site.

    Generates HTML files from your content, applies templates,
    processes assets, and outputs a production-ready site.
    """

    # Import profile system
    from bengal.utils.profile import BuildProfile, set_current_profile

    # Handle fast mode (CLI flag takes precedence, then check config later)
    # For now, determine from CLI flag only - config will be checked after Site.from_config
    fast_mode_enabled = fast if fast is not None else False

    # Apply fast mode settings if enabled
    if fast_mode_enabled:
        # Note: PYTHON_GIL=0 must be set in shell before Python starts to suppress warnings
        # We can't set it here as modules are already imported
        # Force quiet mode for minimal output
        quiet = True
        # Ensure parallel is enabled
        parallel = True

    # New validations for build flag combinations
    if memory_optimized and perf_profile:
        raise click.UsageError(
            "--memory-optimized and --perf-profile cannot be used together (profiler doesn't work with streaming)"
        )

    if memory_optimized and incremental is True:
        cli = get_cli_output(quiet=quiet, verbose=verbose)
        cli.warning("⚠️  Warning: --memory-optimized with --incremental may not fully utilize cache")
        cli.warning("   Streaming build processes pages in batches, limiting incremental benefits.")
        cli.blank()

    # Determine build profile with proper precedence.
    # NOTE: --verbose is NOT passed here - it only controls output verbosity, not profile.
    #       Build profiles (dev, theme_dev, debug) are separate from verbosity settings.
    build_profile = BuildProfile.from_cli_args(
        profile=profile, dev=use_dev, theme_dev=use_theme_dev, debug=debug
    )

    # Set global profile for helper functions
    set_current_profile(build_profile)

    # Get profile configuration
    profile_config = build_profile.get_config()

    # Configure logging based on profile
    if build_profile == BuildProfile.DEVELOPER:
        log_level = LogLevel.DEBUG
    elif build_profile == BuildProfile.THEME_DEV:
        log_level = LogLevel.INFO
    else:  # WRITER
        log_level = LogLevel.WARNING

    # Determine log file path
    log_path = Path(log_file) if log_file else Path(source) / ".bengal-build.log"

    configure_logging(
        level=log_level,
        log_file=log_path,
        verbose=profile_config["verbose_build_stats"],
        track_memory=profile_config["track_memory"],
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

        # Apply file-based traceback config after site is loaded (lowest precedence)
        configure_traceback(debug=debug, traceback=traceback, site=site)

        # Check if fast_mode is enabled in config (CLI flag takes precedence)
        if fast is None:
            # No explicit CLI flag, check config
            config_fast_mode = site.config.get("build", {}).get("fast_mode", False)
            if config_fast_mode:
                # Enable fast mode from config
                # Note: PYTHON_GIL=0 must be set in shell to suppress import warnings
                quiet = True
                parallel = True
                fast_mode_enabled = True

        # Override config with CLI flags
        if strict:
            site.config["strict_mode"] = True
        if debug:
            site.config["debug"] = True

        # Override asset pipeline toggle if provided
        if assets_pipeline is not None:
            assets_cfg = (
                site.config.get("assets") if isinstance(site.config.get("assets"), dict) else {}
            )
            if not assets_cfg:
                assets_cfg = {}
            assets_cfg["pipeline"] = bool(assets_pipeline)
            site.config["assets"] = assets_cfg

        # Handle autodoc regeneration
        root_path = Path(source).resolve()
        # Find config file if not explicitly provided (same logic as ConfigLoader)
        if config:
            config_path = Path(config).resolve()
        else:
            # Try to find config file automatically (same as ConfigLoader.load())
            config_path = None
            for filename in ["bengal.toml", "bengal.yaml", "bengal.yml"]:
                candidate = root_path / filename
                if candidate.exists():
                    config_path = candidate
                    break
        if should_regenerate_autodoc(
            autodoc_flag=autodoc, config_path=config_path, root_path=root_path, quiet=quiet
        ):
            run_autodoc_before_build(config_path=config_path, root_path=root_path, quiet=quiet)

        # Validate templates if requested (via service)
        if validate:
            from bengal.services.validation import DefaultTemplateValidationService

            error_count = DefaultTemplateValidationService().validate(site)

            if error_count > 0:
                cli.blank()
                cli.error(f"❌ Validation failed with {error_count} error(s).")
                cli.warning("Fix errors above, then run 'bengal build'")
                raise click.Abort()

            cli.blank()  # Blank line before build

        # Determine if we should use rich status spinner
        try:
            from bengal.utils.rich_console import should_use_rich

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

            from bengal.utils.paths import BengalPaths

            profiler = cProfile.Profile()
            profiler.enable()

            # Pass profile to build
            stats = site.build(
                parallel=parallel,
                incremental=incremental,
                verbose=profile_config["verbose_build_stats"],
                quiet=quiet,
                profile=build_profile,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output,
            )

            profiler.disable()

            # Determine profile output path (use organized directory structure)
            if perf_profile is True:
                # Flag set without path - use default organized location
                perf_profile_path = BengalPaths.get_profile_path(
                    root_path, filename="profile.stats"
                )
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
                cli.header("📊 Performance Profile (Top 20 by cumulative time):")
                for line in s.getvalue().splitlines():
                    cli.info(line)
                cli.success(f"Full profile saved to: {perf_profile_path}")
                cli.warning("Analyze with: python -m pstats " + str(perf_profile_path))
        else:
            # Enable template profiling if requested
            if profile_templates:
                from bengal.rendering.template_profiler import enable_profiling

                enable_profiling()

            # Pass profile to build
            # When --full-output is used, enable console logs for debugging
            stats = site.build(
                parallel=parallel,
                incremental=incremental,
                verbose=profile_config.get("verbose_console_logs", False) or full_output,
                quiet=quiet,
                profile=build_profile,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output,
                profile_templates=profile_templates,
            )

            # Display template profiling report if enabled
            if profile_templates and not quiet:
                from bengal.rendering.template_profiler import (
                    format_profile_report,
                    get_profiler,
                )

                profiler = get_profiler()
                if profiler:
                    report = profiler.get_report()
                    cli.blank()
                    cli.header("📊 Template Profiling Report")
                    for line in format_profile_report(report, top_n=20).splitlines():
                        cli.info(line)

        # Display template errors first if we're in theme-dev or dev mode
        if stats.template_errors and build_profile != BuildProfile.WRITER:
            from bengal.utils.build_stats import display_template_errors

            display_template_errors(stats)

        # Store output directory in stats for display
        stats.output_dir = str(site.output_dir)

        # Display build stats based on profile (unless quiet mode)
        if not quiet:
            if build_profile == BuildProfile.WRITER:
                # Simple, clean output for writers
                from bengal.utils.build_stats import display_simple_build_stats

                display_simple_build_stats(stats, output_dir=str(site.output_dir))
            elif build_profile == BuildProfile.DEVELOPER:
                # Rich intelligent summary with performance insights (Phase 2)
                from bengal.utils.build_summary import display_build_summary
                from bengal.utils.rich_console import detect_environment

                environment = detect_environment()
                display_build_summary(stats, environment=environment)
            else:
                # Theme-dev: Use existing detailed display
                display_build_stats(stats, show_art=True, output_dir=str(site.output_dir))
        else:
            cli.success("✅ Build complete!")
            cli.path(str(site.output_dir), label="", icon="↪")

        # Print phase timing summary in dev mode only
        if build_profile == BuildProfile.DEVELOPER and not quiet:
            print_all_summaries()
    finally:
        # Always close log file handles
        close_all_loggers()
