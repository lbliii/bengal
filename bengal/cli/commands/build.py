"""Build command for generating the static site."""

from pathlib import Path

import click

from bengal.core.site import Site
from bengal.utils.build_stats import (
    display_build_stats,
    show_building_indicator,
    show_error,
)
from bengal.utils.logger import LogLevel, close_all_loggers, configure_logging, print_all_summaries


def _should_regenerate_autodoc(autodoc_flag: bool, config_path: Path, root_path: Path, quiet: bool) -> bool:
    """
    Determine if autodoc should be regenerated based on:
    1. CLI flag (highest priority)
    2. Config setting
    3. Timestamp checking (if neither flag nor config explicitly disable)
    """
    # CLI flag takes precedence
    if autodoc_flag is not None:
        return autodoc_flag

    # Check config
    from bengal.autodoc.config import load_autodoc_config
    config = load_autodoc_config(config_path)
    build_config = config.get('build', {})

    # Check if auto_regenerate_autodoc is explicitly set in config
    auto_regen = build_config.get('auto_regenerate_autodoc', False)

    if not auto_regen:
        return False

    # If enabled in config, check timestamps to see if regeneration is needed
    needs_regen = _check_autodoc_needs_regeneration(config, root_path, quiet)
    return needs_regen


def _check_autodoc_needs_regeneration(autodoc_config: dict, root_path: Path, quiet: bool) -> bool:
    """
    Check if source files are newer than generated docs.
    Returns True if regeneration is needed.
    """
    import os

    python_config = autodoc_config.get('python', {})
    cli_config = autodoc_config.get('cli', {})

    needs_regen = False

    # Check Python docs
    if python_config.get('enabled', True):
        source_dirs = python_config.get('source_dirs', ['.'])
        output_dir = root_path / python_config.get('output_dir', 'content/api')

        if output_dir.exists():
            # Get newest source file
            newest_source = 0
            for source_dir in source_dirs:
                source_path = root_path / source_dir
                if source_path.exists():
                    for py_file in source_path.rglob('*.py'):
                        if '__pycache__' not in str(py_file):
                            mtime = os.path.getmtime(py_file)
                            newest_source = max(newest_source, mtime)

            # Get oldest generated file
            oldest_output = float('inf')
            for md_file in output_dir.rglob('*.md'):
                mtime = os.path.getmtime(md_file)
                oldest_output = min(oldest_output, mtime)

            if newest_source > oldest_output:
                if not quiet:
                    click.echo(click.style("📝 Python source files changed, regenerating API docs...", fg='yellow'))
                needs_regen = True
        else:
            # Output doesn't exist, need to generate
            if not quiet:
                click.echo(click.style("📝 API docs not found, generating...", fg='yellow'))
            needs_regen = True

    # Check CLI docs
    if cli_config.get('enabled', False) and cli_config.get('app_module'):
        output_dir = root_path / cli_config.get('output_dir', 'content/cli')

        if not output_dir.exists() or not list(output_dir.rglob('*.md')):
            if not quiet:
                click.echo(click.style("📝 CLI docs not found, generating...", fg='yellow'))
            needs_regen = True

    return needs_regen


def _run_autodoc_before_build(config_path: Path, root_path: Path, quiet: bool) -> None:
    """Run autodoc generation before build."""
    from bengal.autodoc.config import load_autodoc_config
    from bengal.cli.commands.autodoc import _generate_cli_docs, _generate_python_docs

    if not quiet:
        click.echo()
        click.echo(click.style("📚 Regenerating documentation...", fg='cyan', bold=True))
        click.echo()

    autodoc_config = load_autodoc_config(config_path)
    python_config = autodoc_config.get('python', {})
    cli_config = autodoc_config.get('cli', {})

    # Determine what to generate
    generate_python = python_config.get('enabled', True)
    generate_cli = cli_config.get('enabled', False) and cli_config.get('app_module')

    # Generate Python docs
    if generate_python:
        try:
            _generate_python_docs(
                source=tuple(python_config.get('source_dirs', ['.'])),
                output=python_config.get('output_dir', 'content/api'),
                clean=False,
                parallel=True,
                verbose=False,
                stats=False,
                python_config=python_config
            )
        except Exception as e:
            if not quiet:
                click.echo(click.style(f"⚠️  Python autodoc failed: {e}", fg='yellow'))
                click.echo(click.style("Continuing with build...", fg='yellow'))

    # Generate CLI docs
    if generate_cli:
        try:
            _generate_cli_docs(
                app=cli_config.get('app_module'),
                framework=cli_config.get('framework', 'click'),
                output=cli_config.get('output_dir', 'content/cli'),
                include_hidden=cli_config.get('include_hidden', False),
                clean=False,
                verbose=False,
                cli_config=cli_config
            )
        except Exception as e:
            if not quiet:
                click.echo(click.style(f"⚠️  CLI autodoc failed: {e}", fg='yellow'))
                click.echo(click.style("Continuing with build...", fg='yellow'))

    if not quiet:
        click.echo()


