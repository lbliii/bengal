"""
LiveReloadMixin: SSE handling and HTML injection for HTTP request handlers.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from io import BufferedIOBase
from pathlib import Path
from typing import ClassVar, Protocol

from bengal.errors import ErrorCode
from bengal.utils.observability.logger import get_logger

from .injection import inject_live_reload_into_response
from .script import LIVE_RELOAD_SCRIPT
from .sse import _get_keepalive_interval, run_sse_loop

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class HtmlCacheKey:
    """Cache key for HTML injection (path + mtime)."""

    path: str
    mtime: float


@dataclass(frozen=True, slots=True)
class AssetCacheEntry:
    """Cached asset (content + content type)."""

    content: bytes
    content_type: str


class HTTPHandlerProtocol(Protocol):
    """Protocol for HTTP request handler methods used by LiveReloadMixin."""

    path: str
    wfile: BufferedIOBase
    _html_cache: dict[HtmlCacheKey, bytes]
    _html_cache_max_size: int
    _html_cache_lock: threading.Lock

    def send_response(self, code: int, message: str | None = None) -> None: ...
    def send_header(self, keyword: str, value: str) -> None: ...
    def end_headers(self) -> None: ...
    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None: ...
    def translate_path(self, path: str) -> str: ...


class LiveReloadMixin:
    """
    Mixin class providing SSE-based live reload for HTTP request handlers.

    Designed to be mixed into an HTTP request handler (before SimpleHTTPRequestHandler
    in MRO) to add live reload capabilities. Provides SSE endpoint handling and
    automatic script injection into HTML responses.
    """

    path: str
    client_address: tuple[str, int]
    wfile: BufferedIOBase

    _html_cache: ClassVar[dict[HtmlCacheKey, bytes]] = {}
    _html_cache_max_size = 50
    _html_cache_lock = threading.Lock()

    _asset_cache: ClassVar[dict[str, AssetCacheEntry]] = {}
    _asset_cache_max_size = 30
    _asset_cache_lock = threading.Lock()

    def handle_sse(self: HTTPHandlerProtocol) -> None:
        """Handle Server-Sent Events endpoint for live reload."""
        client_addr = getattr(self, "client_address", ["unknown", 0])[0]
        logger.info("sse_client_connected", client_address=client_addr)

        message_count = 0
        keepalive_count = 0

        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header(
                "Cache-Control",
                "no-store, no-cache, must-revalidate, max-age=0, private, no-transform",
            )
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            def write_sse(chunk: bytes) -> None:
                self.wfile.write(chunk)
                self.wfile.flush()

            logger.info(
                "sse_stream_started",
                keepalive_interval_secs=_get_keepalive_interval(),
            )

            try:
                message_count, keepalive_count = run_sse_loop(write_sse)
            except (BrokenPipeError, ConnectionResetError) as exc:
                logger.debug(
                    "sse_client_disconnected_error",
                    error_code=ErrorCode.S004.name,
                    client_address=client_addr,
                    error_type=type(exc).__name__,
                    messages_sent=message_count,
                    keepalives_sent=keepalive_count,
                )
        finally:
            logger.info(
                "sse_client_disconnected",
                client_address=client_addr,
                messages_sent=message_count,
                keepalives_sent=keepalive_count,
            )

    def serve_html_with_live_reload(self: HTTPHandlerProtocol) -> bool:
        """Serve HTML file with live reload script injected (with caching)."""
        path = self.translate_path(self.path)

        if path is None:
            return False

        path_obj = Path(path)
        if path_obj.is_dir():
            for index in ["index.html", "index.htm"]:
                index_path = path_obj / index
                if index_path.exists():
                    path = str(index_path)
                    break

        if not path.endswith(".html") and not path.endswith(".htm"):
            return False

        try:
            mtime = Path(path).stat().st_mtime
            cache_key = HtmlCacheKey(path=path, mtime=mtime)
            cls = type(self)

            with cls._html_cache_lock:
                cached = cls._html_cache.get(cache_key)
            if cached is not None:
                modified_content = cached
                logger.debug("html_cache_hit", path=path)
            else:
                with open(path, "rb") as f:
                    content = f.read()

                from bengal.server.utils import find_html_injection_point

                script_bytes = LIVE_RELOAD_SCRIPT.encode("utf-8")
                injection_idx = find_html_injection_point(content)

                if injection_idx != -1:
                    modified_content = (
                        content[:injection_idx] + script_bytes + content[injection_idx:]
                    )
                else:
                    modified_content = content + script_bytes

                with cls._html_cache_lock:
                    if cache_key not in cls._html_cache:
                        cls._html_cache[cache_key] = modified_content
                        if len(cls._html_cache) > cls._html_cache_max_size:
                            first_key = next(iter(cls._html_cache))
                            del cls._html_cache[first_key]
                    cache_size = len(cls._html_cache)
                logger.debug("html_cache_miss", path=path, cache_size=cache_size)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(modified_content)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.end_headers()
            self.wfile.write(modified_content)
            return True

        except FileNotFoundError, IsADirectoryError:
            self.send_error(404, "File not found")
            return True
        except Exception as e:
            logger.warning(
                "live_reload_injection_failed",
                path=self.path,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def _inject_live_reload(self, response: bytes) -> bytes:
        """Inject live reload script into an HTTP response (test compatibility)."""
        return inject_live_reload_into_response(response)

    def _is_cacheable_asset(self, url_path: str) -> bool:
        """Check if a URL path is a cacheable asset (CSS/JS)."""
        path_lower = url_path.lower()
        if "/assets/" not in path_lower:
            return False
        return path_lower.endswith((".css", ".js"))

    def _get_content_type(self, url_path: str) -> str:
        """Get content type for a file path."""
        from bengal.server.utils import get_content_type

        return get_content_type(url_path)

    def serve_asset_with_cache(self: HTTPHandlerProtocol, build_in_progress: bool) -> bool:
        """Serve CSS/JS assets with build-aware caching."""
        if not self._is_cacheable_asset(self.path):
            return False

        cache_key = self.path.split("?")[0].lstrip("/")
        content_type = self._get_content_type(self.path)

        file_path = self.translate_path(self.path)
        if file_path is None:
            return False

        file_path_obj = Path(file_path)
        cls = type(self)

        content: bytes | None = None
        try:
            if file_path_obj.exists() and file_path_obj.is_file():
                content = file_path_obj.read_bytes()
        except (OSError, PermissionError) as e:
            logger.debug(
                "asset_read_failed_during_build",
                path=self.path,
                error=str(e),
                build_in_progress=build_in_progress,
            )
            content = None

        if content is not None:
            with cls._asset_cache_lock:
                cls._asset_cache[cache_key] = AssetCacheEntry(
                    content=content, content_type=content_type
                )
                if len(cls._asset_cache) > cls._asset_cache_max_size:
                    first_key = next(iter(cls._asset_cache))
                    del cls._asset_cache[first_key]

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(content)
            return True

        if build_in_progress:
            with cls._asset_cache_lock:
                cached = cls._asset_cache.get(cache_key)

            if cached is not None:
                cached_content, cached_type = cached.content, cached.content_type
                logger.info(
                    "asset_served_from_cache_during_build",
                    path=self.path,
                    cache_key=cache_key,
                    size=len(cached_content),
                )
                self.send_response(200)
                self.send_header("Content-Type", cached_type)
                self.send_header("Content-Length", str(len(cached_content)))
                self.send_header("X-Bengal-Cache", "hit-during-build")
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.end_headers()
                self.wfile.write(cached_content)
                return True

            logger.warning(
                "asset_unavailable_during_build_no_cache",
                path=self.path,
                cache_key=cache_key,
            )

        return False

    @classmethod
    def clear_asset_cache(cls) -> None:
        """Clear the asset cache."""
        with cls._asset_cache_lock:
            cache_size = len(cls._asset_cache)
            cls._asset_cache.clear()
        if cache_size > 0:
            logger.debug("asset_cache_cleared", entries=cache_size)
