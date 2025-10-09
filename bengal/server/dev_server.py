"""
Development server with file watching and hot reload.
"""

from pathlib import Path
from typing import Any
import socketserver
import socket
import threading
import time
import os
from watchdog.observers import Observer

from bengal.utils.build_stats import display_build_stats, show_building_indicator
from bengal.utils.logger import get_logger
from bengal.server.resource_manager import ResourceManager
from bengal.server.pid_manager import PIDManager
from bengal.server.request_handler import BengalRequestHandler
from bengal.server.build_handler import BuildHandler

logger = get_logger(__name__)


class DevServer:
    """
    Development server with file watching and auto-rebuild.
    """
    
    def __init__(self, site: Any, host: str = "localhost", port: int = 5173, watch: bool = True, auto_port: bool = True, open_browser: bool = False) -> None:
        """
        Initialize the dev server.
        
        Args:
            site: Site instance
            host: Server host
            port: Server port
            watch: Whether to watch for file changes
            auto_port: Whether to automatically find an available port if the specified one is in use
            open_browser: Whether to automatically open the browser
        """
        self.site = site
        self.host = host
        self.port = port
        self.watch = watch
        self.auto_port = auto_port
        self.open_browser = open_browser
    
    def start(self) -> None:
        """Start the development server with robust resource cleanup."""
        logger.info("dev_server_starting",
                   host=self.host,
                   port=self.port,
                   watch_enabled=self.watch,
                   auto_port=self.auto_port,
                   open_browser=self.open_browser,
                   site_root=str(self.site.root_path))
        
        # Check for and handle stale processes
        self._check_stale_processes()
        
        # Use ResourceManager for comprehensive cleanup handling
        with ResourceManager() as rm:
            # Always do an initial build to ensure site is up to date
            show_building_indicator("Initial build")
            stats = self.site.build()
            display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))
            
            logger.debug("initial_build_complete",
                        pages_built=stats.total_pages,
                        duration_ms=stats.build_time_ms)
            
            # Create and register PID file for this process
            pid_file = PIDManager.get_pid_file(self.site.root_path)
            PIDManager.write_pid_file(pid_file)
            rm.register_pidfile(pid_file)
            
            # Start file watcher if enabled
            if self.watch:
                observer = self._create_observer()
                rm.register_observer(observer)
                observer.start()
                logger.info("file_watcher_started",
                           watch_dirs=self._get_watched_directories())
            
            # Create and start HTTP server
            httpd, actual_port = self._create_server()
            rm.register_server(httpd)
            
            # Open browser if requested
            if self.open_browser:
                self._open_browser_delayed(actual_port)
                logger.debug("browser_opening",
                            url=f'http://{self.host}:{actual_port}/')
            
            # Print startup message (keep for UX)
            self._print_startup_message(actual_port)
            
            logger.info("dev_server_started",
                       host=self.host,
                       port=actual_port,
                       output_dir=str(self.site.output_dir),
                       watch_enabled=self.watch)
            
            # Run until interrupted (cleanup happens automatically via ResourceManager)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                # KeyboardInterrupt caught by serve_forever (backup to signal handler)
                print("\n  👋 Shutting down server...")
                logger.info("dev_server_shutdown", reason="keyboard_interrupt")
            # ResourceManager cleanup happens automatically via __exit__
    
    def _get_watched_directories(self) -> list:
        """Get list of directories that will be watched."""
        watch_dirs = [
            self.site.root_path / "content",
            self.site.root_path / "assets",
            self.site.root_path / "templates",
            self.site.root_path / "data",
        ]
        
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
        
        # Filter to only existing directories
        return [str(d) for d in watch_dirs if d.exists()]
    
    def _create_observer(self) -> Observer:
        """Create file system observer (does not start it)."""
        event_handler = BuildHandler(self.site)
        observer = Observer()
        
        # Get all watch directories
        watch_dirs = self._get_watched_directories()
        
        for watch_dir in watch_dirs:
            observer.schedule(event_handler, watch_dir, recursive=True)
            logger.debug("watching_directory", path=watch_dir, recursive=True)
        
        # Watch bengal.toml for config changes
        # Use non-recursive watching for the root directory to only catch bengal.toml
        observer.schedule(event_handler, str(self.site.root_path), recursive=False)
        logger.debug("watching_directory", 
                    path=str(self.site.root_path), 
                    recursive=False,
                    reason="config_file_changes")
        
        return observer
    
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
        raise OSError(f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}")
    
    def _check_stale_processes(self) -> None:
        """Check for and offer to clean up stale processes."""
        pid_file = PIDManager.get_pid_file(self.site.root_path)
        stale_pid = PIDManager.check_stale_pid(pid_file)
        
        if stale_pid:
            port_pid = PIDManager.get_process_on_port(self.port)
            is_holding_port = port_pid == stale_pid
            
            logger.warning("stale_process_detected",
                          pid=stale_pid,
                          pid_file=str(pid_file),
                          holding_port=is_holding_port,
                          port=self.port if is_holding_port else None)
            
            print(f"\n⚠️  Found stale Bengal server process (PID {stale_pid})")
            
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
                should_kill = response in ('', 'y', 'yes')
            
            if should_kill:
                if PIDManager.kill_stale_process(stale_pid):
                    print("  ✅ Stale process terminated")
                    logger.info("stale_process_killed", pid=stale_pid)
                    time.sleep(1)  # Give OS time to release resources
                else:
                    print(f"  ❌ Failed to kill process")
                    print(f"     Try manually: kill {stale_pid}")
                    logger.error("stale_process_kill_failed",
                                pid=stale_pid,
                                user_action="kill_manually")
                    raise OSError(f"Cannot start: stale process {stale_pid} is still running")
            else:
                print("  Continuing anyway (may encounter port conflicts)...")
                logger.warning("stale_process_ignored",
                              pid=stale_pid,
                              user_choice="continue_anyway")
    
    def _create_server(self):
        """Create HTTP server (does not start it)."""
        # Change to output directory
        os.chdir(self.site.output_dir)
        logger.debug("changed_directory", path=str(self.site.output_dir))
        
        # Determine port to use
        actual_port = self.port
        
        # Check if requested port is available
        if not self._is_port_available(self.port):
            logger.warning("port_unavailable", 
                          port=self.port,
                          auto_port_enabled=self.auto_port)
            
            if self.auto_port:
                # Try to find an available port
                try:
                    actual_port = self._find_available_port(self.port + 1)
                    print(f"⚠️  Port {self.port} is already in use")
                    print(f"🔄 Using port {actual_port} instead")
                    logger.info("port_fallback",
                               requested_port=self.port,
                               actual_port=actual_port)
                except OSError as e:
                    print(f"❌ Port {self.port} is already in use and no alternative ports are available.")
                    print(f"\nTo fix this issue:")
                    print(f"  1. Stop the process using port {self.port}, or")
                    print(f"  2. Specify a different port with: bengal serve --port <PORT>")
                    print(f"  3. Find the blocking process with: lsof -ti:{self.port}")
                    logger.error("no_ports_available",
                                requested_port=self.port,
                                search_range=(self.port + 1, self.port + 10),
                                user_action="check_running_processes")
                    raise OSError(f"Port {self.port} is already in use") from e
            else:
                print(f"❌ Port {self.port} is already in use.")
                print(f"\nTo fix this issue:")
                print(f"  1. Stop the process using port {self.port}, or")
                print(f"  2. Specify a different port with: bengal serve --port <PORT>")
                print(f"  3. Find the blocking process with: lsof -ti:{self.port}")
                logger.error("port_unavailable_no_fallback",
                            port=self.port,
                            user_action="specify_different_port")
                raise OSError(f"Port {self.port} is already in use")
        
        # Allow address reuse to prevent "address already in use" errors on restart
        socketserver.TCPServer.allow_reuse_address = True
        
        # Create server (don't use context manager - ResourceManager handles cleanup)
        httpd = socketserver.TCPServer((self.host, actual_port), BengalRequestHandler)
        
        logger.info("http_server_created",
                   host=self.host,
                   port=actual_port,
                   handler_class="BengalRequestHandler")
        
        return httpd, actual_port
    
    def _print_startup_message(self, port: int) -> None:
        """Print server startup message."""
        print(f"\n╭{'─' * 78}╮")
        print(f"│ 🚀 \033[1mBengal Dev Server\033[0m{' ' * 59}│")
        print(f"│{' ' * 78}│")
        print(f"│   \033[36m➜\033[0m  Local:   \033[1mhttp://{self.host}:{port}/\033[0m{' ' * (52 - len(self.host) - len(str(port)))}│")
        print(f"│   \033[90m➜\033[0m  Serving: {str(self.site.output_dir)[:60]}{' ' * max(0, 60 - len(str(self.site.output_dir)))}│")
        print(f"│{' ' * 78}│")
        
        # Show watching status
        if self.watch:
            print(f"│   \033[33m⚠\033[0m  File watching enabled (auto-reload on changes){' ' * 27}│")
            print(f"│   \033[90m   (Live reload disabled - refresh browser manually)\033[0m{' ' * 24}│")
        else:
            print(f"│   \033[90m○\033[0m  File watching disabled{' ' * 48}│")
        
        print(f"│{' ' * 78}│")
        print(f"│   \033[90mPress Ctrl+C to stop (or twice to force quit)\033[0m{' ' * 37}│")
        print(f"╰{'─' * 78}╯\n")
        print(f"  \033[90m{'TIME':8} │ {'METHOD':6} │ {'STATUS':3} │ PATH\033[0m")
        print(f"  \033[90m{'─' * 8}─┼─{'─' * 6}─┼─{'─' * 3}─┼─{'─' * 60}\033[0m")
    
    def _open_browser_delayed(self, port: int) -> None:
        """Open browser after a short delay (in background thread)."""
        import webbrowser
        def open_browser():
            time.sleep(0.5)  # Give server time to start
            webbrowser.open(f'http://{self.host}:{port}/')
        threading.Thread(target=open_browser, daemon=True).start()
