"""
Ignore policy for link checking.

Provides configurable rules for skipping certain URLs or HTTP status codes
during link checking. Useful for excluding known-broken external links,
rate-limited domains, or expected error responses.

Configuration Options:
    patterns: Regex patterns matched against full URL
    domains: Domain substrings matched against URL
    status_ranges: HTTP status codes or ranges to ignore

Example config:
    linkcheck:
      exclude:
        - "^https://example\\.com/legacy"
      exclude_domain:
        - "localhost"
        - "127.0.0.1"
      ignore_status:
        - "403"
        - "500-599"
"""

from __future__ import annotations

import re
from typing import Any


class IgnorePolicy:
    """
    Configurable policy for ignoring links and HTTP status codes.

    Supports three types of ignore rules:
        patterns: Regex patterns matched against full URL string
        domains: Domain substrings checked via "in" operator
        status_ranges: HTTP status codes as singles ("403") or ranges ("500-599")

    All rules are applied with OR logic - matching any rule causes ignore.

    Attributes:
        patterns: List of regex pattern strings
        domains: List of domain substrings to match
        status_ranges: List of status code specs
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
            patterns: Regex patterns matched against full URL.
            domains: Domain substrings (e.g., "localhost", "example.com").
            status_ranges: Status codes/ranges (e.g., "403", "500-599").
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
        Check if URL should be ignored based on policy.

        Checks domain exclusions first, then pattern matches.

        Args:
            url: Full URL string to check.

        Returns:
            Tuple of (should_ignore, reason) where reason explains the match.
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
        Check if HTTP status code should be ignored.

        Args:
            status_code: HTTP status code (e.g., 403, 500).

        Returns:
            Tuple of (should_ignore, reason) where reason explains the match.
        """
        if status_code in self._status_codes:
            return True, f"status {status_code} is in ignore list"

        return False, None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> IgnorePolicy:
        """
        Create IgnorePolicy from configuration dict.

        Args:
            config: Dict with optional keys:
                - exclude: List of regex URL patterns
                - exclude_domain: List of domain substrings
                - ignore_status: List of status code specs

        Returns:
            Configured IgnorePolicy instance.

        Example:
            >>> config = {
            ...     "exclude": ["^https://legacy\\."],
            ...     "exclude_domain": ["localhost"],
            ...     "ignore_status": ["403", "500-599"],
            ... }
            >>> policy = IgnorePolicy.from_config(config)
        """
        return cls(
            patterns=config.get("exclude", []),
            domains=config.get("exclude_domain", []),
            status_ranges=config.get("ignore_status", []),
        )
