"""Build command for generating the static site."""

from __future__ import annotations

from pathlib import Path

import click

from bengal.cli.base import BengalCommand
from bengal.core.site import Site
from bengal.utils.build_stats import (
    display_build_stats,
    show_building_indicator,
    show_error,
)
from bengal.utils.cli_output import CLIOutput
from bengal.utils.logger import (
    LogLevel,
    close_all_loggers,
    configure_logging,
    print_all_summaries,
    truncate_error,
)
from bengal.utils.traceback_config import (
    TracebackConfig,
    TracebackStyle,
    map_debug_flag_to_traceback,
    set_effective_style_from_cli,
)


def _should_regenerate_autodoc(
    autodoc_flag: bool, config_path: Path, root_path: Path, quiet: bool
) -> bool:
    """
    Determine if autodoc should be regenerated based on:
    1. CLI flag (highest priority)
    2. Config setting
    3. Timestamp checking (if neither flag nor config explicitly disable)
    """
    # CLI flag takes precedence
    if autodoc_flag is not None:
        return autodoc_flag

    # If no explicit flag, delegate to checker (tests patch this; config gate handled by caller)
    from bengal.autodoc.config import load_autodoc_config

    config = load_autodoc_config(config_path)
    return _check_autodoc_needs_regeneration(config, root_path, quiet)


def _check_autodoc_needs_regeneration(autodoc_config: dict, root_path: Path, quiet: bool) -> bool:
    """
    Check if source files are newer than generated docs.
    Returns True if regeneration is needed.
    """
    import os

    python_config = autodoc_config.get("python", {})
    cli_config = autodoc_config.get("cli", {})

    needs_regen = False

    # Check Python docs
    if python_config.get("enabled", True):
        source_dirs = python_config.get("source_dirs", ["."])
        output_dir = root_path / python_config.get("output_dir", "content/api")

        if output_dir.exists():
            # Get newest source file
            newest_source = 0
            for source_dir in source_dirs:
                source_path = root_path / source_dir
                if source_path.exists():
                    for py_file in source_path.rglob("*.py"):
                        if "__pycache__" not in str(py_file):
                            mtime = os.path.getmtime(py_file)
                            newest_source = max(newest_source, mtime)

            # Get oldest generated file
            oldest_output = float("inf")
            for md_file in output_dir.rglob("*.md"):
                mtime = os.path.getmtime(md_file)
                oldest_output = min(oldest_output, mtime)

            if newest_source > oldest_output:
                if not quiet:
                    cli = CLIOutput()
                    cli.warning("📝 Python source files changed, regenerating API docs...")
                needs_regen = True
        else:
            # Output doesn't exist: do not force regeneration from this heuristic alone
            # (callers may still choose to regenerate).
            needs_regen = False

    # Check CLI docs
    if cli_config.get("enabled", False) and cli_config.get("app_module"):
        output_dir = root_path / cli_config.get("output_dir", "content/cli")

        if not output_dir.exists() or not list(output_dir.rglob("*.md")):
            if not quiet:
                cli = CLIOutput()
                cli.warning("📝 CLI docs not found, generating...")
            needs_regen = True

    return needs_regen


