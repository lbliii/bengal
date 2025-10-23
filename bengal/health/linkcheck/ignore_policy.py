"""
Ignore policy for link checking.

Supports patterns, domains, and status ranges.
"""

from __future__ import annotations

import re
from typing import Any


class IgnorePolicy:
    """
    Policy for ignoring certain links or statuses.

    Supports:
    - URL patterns (regex)
    - Domain exclusions
    - Status code ranges (e.g., "500-599", "403")
    """

    def __init__(
        self,
        patterns: list[str] | None = None,
        domains: list[str] | None = None,
        status_ranges: list[str] | None = None,
    ):
        """
        Initialize ignore policy.

        Args:
            patterns: Regex patterns to match against URLs
            domains: Domain names to ignore (e.g., "localhost", "example.com")
            status_ranges: Status code ranges to ignore (e.g., "500-599", "403")
        """
        self.patterns = patterns or []
        self.domains = domains or []
        self.status_ranges = status_ranges or []

        # Compile regex patterns
        self._compiled_patterns = [re.compile(pattern) for pattern in self.patterns]

        # Parse status ranges
        self._status_codes: set[int] = set()
        for range_str in self.status_ranges:
            if "-" in range_str:
                # Range like "500-599"
                start_str, end_str = range_str.split("-", 1)
                start = int(start_str.strip())
                end = int(end_str.strip())
                self._status_codes.update(range(start, end + 1))
            else:
                # Single status like "403"
                self._status_codes.add(int(range_str.strip()))

    def should_ignore_url(self, url: str) -> tuple[bool, str | None]:
        """
        Check if URL should be ignored.

        Args:
            url: URL to check

        Returns:
            Tuple of (should_ignore, reason)
        """
        # Check domain exclusions
        for domain in self.domains:
            if domain in url:
                return True, f"domain '{domain}' is excluded"

        # Check pattern matches
        for pattern in self._compiled_patterns:
            if pattern.search(url):
                return True, f"matches pattern '{pattern.pattern}'"

        return False, None

    def should_ignore_status(self, status_code: int) -> tuple[bool, str | None]:
        """
        Check if status code should be ignored.

        Args:
            status_code: HTTP status code

        Returns:
            Tuple of (should_ignore, reason)
        """
        if status_code in self._status_codes:
            return True, f"status {status_code} is in ignore list"

        return False, None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> IgnorePolicy:
        """
        Create IgnorePolicy from config dict.

        Args:
            config: Configuration dict with optional keys:
                - exclude: list of URL patterns
                - exclude_domain: list of domains
                - ignore_status: list of status ranges

        Returns:
            Configured IgnorePolicy instance
        """
        return cls(
            patterns=config.get("exclude", []),
            domains=config.get("exclude_domain", []),
            status_ranges=config.get("ignore_status", []),
        )
