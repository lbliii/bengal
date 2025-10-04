"""
Development server with file watching and hot reload.
"""

from pathlib import Path
from typing import Any
import http.server
import socketserver
import socket
import threading
import time
import os
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from bengal.utils.build_stats import display_build_stats, show_building_indicator, show_error
from bengal.server.resource_manager import ResourceManager
from bengal.server.pid_manager import PIDManager


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler with beautiful, minimal logging.
    """
    
    # Suppress default server version header
    server_version = "Bengal/1.0"
    sys_version = ""
    
    def log_message(self, format: str, *args: Any) -> None:
        """
        Log an HTTP request with beautiful formatting.
        
        Args:
            format: Format string
            *args: Format arguments
        """
        # Skip certain requests that clutter the logs
        path = args[0] if args else ""
        status_code = args[1] if len(args) > 1 else ""
        
        # Skip these noisy requests
        skip_patterns = [
            "/.well-known/",
            "/favicon.ico",
            "/favicon.png",
        ]
        
        for pattern in skip_patterns:
            if pattern in path:
                return
        
        # Get request method and path
        parts = path.split()
        method = parts[0] if parts else "GET"
        request_path = parts[1] if len(parts) > 1 else "/"
        
        # Skip assets unless they're errors or initial loads
        is_asset = any(request_path.startswith(prefix) for prefix in ['/assets/', '/static/'])
        is_cached = status_code == "304"
        is_success = status_code.startswith("2")
        
        # Only show assets if they're errors, not cached successful loads
        if is_asset and (is_cached or is_success):
            return
        
        # Skip 304s entirely - they're just cache hits
        if is_cached:
            return
        
        # Colorize status codes
        status_color = self._get_status_color(status_code)
        method_color = self._get_method_color(method)
        
        # Format path nicely
        if len(request_path) > 60:
            request_path = request_path[:57] + "..."
        
        # Get timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Add emoji indicators for different types
        indicator = ""
        if not is_asset:
            if status_code.startswith("2"):
                indicator = "📄 "  # Page load
            elif status_code.startswith("4"):
                indicator = "❌ "  # Error
        
        # Beautiful output
        print(f"  {timestamp} │ {method_color}{method:6}{self._reset()} │ {status_color}{status_code:3}{self._reset()} │ {indicator}{request_path}")
    
    def _get_status_color(self, status: str) -> str:
        """Get ANSI color code for status code."""
        try:
            code = int(status)
            if 200 <= code < 300:
                return "\033[32m"  # Green
            elif code == 304:
                return "\033[90m"  # Gray
            elif 300 <= code < 400:
                return "\033[36m"  # Cyan
            elif 400 <= code < 500:
                return "\033[33m"  # Yellow
            else:
                return "\033[31m"  # Red
        except (ValueError, TypeError):
            return ""
    
    def _get_method_color(self, method: str) -> str:
        """Get ANSI color code for HTTP method."""
        colors = {
            "GET": "\033[36m",     # Cyan
            "POST": "\033[33m",    # Yellow
            "PUT": "\033[35m",     # Magenta
            "DELETE": "\033[31m",  # Red
            "PATCH": "\033[35m",   # Magenta
        }
        return colors.get(method, "\033[37m")  # Default white
    
    def _reset(self) -> str:
        """Get ANSI reset code."""
        return "\033[0m"
    
    def log_error(self, format: str, *args: Any) -> None:
        """
        Suppress error logging - we handle everything in log_message.
        
        Args:
            format: Format string
            *args: Format arguments
        """
        # All error logging is handled in log_message with proper filtering
        # This prevents duplicate error messages
        pass


class BuildHandler(FileSystemEventHandler):
    """
    File system event handler that triggers site rebuild.
    """
    
    def __init__(self, site: Any) -> None:
        """
        Initialize the build handler.
        
        Args:
            site: Site instance
        """
        self.site = site
        self.building = False
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events.
        
        Args:
            event: File system event
        """
        if event.is_directory:
            return
        
        # Skip files in output directory
        try:
            Path(event.src_path).relative_to(self.site.output_dir)
            return
        except ValueError:
            pass
        
        # Trigger rebuild
        if not self.building:
            self.building = True
            timestamp = datetime.now().strftime("%H:%M:%S")
            file_name = Path(event.src_path).name
            print(f"\n  \033[90m{'─' * 78}\033[0m")
            print(f"  {timestamp} │ \033[33m📝 File changed:\033[0m {file_name}")
            print(f"  \033[90m{'─' * 78}\033[0m\n")
            show_building_indicator("Rebuilding")
            
            try:
                stats = self.site.build(parallel=False)
                display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))
                print(f"\n  \033[90m{'TIME':8} │ {'METHOD':6} │ {'STATUS':3} │ PATH\033[0m")
                print(f"  \033[90m{'─' * 8}─┼─{'─' * 6}─┼─{'─' * 3}─┼─{'─' * 60}\033[0m")
            except Exception as e:
                show_error(f"Build failed: {e}", show_art=False)
                print(f"\n  \033[90m{'TIME':8} │ {'METHOD':6} │ {'STATUS':3} │ PATH\033[0m")
                print(f"  \033[90m{'─' * 8}─┼─{'─' * 6}─┼─{'─' * 3}─┼─{'─' * 60}\033[0m")
            finally:
                self.building = False


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
        # Check for and handle stale processes
        self._check_stale_processes()
        
        # Use ResourceManager for comprehensive cleanup handling
        with ResourceManager() as rm:
            # Always do an initial build to ensure site is up to date
            show_building_indicator("Initial build")
            stats = self.site.build()
            display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))
            
            # Create and register PID file for this process
            pid_file = PIDManager.get_pid_file(self.site.root_path)
            PIDManager.write_pid_file(pid_file)
            rm.register_pidfile(pid_file)
            
            # Start file watcher if enabled
            if self.watch:
                observer = self._create_observer()
                rm.register_observer(observer)
                observer.start()
            
            # Create and start HTTP server
            httpd, actual_port = self._create_server()
            rm.register_server(httpd)
            
            # Open browser if requested
            if self.open_browser:
                self._open_browser_delayed(actual_port)
            
            # Print startup message
            self._print_startup_message(actual_port)
            
            # Run until interrupted (cleanup happens automatically via ResourceManager)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                # KeyboardInterrupt caught by serve_forever (backup to signal handler)
                print("\n  👋 Shutting down server...")
            # ResourceManager cleanup happens automatically via __exit__
    
    def _create_observer(self) -> Observer:
        """Create file system observer (does not start it)."""
        event_handler = BuildHandler(self.site)
        observer = Observer()
        
        # Watch content and assets directories
        watch_dirs = [
            self.site.root_path / "content",
            self.site.root_path / "assets",
            self.site.root_path / "templates",
        ]
        
        for watch_dir in watch_dirs:
            if watch_dir.exists():
                observer.schedule(event_handler, str(watch_dir), recursive=True)
        
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
            print(f"\n⚠️  Found stale Bengal server process (PID {stale_pid})")
            
            # Check if it's holding our port
            port_pid = PIDManager.get_process_on_port(self.port)
            if port_pid == stale_pid:
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
                    time.sleep(1)  # Give OS time to release resources
                else:
                    print(f"  ❌ Failed to kill process")
                    print(f"     Try manually: kill {stale_pid}")
                    raise OSError(f"Cannot start: stale process {stale_pid} is still running")
            else:
                print("  Continuing anyway (may encounter port conflicts)...")
    
    def _create_server(self):
        """Create HTTP server (does not start it)."""
        # Change to output directory
        os.chdir(self.site.output_dir)
        
        # Create server with our custom handler
        Handler = QuietHTTPRequestHandler
        
        # Determine port to use
        actual_port = self.port
        
        # Check if requested port is available
        if not self._is_port_available(self.port):
            if self.auto_port:
                # Try to find an available port
                try:
                    actual_port = self._find_available_port(self.port + 1)
                    print(f"⚠️  Port {self.port} is already in use")
                    print(f"🔄 Using port {actual_port} instead")
                except OSError as e:
                    print(f"❌ Port {self.port} is already in use and no alternative ports are available.")
                    print(f"\nTo fix this issue:")
                    print(f"  1. Stop the process using port {self.port}, or")
                    print(f"  2. Specify a different port with: bengal serve --port <PORT>")
                    print(f"  3. Find the blocking process with: lsof -ti:{self.port}")
                    raise OSError(f"Port {self.port} is already in use") from e
            else:
                print(f"❌ Port {self.port} is already in use.")
                print(f"\nTo fix this issue:")
                print(f"  1. Stop the process using port {self.port}, or")
                print(f"  2. Specify a different port with: bengal serve --port <PORT>")
                print(f"  3. Find the blocking process with: lsof -ti:{self.port}")
                raise OSError(f"Port {self.port} is already in use")
        
        # Allow address reuse to prevent "address already in use" errors on restart
        socketserver.TCPServer.allow_reuse_address = True
        
        # Create server (don't use context manager - ResourceManager handles cleanup)
        httpd = socketserver.TCPServer((self.host, actual_port), Handler)
        
        return httpd, actual_port
    
    def _print_startup_message(self, port: int) -> None:
        """Print server startup message."""
        print(f"\n╭{'─' * 78}╮")
        print(f"│ 🚀 \033[1mBengal Dev Server\033[0m{' ' * 59}│")
        print(f"│{' ' * 78}│")
        print(f"│   \033[36m➜\033[0m  Local:   \033[1mhttp://{self.host}:{port}/\033[0m{' ' * (52 - len(self.host) - len(str(port)))}│")
        print(f"│   \033[90m➜\033[0m  Serving: {str(self.site.output_dir)[:60]}{' ' * max(0, 60 - len(str(self.site.output_dir)))}│")
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

