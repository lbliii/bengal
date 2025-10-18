"""Server utilities for development behavior."""

from __future__ import annotations

from typing import Protocol


class HeaderSender(Protocol):
    def send_header(self, key: str, value: str) -> None: ...


def apply_dev_no_cache_headers(sender: HeaderSender) -> None:
    """
    Apply consistent dev no-cache headers to an HTTP response.

    Intended to be called before end_headers().
    """
    try:
        sender.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        sender.send_header("Pragma", "no-cache")
    except Exception:
        # Best-effort only
        pass


