"""
Server-Sent Events (SSE) live reload for Bengal dev server.

Provides browser hot reload functionality via SSE, enabling automatic page
refresh when site content changes. Supports full page reload and CSS-only
hot reload (no page refresh for style changes).

Features:
    - SSE endpoint (/__bengal_reload__) for push notifications
    - JavaScript client auto-injected into HTML pages
    - Full page reload on content/template changes
    - CSS-only hot reload (no flicker, preserves scroll position)
    - Scroll position preservation across reloads
    - Automatic reconnection with exponential backoff
    - Keepalive messages to prevent connection timeout
    - Generation counter for reliable event delivery

Classes:
    LiveReloadMixin: Mixin adding SSE handling to HTTP request handlers

Functions:
    notify_clients_reload: Trigger full page reload on all clients
    send_reload_payload: Send structured reload event with metadata
    set_reload_action: Set next reload type (reload, reload-css)
    inject_live_reload_into_response: Inject script into HTTP response bytes

Constants:
    LIVE_RELOAD_SCRIPT: JavaScript client code injected into HTML

Architecture:
    The live reload system uses a generation counter and condition variable
    for efficient event distribution (no per-client queues):

    BuildTrigger → notify_clients_reload() → increment generation
                                           → notify_all() on condition

    SSE Handler → wait on condition with timeout (keepalive interval)
               → if generation changed: send event
               → else: send keepalive comment

    Client Connection Lifecycle:
    1. EventSource connects to /__bengal_reload__
    2. Server sends retry interval and connected comment
    3. Client waits for events, handles reload/reload-css
    4. On disconnect: client reconnects with exponential backoff
    5. On reconnect: last_seen_generation = current (no replay)

SSE Protocol:
    Client → Server: GET /__bengal_reload__ (Accept: text/event-stream)
    Server → Client: retry: 2000\\n\\n (reconnect delay)
    Server → Client: : connected\\n\\n (comment, ignored by client)
    Server → Client: data: reload\\n\\n (triggers location.reload())
    Server → Client: data: {"action":"reload-css",...}\\n\\n (CSS hot reload)
    Server → Client: : keepalive\\n\\n (comment, keeps connection alive)

Environment Variables:
    BENGAL_SSE_KEEPALIVE_SECS: Keepalive interval in seconds (default: 15)
    BENGAL_DISABLE_RELOAD_EVENTS: Suppress reload events (diagnostic)

Related:
    - bengal/server/request_handler.py: Uses LiveReloadMixin
    - bengal/server/build_trigger.py: Calls notify_clients_reload
    - bengal/server/reload_controller.py: Decides reload type
"""

from __future__ import annotations

import json
import os
import threading
from io import BufferedIOBase
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# Global reload generation and condition to wake clients
_reload_generation: int = 0
_last_action: str = "reload"
_reload_sent_count: int = 0
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
    Mixin class providing SSE-based live reload for HTTP request handlers.

    Designed to be mixed into an HTTP request handler (before SimpleHTTPRequestHandler
    in MRO) to add live reload capabilities. Provides SSE endpoint handling and
    automatic script injection into HTML responses.

    Methods:
        handle_sse(): Handle the /__bengal_reload__ SSE endpoint
        serve_html_with_live_reload(): Serve HTML with injected reload script

    Type Declarations:
        The mixin declares types for attributes provided by SimpleHTTPRequestHandler
        (path, client_address, wfile) to help type checkers understand the interface.

    Important:
        Do NOT add stub methods for send_response, send_header, etc. Python MRO
        resolves this mixin BEFORE SimpleHTTPRequestHandler, so stubs would shadow
        the real implementations.

    Example:
        >>> class CustomHandler(LiveReloadMixin, SimpleHTTPRequestHandler):
        ...     def do_GET(self):
        ...         if self.path == '/__bengal_reload__':
        ...             self.handle_sse()
        ...         elif self.serve_html_with_live_reload():
        ...             return  # HTML served with script injected
        ...         else:
        ...             super().do_GET()  # Default file serving
    """

    # Type declarations for attributes provided by SimpleHTTPRequestHandler
    # These tell mypy what to expect when this mixin is used
    path: str
    client_address: tuple[str, int]
    wfile: BufferedIOBase

    # NOTE: Do NOT add stub methods here for send_response, send_header, etc.!
    # Python MRO resolves this mixin BEFORE SimpleHTTPRequestHandler, so stubs
    # would shadow the real implementations. The type checker can find the methods
    # from SimpleHTTPRequestHandler in the concrete class's MRO.

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
            except Exception as e:
                logger.debug("keepalive_env_parse_failed", error=str(e))
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

        # Guard against translate_path returning None (can happen if self.directory is None)
        if path is None:
            return False

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

    def _inject_live_reload(self, response: bytes) -> bytes:
        """
        Inject live reload script into an HTTP response.

        This method is provided for test compatibility and wraps the
        module-level inject_live_reload_into_response function.

        Args:
            response: Complete HTTP response (headers + body)

        Returns:
            Modified response with live reload script injected
        """
        return inject_live_reload_into_response(response)


def notify_clients_reload() -> None:
    """
    Notify all connected SSE clients to trigger a full page reload.

    Increments the global generation counter and wakes all SSE handlers
    waiting on the condition variable. Each handler will send a reload
    event to its connected client.

    Thread Safety:
        Safe to call from any thread (e.g., build handler thread).
        Uses condition variable for synchronization.

    Note:
        Does nothing if BENGAL_DISABLE_RELOAD_EVENTS environment variable
        is set (useful for diagnostic purposes).
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
    Send a structured JSON reload event to all connected SSE clients.

    Provides detailed reload information including the specific files that
    changed, enabling smarter client-side reload behavior (e.g., CSS-only
    reload targets specific stylesheets).

    Args:
        action: Reload type - 'reload' (full), 'reload-css' (stylesheets only),
                or 'reload-page' (explicit full reload)
        reason: Machine-readable reason (e.g., 'css-only', 'content-changed')
        changed_paths: Changed output paths relative to output directory.
                      For CSS reload, client uses these to target specific links.

    Example:
        >>> send_reload_payload(
        ...     action="reload-css",
        ...     reason="css-only",
        ...     changed_paths=["assets/style.css", "assets/print.css"]
        ... )
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
    except Exception as e:
        logger.warning(
            "reload_payload_serialization_failed",
            action=action,
            reason=reason,
            error=str(e),
        )
        # Fallback to simple action string on serialization failure
        payload = action

    global _reload_sent_count
    with _reload_condition:
        _last_action = payload
        _reload_generation += 1
        _reload_sent_count += 1
        _reload_condition.notify_all()

    logger.info(
        "reload_notification_sent_structured",
        action=action,
        reason=reason,
        changed=min(len(changed_paths), 5),
        changed_paths=changed_paths[:5],
        generation=_reload_generation,
        sent_count=_reload_sent_count,
    )