def _run_autodoc_before_build(config_path: Path, root_path: Path, quiet: bool) -> None:
    """Run autodoc generation before build."""
    from bengal.autodoc.config import load_autodoc_config
    from bengal.cli.commands.autodoc import _generate_cli_docs, _generate_python_docs

    cli = CLIOutput(quiet=quiet)

    if not quiet:
        cli.blank()
        cli.header("📚 Regenerating documentation...")
        cli.blank()

    autodoc_config = load_autodoc_config(config_path)
    python_config = autodoc_config.get("python", {})
    cli_config = autodoc_config.get("cli", {})

    # Determine what to generate
    generate_python = python_config.get("enabled", True)
    generate_cli = cli_config.get("enabled", False) and cli_config.get("app_module")

    # Generate Python docs
    if generate_python:
        try:
            _generate_python_docs(
                source=tuple(python_config.get("source_dirs", ["."])),
                output=python_config.get("output_dir", "content/api"),
                clean=False,
                parallel=True,
                verbose=False,
                stats=False,
                python_config=python_config,
            )
        except Exception as e:
            if not quiet:
                cli.warning(f"⚠️  Python autodoc failed: {e}")
                cli.warning("Continuing with build...")

    # Generate CLI docs
    if generate_cli:
        try:
            _generate_cli_docs(
                app=cli_config.get("app_module"),
                framework=cli_config.get("framework", "click"),
                output=cli_config.get("output_dir", "content/cli"),
                include_hidden=cli_config.get("include_hidden", False),
                clean=False,
                verbose=False,
                cli_config=cli_config,
            )
        except Exception as e:
            if not quiet:
                cli.warning(f"⚠️  CLI autodoc failed: {e}")
                cli.warning("Continuing with build...")

    if not quiet:
        cli.blank()


@click.command(cls=BengalCommand)
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
    type=str,
    help="Environment name (local, preview, production) - auto-detects if not specified",
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
    help="Show detailed build information (maps to theme-dev profile)",
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

    # Validate conflicting flags (check before applying fast mode settings)
    if fast and (use_dev or use_theme_dev):
        raise click.UsageError("--fast cannot be used with --dev or --theme-dev profiles")
    if quiet and verbose:
        raise click.UsageError("--quiet and --verbose cannot be used together")
    if quiet and (use_dev or use_theme_dev):
        raise click.UsageError("--quiet cannot be used with --dev or --theme-dev")

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
        cli = CLIOutput()
        cli.warning("⚠️  Warning: --memory-optimized with --incremental may not fully utilize cache")
        cli.warning("   Streaming build processes pages in batches, limiting incremental benefits.")
        cli.blank()

    # Determine build profile with proper precedence
    build_profile = BuildProfile.from_cli_args(
        profile=profile, dev=use_dev, theme_dev=use_theme_dev, verbose=verbose, debug=debug
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

    try:
        # Configure traceback behavior from CLI flags and install rich handler
        # Map legacy --debug to full unless user explicitly set --traceback
        map_debug_flag_to_traceback(debug, traceback)
        set_effective_style_from_cli(traceback)
        TracebackConfig.from_environment().install()

        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None

        # Create and build site
        site = Site.from_config(root_path, config_path, environment=environment, profile=profile)

        # Apply file-based traceback config ([dev.traceback]) with lowest precedence
        # after site config is available, then re-install in case values changed
        try:
            from bengal.utils.traceback_config import apply_file_traceback_to_env

            apply_file_traceback_to_env(site.config)
            TracebackConfig.from_environment().install()
        except Exception:
            pass

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
        should_regenerate_autodoc = _should_regenerate_autodoc(
            autodoc_flag=autodoc, config_path=config_path, root_path=root_path, quiet=quiet
        )

        if should_regenerate_autodoc:
            _run_autodoc_before_build(config_path=config_path, root_path=root_path, quiet=quiet)

        # Validate templates if requested (via service)
        if validate:
            from bengal.services.validation import DefaultTemplateValidationService

            cli = CLIOutput()
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
                cli = CLIOutput()
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
            )

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
            cli = CLIOutput()
            cli.success("✅ Build complete!")
            cli.path(str(site.output_dir), label="", icon="↪")

        # Print phase timing summary in dev mode only
        if build_profile == BuildProfile.DEVELOPER and not quiet:
            print_all_summaries()

    except Exception as e:
        show_error(f"Build failed: {truncate_error(e)}", show_art=True)
        if debug:
            raise
        # Show configured traceback renderer for better diagnostics
        try:
            renderer = TracebackConfig.from_environment().get_renderer()
            renderer.display_exception(e)
        except Exception:
            pass
        raise click.Abort() from e
    finally:
        # Always close log file handles
        close_all_loggers()
