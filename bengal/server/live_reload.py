"""
Live reload functionality for the dev server.

Provides Server-Sent Events (SSE) endpoint and HTML injection for hot reload.

Architecture:
- SSE Endpoint (/__bengal_reload__): Maintains persistent connections to clients
- Live Reload Script: Injected into HTML pages to connect to SSE endpoint
- Reload Notifications: Broadcast to all clients when build completes using a
  global generation counter and condition variable (no per-client queues)

SSE Protocol:
    Client: EventSource('/__bengal_reload__')
    Server (init): retry: 2000\n\n  (client waits 2s before reconnect after disconnect)
    Server (events): data: {json payload}|reload\n\n  (triggers reload/css update)
    Server (idle): : keepalive\n\n  (sent on interval; ignored by client)

Dev behavior:
- Keepalive interval is configurable via env BENGAL_SSE_KEEPALIVE_SECS (default 15s).
- On new connections/reconnects, last_seen_generation is initialized to the current
  generation so we do not replay the last reload event to the client.
"""

import json
import os
import threading

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Global reload generation and condition to wake clients
_reload_generation: int = 0
_last_action: str = "reload"
_reload_condition = threading.Condition()


# Diagnostic: allow suppressing reload events via environment variable
def _reload_events_disabled() -> bool:
    try:
        val = (os.environ.get("BENGAL_DISABLE_RELOAD_EVENTS", "") or "").strip().lower()
        return val in ("1", "true", "yes", "on")
    except Exception:
        return False


# Live reload script to inject into HTML pages
LIVE_RELOAD_SCRIPT = r"""
<script>
(function() {
    // Bengal Live Reload
    let backoffMs = 1000;
    const maxBackoffMs = 10000;

    function connect() {
        const source = new EventSource('/__bengal_reload__');
        // Ensure the connection is closed on page unload/navigation to free server threads quickly
        const closeSource = () => { try { source.close(); } catch (e) {} };
        window.addEventListener('beforeunload', closeSource, { once: true });
        window.addEventListener('pagehide', closeSource, { once: true });

        source.onmessage = function(event) {
            let payload = null;
            try { payload = JSON.parse(event.data); } catch (e) {}

            const action = payload && payload.action ? payload.action : event.data;
            const changedPaths = (payload && payload.changedPaths) || [];
            const reason = (payload && payload.reason) || '';

            if (action === 'reload') {
                console.log('🔄 Bengal: Reloading page...');
                // Save scroll position before reload
                sessionStorage.setItem('bengal_scroll_x', window.scrollX.toString());
                sessionStorage.setItem('bengal_scroll_y', window.scrollY.toString());
                location.reload();
            } else if (action === 'reload-css') {
                console.log('🎨 Bengal: Reloading CSS...', reason || '', changedPaths);
                const links = document.querySelectorAll('link[rel="stylesheet"]');
                const now = Date.now();
                links.forEach(link => {
                    const href = link.getAttribute('href');
                    if (!href) return;
                    const url = new URL(href, window.location.origin);
                    // If targeted list provided, only reload those
                    if (changedPaths.length > 0) {
                        const path = url.pathname.replace(/^\//, '');
                        if (!changedPaths.includes(path)) return;
                    }
                    // Bust cache with a version param
                    url.searchParams.set('v', now.toString());
                    // Replace the link to trigger reload
                    const newLink = link.cloneNode();
                    newLink.href = url.toString();
                    newLink.onload = () => {
                        // Remove old link after new CSS loads
                        link.remove();
                    };
                    link.parentNode.insertBefore(newLink, link.nextSibling);
                });
            } else if (action === 'reload-page') {
                console.log('📄 Bengal: Reloading current page...');
                // Save scroll position before reload
                sessionStorage.setItem('bengal_scroll_x', window.scrollX.toString());
                sessionStorage.setItem('bengal_scroll_y', window.scrollY.toString());
                location.reload();
            }
        };

        // Restore scroll position after page load
        window.addEventListener('load', function() {
            const scrollX = sessionStorage.getItem('bengal_scroll_x');
            const scrollY = sessionStorage.getItem('bengal_scroll_y');
            if (scrollX !== null && scrollY !== null) {
                window.scrollTo(parseInt(scrollX, 10), parseInt(scrollY, 10));
                // Clear stored position after restoring
                sessionStorage.removeItem('bengal_scroll_x');
                sessionStorage.removeItem('bengal_scroll_y');
            }
        });

        source.onopen = function() {
            backoffMs = 1000; // reset on successful connection
            console.log('🚀 Bengal: Live reload connected');
        };

        source.onerror = function() {
            console.log('⚠️  Bengal: Live reload disconnected - retrying soon');
            try { source.close(); } catch (e) {}
            setTimeout(connect, backoffMs);
            backoffMs = Math.min(maxBackoffMs, Math.floor(backoffMs * 1.5));
        };
    }

    connect();
})();
</script>
"""


