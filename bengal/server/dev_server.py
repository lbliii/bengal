"""
Development server with file watching, hot reload, and auto-rebuild.

Provides a complete local development environment for Bengal sites with
HTTP serving, file watching, incremental builds, and browser live reload.

Features:
- Serve-first startup: Serves cached content immediately for instant first paint
- Background validation: Validates cache and hot-reloads if stale
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

1. Serve-First Check: If cached output exists, serve immediately
2. Background Validation: Run incremental build to detect stale content
3. HTTP Server: Pounce ASGI with Bengal dev app
4. File Watcher: WatcherRunner with watchfiles backend
5. Build Trigger: Handles file changes and triggers rebuilds
6. Resource Manager: Ensures cleanup on all exit scenarios

Startup Flow (serve-first, when cache exists):
1. Check for cached output in public/
2. Start HTTP server immediately (instant first paint)
3. Open browser
4. Run validation build in background
5. Hot reload if stale content detected

Startup Flow (build-first, when no cache):
1. Run full build
2. Start HTTP server
3. Open browser

Build Pipeline:
FileWatcher → WatcherRunner → BuildTrigger → BuildExecutor → Site.build()
                                  ↓
                         ReloadController → LiveReload → Browser

Related:
- bengal/server/watcher_runner.py: Async file watching bridge
- bengal/server/build_trigger.py: Build orchestration
- bengal/server/build_executor.py: Process-isolated builds
- bengal/server/asgi_app.py: ASGI app with static serving and live reload
- bengal/server/live_reload.py: SSE-based hot reload
- bengal/server/resource_manager.py: Cleanup coordination

"""

from __future__ import annotations

import errno
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from bengal.assets.manifest import inspect_asset_outputs
from bengal.cache import clear_build_cache, clear_output_directory, clear_template_cache
from bengal.errors import BengalServerError, ErrorCode, reset_dev_server_state
from bengal.orchestration.stats import display_build_stats, show_building_indicator
from bengal.output import CLIOutput
from bengal.server.backend import ServerBackend, create_pounce_backend
from bengal.server.buffer_manager import BufferManager
from bengal.server.build_executor import BuildExecutor, BuildRequest
from bengal.server.build_state import build_state
from bengal.server.build_trigger import BuildTrigger
from bengal.server.constants import DEFAULT_DEV_HOST, DEFAULT_DEV_PORT
from bengal.server.ignore_filter import IgnoreFilter
from bengal.server.live_reload import LiveReloadMixin
from bengal.server.pid_manager import PIDManager
from bengal.server.resource_manager import ResourceManager
from bengal.server.utils import get_icons
from bengal.server.watcher_runner import WatcherRunner
from bengal.utils.observability.logger import get_logger
from bengal.utils.stats_minimal import MinimalStats

logger = get_logger(__name__)


