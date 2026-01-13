"""
Validation commands for Bengal.

Commands:
    bengal validate - Run health checks on the site
"""

from __future__ import annotations

import signal
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from bengal.cache.paths import STATE_DIR_NAME
from bengal.cli.helpers import (
    configure_traceback,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.errors.traceback import TracebackStyle
from bengal.health import HealthCheck
from bengal.utils.profile import BuildProfile

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.output import CLIOutput


@click.command("validate")
@handle_cli_errors(show_art=False)
@click.option(
    "--file",
    "files",
    multiple=True,
    type=click.Path(exists=True, path_type=Path),
    help="Validate specific files (can be specified multiple times)",
)
@click.option(
    "--changed",
    is_flag=True,
    help="Only validate changed files (requires incremental build cache)",
)
@click.option(
    "--watch",
    is_flag=True,
    help="Watch mode: validate on file changes (experimental)",
)
@click.option(
    "--profile",
    type=click.Choice(["writer", "theme-dev", "developer"], case_sensitive=False),
    help="Build profile to use (writer, theme-dev, developer)",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show verbose output (all checks, not just problems)",
)
@click.option(
    "--suggestions",
    is_flag=True,
    help="Show quality suggestions (collapsed by default)",
)
@click.option(
    "--incremental",
    is_flag=True,
    help="Use incremental validation (only check changed files)",
)
@click.option(
    "--ignore",
    multiple=True,
    help="Health check code to ignore (e.g., H101, H202). Can be specified multiple times.",
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    help="Traceback verbosity: full | compact | minimal | off",
)
@click.option(
    "--templates",
    is_flag=True,
    help="Validate template syntax (Kida/Jinja2 templates)",
)
@click.option(
    "--templates-pattern",
    default=None,
    help="Glob pattern for templates (e.g., 'autodoc/**/*.html')",
)
@click.option(
    "--fix",
    is_flag=True,
    help="Show migration hints for template errors",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def validate(
    files: tuple[Path, ...],
    changed: bool,
    watch: bool,
    profile: str | None,
    verbose: bool,
    suggestions: bool,
    incremental: bool,
    ignore: tuple[str, ...],
    traceback: str | None,
    templates: bool,
    templates_pattern: str | None,
    fix: bool,
    source: str,
) -> None:
    """
    Validate site health and content quality.
    
    Runs health checks on your site to find errors, warnings, and issues.
    By default, shows only problems (errors and warnings).
    
    Examples:
        bengal validate
        bengal validate --file content/page.md
        bengal validate --changed
        bengal validate --profile writer
        bengal validate --verbose
        bengal validate --ignore H101 --ignore H202
        bengal validate --templates
        bengal validate --templates --fix
        bengal validate --templates --templates-pattern "autodoc/**/*.html"
    
    See also:
        bengal site build - Build the site
        bengal health linkcheck - Check links specifically
        
    """
    cli = get_cli_output()

    # Configure traceback behavior
    configure_traceback(debug=False, traceback=traceback, site=None)

    # Load site
    cli.header("Health Check Validation")

    # Determine profile (default to WRITER for fast validation)
    build_profile = BuildProfile.from_string(profile) if profile else BuildProfile.WRITER

    site = load_site_from_cli(
        source=source, config=None, environment=None, profile=build_profile, cli=cli
    )

    # Apply file-based traceback config after site is loaded
    configure_traceback(debug=False, traceback=traceback, site=site)

    # Discover content (required for validation)
    site.discover_content()
    site.discover_assets()

    cli.success(f"Loaded {len(site.pages)} pages")

    # Handle template validation mode
    if templates:
        _validate_templates(site, templates_pattern, fix, cli)
        return

    # Determine context for validation
    context: list[Path] | None = None
    if files:
        context = list(files)
    elif changed:
        # Find changed files using build cache
        from bengal.cache import BuildCache

        cache = BuildCache.load(site.paths.build_cache)

        context = []
        for page in site.pages:
            if page.source_path and cache.is_changed(page.source_path):
                context.append(page.source_path)

        if not context:
            cli.info("No changed files found - all files are up to date")
            return
        else:
            cli.info(f"Found {len(context)} changed file(s)")

    # Load cache for incremental validation
    cache: BuildCache | None = None
    if incremental or changed:
        from bengal.cache import BuildCache

        cache = BuildCache.load(site.paths.build_cache)

    # Run health checks
    cli.blank()
    health_check = HealthCheck(site)

    # Convert ignore codes to set
    ignore_codes = set(code.upper() for code in ignore) if ignore else None

    report = health_check.run(
        profile=build_profile,
        verbose=verbose,
        incremental=incremental or changed,
        context=context,
        cache=cache,
        ignore_codes=ignore_codes,
    )

    # Print report
    cli.blank()
    cli.info(report.format_console(verbose=verbose, show_suggestions=suggestions))

    # Exit with error code if there are errors (unless in watch mode)
    if watch:
        # Watch mode - don't exit, start watching
        _run_watch_mode(
            site=site,
            build_profile=build_profile,
            verbose=verbose,
            suggestions=suggestions,
            incremental=incremental or changed,
            cli=cli,
        )
    else:
        # Normal mode - exit with error code if there are errors
        if report.has_errors():
            raise click.ClickException(f"Validation failed: {report.total_errors} error(s) found")
        elif report.has_warnings():
            cli.warning(f"Validation completed with {report.total_warnings} warning(s)")
        else:
            cli.success("Validation passed - no issues found")


def _run_watch_mode(
    site: Site,
    build_profile: BuildProfile,
    verbose: bool,
    suggestions: bool,
    incremental: bool,
    cli: CLIOutput,
) -> None:
    """
    Run validation in watch mode - continuously validate on file changes.
    
    Args:
        site: Site instance
        build_profile: Build profile to use
        verbose: Whether to show verbose output
        suggestions: Whether to show suggestions
        incremental: Whether to use incremental validation
        cli: CLI output instance
        
    """
    import watchfiles

    from bengal.utils.async_compat import run_async

    cli.blank()
    cli.info("Watch mode: Validating on file changes (Ctrl+C to stop)")
    cli.blank()

    # Track files for validation
    DEBOUNCE_DELAY = 0.5  # 500ms debounce
    stop_event = threading.Event()

    def _should_validate(file_path: Path) -> bool:
        """Check if file should trigger validation."""
        # Only validate markdown/content files, config, templates
        valid_extensions = {".md", ".toml", ".yaml", ".yml", ".html", ".jinja2", ".jinja"}
        if file_path.suffix.lower() not in valid_extensions:
            return False

        # Ignore output directory
        if "public" in str(file_path) or STATE_DIR_NAME in str(file_path):
            return False

        # Ignore temp files
        return not (file_path.name.startswith(".") or file_path.name.endswith("~"))

    def _run_validation(files_to_validate: list[Path]) -> None:
        """Run validation on changed files."""
        # Show what changed
        cli.blank()
        cli.info(f"Files changed: {len(files_to_validate)}")
        for file_path in files_to_validate[:5]:  # Show first 5
            cli.info(f"   • {file_path}")
        if len(files_to_validate) > 5:
            cli.info(f"   ... and {len(files_to_validate) - 5} more")

        # Reload site content
        site.discover_content()
        site.discover_assets()

        # Load cache for incremental validation
        cache = None
        if incremental:
            from bengal.cache import BuildCache

            cache = BuildCache.load(site.paths.build_cache)

        # Run validation
        health_check = HealthCheck(site)
        report = health_check.run(
            profile=build_profile,
            verbose=verbose,
            incremental=incremental,
            context=files_to_validate,
            cache=cache,
        )

        # Print report
        cli.blank()
        cli.info(report.format_console(verbose=verbose, show_suggestions=suggestions))

        # Show summary
        if report.has_errors():
            cli.error(f"{report.total_errors} error(s) found")
        elif report.has_warnings():
            cli.warning(f"{report.total_warnings} warning(s)")
        else:
            cli.success("Validation passed")

        cli.blank()
        cli.info("Watching for changes...")

    def watch_filter(change: watchfiles.Change, path: str) -> bool:
        """Filter for watchfiles - returns True to INCLUDE."""
        return _should_validate(Path(path))

    async def _watch_loop() -> None:
        """Async watch loop using watchfiles."""
        # Watch content, config, templates directories
        watch_dirs = [
            site.root_path / "content",
            site.root_path / "templates",
            site.root_path,
        ]
        watch_paths = [d for d in watch_dirs if d.exists()]

        async for changes in watchfiles.awatch(
            *watch_paths,
            watch_filter=watch_filter,
            debounce=int(DEBOUNCE_DELAY * 1000),
            stop_event=stop_event,
        ):
            if stop_event.is_set():
                break

            files_to_validate = [Path(path) for (_, path) in changes]
            if files_to_validate:
                _run_validation(files_to_validate)

    # Handle Ctrl+C gracefully
    def signal_handler(sig: int, frame: Any) -> None:
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
    site: Site,
    pattern: str | None,
    show_hints: bool,
    cli: CLIOutput,
) -> None:
    """Validate templates using existing engine.validate() method.
    
    Args:
        site: Site instance with template engine
        pattern: Optional glob pattern to filter templates
        show_hints: Whether to show migration hints for errors
        cli: CLI output instance
    
    Raises:
        click.ClickException: If template validation fails
        
    """
    from bengal.rendering.engines import create_engine

    cli.blank()
    cli.info("Validating templates...")

    # Create the template engine
    engine = create_engine(site)

    # Build patterns list if provided
    patterns = [pattern] if pattern else None

    # Validate templates
    errors = engine.validate(patterns)

    if not errors:
        cli.blank()
        cli.success("✓ All templates valid")
        return

    cli.blank()
    cli.error(f"✗ Found {len(errors)} template error(s):")

    for error in errors:
        cli.blank()
        cli.warning(f"  Template: {error.template}")
        if error.line:
            cli.info(f"    Line {error.line}: {error.message}")
        else:
            cli.info(f"    {error.message}")

        # Show migration hints if requested and available
        if show_hints:
            suggestion = getattr(error, "suggestion", None)
            if suggestion:
                cli.info(f"    💡 {suggestion}")
            else:
                # Provide common migration hints based on error type
                _show_migration_hint(error, cli)

    cli.blank()
    raise click.ClickException(f"Template validation failed: {len(errors)} error(s)")


def _show_migration_hint(error: Any, cli: CLIOutput) -> None:
    """Show migration hints for common Jinja2 → Kida issues.
    
    Args:
        error: Template error object
        cli: CLI output instance
        
    """
    message = error.message.lower() if error.message else ""

    # Common Jinja2 migration patterns
    if "include" in message and "with" in message:
        cli.info("    💡 Hint: Kida uses {% let var=value %} before {% include %}")
        cli.info("             instead of Jinja2's 'include with var=value' syntax.")
    elif "items" in message or "keys" in message or "values" in message:
        cli.info("    💡 Hint: Use {{ dict | get('items') }} instead of {{ dict.items }}")
        cli.info("             to avoid conflicts with Python dict method names.")
    elif "undefined" in message:
        cli.info("    💡 Hint: Use {{ var ?? default }} or {{ var | default(value) }}")
        cli.info("             to handle undefined variables.")
    elif "slice" in message:
        cli.info("    💡 Hint: Kida's slice filter groups items (like Jinja2).")
        cli.info("             For string slicing, use {{ text[:5] }} syntax.")
