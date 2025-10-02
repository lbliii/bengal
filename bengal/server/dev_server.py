"""
Development server with file watching and hot reload.
"""

from pathlib import Path
from typing import Any
import http.server
import socketserver
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


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
            print(f"\n📝 Change detected: {event.src_path}")
            print("🔨 Rebuilding site...")
            
            try:
                self.site.build(parallel=False)
                print("✅ Rebuild complete!\n")
            except Exception as e:
                print(f"❌ Build failed: {e}\n")
            finally:
                self.building = False


class DevServer:
    """
    Development server with file watching and auto-rebuild.
    """
    
    def __init__(self, site: Any, host: str = "localhost", port: int = 8000, watch: bool = True) -> None:
        """
        Initialize the dev server.
        
        Args:
            site: Site instance
            host: Server host
            port: Server port
            watch: Whether to watch for file changes
        """
        self.site = site
        self.host = host
        self.port = port
        self.watch = watch
        self.observer: Any = None
    
    def start(self) -> None:
        """Start the development server."""
        # Ensure site is built
        if not self.site.output_dir.exists():
            print("Building site before starting server...")
            self.site.build()
        
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
    
    def _start_http_server(self) -> None:
        """Start HTTP server."""
        # Change to output directory
        import os
        os.chdir(self.site.output_dir)
        
        # Create server
        Handler = http.server.SimpleHTTPRequestHandler
        
        with socketserver.TCPServer((self.host, self.port), Handler) as httpd:
            print(f"\n🚀 Bengal dev server running at http://{self.host}:{self.port}/")
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

