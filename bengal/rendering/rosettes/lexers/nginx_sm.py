"""Hand-written Nginx config lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    HashCommentsMixin,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["NginxStateMachineLexer"]


_DIRECTIVES: frozenset[str] = frozenset(
    {
        "accept_mutex",
        "access_log",
        "add_header",
        "alias",
        "allow",
        "auth_basic",
        "auth_basic_user_file",
        "autoindex",
        "break",
        "charset",
        "client_body_buffer_size",
        "client_body_temp_path",
        "client_body_timeout",
        "client_max_body_size",
        "default_type",
        "deny",
        "error_log",
        "error_page",
        "events",
        "expires",
        "fastcgi_buffer_size",
        "fastcgi_buffers",
        "fastcgi_param",
        "fastcgi_pass",
        "geo",
        "gzip",
        "gzip_comp_level",
        "gzip_disable",
        "gzip_min_length",
        "gzip_proxied",
        "gzip_types",
        "gzip_vary",
        "http",
        "if",
        "include",
        "index",
        "internal",
        "keepalive_timeout",
        "limit_conn",
        "limit_conn_zone",
        "limit_rate",
        "limit_req",
        "limit_req_zone",
        "listen",
        "location",
        "log_format",
        "map",
        "open_file_cache",
        "pid",
        "proxy_buffer_size",
        "proxy_buffers",
        "proxy_cache",
        "proxy_cache_path",
        "proxy_connect_timeout",
        "proxy_hide_header",
        "proxy_http_version",
        "proxy_pass",
        "proxy_read_timeout",
        "proxy_redirect",
        "proxy_send_timeout",
        "proxy_set_header",
        "resolver",
        "return",
        "rewrite",
        "root",
        "sendfile",
        "server",
        "server_name",
        "server_tokens",
        "set",
        "ssl",
        "ssl_certificate",
        "ssl_certificate_key",
        "ssl_ciphers",
        "ssl_prefer_server_ciphers",
        "ssl_protocols",
        "ssl_session_cache",
        "ssl_session_timeout",
        "tcp_nodelay",
        "tcp_nopush",
        "try_files",
        "types",
        "upstream",
        "user",
        "worker_connections",
        "worker_processes",
    }
)


class NginxStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Nginx configuration lexer."""

    name = "nginx"
    aliases = ()
    filenames = ("nginx.conf", "*.nginx", "*.nginxconf")
    mimetypes = ("text/x-nginx-conf",)

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = start

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace
            if char in " \t":
                start = pos
                while pos < length and code[pos] in " \t":
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], line, col)
                continue

            if char == "\n":
                yield Token(TokenType.WHITESPACE, char, line, col)
                pos += 1
                line += 1
                line_start = pos
                continue

            # Comments
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Strings
            if char in "\"'":
                start = pos
                quote = char
                pos += 1
                pos, _ = scan_string(code, pos, quote)
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Variables $var
            if char == "$":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                continue

            # Numbers (with units like 10m, 1h, 4k)
            if char in DIGITS:
                start = pos
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                if pos < length and code[pos] == ".":
                    pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                # Units
                if pos < length and code[pos] in "kmghKMGHsSmMdD":
                    pos += 1
                yield Token(TokenType.NUMBER_INTEGER, code[start:pos], line, col)
                continue

            # Regex (after ~ or ~*)
            if char == "~":
                start = pos
                pos += 1
                if pos < length and code[pos] == "*":
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                # The following pattern is regex
                while pos < length and code[pos] in " \t":
                    yield Token(TokenType.WHITESPACE, code[pos], line, pos - line_start + 1)
                    pos += 1
                if pos < length and code[pos] not in "{\n;":
                    regex_start = pos
                    while pos < length and code[pos] not in " \t\n{;":
                        pos += 1
                    yield Token(
                        TokenType.STRING_REGEX,
                        code[regex_start:pos],
                        line,
                        regex_start - line_start + 1,
                    )
                continue

            # Directives and values
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_-"):
                    pos += 1
                word = code[start:pos]
                if word in _DIRECTIVES:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in ("on", "off"):
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "=!<>":
                start = pos
                if pos + 1 < length and code[pos : pos + 2] in ("==", "!=", "<=", ">="):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Punctuation
            if char in "{}();,":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            # Paths and other text
            if char in "/.":
                start = pos
                while pos < length and code[pos] not in " \t\n{};":
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
