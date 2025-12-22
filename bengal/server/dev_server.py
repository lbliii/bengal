"""
Development server with file watching, hot reload, and auto-rebuild.

Provides a complete local development environment for Bengal sites with
HTTP serving, file watching, incremental builds, and browser live reload.

Features:
    - HTTP server for viewing the built site locally
    - File watching with automatic incremental rebuilds
    - Live reload via Server-Sent Events (no full page refresh for CSS)
    - Graceful shutdown handling (Ctrl+C, SIGTERM)
    - Stale process detection and cleanup
    - Automatic port fallback if port is in use
    - Optional browser auto-open
    - Pre/post build hooks for custom workflows
    - Process-isolated builds for crash resilience
    - Custom 404 error pages

Classes:
    DevServer: Main entry point orchestrating all server components

Architecture:
    The DevServer coordinates several subsystems:

    1. Initial Build: Runs a full site build before starting the server
    2. HTTP Server: ThreadingTCPServer with BengalRequestHandler
    3. File Watcher: WatcherRunner with watchfiles backend
    4. Build Trigger: Handles file changes and triggers rebuilds
    5. Resource Manager: Ensures cleanup on all exit scenarios

    Build Pipeline:
    FileWatcher → WatcherRunner → BuildTrigger → BuildExecutor → Site.build()
                                      ↓
                             ReloadController → LiveReload → Browser

Related:
    - bengal/server/watcher_runner.py: Async file watching bridge
    - bengal/server/build_trigger.py: Build orchestration
    - bengal/server/build_executor.py: Process-isolated builds
    - bengal/server/request_handler.py: HTTP request handling
    - bengal/server/live_reload.py: SSE-based hot reload
    - bengal/server/resource_manager.py: Cleanup coordination
"""

from __future__ import annotations

import os
import socket
import socketserver
import threading
import time
from pathlib import Path
from typing import Any

from bengal.cache import clear_build_cache, clear_output_directory, clear_template_cache
from bengal.orchestration.stats import display_build_stats, show_building_indicator
from bengal.output.icons import get_icon_set
from bengal.server.build_trigger import BuildTrigger
from bengal.server.constants import DEFAULT_DEV_HOST, DEFAULT_DEV_PORT
from bengal.server.ignore_filter import IgnoreFilter
from bengal.server.pid_manager import PIDManager
from bengal.server.request_handler import BengalRequestHandler
from bengal.server.resource_manager import ResourceManager
from bengal.server.watcher_runner import WatcherRunner
from bengal.utils.logger import get_logger
from bengal.utils.rich_console import should_use_emoji

logger = get_logger(__name__)