class DevServer:
    """
    Development server with file watching, auto-rebuild, and serve-first startup.

    Provides a complete development environment for Bengal sites with:
    - Serve-first startup: Serves cached content immediately for instant first paint
    - Background validation: Validates cache and hot-reloads if stale
    - HTTP server for viewing the site locally
    - File watching for automatic rebuilds
    - Graceful shutdown handling
    - Stale process detection and cleanup
    - Automatic port fallback
    - Optional browser auto-open

    The server uses serve-first when cached output exists: it starts serving
    immediately while validating in the background. If validation finds stale
    content, it triggers a hot reload. This provides instant first paint for
    returning users.

    When no cache exists, the server falls back to build-first mode.

    Features:
    - Serve-first startup (instant first paint when cache exists)
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
            version_scope: Focus rebuilds on a single version (e.g., "v2", "latest").
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

        # Double-buffered output: the ASGI app serves from the active buffer
        # while builds write to the staging buffer, then swap atomically.
        staging_dir = self.site.root_path / ".bengal" / "staging"
        self._buffer_manager = BufferManager.for_dev_server(
            output_dir=self.site.output_dir,
            staging_dir=staging_dir,
        )
        self._buffer_manager.setup()

    def start(self) -> None:
        """
        Start the development server with serve-first optimization.

        Uses serve-first startup when cached output exists:
        1. Checks for and handles stale processes
        2. Prepares dev-specific configuration
        3. If cache exists: Start server immediately, validate in background
        4. If no cache: Build first, then start server
        5. Starts file watcher (if enabled)
        6. Opens browser (if requested)
        7. Runs until interrupted (Ctrl+C, SIGTERM, etc.)

        Serve-first provides instant first paint by serving cached content
        while validating in the background. Any stale content triggers
        automatic hot reload.

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

        # Reset error session for fresh server start
        reset_dev_server_state()

        # Use ResourceManager for comprehensive cleanup handling
        with ResourceManager() as rm:
            # Mark process as dev server for CLI output tuning
            os.environ["BENGAL_DEV_SERVER"] = "1"
            # Force process executor for dev server builds so Ctrl+C exits cleanly
            # (no ThreadPoolExecutor in main process → no shutdown traceback)
            os.environ["BENGAL_BUILD_EXECUTOR"] = "process"

            # 2. Prepare dev-specific configuration
            from bengal.utils.observability.profile import BuildProfile

            baseurl_was_cleared = self._prepare_dev_config()

            # 3. Determine startup strategy: serve-first or build-first
            # Serve-first when: cache exists AND baseurl wasn't cleared
            has_cache = self._has_cached_output()
            can_serve_first = not baseurl_was_cleared and has_cache

            logger.debug(
                "serve_first_decision",
                baseurl_was_cleared=baseurl_was_cleared,
                has_cached_output=has_cache,
                output_dir=str(self.site.output_dir),
                can_serve_first=can_serve_first,
            )

            if can_serve_first:
                # SERVE-FIRST: Instant first paint, validate in background
                logger.info("serve_first_mode", reason="cached_output_exists")

                # Create and register PID file
                pid_file = PIDManager.get_pid_file(self.site.root_path)
                PIDManager.write_pid_file(pid_file)
                rm.register_pidfile(pid_file)

                # Create HTTP server immediately
                backend = self._create_server()
                rm.register_server(backend)
                rm.register_sse_shutdown()
                actual_port = backend.port

                # Create watcher but don't start yet - validation runs first to avoid
                # race where user edits during validation trigger concurrent builds
                if self.watch:
                    self._watcher_runner, self._build_trigger = self._create_watcher(actual_port)
                    rm.register_watcher_runner(self._watcher_runner)
                    rm.register_build_trigger(self._build_trigger)

                # Print startup message
                self._print_startup_message(actual_port, serve_first=True)

                # Start serving in background thread while we validate
                server_error: list[BaseException | None] = [None]

                def _run_server() -> None:
                    try:
                        backend.start()
                    except Exception as exc:
                        server_error[0] = exc
                        self._print_server_error(exc, actual_port)

                server_thread = threading.Thread(target=_run_server, daemon=True)
                server_thread.start()

                # Run validation build in foreground (shows progress)
                self._run_validation_build(BuildProfile.WRITER, actual_port)

                # Open browser only after validation completes - site is ready
                if self.open_browser:
                    self._open_browser_when_ready(actual_port)

                # Now wait for server to be interrupted
                logger.info(
                    "dev_server_started",
                    host=self.host,
                    port=actual_port,
                    output_dir=str(self.site.output_dir),
                    watch_enabled=self.watch,
                    mode="serve_first",
                )

                try:
                    # Wait for server thread (blocks until interrupted)
                    while server_thread.is_alive():
                        server_thread.join(timeout=1.0)
                    if server_error[0] is not None:
                        sys.exit(1)
                except KeyboardInterrupt:
                    print("\n  👋 Shutting down server...")
                    logger.info("dev_server_shutdown", reason="keyboard_interrupt")
                    backend.shutdown()

            else:
                # BUILD-FIRST: No cache, must build before serving
                logger.info(
                    "build_first_mode",
                    reason="no_cache" if not self._has_cached_output() else "baseurl_cleared",
                )

                # Initial build (process-isolated for clean Ctrl+C shutdown)
                show_building_indicator("Initial build")
                from bengal.orchestration.build.options import BuildOptions

                build_opts = BuildOptions(
                    profile=BuildProfile.WRITER,
                    incremental=not baseurl_was_cleared,
                )
                stats = self._run_build_via_executor(build_opts, "Initial build")
                display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))

                logger.debug(
                    "initial_build_complete",
                    pages_built=stats.total_pages,
                    duration_ms=stats.build_time_ms,
                )

                # Clear HTML cache after build
                self._clear_html_cache_after_build()

                # Set active palette for rebuilding page styling
                self._set_active_palette()

                # Initialize reload controller baseline
                self._init_reload_controller()

                # Create and register PID file
                pid_file = PIDManager.get_pid_file(self.site.root_path)
                PIDManager.write_pid_file(pid_file)
                rm.register_pidfile(pid_file)

                # Create HTTP server
                backend = self._create_server()
                rm.register_server(backend)
                rm.register_sse_shutdown()
                actual_port = backend.port

                # Start file watcher if enabled
                if self.watch:
                    watcher_runner, build_trigger = self._create_watcher(actual_port)
                    rm.register_watcher_runner(watcher_runner)
                    rm.register_build_trigger(build_trigger)
                    # Seed content hash cache so first edit can use reactive path
                    build_trigger.seed_content_hash_cache(list(self.site.pages))
                    watcher_runner.start()
                    logger.info("file_watcher_started", watch_dirs=self._get_watched_directories())

                # Print startup message
                self._print_startup_message(actual_port)

                logger.info(
                    "dev_server_started",
                    host=self.host,
                    port=actual_port,
                    output_dir=str(self.site.output_dir),
                    watch_enabled=self.watch,
                    mode="build_first",
                )

                # Open browser when server is ready (runs in background thread)
                if self.open_browser:
                    self._open_browser_when_ready(actual_port)

                # Run until interrupted
                try:
                    backend.start()
                except OSError as exc:
                    raise BengalServerError(
                        str(exc),
                        code=ErrorCode.S001,
                        suggestion=f"Use --port {actual_port + 1} or kill the process: lsof -ti:{actual_port} | xargs kill",
                    ) from exc
                except KeyboardInterrupt:
                    print("\n  👋 Shutting down server...")
                    logger.info("dev_server_shutdown", reason="keyboard_interrupt")
            # ResourceManager cleanup happens automatically via __exit__

    def _has_cached_output(self) -> bool:
        """
        Check if the output directory has cached content that can be served.

        Requires BOTH output HTML files AND a valid build cache. This prevents
        serve-first mode when ``bengal clean --cache`` removed the cache but
        the output directory survived (macOS filesystem race / Spotlight).

        Returns:
            True if output directory has HTML files backed by a build cache
        """
        output_dir = self.site.output_dir
        if not output_dir.exists():
            return False

        # Build cache must exist — stale output without a cache is not servable
        build_cache = self.site.config_service.paths.build_cache
        has_build_cache = build_cache.exists() or build_cache.with_suffix(".json.zst").exists()
        if not has_build_cache:
            logger.debug(
                "cached_output_rejected",
                reason="no_build_cache",
                output_dir=str(output_dir),
            )
            return False

        # Check for index.html as a proxy for "has content"
        index_file = output_dir / "index.html"
        try:
            has_html = index_file.exists() or any(output_dir.rglob("*.html"))
        except Exception:
            return False

        if not has_html:
            logger.debug(
                "cached_output_rejected",
                reason="no_html_output",
                output_dir=str(output_dir),
            )
            return False

        asset_integrity = inspect_asset_outputs(output_dir)
        if not asset_integrity.is_complete:
            logger.debug(
                "cached_output_rejected",
                reason=(
                    "no_asset_manifest"
                    if not asset_integrity.manifest_present
                    else "asset_output_incomplete"
                ),
                output_dir=str(output_dir),
                manifest_present=asset_integrity.manifest_present,
                manifest_entries=asset_integrity.total_entries,
                missing_outputs=asset_integrity.missing_count,
                missing_output_samples=list(asset_integrity.missing_outputs),
            )
            return False

        return True

    def _run_validation_build(self, profile: Any, port: int) -> None:
        """
        Run a validation build in the foreground while server is already running.

        This validates cached content and triggers hot reload if stale.

        Args:
            profile: Build profile to use
            port: Server port for display
        """
        from bengal.orchestration.build.options import BuildOptions
        from bengal.server.live_reload import send_reload_payload

        show_building_indicator("Validating cache")

        build_opts = BuildOptions(
            profile=profile,
            incremental=True,
        )

        # RFC: Output Cache Architecture - Capture content hash baseline before build
        from bengal.server.reload_controller import controller

        if controller._use_content_hashes:
            controller.capture_content_hash_baseline(self.site.output_dir)
        else:
            controller.decide_and_update(self.site.output_dir)  # Set baseline (legacy)

        stats = self._run_build_via_executor(build_opts, "Validation build")
        display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))

        logger.debug(
            "validation_build_complete",
            pages_built=stats.total_pages,
            pages_rebuilt=stats.pages_rebuilt,
            duration_ms=stats.build_time_ms,
        )

        # Clear HTML cache after validation
        self._clear_html_cache_after_build()

        # Set active palette
        self._set_active_palette()

        # Initialize reload controller with post-build state
        self._init_reload_controller()

        # RFC: Output Cache Architecture - Use content-hash detection for accurate change counts
        if controller._use_content_hashes:
            decision = controller.decide_with_content_hashes(self.site.output_dir)
            # Report actual content changes, not regeneration noise
            actual_changes = decision.meaningful_change_count
        else:
            decision = controller.decide_and_update(self.site.output_dir)
            actual_changes = len(decision.changed_paths)

        if decision.action != "none":
            logger.info(
                "validation_found_stale_content",
                action=decision.action,
                reason=decision.reason,
                changed_count=actual_changes,
            )
            # Trigger hot reload
            send_reload_payload(decision.action, "cache-validation", decision.changed_paths)
            icons = get_icons()
            print(
                f"\n  {icons.success} Cache validated - {actual_changes} files updated, browser reloading..."
            )
        else:
            icons = get_icons()
            print(f"\n  {icons.success} Cache validated - content is fresh")

        # Start watcher after validation to avoid race; seed cache for reactive path
        if self.watch and hasattr(self, "_watcher_runner") and hasattr(self, "_build_trigger"):
            self._build_trigger.seed_content_hash_cache(list(self.site.pages))
            self._watcher_runner.start()
            logger.info("file_watcher_started", watch_dirs=self._get_watched_directories())

    def _run_build_via_executor(self, build_opts: Any, description: str = "Build") -> MinimalStats:
        """
        Run build in process-isolated subprocess for clean Ctrl+C shutdown.

        Uses BuildExecutor with ProcessPoolExecutor so the main process has no
        build ThreadPoolExecutors. When user presses Ctrl+C, normal sys.exit()
        works without "Exception ignored on threading shutdown" traceback.
        """
        from bengal.orchestration.stats import show_error
        from bengal.utils.observability.profile import BuildProfile

        profile_str = (
            build_opts.profile.value
            if isinstance(build_opts.profile, BuildProfile)
            else str(build_opts.profile)
        )
        incremental = build_opts.incremental if build_opts.incremental is not None else True
        request = BuildRequest(
            site_root=str(self.site.root_path),
            incremental=incremental,
            profile=profile_str,
            version_scope=self.version_scope,
        )
        executor = BuildExecutor(max_workers=1)
        try:
            result = executor.submit(request, timeout=600.0)
            if not result.success:
                msg = result.error_message or "Build failed"
                show_error(f"{description} failed: {msg}", show_art=False)
                raise BengalServerError(msg, code=ErrorCode.S003)
            return MinimalStats.from_build_result(result, incremental=incremental)
        finally:
            executor.shutdown(wait=True)

    def _clear_html_cache_after_build(self) -> None:
        """Clear HTML injection cache after a build to ensure fresh pages."""
        try:
            with LiveReloadMixin._html_cache_lock:
                LiveReloadMixin._html_cache.clear()
            logger.debug("html_cache_cleared_after_build")
        except Exception as e:
            logger.debug("html_cache_clear_failed", error=str(e))

    def _set_active_palette(self) -> None:
        """Set active palette for rebuilding page styling."""
        try:
            default_palette = self.site.config.get("default_palette")
            if default_palette:
                build_state.set_active_palette(default_palette)
                logger.debug("rebuilding_page_palette_set", palette=default_palette)
        except Exception:  # noqa: S110
            pass

    def _init_reload_controller(self) -> None:
        """Initialize reload controller with configuration."""
        try:
            from bengal.server.reload_controller import controller
            from bengal.server.utils import get_dev_config

            cfg = self.site.config or {}

            try:
                min_interval = get_dev_config(cfg, "reload", "min_notify_interval_ms", default=300)
                controller.set_min_notify_interval_ms(int(min_interval))
            except Exception as e:
                logger.warning("reload_config_min_interval_failed", error=str(e))

            try:
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

            logger.debug("reload_controller_initialized")
        except Exception as e:
            logger.warning("reload_controller_init_failed", error=str(e))

    def _prepare_dev_config(self) -> bool:
        """
        Prepare site configuration for development mode.

        Sets development-specific defaults:
        - Disables asset fingerprinting (stable URLs for hot reload)
        - Disables minification (faster rebuilds, easier debugging)
        - Forces atomic writes (required for double-buffered output)
        - Clears baseurl (serves from root '/' not subdirectory)

        When baseurl is cleared, also clears the build cache to prevent
        stale baseurl values from persisting in cached data.

        Returns:
            True if baseurl was cleared (requires clean rebuild)
        """
        cfg = self.site.config

        # Development defaults for faster iteration
        cfg["fingerprint_assets"] = False  # Stable CSS/JS filenames
        cfg.setdefault("minify_assets", False)  # Faster builds

        # Force atomic writes (temp+rename) for two reasons:
        # 1. Breaks hardlinks during double-buffered builds so the active buffer
        #    is never corrupted when the staging buffer is written.
        # 2. Prevents torn reads if the browser fetches during a write.
        build_settings = cfg.get("build")
        if isinstance(build_settings, dict):
            build_settings["fast_writes"] = False
        else:
            cfg["build"] = {"fast_writes": False}
        # Disable search index preloading in dev to avoid background index.json fetches
        cfg.setdefault("search_preload", "off")
        # Disable social cards in dev (OG images not needed, saves ~30s on large sites)
        # Force disable even if enabled in config - social cards only matter for production
        social_cards = cfg.get("social_cards")
        if isinstance(social_cards, dict):
            social_cards["enabled"] = False
        else:
            cfg["social_cards"] = {"enabled": False}

        # Clear template bytecode cache to ensure fresh template compilation
        # This prevents stale bytecode from previous builds causing "stuck" templates
        clear_template_cache(self.site.root_path, logger)

        # Clear baseurl for local development
        # This prevents 404s since dev server serves from '/' not '/baseurl'
        baseurl_value = (cfg.get("baseurl", "") or "").strip()
        # "/" is equivalent to no baseurl (dev server serves from root)
        if not baseurl_value or baseurl_value == "/":
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

            assert bengal.__file__ is not None, "bengal module has no __file__"
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

        # Resolve to absolute paths for reliable watching (symlinks, monorepos,
        # editable installs). Filter to only existing directories.
        return [str(d.resolve()) for d in watch_dirs if d.exists()]

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
        build_trigger = BuildTrigger(
            site=self.site,
            host=self.host,
            port=actual_port,
            version_scope=self.version_scope,
            buffer_manager=self._buffer_manager,
        )

        # Create ignore filter from config using class method
        config = self.site.config or {}
        # Handle ConfigSection objects that need .raw for dict access
        raw = getattr(config, "raw", config)
        config_dict: dict[str, Any] = raw if isinstance(raw, dict) else {}
        ignore_filter = IgnoreFilter.from_config(config_dict, output_dir=self.site.output_dir)

        # Get watch directories (already resolved to absolute in _get_watched_directories)
        watch_dirs = [Path(d) for d in self._get_watched_directories()]

        # Also watch root for bengal.toml
        watch_dirs.append(self.site.root_path.resolve())

        # Force polling for reliable hot reload (macOS, symlinks, editable installs)
        from bengal.server.utils import get_dev_config

        force_polling_val = get_dev_config(config_dict, "watch", "force_polling", default=None)
        force_polling: bool | None = (
            force_polling_val if isinstance(force_polling_val, bool) else None
        )

        # Create watcher runner
        watcher_runner = WatcherRunner(
            paths=watch_dirs,
            ignore_filter=ignore_filter,
            on_changes=build_trigger.trigger_build,
            debounce_ms=300,
            force_polling=force_polling,
        )

        logger.debug(
            "watcher_created",
            watch_dirs=[str(p) for p in watch_dirs],
            force_polling=force_polling,
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
            addr_infos = socket.getaddrinfo(self.host, port, type=socket.SOCK_STREAM)
        except OSError:
            return False

        checked = False
        for family, socktype, proto, _canonname, sockaddr in addr_infos:
            try:
                with socket.socket(family, socktype, proto) as s:
                    s.bind(sockaddr)
                    checked = True
            except OSError:
                return False
        return checked

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
        raise BengalServerError(
            f"Could not find an available port in range "
            f"{start_port}-{start_port + max_attempts - 1}",
            code=ErrorCode.S001,
            suggestion=f"Kill processes using these ports: lsof -ti:{start_port}-{start_port + max_attempts - 1} | xargs kill",
        )

    def _check_stale_processes(self) -> None:
        """
        Check for and offer to clean up stale processes.

        Looks for a PID file from a previous Bengal server run. If found,
        verifies the process is actually a Bengal process and offers to
        terminate it gracefully.

        Also checks if the target port is currently held by a Bengal process,
        even if no PID file exists, providing a safety net for lost PID files.

        Raises:
            OSError: If stale process cannot be killed and user chooses not to continue
        """
        pid_file = PIDManager.get_pid_file(self.site.root_path)
        stale_pid = PIDManager.check_stale_pid(pid_file)

        # If no PID file, check if a Bengal process is already on our preferred port
        # This handles cases where the PID file was lost or we're restarting
        if not stale_pid:
            port_pid = PIDManager.get_process_on_port(self.port)
            if port_pid and PIDManager.is_bengal_process(port_pid):
                stale_pid = port_pid
                logger.info(
                    "bengal_process_found_on_port_without_pid_file",
                    pid=stale_pid,
                    port=self.port,
                )

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

            self._print_stale_process_panel(stale_pid, pid_file, is_holding_port)

            response = input("  Kill stale process? [Y/n]: ").strip().lower()
            should_kill = response in ("", "y", "yes")

            if should_kill:
                if PIDManager.kill_stale_process(stale_pid):
                    CLIOutput().success("Stale process terminated")
                    logger.info("stale_process_killed", pid=stale_pid)
                    time.sleep(1)  # Give OS time to release resources
                else:
                    CLIOutput().error("Failed to kill process")
                    CLIOutput().info(f"Try manually: kill {stale_pid}")
                    logger.error(
                        "stale_process_kill_failed",
                        error_code=ErrorCode.S002.name,
                        pid=stale_pid,
                        user_action="kill_manually",
                    )
                    raise BengalServerError(
                        f"Cannot start: stale process {stale_pid} is still running",
                        code=ErrorCode.S002,
                        suggestion=f"Kill the stale process manually: kill {stale_pid}",
                    )
            else:
                CLIOutput().warning("Continuing anyway (may encounter port conflicts)...")
                logger.warning(
                    "stale_process_ignored", pid=stale_pid, user_choice="continue_anyway"
                )

    def _create_server(self) -> ServerBackend:
        """
        Create HTTP server backend (does not start it).

        Resolves port (with fallback if auto_port) and creates a
        PounceBackend serving the Bengal ASGI app.

        Returns:
            ServerBackend instance (PounceBackend)

        Raises:
            OSError: If no available port can be found
        """
        output_dir = self.site.output_dir
        logger.debug("serving_directory", path=str(output_dir))

        actual_port = self.port

        if not self._is_port_available(self.port):
            logger.warning("port_unavailable", port=self.port, auto_port_enabled=self.auto_port)

            icons = get_icons()
            if self.auto_port:
                try:
                    actual_port = self._find_available_port(self.port + 1)
                    print(f"{icons.warning} Port {self.port} is already in use")
                    print(f"{icons.arrow} Using port {actual_port} instead")
                    logger.info("port_fallback", requested_port=self.port, actual_port=actual_port)
                except (OSError, BengalServerError) as e:
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
                        error_code=ErrorCode.S001.name,
                        requested_port=self.port,
                        search_range=(self.port + 1, self.port + 10),
                        user_action="check_running_processes",
                    )
                    raise BengalServerError(
                        f"Port {self.port} is already in use",
                        code=ErrorCode.S001,
                        suggestion=f"Use --port {self.port + 100} or kill the process: lsof -ti:{self.port} | xargs kill",
                    ) from e
            else:
                print(f"❌ Port {self.port} is already in use.")
                print("\nTo fix this issue:")
                print(f"  1. Stop the process using port {self.port}, or")
                print("  2. Specify a different port with: bengal serve --port <PORT>")
                print(f"  3. Find the blocking process with: lsof -ti:{self.port}")
                logger.error(
                    "port_unavailable_no_fallback",
                    error_code=ErrorCode.S001.name,
                    port=self.port,
                    user_action="specify_different_port",
                )
                raise BengalServerError(
                    f"Port {self.port} is already in use",
                    code=ErrorCode.S001,
                    suggestion=f"Use --port {self.port + 100} or kill the process: lsof -ti:{self.port} | xargs kill",
                )

        self._request_callback_holder: list = [None]
        # Pass the buffer manager's active_dir property as a callable so
        # the ASGI app resolves the serving directory per-request, enabling
        # atomic buffer swaps without re-creating the app.
        backend = create_pounce_backend(
            host=self.host,
            port=actual_port,
            output_dir=lambda: self._buffer_manager.active_dir,
            build_in_progress=build_state.get_build_in_progress,
            active_palette=build_state.get_active_palette,
            request_callback=lambda: self._request_callback_holder[0],
        )

        logger.info(
            "http_server_created",
            host=self.host,
            port=actual_port,
            handler_class="PounceBackend",
            threaded=True,
        )

        return backend

    def _print_server_error(self, exc: BaseException, port: int) -> None:
        """Print a friendly error message for server startup failures (no traceback)."""
        import sys

        icons = get_icons()

        if isinstance(exc, OSError):
            err = exc
            if (
                getattr(err, "errno", None) == errno.EADDRINUSE
                or "already in use" in str(err).lower()
            ):
                lines = [
                    f"{icons.error} Port {self.host}:{port} is already in use.",
                    "",
                    "To fix:",
                    f"  1. Stop the process: lsof -ti:{port} | xargs kill",
                    f"  2. Use another port: bengal serve --port {port + 1}",
                ]
            elif getattr(err, "errno", None) == errno.EACCES:
                lines = [
                    f"{icons.error} Permission denied binding to {self.host}:{port}.",
                    "",
                    "Try a port > 1024 or run with elevated permissions.",
                ]
            else:
                lines = [f"{icons.error} {err}"]
        else:
            lines = [f"{icons.error} Server failed to start: {exc}"]

        sys.stderr.write("\n".join(lines) + "\n")
        sys.stderr.flush()

    def _print_stale_process_panel(
        self, stale_pid: int, pid_file: Path, is_holding_port: bool
    ) -> None:
        """Print a friendly message for stale process detection."""
        import sys

        icons = get_icons()

        lines = [
            f"{icons.warning} Found stale Bengal server process (PID {stale_pid})",
        ]
        if is_holding_port:
            lines.append(f"   This process is holding port {self.port}")
        lines.extend(
            [
                f"   PID file: {pid_file}",
                "",
                "To recover:",
                f"   kill {stale_pid}",
                "",
                "Or remove stale PID file and kill manually:",
                f"   rm {pid_file}",
                f"   lsof -nP -iTCP:{self.port} -sTCP:LISTEN -t | xargs kill",
            ]
        )

        sys.stderr.write("\n".join(lines) + "\n")
        sys.stderr.flush()

    def _print_startup_message(self, port: int, serve_first: bool = False) -> None:
        """Print server startup message."""
        import sys

        icons = get_icons()
        url = f"http://{self.host}:{port}/"

        try:
            serving_path = str(self.site.output_dir.relative_to(self.site.root_path))
        except ValueError:
            serving_path = str(self.site.output_dir)

        lines = [
            "",
            "ᓚᘏᗢ Bengal Dev Server",
            "",
            f"   →  Local:   {url}",
            f"   →  Serving: {serving_path}",
            "",
        ]

        if serve_first:
            lines.append(
                f"   {icons.success}  Serving cached content (validating in background...)"
            )

        if self.watch:
            lines.append(f"   {icons.info}  File watching enabled (auto-reload on changes)")
        else:
            lines.append(f"   {icons.info}  File watching disabled")

        from bengal.utils.dx import collect_hints

        hints = collect_hints("serve", host=self.host, max_hints=1)
        if hints:
            lines.append(f"   → {hints[0].message}")

        lines.append("")
        lines.append("   Press Ctrl+C to stop")
        lines.append("")

        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()

        # Request log header
        from datetime import datetime

        cli = CLIOutput()

        def _log_request(method: str, path: str, status: int, _duration_ms: float) -> None:
            ts = datetime.now().strftime("%H:%M:%S")
            cli.http_request(ts, method, str(status), path, is_asset=False)

        if hasattr(self, "_request_callback_holder"):
            self._request_callback_holder[0] = _log_request

        cli.request_log_header()

    def _wait_for_server_ready(self, port: int, timeout_sec: float = 10.0) -> bool:
        """
        Poll until the server responds with 200 or timeout.

        Ensures we don't open the browser before the site is ready to serve.

        Args:
            port: Server port
            timeout_sec: Max seconds to wait

        Returns:
            True if server responded with 200, False on timeout
        """
        url = f"http://{self.host}:{port}/"
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            try:
                with urlopen(Request(url), timeout=2) as resp:
                    if resp.status in (200, 304):
                        return True
            except OSError as e:
                logger.debug("server_readiness_poll_failed", port=port, error=str(e))
            time.sleep(0.15)
        return False

    def _open_browser_when_ready(self, port: int) -> None:
        """
        Open browser only after server is ready to serve.

        Waits for server to respond with 200 before opening, preventing
        the unstyled flash (FOUC) when the browser loads before assets exist.

        Args:
            port: Port number to include in the URL
        """
        import webbrowser

        def open_browser() -> None:
            try:
                if self._wait_for_server_ready(port):
                    webbrowser.open(f"http://{self.host}:{port}/")
                    logger.debug("browser_opened", url=f"http://{self.host}:{port}/")
                else:
                    logger.warning(
                        "browser_open_skipped",
                        reason="server_not_ready",
                        url=f"http://{self.host}:{port}/",
                    )
            except Exception as exc:
                logger.warning("browser_open_failed", error=str(exc))
                CLIOutput().warning("Could not open browser")

        threading.Thread(target=open_browser, daemon=True).start()
