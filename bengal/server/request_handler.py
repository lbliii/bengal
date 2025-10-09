"""
Custom HTTP request handler for the dev server.

Provides beautiful logging, custom 404 pages, and live reload support.
"""

from pathlib import Path
import http.server

from bengal.utils.logger import get_logger
from bengal.server.request_logger import RequestLogger
from bengal.server.live_reload import LiveReloadMixin

logger = get_logger(__name__)


class BengalRequestHandler(RequestLogger, LiveReloadMixin, http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler with beautiful logging, custom 404 page, and live reload support.
    
    This handler combines:
    - RequestLogger: Beautiful, minimal HTTP request logging
    - LiveReloadMixin: Server-Sent Events for hot reload
    - SimpleHTTPRequestHandler: Standard HTTP file serving
    """
    
    # Suppress default server version header
    server_version = "Bengal/1.0"
    sys_version = ""
    
    def handle(self) -> None:
        """Override handle to suppress BrokenPipeError tracebacks."""
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected - don't print traceback
            pass
    
    def do_GET(self) -> None:
        """
        Override GET handler to support SSE endpoint and inject live reload script.
        """
        # TEMPORARY: Disable live reload to debug navigation issues
        # Handle SSE endpoint for live reload
        # if self.path == '/__bengal_reload__':
        #     self.handle_sse()
        #     return
        
        # # For HTML files, inject live reload script
        # if self.path.endswith('.html') or self.path.endswith('/'):
        #     try:
        #         handled = self.serve_html_with_live_reload()
        #         if handled:
        #             return
        #         # If not handled, fall through to default handling
        #     except (BrokenPipeError, ConnectionResetError):
        #         # Client disconnected while we were serving - this is normal
        #         return
        
        # Default handling for other files
        super().do_GET()
    
    def send_error(self, code: int, message: str = None, explain: str = None) -> None:
        """
        Override send_error to serve custom 404 page.
        
        Args:
            code: HTTP error code
            message: Error message
            explain: Detailed explanation
        """
        # If it's a 404 error, try to serve custom 404.html
        if code == 404:
            custom_404_path = Path(self.directory) / "404.html"
            if custom_404_path.exists():
                try:
                    # Read custom 404 page
                    with open(custom_404_path, 'rb') as f:
                        content = f.read()
                    
                    # Send custom 404 response
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    
                    logger.debug("custom_404_served",
                                path=self.path,
                                custom_page_path=str(custom_404_path))
                    return
                except Exception as e:
                    # If custom 404 fails, fall back to default
                    logger.warning("custom_404_failed",
                                  path=self.path,
                                  custom_page_path=str(custom_404_path),
                                  error=str(e),
                                  error_type=type(e).__name__,
                                  action="using_default_404")
                    pass
        
        # Fall back to default error handling for non-404 or if custom 404 failed
        super().send_error(code, message, explain)

