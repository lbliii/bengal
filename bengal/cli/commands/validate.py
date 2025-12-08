"""
Validation commands for Bengal.

Commands:
    bengal validate - Run health checks on the site
"""

from __future__ import annotations

import signal
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import click

from bengal.cli.helpers import (
    configure_traceback,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.health import HealthCheck
from bengal.utils.profile import BuildProfile
from bengal.utils.traceback_config import TracebackStyle

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.cli_output import CLIOutput


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
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    help="Traceback verbosity: full | compact | minimal | off",
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
    traceback: str | None,
    source: str,
) -> None:
    """
    🔍 Validate site health and content quality.

    Runs health checks on your site to find errors, warnings, and issues.
    By default, shows only problems (errors and warnings).

    Examples:
        bengal validate
        bengal validate --file content/page.md
        bengal validate --changed
        bengal validate --profile writer
        bengal validate --verbose

    See also:
        bengal site build - Build the site
        bengal health linkcheck - Check links specifically
    """
    cli = get_cli_output()

    # Configure traceback behavior
    configure_traceback(debug=False, traceback=traceback, site=None)

    # Load site
    cli.header("🔍 Health Check Validation")
    cli.info("Loading site...")

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

    # Determine context for validation
    context: list[Path] | None = None
    if files:
        context = list(files)
    elif changed:
        # Find changed files using build cache
        from bengal.cache import BuildCache

        cache_dir = site.root_path / ".bengal"
        cache_path = cache_dir / "cache.json"
        cache = BuildCache.load(cache_path)

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

        cache_dir = site.root_path / ".bengal"
        cache_path = cache_dir / "cache.json"
        cache = BuildCache.load(cache_path)

    # Run health checks
    cli.blank()
    health_check = HealthCheck(site)
    report = health_check.run(
        profile=build_profile,
        verbose=verbose,
        incremental=incremental or changed,
        context=context,
        cache=cache,
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
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    cli.blank()
    cli.info("👀 Watch mode: Validating on file changes...")
    cli.info("   Press Ctrl+C to stop")
    cli.blank()

    # Track changed files for incremental validation
    changed_files: set[Path] = set()
    changed_files_lock = threading.Lock()
    debounce_timer: threading.Timer | None = None
    timer_lock = threading.Lock()
    DEBOUNCE_DELAY = 0.5  # 500ms debounce

    def _trigger_validation() -> None:
        """Trigger validation with current changed files."""
        nonlocal changed_files

        with changed_files_lock:
            files_to_validate = list(changed_files)
            changed_files.clear()

        if not files_to_validate:
            return

        # Show what changed
        cli.blank()
        cli.info(f"📝 Files changed: {len(files_to_validate)}")
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

            cache_dir = site.root_path / ".bengal"
            cache_path = cache_dir / "cache.json"
            cache = BuildCache.load(cache_path)

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
            cli.error(f"❌ {report.total_errors} error(s) found")
        elif report.has_warnings():
            cli.warning(f"⚠️  {report.total_warnings} warning(s)")
        else:
            cli.success("✅ Validation passed - no issues found")

        cli.blank()
        cli.info("👀 Watching for changes...")

    class ValidationHandler(FileSystemEventHandler):
        """File system event handler for validation watch mode."""

        def _should_validate(self, file_path: Path) -> bool:
            """Check if file should trigger validation."""
            # Only validate markdown/content files, config, templates
            valid_extensions = {".md", ".toml", ".yaml", ".yml", ".html", ".jinja2", ".jinja"}
            if file_path.suffix.lower() not in valid_extensions:
                return False

            # Ignore output directory
            if "public" in str(file_path) or ".bengal" in str(file_path):
                return False

            # Ignore temp files
            return not (file_path.name.startswith(".") or file_path.name.endswith("~"))

        def on_modified(self, event: FileSystemEvent) -> None:
            """Handle file modification."""
            if event.is_directory:
                return

            file_path = Path(event.src_path)
            if not self._should_validate(file_path):
                return

            with changed_files_lock:
                changed_files.add(file_path)

            # Debounce validation
            with timer_lock:
                nonlocal debounce_timer
                if debounce_timer:
                    debounce_timer.cancel()

                debounce_timer = threading.Timer(DEBOUNCE_DELAY, _trigger_validation)
                debounce_timer.daemon = True
                debounce_timer.start()

        def on_created(self, event: FileSystemEvent) -> None:
            """Handle file creation."""
            self.on_modified(event)

        def on_deleted(self, event: FileSystemEvent) -> None:
            """Handle file deletion."""
            self.on_modified(event)

    # Create observer and start watching
    observer = Observer()
    handler = ValidationHandler()

    # Watch content, config, templates directories
    watch_dirs = [
        site.root_path / "content",
        site.root_path / "templates",
        site.root_path,
    ]

    for watch_dir in watch_dirs:
        if watch_dir.exists():
            observer.schedule(handler, str(watch_dir), recursive=True)

    observer.start()

    # Handle Ctrl+C gracefully
    def signal_handler(sig: int, frame: Any) -> None:
        cli.blank()
        cli.info("Stopping watch mode...")
        observer.stop()
        observer.join()
        cli.success("Watch mode stopped")

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Keep running until interrupted
        while observer.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        signal_handler(None, None)