class DevServer:
    """
    Development server with file watching and auto-rebuild.

    Provides a complete development environment for Bengal sites with:
    - HTTP server for viewing the site locally
    - File watching for automatic rebuilds
    - Graceful shutdown handling
    - Stale process detection and cleanup
    - Automatic port fallback
    - Optional browser auto-open

    The server performs an initial build, then watches for changes and
    automatically rebuilds only what's needed using incremental builds.

    Features:
    - Incremental + parallel builds (5-10x faster than full builds)
    - Beautiful, minimal request logging
    - Custom 404 error pages
    - PID file tracking for stale process detection
    - Comprehensive resource cleanup on shutdown

    Example:
        from bengal.core import Site
        from bengal.server import DevServer

        site = Site.from_config()
        server = DevServer(site, port=5173, watch=True)
        server.start()  # Runs until Ctrl+C
    """

    def __init__(
        self,
        site: Any,
        host: str = DEFAULT_DEV_HOST,
        port: int = DEFAULT_DEV_PORT,
        watch: bool = True,
        auto_port: bool = True,
        open_browser: bool = False,
        version_scope: str | None = None,
    ) -> None:
        """
        Initialize the dev server.

        Args:
            site: Site instance
            host: Server host
            port: Server port
            watch: Whether to watch for file changes
            auto_port: Whether to automatically find an available port if the
                specified one is in use
            open_browser: Whether to automatically open the browser
            version_scope: RFC: rfc-versioned-docs-pipeline-integration (Phase 3)
                Focus rebuilds on a single version (e.g., "v2", "latest").
                If None, all versions are rebuilt on changes.
        """
        self.site = site
        self.host = host
        self.port = port
        self.watch = watch
        self.auto_port = auto_port
        self.open_browser = open_browser
        self.version_scope = version_scope

        # Mark site as running in dev mode to prevent timestamp churn in output files
        self.site.dev_mode = True

    def start(self) -> None:
        """
        Start the development server with robust resource cleanup.

        This method:
        1. Checks for and handles stale processes
        2. Prepares dev-specific configuration
        3. Performs an initial build
        4. Creates HTTP server (with port fallback if needed)
        5. Starts file watcher (if enabled)
        6. Opens browser (if requested)
        7. Runs until interrupted (Ctrl+C, SIGTERM, etc.)

        The server uses ResourceManager for comprehensive cleanup handling,
        ensuring all resources are properly released on shutdown regardless
        of how the process exits.

        Raises:
            OSError: If no available port can be found
            KeyboardInterrupt: When user presses Ctrl+C (handled gracefully)
        """
        logger.debug(
            "dev_server_starting",
            host=self.host,
            port=self.port,
            watch_enabled=self.watch,
            auto_port=self.auto_port,
            open_browser=self.open_browser,
            site_root=str(self.site.root_path),
        )

        # 1. Check for and handle stale processes
        self._check_stale_processes()

        # Use ResourceManager for comprehensive cleanup handling
        with ResourceManager() as rm:
            # Mark process as dev server for CLI output tuning
            os.environ["BENGAL_DEV_SERVER"] = "1"

            # 2. Prepare dev-specific configuration
            from bengal.utils.profile import BuildProfile

            baseurl_was_cleared = self._prepare_dev_config()

            # 3. Initial build
            # Use WRITER profile for fast builds (can enable specific validators via config)
            # Config can override profile to enable directives validator without full THEME_DEV overhead
            show_building_indicator("Initial build")
            stats = self.site.build(
                profile=BuildProfile.WRITER,
                incremental=not baseurl_was_cleared,
            )
            display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))

            logger.debug(
                "initial_build_complete",
                pages_built=stats.total_pages,
                duration_ms=stats.build_time_ms,
            )

            # Clear HTML cache after initial build to ensure fresh pages with live reload script
            try:
                with BengalRequestHandler._html_cache_lock:
                    BengalRequestHandler._html_cache.clear()
                logger.debug("html_cache_cleared_after_initial_build")
            except Exception as e:
                logger.debug("html_cache_clear_failed", error=str(e))
                pass  # Cache might not be initialized yet, ignore

            # Set active palette for rebuilding page styling
            # Uses the site's default_palette config or falls back to built-in default
            try:
                default_palette = self.site.config.get("default_palette")
                if default_palette:
                    BengalRequestHandler._active_palette = default_palette
                    logger.debug("rebuilding_page_palette_set", palette=default_palette)
            except Exception:
                pass  # Use default palette if config access fails

            # Initialize reload controller baseline after initial build
            # This prevents the first file change from being treated as "baseline" (which skips reload)
            try:
                from bengal.server.reload_controller import controller
                from bengal.server.utils import get_dev_config

                # Apply runtime controller configuration from dev config
                cfg = getattr(self.site, "config", {}) or {}
                try:
                    min_interval = get_dev_config(
                        cfg, "reload", "min_notify_interval_ms", default=300
                    )
                    controller.set_min_notify_interval_ms(int(min_interval))
                except Exception as e:
                    logger.warning("reload_config_min_interval_failed", error=str(e))
                    pass
                try:
                    # Provide sensible defaults to suppress known benign churn in dev
                    default_ignores = [
                        "index.json",
                        "index.txt",
                        "search/**",
                        "llm-full.txt",
                    ]
                    ignore_paths = get_dev_config(
                        cfg, "reload", "ignore_paths", default=default_ignores
                    )
                    controller.set_ignored_globs(list(ignore_paths) if ignore_paths else None)
                except Exception as e:
                    logger.warning("reload_config_ignores_failed", error=str(e))
                    pass
                try:
                    suspect_hash_limit = get_dev_config(
                        cfg, "reload", "suspect_hash_limit", default=200
                    )
                    suspect_size_limit = get_dev_config(
                        cfg, "reload", "suspect_size_limit_bytes", default=2_000_000
                    )
                    controller.set_hashing_options(
                        hash_on_suspect=bool(
                            get_dev_config(cfg, "reload", "hash_on_suspect", default=True)
                        ),
                        suspect_hash_limit=int(suspect_hash_limit)
                        if suspect_hash_limit is not None
                        else None,
                        suspect_size_limit_bytes=int(suspect_size_limit)
                        if suspect_size_limit is not None
                        else None,
                    )
                except Exception as e:
                    logger.warning("reload_config_hashing_failed", error=str(e))
                    pass

                controller.decide_and_update(self.site.output_dir)
                logger.debug("reload_controller_baseline_initialized")
            except Exception as e:
                logger.warning("reload_controller_init_failed", error=str(e))

            # 4. Create and register PID file for this process
            pid_file = PIDManager.get_pid_file(self.site.root_path)
            PIDManager.write_pid_file(pid_file)
            rm.register_pidfile(pid_file)

            # 5. Create HTTP server (determines actual port)
            httpd, actual_port = self._create_server()
            rm.register_server(httpd)

            # 6. Start file watcher if enabled (needs actual_port for rebuild messages)
            if self.watch:
                watcher_runner, build_trigger = self._create_watcher(actual_port)
                rm.register_watcher_runner(watcher_runner)
                rm.register_build_trigger(build_trigger)
                watcher_runner.start()
                logger.info("file_watcher_started", watch_dirs=self._get_watched_directories())

            # 7. Open browser if requested
            if self.open_browser:
                self._open_browser_delayed(actual_port)
                logger.debug("browser_opening", url=f"http://{self.host}:{actual_port}/")

            # Print startup message (keep for UX)
            self._print_startup_message(actual_port)

            logger.info(
                "dev_server_started",
                host=self.host,
                port=actual_port,
                output_dir=str(self.site.output_dir),
                watch_enabled=self.watch,
            )

            # 8. Run until interrupted (cleanup happens automatically via ResourceManager)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                # KeyboardInterrupt caught by serve_forever (backup to signal handler)
                print("\n  👋 Shutting down server...")
                logger.info("dev_server_shutdown", reason="keyboard_interrupt")
            # ResourceManager cleanup happens automatically via __exit__

    def _prepare_dev_config(self) -> bool:
        """
        Prepare site configuration for development mode.

        Sets development-specific defaults:
        - Disables asset fingerprinting (stable URLs for hot reload)
        - Disables minification (faster rebuilds, easier debugging)
        - Clears baseurl (serves from root '/' not subdirectory)

        When baseurl is cleared, also clears the build cache to prevent
        stale baseurl values from persisting in cached data.

        Returns:
            True if baseurl was cleared (requires clean rebuild)
        """
        cfg = self.site.config

        # Development defaults for faster iteration
        # NOTE: site.dev_mode is already set in __init__
        cfg["fingerprint_assets"] = False  # Stable CSS/JS filenames
        cfg.setdefault("minify_assets", False)  # Faster builds
        # Disable search index preloading in dev to avoid background index.json fetches
        cfg.setdefault("search_preload", "off")

        # Clear template bytecode cache to ensure fresh template compilation
        # This prevents stale bytecode from previous builds causing "stuck" templates
        clear_template_cache(self.site.root_path, logger)

        # Clear baseurl for local development
        # This prevents 404s since dev server serves from '/' not '/baseurl'
        baseurl_value = (cfg.get("baseurl", "") or "").strip()
        if not baseurl_value:
            return False  # No baseurl to clear

        # Store original and clear for dev server
        cfg["_dev_original_baseurl"] = baseurl_value
        cfg["baseurl"] = ""

        logger.info(
            "dev_server_baseurl_ignored",
            original=baseurl_value,
            effective="",
            action="forcing_clean_rebuild",
        )

        # Clear build cache AND output directory to prevent stale baseurl from persisting
        # The cache stores incremental build state, but HTML files in public/ may have
        # the old baseurl baked into meta tags like <meta name="bengal:index_url" content="/baseurl/index.json">
        clear_build_cache(self.site.root_path, logger)
        clear_output_directory(self.site.output_dir, logger)

        return True  # Baseurl was cleared

    def _get_watched_directories(self) -> list[str]:
        """
        Get list of directories that will be watched.

        Returns:
            List of directory paths (as strings) that exist and will be watched

        Note:
            Non-existent directories are filtered out
        """
        watch_dirs = [
            self.site.root_path / "content",
            self.site.root_path / "assets",
            self.site.root_path / "templates",
            self.site.root_path / "data",
        ]

        # Watch static directory for passthrough files (copied verbatim to output)
        static_config = self.site.config.get("static", {})
        if static_config.get("enabled", True):
            static_dir_name = static_config.get("dir", "static")
            static_dir = self.site.root_path / static_dir_name
            if static_dir.exists():
                watch_dirs.append(static_dir)

        # Watch i18n directory for translation file changes (hot reload)
        i18n_dir = self.site.root_path / "i18n"
        if i18n_dir.exists():
            watch_dirs.append(i18n_dir)

        # Add theme directories if they exist
        if self.site.theme:
            project_theme_dir = self.site.root_path / "themes" / self.site.theme
            if project_theme_dir.exists():
                watch_dirs.append(project_theme_dir)

            import bengal

            bengal_dir = Path(bengal.__file__).parent
            bundled_theme_dir = bengal_dir / "themes" / self.site.theme
            if bundled_theme_dir.exists():
                watch_dirs.append(bundled_theme_dir)

        # Watch autodoc source directories for Python file changes
        autodoc_config = self.site.config.get("autodoc", {})

        # Python source directories
        python_config = autodoc_config.get("python", {})
        if python_config.get("enabled", False):
            for source_dir in python_config.get("source_dirs", []):
                source_path = self.site.root_path / source_dir
                if source_path.exists():
                    watch_dirs.append(source_path)
                    logger.debug(
                        "watching_autodoc_source_dir",
                        path=str(source_path),
                        type="python",
                    )

        # OpenAPI spec file directory
        openapi_config = autodoc_config.get("openapi", {})
        if openapi_config.get("enabled", False):
            spec_file = openapi_config.get("spec_file")
            if spec_file:
                spec_path = self.site.root_path / Path(spec_file).parent
                if spec_path.exists():
                    watch_dirs.append(spec_path)
                    logger.debug(
                        "watching_autodoc_source_dir",
                        path=str(spec_path),
                        type="openapi",
                    )

        # Filter to only existing directories
        return [str(d) for d in watch_dirs if d.exists()]

    def _create_watcher(self, actual_port: int) -> tuple[WatcherRunner, BuildTrigger]:
        """
        Create file watcher and build trigger.

        Uses the modern FileWatcher abstraction (watchfiles)
        and always executes builds via BuildExecutor in a subprocess.

        Args:
            actual_port: Port number to display in rebuild messages

        Returns:
            Tuple of (WatcherRunner, BuildTrigger)
        """
        # Create build trigger (handles all build execution)
        # RFC: rfc-versioned-docs-pipeline-integration (Phase 3)
        build_trigger = BuildTrigger(
            site=self.site,
            host=self.host,
            port=actual_port,
            version_scope=self.version_scope,
        )

        # Create ignore filter from config
        config = getattr(self.site, "config", {}) or {}
        dev_server = config.get("dev_server", {})

        ignore_filter = IgnoreFilter(
            glob_patterns=dev_server.get("exclude_patterns", []),
            regex_patterns=dev_server.get("exclude_regex", []),
            directories=[self.site.output_dir],
            include_defaults=True,
        )

        # Get watch directories
        watch_dirs = [Path(d) for d in self._get_watched_directories()]

        # Also watch root for bengal.toml
        watch_dirs.append(self.site.root_path)

        # Create watcher runner
        watcher_runner = WatcherRunner(
            paths=watch_dirs,
            ignore_filter=ignore_filter,
            on_changes=build_trigger.trigger_build,
            debounce_ms=300,
        )

        logger.debug(
            "watcher_created",
            watch_dirs=[str(p) for p in watch_dirs],
        )

        return watcher_runner, build_trigger

    def _is_port_available(self, port: int) -> bool:
        """
        Check if a port is available for use.

        Args:
            port: Port number to check

        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.host, port))
                return True
        except OSError:
            return False

    def _find_available_port(self, start_port: int, max_attempts: int = 10) -> int:
        """
        Find an available port starting from the given port.

        Args:
            start_port: Port to start searching from
            max_attempts: Maximum number of ports to try

        Returns:
            Available port number

        Raises:
            OSError: If no available port is found
        """
        for port in range(start_port, start_port + max_attempts):
            if self._is_port_available(port):
                return port
        raise OSError(
            f"Could not find an available port in range "
            f"{start_port}-{start_port + max_attempts - 1}"
        )

    def _check_stale_processes(self) -> None:
        """
        Check for and offer to clean up stale processes.

        Looks for a PID file from a previous Bengal server run. If found,
        verifies the process is actually a Bengal process and offers to
        terminate it gracefully.

        Raises:
            OSError: If stale process cannot be killed and user chooses not to continue
        """
        pid_file = PIDManager.get_pid_file(self.site.root_path)
        stale_pid = PIDManager.check_stale_pid(pid_file)

        if stale_pid:
            port_pid = PIDManager.get_process_on_port(self.port)
            is_holding_port = port_pid == stale_pid

            logger.warning(
                "stale_process_detected",
                pid=stale_pid,
                pid_file=str(pid_file),
                holding_port=is_holding_port,
                port=self.port if is_holding_port else None,
            )

            icons = get_icon_set(should_use_emoji())
            print(f"\n{icons.warning} Found stale Bengal server process (PID {stale_pid})")

            if is_holding_port:
                print(f"   This process is holding port {self.port}")

            # Try to import click for confirmation, fall back to input
            try:
                import click

                if click.confirm("  Kill stale process?", default=True):
                    should_kill = True
                else:
                    should_kill = False
            except ImportError:
                response = input("  Kill stale process? [Y/n]: ").strip().lower()
                should_kill = response in ("", "y", "yes")

            if should_kill:
                if PIDManager.kill_stale_process(stale_pid):
                    print(f"  {icons.success} Stale process terminated")
                    logger.info("stale_process_killed", pid=stale_pid)
                    time.sleep(1)  # Give OS time to release resources
                else:
                    print("  ❌ Failed to kill process")
                    print(f"     Try manually: kill {stale_pid}")
                    logger.error(
                        "stale_process_kill_failed", pid=stale_pid, user_action="kill_manually"
                    )
                    raise OSError(f"Cannot start: stale process {stale_pid} is still running")
            else:
                print("  Continuing anyway (may encounter port conflicts)...")
                logger.warning(
                    "stale_process_ignored", pid=stale_pid, user_choice="continue_anyway"
                )

    def _create_server(self) -> tuple[socketserver.ThreadingTCPServer, int]:
        """
        Create HTTP server (does not start it).

        Changes to the output directory and creates a TCP server on the
        specified port. If the port is unavailable and auto_port is enabled,
        automatically finds the next available port.

        Returns:
            Tuple of (httpd, actual_port) where httpd is the TCPServer instance
            and actual_port is the port it's bound to

        Raises:
            OSError: If no available port can be found
        """
        # Store output directory for handler (don't rely on CWD - it can become invalid during rebuilds)
        output_dir = str(self.site.output_dir)
        logger.debug("serving_directory", path=output_dir)

        # Determine port to use
        actual_port = self.port

        # Check if requested port is available
        if not self._is_port_available(self.port):
            logger.warning("port_unavailable", port=self.port, auto_port_enabled=self.auto_port)

            icons = get_icon_set(should_use_emoji())
            if self.auto_port:
                # Try to find an available port
                try:
                    actual_port = self._find_available_port(self.port + 1)
                    print(f"{icons.warning} Port {self.port} is already in use")
                    print(f"{icons.arrow} Using port {actual_port} instead")
                    logger.info("port_fallback", requested_port=self.port, actual_port=actual_port)
                except OSError as e:
                    print(
                        f"{icons.error} Port {self.port} is already in use and no alternative "
                        f"ports are available."
                    )
                    print("\nTo fix this issue:")
                    print(f"  1. Stop the process using port {self.port}, or")
                    print("  2. Specify a different port with: bengal serve --port <PORT>")
                    print(f"  3. Find the blocking process with: lsof -ti:{self.port}")
                    logger.error(
                        "no_ports_available",
                        requested_port=self.port,
                        search_range=(self.port + 1, self.port + 10),
                        user_action="check_running_processes",
                    )
                    raise OSError(f"Port {self.port} is already in use") from e
            else:
                print(f"❌ Port {self.port} is already in use.")
                print("\nTo fix this issue:")
                print(f"  1. Stop the process using port {self.port}, or")
                print("  2. Specify a different port with: bengal serve --port <PORT>")
                print(f"  3. Find the blocking process with: lsof -ti:{self.port}")
                logger.error(
                    "port_unavailable_no_fallback",
                    port=self.port,
                    user_action="specify_different_port",
                )
                raise OSError(f"Port {self.port} is already in use")

        # Allow address reuse to prevent "address already in use" errors on restart
        socketserver.TCPServer.allow_reuse_address = True

        # Use a custom server class to increase the socket backlog (request queue size)
        # which helps avoid temporary stalls under bursts of rapid navigation.
        class BengalThreadingTCPServer(socketserver.ThreadingTCPServer):
            request_queue_size = 128

        # Create handler with directory bound (avoids os.getcwd() which fails if CWD is deleted during rebuild)
        from functools import partial

        handler = partial(BengalRequestHandler, directory=output_dir)

        # Create threaded server so SSE long-lived connections don't block other requests
        # (don't use context manager - ResourceManager handles cleanup)
        httpd = BengalThreadingTCPServer((self.host, actual_port), handler)
        httpd.daemon_threads = True  # Ensure worker threads don't block shutdown

        logger.info(
            "http_server_created",
            host=self.host,
            port=actual_port,
            handler_class="BengalRequestHandler",
            threaded=True,
        )

        return httpd, actual_port

    def _print_startup_message(self, port: int) -> None:
        """
        Print server startup message using Rich for stable borders.

        Displays a beautiful panel with:
        - Server URL
        - Output directory being served
        - File watching status
        - Shutdown instructions

        Args:
            port: Port number the server is listening on
        """
        from rich.console import Console
        from rich.panel import Panel

        console = Console()

        # Build message content
        lines = []
        lines.append("")  # Blank line for spacing

        # Server info
        url = f"http://{self.host}:{port}/"
        lines.append(f"   [cyan]➜[/cyan]  Local:   [bold]{url}[/bold]")

        # Serving path (truncate intelligently if too long)
        serving_path = str(self.site.output_dir)
        if len(serving_path) > 60:
            # Show start and end of path with ellipsis
            serving_path = serving_path[:30] + "..." + serving_path[-27:]
        lines.append(f"   [dim]➜[/dim]  Serving: {serving_path}")

        lines.append("")  # Blank line

        icons = get_icon_set(should_use_emoji())

        # Watching status
        if self.watch:
            lines.append(
                f"   [yellow]{icons.warning}[/yellow]  File watching enabled (auto-reload on changes)"
            )
            lines.append("      [dim](Live reload enabled - browser refreshes after rebuild)[/dim]")
        else:
            lines.append("   [dim]○  File watching disabled[/dim]")

        lines.append("")  # Blank line
        lines.append("   [dim]Press Ctrl+C to stop (or twice to force quit)[/dim]")

        # Create panel with content
        content = "\n".join(lines)
        panel = Panel(
            content,
            title=f"[bold]{icons.arrow} Bengal Dev Server[/bold]",
            border_style="cyan",
            padding=(0, 1),
            expand=False,  # Don't expand to full terminal width
            width=80,  # Fixed width that works well
        )

        console.print()
        console.print(panel)
        console.print()

        # Request log header
        from bengal.output import CLIOutput

        cli = CLIOutput()
        cli.request_log_header()

    def _open_browser_delayed(self, port: int) -> None:
        """
        Open browser after a short delay (in background thread).

        Uses a background thread to avoid blocking server startup.

        Args:
            port: Port number to include in the URL
        """
        import webbrowser

        def open_browser() -> None:
            time.sleep(0.5)  # Give server time to start
            webbrowser.open(f"http://{self.host}:{port}/")

        threading.Thread(target=open_browser, daemon=True).start()
