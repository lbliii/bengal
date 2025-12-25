"""HTTP request/response lexer for Rosettes.

Thread-safe regex-based tokenizer for HTTP messages.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["HttpLexer"]

# HTTP methods
_METHODS = frozenset(
    (
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "HEAD",
        "OPTIONS",
        "CONNECT",
        "TRACE",
    )
)

# Common HTTP headers
_HEADERS = frozenset(
    (
        "Accept",
        "Accept-Charset",
        "Accept-Encoding",
        "Accept-Language",
        "Accept-Ranges",
        "Access-Control-Allow-Origin",
        "Age",
        "Allow",
        "Authorization",
        "Cache-Control",
        "Connection",
        "Content-Disposition",
        "Content-Encoding",
        "Content-Language",
        "Content-Length",
        "Content-Location",
        "Content-Range",
        "Content-Security-Policy",
        "Content-Type",
        "Cookie",
        "Date",
        "ETag",
        "Expect",
        "Expires",
        "From",
        "Host",
        "If-Match",
        "If-Modified-Since",
        "If-None-Match",
        "If-Range",
        "If-Unmodified-Since",
        "Last-Modified",
        "Link",
        "Location",
        "Max-Forwards",
        "Origin",
        "Pragma",
        "Proxy-Authenticate",
        "Proxy-Authorization",
        "Range",
        "Referer",
        "Retry-After",
        "Server",
        "Set-Cookie",
        "Strict-Transport-Security",
        "TE",
        "Trailer",
        "Transfer-Encoding",
        "Upgrade",
        "User-Agent",
        "Vary",
        "Via",
        "Warning",
        "WWW-Authenticate",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-Requested-With",
        "X-XSS-Protection",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify HTTP methods and status."""
    word = match.group(0)
    if word in _METHODS:
        return TokenType.KEYWORD
    return TokenType.NAME


class HttpLexer(PatternLexer):
    """HTTP request/response lexer. Thread-safe."""

    name = "http"
    aliases = ("https",)
    filenames = ("*.http",)
    mimetypes = ("message/http",)

    rules = (
        # Request line: GET /path HTTP/1.1
        Rule(
            re.compile(r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|CONNECT|TRACE)\b"),
            TokenType.KEYWORD,
        ),
        # Response status line: HTTP/1.1 200 OK
        Rule(re.compile(r"^HTTP/[\d.]+"), TokenType.KEYWORD_NAMESPACE),
        # Status codes
        Rule(re.compile(r"\b[1-5]\d{2}\b"), TokenType.NUMBER_INTEGER),
        # Status text (after status code)
        Rule(re.compile(r"(?<=\d{3}\s)[A-Za-z ]+$", re.MULTILINE), TokenType.STRING),
        # Headers: Header-Name: value
        Rule(re.compile(r"^[A-Za-z][A-Za-z0-9-]*(?=:)", re.MULTILINE), TokenType.NAME_ATTRIBUTE),
        # Header separator
        Rule(re.compile(r":"), TokenType.PUNCTUATION),
        # URLs and paths
        Rule(re.compile(r"(?:https?://)?[a-zA-Z0-9.-]+(?:/[^\s]*)?"), TokenType.STRING_OTHER),
        # Query string parameters
        Rule(re.compile(r"[?&][a-zA-Z_][a-zA-Z0-9_]*="), TokenType.NAME_TAG),
        # Quoted strings
        Rule(re.compile(r'"[^"]*"'), TokenType.STRING_DOUBLE),
        # Content-Type values
        Rule(
            re.compile(r"\b(?:application|text|image|audio|video|multipart)/[a-zA-Z0-9.+-]+"),
            TokenType.STRING,
        ),
        # Charset and other params
        Rule(re.compile(r"\b(?:charset|boundary|name|filename)="), TokenType.NAME_ATTRIBUTE),
        # Numbers
        Rule(re.compile(r"\b\d+\b"), TokenType.NUMBER_INTEGER),
        # Semicolons in header values
        Rule(re.compile(r";"), TokenType.PUNCTUATION),
        # Other text
        Rule(re.compile(r"[^\s:;\"]+"), TokenType.TEXT),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