@click.command()
@click.option('--parallel/--no-parallel', default=True, help='Enable parallel processing for faster builds (default: enabled)')
@click.option('--incremental', is_flag=True, help='Perform incremental build (only rebuild changed files)')
@click.option('--memory-optimized', is_flag=True, help='Use streaming build for memory efficiency (best for 5K+ pages)')
@click.option('--profile', type=click.Choice(['writer', 'theme-dev', 'dev']),
              help='Build profile: writer (fast/clean), theme-dev (templates), dev (full debug)')
@click.option('--perf-profile', type=click.Path(), help='Enable performance profiling and save to file (default: .bengal/profiles/profile.stats)')
@click.option('--theme-dev', 'use_theme_dev', is_flag=True, help='Use theme developer profile (shorthand for --profile theme-dev)')
@click.option('--dev', 'use_dev', is_flag=True, help='Use developer profile with full observability (shorthand for --profile dev)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed build information (maps to theme-dev profile)')
@click.option('--strict', is_flag=True, help='Fail on template errors (recommended for CI/CD)')
@click.option('--debug', is_flag=True, help='Show debug output and full tracebacks (maps to dev profile)')
@click.option('--validate', is_flag=True, help='Validate templates before building (catch errors early)')
@click.option('--assets-pipeline/--no-assets-pipeline', default=None, help='Enable/disable Node-based assets pipeline (overrides config)')
@click.option('--autodoc/--no-autodoc', default=None, help='Force regenerate autodoc before building (overrides config)')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output - only show errors and summary')
@click.option('--full-output', is_flag=True, help='Show full traditional output instead of live progress (useful for debugging)')
@click.option('--log-file', type=click.Path(), help='Write detailed logs to file (default: .bengal-build.log)')
@click.argument('source', type=click.Path(exists=True), default='.')
def build(parallel: bool, incremental: bool, memory_optimized: bool, profile: str, perf_profile: str, use_theme_dev: bool, use_dev: bool, verbose: bool, strict: bool, debug: bool, validate: bool, assets_pipeline: bool, autodoc: bool, config: str, quiet: bool, full_output: bool, log_file: str, source: str) -> None:
    """
    🔨 Build the static site.

    Generates HTML files from your content, applies templates,
    processes assets, and outputs a production-ready site.
    """
    # Import profile system
    from bengal.utils.profile import BuildProfile, set_current_profile

    # Validate conflicting flags
    if quiet and verbose:
        raise click.UsageError("--quiet and --verbose cannot be used together")
    if quiet and (use_dev or use_theme_dev):
        raise click.UsageError("--quiet cannot be used with --dev or --theme-dev")

    # New validations for build flag combinations
    if memory_optimized and perf_profile:
        raise click.UsageError("--memory-optimized and --perf-profile cannot be used together (profiler doesn't work with streaming)")

    if memory_optimized and incremental:
        click.echo(click.style("⚠️  Warning: --memory-optimized with --incremental may not fully utilize cache", fg='yellow'))
        click.echo(click.style("   Streaming build processes pages in batches, limiting incremental benefits.\n", fg='yellow'))

    # Determine build profile with proper precedence
    build_profile = BuildProfile.from_cli_args(
        profile=profile,
        dev=use_dev,
        theme_dev=use_theme_dev,
        verbose=verbose,
        debug=debug
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
    log_path = Path(log_file) if log_file else Path(source) / '.bengal-build.log'

    configure_logging(
        level=log_level,
        log_file=log_path,
        verbose=profile_config['verbose_build_stats'],
        track_memory=profile_config['track_memory']
    )

    try:
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None

        # Create and build site
        site = Site.from_config(root_path, config_path)

        # Override config with CLI flags
        if strict:
            site.config["strict_mode"] = True
        if debug:
            site.config["debug"] = True

        # Override asset pipeline toggle if provided
        if assets_pipeline is not None:
            assets_cfg = site.config.get('assets') if isinstance(site.config.get('assets'), dict) else {}
            if not assets_cfg:
                assets_cfg = {}
            assets_cfg['pipeline'] = bool(assets_pipeline)
            site.config['assets'] = assets_cfg

        # Handle autodoc regeneration
        should_regenerate_autodoc = _should_regenerate_autodoc(
            autodoc_flag=autodoc,
            config_path=config_path,
            root_path=root_path,
            quiet=quiet
        )

        if should_regenerate_autodoc:
            _run_autodoc_before_build(config_path=config_path, root_path=root_path, quiet=quiet)

        # Validate templates if requested
        if validate:
            from bengal.rendering.template_engine import TemplateEngine
            from bengal.rendering.validator import validate_templates

            template_engine = TemplateEngine(site)
            error_count = validate_templates(template_engine)

            if error_count > 0:
                click.echo(click.style(f"\n❌ Validation failed with {error_count} error(s).",
                                      fg='red', bold=True))
                click.echo(click.style("Fix errors above, then run 'bengal build'", fg='yellow'))
                raise click.Abort()

            click.echo()  # Blank line before build

        # Determine if we should use rich status spinner
        try:
            from bengal.utils.rich_console import get_console, should_use_rich
            use_rich_spinner = should_use_rich() and not quiet
        except ImportError:
            use_rich_spinner = False

        if use_rich_spinner:
            # Show rich animated indicator
            console = get_console()
            console.print()
            console.print("    [bengal]ᓚᘏᗢ[/bengal]  [bold]Building your site...[/bold]")
            console.print()
        else:
            # Traditional static indicator
            show_building_indicator("Building site")

        # Validate templates if requested
        if validate:
            click.echo(click.style("\n🔍 Validating templates...", fg='cyan'))
            from bengal.rendering.validator import TemplateValidator
            validator = TemplateValidator(site)
            errors = validator.validate_all()

            if errors:
                click.echo(click.style(f"\n❌ Found {len(errors)} template error(s):", fg='red', bold=True))
                for error in errors[:5]:  # Show first 5
                    click.echo(f"  • {error}")
                if len(errors) > 5:
                    click.echo(f"  ... and {len(errors) - 5} more")
                raise click.Abort()
            else:
                click.echo(click.style("✓ All templates valid\n", fg='green'))

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
                verbose=profile_config['verbose_build_stats'],
                quiet=quiet,
                profile=build_profile,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output
            )

            profiler.disable()

            # Determine profile output path (use organized directory structure)
            if perf_profile is True:
                # Flag set without path - use default organized location
                perf_profile_path = BengalPaths.get_profile_path(root_path, filename='profile.stats')
            else:
                # User specified custom path
                perf_profile_path = Path(perf_profile)

            profiler.dump_stats(str(perf_profile_path))

            # Display summary
            if not quiet:
                s = StringIO()
                ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
                ps.print_stats(20)  # Top 20 functions

                click.echo()
                click.echo(click.style("📊 Performance Profile (Top 20 by cumulative time):",
                                      fg='cyan', bold=True))
                click.echo(s.getvalue())
                click.echo(click.style(f"Full profile saved to: {perf_profile_path}",
                                      fg='green'))
                click.echo(click.style("Analyze with: python -m pstats " + str(perf_profile_path),
                                      fg='yellow'))
        else:
            # Pass profile to build
            # When --full-output is used, enable console logs for debugging
            stats = site.build(
                parallel=parallel,
                incremental=incremental,
                verbose=profile_config.get('verbose_console_logs', False) or full_output,
                quiet=quiet,
                profile=build_profile,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output
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
            click.echo(click.style("✅ Build complete!", fg='green', bold=True))
            click.echo(click.style(f"   ↪ {site.output_dir}", fg='cyan'))

        # Print phase timing summary in dev mode only
        if build_profile == BuildProfile.DEVELOPER and not quiet:
            print_all_summaries()

    except Exception as e:
        show_error(f"Build failed: {e}", show_art=True)
        if debug:
            raise
        raise click.Abort() from e
    finally:
        # Always close log file handles
        close_all_loggers()

