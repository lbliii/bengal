"""
Inject live reload script into HTTP response body.
"""

from __future__ import annotations

from bengal.utils.observability.logger import get_logger

from .script import LIVE_RELOAD_SCRIPT

logger = get_logger(__name__)


def inject_live_reload_into_response(response: bytes) -> bytes:
    """
    Inject live reload script into an HTTP response body.

    Parses the HTTP response, locates </body> or </html> tag, and injects
    the LIVE_RELOAD_SCRIPT before it. Updates Content-Length header.
    """
    try:
        if b"\r\n\r\n" not in response:
            return response

        headers_end = response.index(b"\r\n\r\n")
        headers = response[:headers_end]
        body = response[headers_end + 4 :]

        from bengal.server.utils import find_html_injection_point

        script_bytes = LIVE_RELOAD_SCRIPT.encode("utf-8")
        injection_idx = find_html_injection_point(body)

        if injection_idx != -1:
            modified_body = body[:injection_idx] + script_bytes + body[injection_idx:]
        else:
            modified_body = body + script_bytes

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
