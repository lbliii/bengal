"""
Development server with file watching and hot reload.
"""

from pathlib import Path
from typing import Any
import http.server
import socketserver
import socket
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from bengal.utils.build_stats import display_build_stats, show_building_indicator, show_error


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
            print(f"\n📝 Change detected: {Path(event.src_path).name}")
            show_building_indicator("Rebuilding")
            
            try:
                stats = self.site.build(parallel=False)
                display_build_stats(stats, show_art=False)
            except Exception as e:
                show_error(f"Build failed: {e}", show_art=False)
            finally:
                self.building = False


class DevServer:
    """
    Development server with file watching and auto-rebuild.
    """
    
    def __init__(self, site: Any, host: str = "localhost", port: int = 8000, watch: bool = True, auto_port: bool = True) -> None:
        """
        Initialize the dev server.
        
        Args:
            site: Site instance
            host: Server host
            port: Server port
            watch: Whether to watch for file changes
            auto_port: Whether to automatically find an available port if the specified one is in use
        """
        self.site = site
        self.host = host
        self.port = port
        self.watch = watch
        self.auto_port = auto_port
        self.observer: Any = None
    
    def start(self) -> None:
        """Start the development server."""
        # Always do an initial build to ensure site is up to date
        show_building_indicator("Initial build")
        stats = self.site.build()
        display_build_stats(stats, show_art=False)
        
        # Start file watcher if enabled
        if self.watch:
            self._start_watcher()
        
        # Start HTTP server
        self._start_http_server()
    
    def _start_watcher(self) -> None:
        """Start file system watcher."""
        event_handler = BuildHandler(self.site)
        self.observer = Observer()
        
        # Watch content and assets directories
        watch_dirs = [
            self.site.root_path / "content",
            self.site.root_path / "assets",
            self.site.root_path / "templates",
        ]
        
        for watch_dir in watch_dirs:
            if watch_dir.exists():
                self.observer.schedule(event_handler, str(watch_dir), recursive=True)
        
        self.observer.start()
        print(f"👀 Watching for file changes...")
    
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
    
    def _start_http_server(self) -> None:
        """Start HTTP server."""
        # Change to output directory
        import os
        os.chdir(self.site.output_dir)
        
        # Create server
        Handler = http.server.SimpleHTTPRequestHandler
        
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
        
        with socketserver.TCPServer((self.host, actual_port), Handler) as httpd:
            print(f"\n🚀 Bengal dev server running at http://{self.host}:{actual_port}/")
            print(f"📁 Serving from: {self.site.output_dir}")
            print("Press Ctrl+C to stop\n")
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n\n👋 Shutting down server...")
                if self.observer:
                    self.observer.stop()
                    self.observer.join()
                print("✅ Server stopped")

