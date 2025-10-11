from io import BytesIO
from unittest.mock import Mock, patch

from bengal.server.request_handler import BengalRequestHandler


def _make_handler():
    request = Mock()
    request.makefile = Mock(side_effect=lambda *a, **k: BytesIO(b""))
    with patch.object(BengalRequestHandler, 'handle'):
        handler = BengalRequestHandler(
            request=request,
            client_address=('127.0.0.1', 12345),
            server=Mock()
        )
    # Required by BaseHTTPRequestHandler logging
    handler.requestline = "GET / HTTP/1.1"
    handler.command = "GET"
    handler.request_version = "HTTP/1.1"
    return handler


def test_do_get_uses_mixin_for_html(monkeypatch):
    handler = _make_handler()
    handler.path = '/index.html'
    output = BytesIO()
    handler.wfile = output

    # Force mixin path to return True and write content
    def fake_serve_html_with_live_reload(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        body = b"<html><body>ok</body></html>"
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return True

    monkeypatch.setattr(BengalRequestHandler, 'serve_html_with_live_reload', fake_serve_html_with_live_reload, raising=True)

    handler.do_GET()
    data = output.getvalue()
    assert b'ok' in data


def test_do_get_falls_back_for_non_html(monkeypatch):
    handler = _make_handler()
    handler.path = '/assets/app.js'
    output = BytesIO()
    handler.wfile = output

    # Mixin says not HTML
    monkeypatch.setattr(BengalRequestHandler, 'serve_html_with_live_reload', lambda self: False, raising=True)

    # Base handler writes JS
    def fake_super_do_get(self):
        self.wfile.write(b'HTTP/1.1 200 OK\r\n')
        self.wfile.write(b'Content-Type: application/javascript\r\n\r\n')
        self.wfile.write(b'console.log("ok");')

    with patch('http.server.SimpleHTTPRequestHandler.do_GET', fake_super_do_get):
        handler.do_GET()
    
    data = output.getvalue()
    assert b'console.log("ok");' in data