class LiveReloadMixin:
    """
    Mixin class providing live reload functionality via SSE.

    This class is designed to be mixed into an HTTP request handler.
    It provides two key methods:
    - handle_sse(): Handles the SSE endpoint (/__bengal_reload__)
    - serve_html_with_live_reload(): Injects the live reload script into HTML

    The SSE connection remains open, sending keepalive comments roughly every
    9 seconds and "reload" messages (or JSON payloads) when the site is rebuilt.

    Example:
        class CustomHandler(LiveReloadMixin, http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/__bengal_reload__':
                    self.handle_sse()
                elif self.serve_html_with_live_reload():
                    return  # HTML served with script injected
                else:
                    super().do_GET()  # Default file serving
    """

    def handle_sse(self) -> None:
        """
        Handle Server-Sent Events endpoint for live reload.

        Maintains a persistent HTTP connection and sends SSE messages:
        - Keepalive comments (: keepalive) every 30 seconds
        - Reload events (data: reload) when site is rebuilt

        The connection remains open until the client disconnects or an error occurs.

        Note:
            This method blocks until the client disconnects
        """
        client_addr = getattr(self, "client_address", ["unknown", 0])[0]
        logger.info("sse_client_connected", client_address=client_addr)

        try:
            # Send SSE headers
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            # Prevent intermediaries from buffering or closing the stream
            # no-transform avoids proxy transformations; private disables shared caches
            self.send_header(
                "Cache-Control",
                "no-store, no-cache, must-revalidate, max-age=0, private, no-transform",
            )
            self.send_header("Connection", "keep-alive")
            # Explicitly disable Nginx/Apache proxy buffering behaviors if present
            self.send_header("X-Accel-Buffering", "no")
            # Allow any origin during local development (dev server only)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # Advise client on retry delay and send an opening comment to start the stream
            self.wfile.write(b"retry: 2000\n\n")
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()

            keepalive_count = 0
            message_count = 0
            # IMPORTANT: Initialize last_seen_generation to current to avoid replaying
            # the last action on new connections/reconnects
            with _reload_condition:
                last_seen_generation = _reload_generation

            # Keepalive interval (seconds). Default 15s; override via env BENGAL_SSE_KEEPALIVE_SECS
            try:
                ka_env = os.environ.get("BENGAL_SSE_KEEPALIVE_SECS", "15").strip()
                keepalive_interval = max(5, min(120, int(ka_env)))
            except Exception:
                keepalive_interval = 15

            logger.info("sse_stream_started", keepalive_interval_secs=keepalive_interval)

            # Keep connection alive and send messages when generation increments
            while True:
                try:
                    with _reload_condition:
                        # Wait up to keepalive_interval for a generation change, then send keepalive
                        _reload_condition.wait(timeout=keepalive_interval)
                        current_generation = _reload_generation

                    if current_generation != last_seen_generation:
                        # Send the last action (e.g., reload, reload-css, reload-page)
                        self.wfile.write(f"data: {_last_action}\n\n".encode())
                        self.wfile.flush()
                        message_count += 1
                        last_seen_generation = current_generation
                        logger.debug(
                            "sse_message_sent",
                            client_address=client_addr,
                            event_data=_last_action,
                            message_count=message_count,
                        )
                    else:
                        # Send keepalive comment (interval-based) to keep the connection alive
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        keepalive_count += 1
                        logger.debug(
                            "sse_keepalive_sent",
                            client_address=client_addr,
                            keepalives_sent=keepalive_count,
                        )
                except (BrokenPipeError, ConnectionResetError) as e:
                    # Client disconnected
                    logger.debug(
                        "sse_client_disconnected_error",
                        client_address=client_addr,
                        error_type=type(e).__name__,
                        messages_sent=message_count,
                        keepalives_sent=keepalive_count,
                    )
                    break
        finally:
            logger.info(
                "sse_client_disconnected",
                client_address=client_addr,
                messages_sent=message_count,
                keepalives_sent=keepalive_count,
            )

    def serve_html_with_live_reload(self) -> bool:
        """
        Serve HTML file with live reload script injected (with caching).

        Uses file modification time caching to avoid re-reading/re-injecting
        unchanged files during rapid navigation.

        Returns:
            True if HTML was served (with or without injection), False if not HTML

        Note:
            Returns False for non-HTML files so the caller can handle them
        """
        # Resolve the actual file path
        path = self.translate_path(self.path)

        # If path is a directory, look for index.html
        if os.path.isdir(path):
            for index in ["index.html", "index.htm"]:
                index_path = os.path.join(path, index)
                if os.path.exists(index_path):
                    path = index_path
                    break

        # If not an HTML file at this point, return False to indicate we didn't handle it
        if not path.endswith(".html") and not path.endswith(".htm"):
            return False

        try:
            # Get file modification time for cache key
            mtime = os.path.getmtime(path)
            cache_key = (path, mtime)

            # Check cache (defined in BengalRequestHandler)
            from bengal.server.request_handler import BengalRequestHandler

            # Fast path: try cache under lock
            with BengalRequestHandler._html_cache_lock:
                cached = BengalRequestHandler._html_cache.get(cache_key)
            if cached is not None:
                modified_content = cached
                logger.debug("html_cache_hit", path=path)
            else:
                # Cache miss - read and inject outside lock
                with open(path, "rb") as f:
                    content = f.read()

                # Inject script before </body> or </html> (case-insensitive)
                # Optimize: Search bytes directly instead of converting entire file to string
                script_bytes = LIVE_RELOAD_SCRIPT.encode("utf-8")

                # Try to find </body> (case-insensitive search in bytes)
                body_tag_lower = b"</body>"
                body_tag_upper = b"</BODY>"
                body_idx = content.rfind(body_tag_lower)
                if body_idx == -1:
                    body_idx = content.rfind(body_tag_upper)

                if body_idx != -1:
                    # Inject before </body>
                    modified_content = content[:body_idx] + script_bytes + content[body_idx:]
                else:
                    # Fallback: try </html>
                    html_tag_lower = b"</html>"
                    html_tag_upper = b"</HTML>"
                    html_idx = content.rfind(html_tag_lower)
                    if html_idx == -1:
                        html_idx = content.rfind(html_tag_upper)

                    if html_idx != -1:
                        modified_content = content[:html_idx] + script_bytes + content[html_idx:]
                    else:
                        # Last resort: append at end
                        modified_content = content + script_bytes

                # Store in cache under lock (with size control)
                with BengalRequestHandler._html_cache_lock:
                    # Double-check if another thread populated it while we were working
                    if cache_key not in BengalRequestHandler._html_cache:
                        BengalRequestHandler._html_cache[cache_key] = modified_content
                        # Limit cache size (simple FIFO eviction)
                        if (
                            len(BengalRequestHandler._html_cache)
                            > BengalRequestHandler._html_cache_max_size
                        ):
                            first_key = next(iter(BengalRequestHandler._html_cache))
                            del BengalRequestHandler._html_cache[first_key]
                    cache_size = len(BengalRequestHandler._html_cache)
                logger.debug("html_cache_miss", path=path, cache_size=cache_size)

            # Send response with injected script
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(modified_content)))
            # Strongly discourage caching injected HTML in dev
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.end_headers()
            self.wfile.write(modified_content)
            return True

        except (FileNotFoundError, IsADirectoryError):
            self.send_error(404, "File not found")
            return True
        except Exception as e:
            # If anything goes wrong, log it and return False to fall back to default handling
            logger.warning(
                "live_reload_injection_failed",
                path=self.path,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False


def notify_clients_reload() -> None:
    """
    Notify all connected SSE clients to reload.

    Sends a "reload" message to all connected clients via their queues.
    Clients with full queues are skipped to avoid blocking.

    This is called after a successful build to trigger browser refresh.

    Note:
        This is thread-safe and can be called from the build handler thread
    """
    global _reload_generation
    if _reload_events_disabled():
        logger.info("reload_notification_suppressed", reason="env_BENGAL_DISABLE_RELOAD_EVENTS")
        return
    with _reload_condition:
        _reload_generation += 1
        _reload_condition.notify_all()
    logger.info("reload_notification_sent", generation=_reload_generation)


def send_reload_payload(action: str, reason: str, changed_paths: list[str]) -> None:
    """
    Send a structured JSON payload to connected SSE clients.

    Args:
        action: 'reload' | 'reload-css' | 'reload-page'
        reason: short machine-readable reason string
        changed_paths: list of changed output paths (relative to output dir)
    """
    global _reload_generation, _last_action
    if _reload_events_disabled():
        logger.info(
            "reload_notification_suppressed",
            reason="env_BENGAL_DISABLE_RELOAD_EVENTS",
            action=action,
        )
        return
    try:
        payload = json.dumps(
            {
                "action": action,
                "reason": reason,
                "changedPaths": changed_paths,
                "generation": _reload_generation + 1,
            }
        )
    except Exception:
        # Fallback to simple action string on serialization failure
        payload = action

    with _reload_condition:
        _last_action = payload
        _reload_generation += 1
        _reload_condition.notify_all()

    logger.info(
        "reload_notification_sent_structured",
        action=action,
        reason=reason,
        changed=len(changed_paths),
        generation=_reload_generation,
    )


def set_reload_action(action: str) -> None:
    """
    Set the next reload action for SSE clients.

    Actions:
        - 'reload'      : full page reload
        - 'reload-css'  : CSS hot-reload (no page refresh)
        - 'reload-page' : explicit page reload (alias of 'reload')
    """
    global _last_action
    if action not in ("reload", "reload-css", "reload-page"):
        action = "reload"
    _last_action = action
    logger.debug("reload_action_set", action=_last_action)
