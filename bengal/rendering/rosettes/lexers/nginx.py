"""NGINX configuration lexer for Rosettes.

Thread-safe regex-based tokenizer for NGINX config files.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["NginxLexer"]

_DIRECTIVES = (
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
    "client_body_timeout",
    "client_header_buffer_size",
    "client_header_timeout",
    "client_max_body_size",
    "connection_pool_size",
    "daemon",
    "default_type",
    "deny",
    "directio",
    "error_log",
    "error_page",
    "etag",
    "events",
    "expires",
    "fastcgi_buffer_size",
    "fastcgi_buffers",
    "fastcgi_cache",
    "fastcgi_cache_key",
    "fastcgi_cache_path",
    "fastcgi_cache_valid",
    "fastcgi_connect_timeout",
    "fastcgi_hide_header",
    "fastcgi_index",
    "fastcgi_intercept_errors",
    "fastcgi_param",
    "fastcgi_pass",
    "fastcgi_read_timeout",
    "fastcgi_send_timeout",
    "fastcgi_split_path_info",
    "geo",
    "gzip",
    "gzip_buffers",
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
    "map_hash_bucket_size",
    "map_hash_max_size",
    "master_process",
    "multi_accept",
    "open_file_cache",
    "open_file_cache_errors",
    "open_file_cache_min_uses",
    "open_file_cache_valid",
    "output_buffers",
    "pid",
    "postpone_output",
    "proxy_buffer_size",
    "proxy_buffers",
    "proxy_cache",
    "proxy_cache_key",
    "proxy_cache_path",
    "proxy_cache_valid",
    "proxy_connect_timeout",
    "proxy_headers_hash_bucket_size",
    "proxy_headers_hash_max_size",
    "proxy_hide_header",
    "proxy_http_version",
    "proxy_intercept_errors",
    "proxy_pass",
    "proxy_pass_header",
    "proxy_read_timeout",
    "proxy_redirect",
    "proxy_send_timeout",
    "proxy_set_header",
    "proxy_temp_path",
    "recursive_error_pages",
    "request_pool_size",
    "reset_timedout_connection",
    "resolver",
    "resolver_timeout",
    "return",
    "rewrite",
    "root",
    "send_timeout",
    "sendfile",
    "sendfile_max_chunk",
    "server",
    "server_name",
    "server_names_hash_bucket_size",
    "server_names_hash_max_size",
    "server_tokens",
    "set",
    "split_clients",
    "ssl",
    "ssl_certificate",
    "ssl_certificate_key",
    "ssl_ciphers",
    "ssl_client_certificate",
    "ssl_crl",
    "ssl_dhparam",
    "ssl_ecdh_curve",
    "ssl_prefer_server_ciphers",
    "ssl_protocols",
    "ssl_session_cache",
    "ssl_session_timeout",
    "ssl_stapling",
    "ssl_stapling_verify",
    "ssl_trusted_certificate",
    "ssl_verify_client",
    "ssl_verify_depth",
    "tcp_nodelay",
    "tcp_nopush",
    "try_files",
    "types",
    "types_hash_bucket_size",
    "types_hash_max_size",
    "underscores_in_headers",
    "upstream",
    "use",
    "user",
    "uwsgi_pass",
    "valid_referers",
    "variables_hash_bucket_size",
    "variables_hash_max_size",
    "worker_connections",
    "worker_processes",
    "worker_rlimit_nofile",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("on", "off", "true", "false"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("http", "server", "location", "upstream", "events", "stream", "mail"):
        return TokenType.KEYWORD_DECLARATION
    if word in _DIRECTIVES:
        return TokenType.KEYWORD
    return TokenType.NAME


class NginxLexer(PatternLexer):
    """NGINX configuration lexer. Thread-safe."""

    name = "nginx"
    aliases = ("nginxconf",)
    filenames = ("nginx.conf", "*.nginx", "*.nginxconf")
    mimetypes = ("text/x-nginx-conf",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Variables
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        Rule(re.compile(r"\$\{[^}]+\}"), TokenType.NAME_VARIABLE),
        # Regex (in location blocks)
        Rule(re.compile(r"[~*^]=?\s+[^\s{]+"), TokenType.STRING_REGEX),
        # Numbers with units
        Rule(re.compile(r"\d+[kmgKMG]?"), TokenType.NUMBER_INTEGER),
        Rule(re.compile(r"\d+\.\d+"), TokenType.NUMBER_FLOAT),
        # Time units
        Rule(re.compile(r"\d+[smhdwMy]"), TokenType.NUMBER_INTEGER),
        # IP addresses and CIDR
        Rule(re.compile(r"\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?"), TokenType.LITERAL),
        # Keywords/directives
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"[~*^]=?|!=|="), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[{}();]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