def set_reload_action(action: str) -> None:
    """
    Set the next reload action type for SSE clients.

    Updates the global action that will be sent with the next reload event.
    Used by ReloadController to specify CSS-only vs full page reload.

    Args:
        action: One of:
            - 'reload': Full page reload (default)
            - 'reload-css': CSS hot-reload without page refresh
            - 'reload-page': Explicit full reload (alias of 'reload')
            Invalid values are silently replaced with 'reload'.
    """
    global _last_action
    if action not in ("reload", "reload-css", "reload-page"):
        action = "reload"
    _last_action = action
    logger.debug("reload_action_set", action=_last_action)


def inject_live_reload_into_response(response: bytes) -> bytes:
    """
    Inject live reload script into an HTTP response body.

    Parses the HTTP response, locates </body> or </html> tag, and injects
    the LIVE_RELOAD_SCRIPT before it. Updates Content-Length header to
    reflect the new body size.

    Args:
        response: Complete HTTP response bytes (headers + body).
                 Must be formatted as: headers\\r\\n\\r\\nbody

    Returns:
        Modified response with script injected and Content-Length updated.
        Returns original response if injection fails or response is malformed.

    Note:
        This is a fallback method. The preferred approach is using
        LiveReloadMixin.serve_html_with_live_reload() which operates
        on file contents before HTTP response construction.
    """
    try:
        # HTTP response format: headers\r\n\r\nbody
        if b"\r\n\r\n" not in response:
            return response

        headers_end = response.index(b"\r\n\r\n")
        headers = response[:headers_end]
        body = response[headers_end + 4 :]

        # Inject script before </body> or </html> (case-insensitive)
        script_bytes = LIVE_RELOAD_SCRIPT.encode("utf-8")

        # Try to find </body> (case-insensitive search in bytes)
        body_tag_lower = b"</body>"
        body_tag_upper = b"</BODY>"
        body_idx = body.rfind(body_tag_lower)
        if body_idx == -1:
            body_idx = body.rfind(body_tag_upper)

        if body_idx != -1:
            # Inject before </body>
            modified_body = body[:body_idx] + script_bytes + body[body_idx:]
        else:
            # Fallback: try </html>
            html_tag_lower = b"</html>"
            html_tag_upper = b"</HTML>"
            html_idx = body.rfind(html_tag_lower)
            if html_idx == -1:
                html_idx = body.rfind(html_tag_upper)

            if html_idx != -1:
                modified_body = body[:html_idx] + script_bytes + body[html_idx:]
            else:
                # Last resort: append at end
                modified_body = body + script_bytes

        # Update Content-Length header if present
        headers_str = headers.decode("latin-1")
        header_lines = headers_str.split("\r\n")
        new_header_lines = []
        content_length_updated = False

        for line in header_lines:
            if line.lower().startswith("content-length:"):
                new_header_lines.append(f"Content-Length: {len(modified_body)}")
                content_length_updated = True
            else:
                new_header_lines.append(line)

        # If Content-Length wasn't present, add it
        if not content_length_updated:
            new_header_lines.append(f"Content-Length: {len(modified_body)}")

        new_headers = "\r\n".join(new_header_lines).encode("latin-1")
        return new_headers + b"\r\n\r\n" + modified_body

    except Exception as e:
        logger.warning(
            "live_reload_response_injection_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return response
