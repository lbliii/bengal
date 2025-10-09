"""
Live reload functionality for the dev server.

Provides Server-Sent Events (SSE) endpoint and HTML injection for hot reload.
"""

import os
import queue
import threading
from typing import List

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Global list to track SSE clients for live reload
_sse_clients: List[queue.Queue] = []
_sse_clients_lock = threading.Lock()


# Live reload script to inject into HTML pages
LIVE_RELOAD_SCRIPT = """
<script>
(function() {
    // Bengal Live Reload
    const source = new EventSource('/__bengal_reload__');
    
    source.onmessage = function(event) {
        if (event.data === 'reload') {
            console.log('🔄 Bengal: Reloading page...');
            location.reload();
        }
    };
    
    source.onerror = function(error) {
        console.log('⚠️  Bengal: Live reload disconnected');
        source.close();
    };
    
    console.log('🚀 Bengal: Live reload connected');
})();
</script>
"""


class LiveReloadMixin:
    """
    Mixin class providing live reload functionality via SSE.
    
    This class is designed to be mixed into an HTTP request handler.
    """
    
    def handle_sse(self) -> None:
        """Handle Server-Sent Events endpoint for live reload."""
        # Create a queue for this client
        client_queue: queue.Queue = queue.Queue()
        client_addr = getattr(self, 'client_address', ['unknown', 0])[0]
        
        # Register client
        with _sse_clients_lock:
            _sse_clients.append(client_queue)
            client_count = len(_sse_clients)
        
        logger.info("sse_client_connected",
                   client_address=client_addr,
                   total_clients=client_count)
        
        try:
            # Send SSE headers
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            
            keepalive_count = 0
            message_count = 0
            
            # Keep connection alive and send messages from queue
            while True:
                try:
                    # Wait for message with timeout to allow checking if connection is still alive
                    message = client_queue.get(timeout=30)
                    self.wfile.write(f'data: {message}\n\n'.encode())
                    self.wfile.flush()
                    message_count += 1
                    
                    logger.debug("sse_message_sent",
                                client_address=client_addr,
                                message=message,
                                message_count=message_count)
                except queue.Empty:
                    # Send a comment to keep connection alive
                    self.wfile.write(b': keepalive\n\n')
                    self.wfile.flush()
                    keepalive_count += 1
                except (BrokenPipeError, ConnectionResetError) as e:
                    # Client disconnected
                    logger.debug("sse_client_disconnected_error",
                                client_address=client_addr,
                                error_type=type(e).__name__,
                                messages_sent=message_count,
                                keepalives_sent=keepalive_count)
                    break
        finally:
            # Unregister client
            with _sse_clients_lock:
                if client_queue in _sse_clients:
                    _sse_clients.remove(client_queue)
                remaining_clients = len(_sse_clients)
            
            logger.info("sse_client_disconnected",
                       client_address=client_addr,
                       messages_sent=message_count,
                       keepalives_sent=keepalive_count,
                       remaining_clients=remaining_clients)
    
    def serve_html_with_live_reload(self) -> bool:
        """Serve HTML file with live reload script injected."""
        # Resolve the actual file path
        path = self.translate_path(self.path)
        
        # If path is a directory, look for index.html
        if os.path.isdir(path):
            for index in ['index.html', 'index.htm']:
                index_path = os.path.join(path, index)
                if os.path.exists(index_path):
                    path = index_path
                    break
        
        # If not an HTML file at this point, return False to indicate we didn't handle it
        if not path.endswith('.html') and not path.endswith('.htm'):
            return False
        
        try:
            # Read the HTML file
            with open(path, 'rb') as f:
                content = f.read()
            
            # Try to inject script before </body> or </html> (case-insensitive)
            html_str = content.decode('utf-8')
            script_injected = False
            
            # Try to inject before </body> (case-insensitive)
            html_lower = html_str.lower()
            body_idx = html_lower.rfind('</body>')
            if body_idx != -1:
                html_str = html_str[:body_idx] + LIVE_RELOAD_SCRIPT + html_str[body_idx:]
                script_injected = True
            # Fallback: inject before </html> (case-insensitive)
            elif html_lower.rfind('</html>') != -1:
                html_idx = html_lower.rfind('</html>')
                html_str = html_str[:html_idx] + LIVE_RELOAD_SCRIPT + html_str[html_idx:]
                script_injected = True
            
            # If we couldn't inject, just append it
            if not script_injected:
                html_str += LIVE_RELOAD_SCRIPT
            
            # Send response with injected script
            modified_content = html_str.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(modified_content)))
            self.end_headers()
            self.wfile.write(modified_content)
            return True
            
        except (FileNotFoundError, IsADirectoryError):
            self.send_error(404, "File not found")
            return True
        except Exception as e:
            # If anything goes wrong, log it and return False to fall back to default handling
            logger.warning("live_reload_injection_failed",
                          path=self.path,
                          error=str(e),
                          error_type=type(e).__name__)
            return False


def notify_clients_reload() -> None:
    """Notify all connected SSE clients to reload."""
    with _sse_clients_lock:
        client_count = len(_sse_clients)
        notified_count = 0
        failed_count = 0
        
        # Send reload message to all connected clients
        for client_queue in _sse_clients:
            try:
                client_queue.put_nowait('reload')
                notified_count += 1
            except queue.Full:
                # Queue is full, skip this client
                failed_count += 1
        
        logger.info("reload_notification_sent",
                   total_clients=client_count,
                   notified=notified_count,
                   failed=failed_count)

