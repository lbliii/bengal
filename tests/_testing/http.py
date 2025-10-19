"""HTTP server utilities for testing.

Provides ephemeral HTTP servers for link/asset testing.
"""

import http.server
import socket
import socketserver
import threading
import time
from functools import partial

import pytest


def wait_for_port(port: int, host: str = "localhost", timeout: float = 5.0) -> None:
    """Wait until a port is listening or timeout.
    
    Args:
        port: Port number to check
        host: Hostname to check (default: localhost)
        timeout: Maximum seconds to wait
        
    Raises:
        TimeoutError: If port not listening after timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return  # Port is listening
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(0.1)
    raise TimeoutError(f"Port {port} not listening after {timeout}s")


@pytest.fixture
def http_server():
    """Ephemeral HTTP server for testing links/assets.
    
    Usage:
        def test_external_links(http_server, tmp_path):
            # Create some test files
            fixtures = tmp_path / "fixtures"
            fixtures.mkdir()
            (fixtures / "test.html").write_text("<h1>Test</h1>")
            
            # Start server
            base_url = http_server.start(fixtures)
            
            # Use in tests
            assert base_url.startswith("http://localhost:")
            # ... build site with links to base_url ...
    """
    class TestHTTPServer:
        def __init__(self):
            self.server = None
            self.thread = None
            self.port = None

        def start(self, directory, port=0):
            """Start server on ephemeral port.
            
            Args:
                directory: Directory to serve files from
                port: Port to bind (0 = ephemeral)
                
            Returns:
                Base URL of server (e.g., "http://localhost:12345")
            """
            if self.server is not None:
                self.stop()
            handler = partial(
                http.server.SimpleHTTPRequestHandler,
                directory=str(directory)
            )
            self.server = socketserver.ThreadingTCPServer(("localhost", port), handler)
            self.port = self.server.server_address[1]

            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()

            # Wait until listening
            wait_for_port(self.port, timeout=5)

            return f"http://localhost:{self.port}"

        def stop(self):
            """Stop the server gracefully."""
            if self.server:
                self.server.shutdown()
                if self.thread:
                    self.thread.join(timeout=5)
                self.server.server_close()
                self.server = None
                self.thread = None

    server = TestHTTPServer()
    yield server
    server.stop()

