"""Production-like local preview server for completed Bengal output."""

from __future__ import annotations

import socket
import threading
import time
import webbrowser
from typing import TYPE_CHECKING
from urllib.request import Request, urlopen

from bengal.errors import BengalServerError, ErrorCode
from bengal.output import get_cli_output
from bengal.server.backend import create_pounce_preview_backend
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class PreviewServer:
    """Serve completed static output through Pounce without dev-server behavior."""

    def __init__(
        self,
        site: Site,
        *,
        host: str = "localhost",
        port: int = 5173,
        auto_port: bool = True,
        open_browser: bool = False,
    ) -> None:
        self.site = site
        self.host = host
        self.port = port
        self.auto_port = auto_port
        self.open_browser = open_browser

    def start(self) -> None:
        """Start the preview server and block until interrupted."""
        output_dir = self.site.output_dir
        if not output_dir.is_dir():
            raise BengalServerError(
                f"Preview output directory does not exist: {output_dir}",
                code=ErrorCode.S001,
                suggestion="Run `bengal preview` again so Bengal can build the site first.",
            )

        actual_port = self._resolve_port()
        backend = create_pounce_preview_backend(
            host=self.host,
            port=actual_port,
            output_dir=output_dir,
        )

        self._print_startup_message(actual_port)
        if self.open_browser:
            self._open_browser_when_ready(actual_port)

        logger.info(
            "preview_server_started",
            host=self.host,
            port=actual_port,
            output_dir=str(output_dir),
        )

        try:
            backend.start()
        except OSError as exc:
            raise BengalServerError(
                str(exc),
                code=ErrorCode.S001,
                suggestion=f"Use --port {actual_port + 1} or kill the process: lsof -ti:{actual_port} | xargs kill",
            ) from exc
        except KeyboardInterrupt:
            self._print_shutdown_message()
            logger.info("preview_server_shutdown", reason="keyboard_interrupt")
            backend.shutdown()

    def _resolve_port(self) -> int:
        if self._is_port_available(self.port):
            return self.port

        cli = get_cli_output()
        if not self.auto_port:
            cli.error(f"Port {self.port} is already in use.")
            cli.info(f"Use another port: bengal preview --port {self.port + 1}")
            raise BengalServerError(
                f"Port {self.port} is already in use",
                code=ErrorCode.S001,
                suggestion=f"Use --port {self.port + 1} or kill the process: lsof -ti:{self.port} | xargs kill",
            )

        actual_port = self._find_available_port(self.port + 1)
        cli.warning(f"Port {self.port} is already in use")
        cli.info(f"{cli.icons.arrow} Using port {actual_port} instead")
        return actual_port

    def _is_port_available(self, port: int) -> bool:
        try:
            addr_infos = socket.getaddrinfo(self.host, port, type=socket.SOCK_STREAM)
        except OSError:
            return False

        checked = False
        for family, socktype, proto, _canonname, sockaddr in addr_infos:
            try:
                with socket.socket(family, socktype, proto) as sock:
                    sock.bind(sockaddr)
                    checked = True
            except OSError:
                return False
        return checked

    def _find_available_port(self, start_port: int, max_attempts: int = 10) -> int:
        for port in range(start_port, start_port + max_attempts):
            if self._is_port_available(port):
                return port
        raise BengalServerError(
            f"Could not find an available port in range "
            f"{start_port}-{start_port + max_attempts - 1}",
            code=ErrorCode.S001,
            suggestion=f"Kill processes using these ports: lsof -ti:{start_port}-{start_port + max_attempts - 1} | xargs kill",
        )

    def _print_startup_message(self, port: int) -> None:
        cli = get_cli_output()
        cli.blank()
        cli.info("Preview server ready")
        cli.server_url_inline(host=self.host, port=port)
        cli.info("Serving completed output with Pounce static handling")
        cli.info("Press Ctrl+C to stop")
        cli.blank()

    def _print_shutdown_message(self) -> None:
        cli = get_cli_output()
        cli.blank()
        cli.info("Shutting down preview server...")

    def _open_browser_when_ready(self, port: int) -> None:
        def open_when_ready() -> None:
            url = f"http://{self.host}:{port}/"
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                try:
                    with urlopen(Request(url), timeout=2) as response:
                        if response.status in (200, 304):
                            webbrowser.open(url)
                            return
                except OSError:
                    time.sleep(0.2)

        threading.Thread(target=open_when_ready, daemon=True).start()
