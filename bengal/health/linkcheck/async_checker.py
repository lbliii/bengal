"""
Async external link checker with retries, backoff, and concurrency control.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from bengal.health.linkcheck.ignore_policy import IgnorePolicy
from bengal.health.linkcheck.models import LinkCheckResult, LinkKind, LinkStatus
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class AsyncLinkChecker:
    """
    Async HTTP link checker with retries, backoff, and concurrency control.

    Features:
    - Global concurrency limit via semaphore
    - Per-host concurrency limit to avoid rate limits
    - Exponential backoff with jitter for retries
    - HEAD request first, fallback to GET on 405/403
    - Connection pooling and DNS caching via httpx
    - Ignore policies for patterns, domains, and status ranges
    """

    def __init__(
        self,
        max_concurrency: int = 20,
        per_host_limit: int = 4,
        timeout: float = 10.0,
        retries: int = 2,
        retry_backoff: float = 0.5,
        ignore_policy: IgnorePolicy | None = None,
        user_agent: str = "Bengal-LinkChecker/1.0",
    ):
        """
        Initialize async link checker.

        Args:
            max_concurrency: Maximum concurrent requests across all hosts
            per_host_limit: Maximum concurrent requests per host
            timeout: Request timeout in seconds
            retries: Number of retry attempts
            retry_backoff: Base backoff time for exponential backoff (seconds)
            ignore_policy: Policy for ignoring links/statuses
            user_agent: User-Agent header value
        """
        self.max_concurrency = max_concurrency
        self.per_host_limit = per_host_limit
        self.timeout = timeout
        self.retries = retries
        self.retry_backoff = retry_backoff
        self.ignore_policy = ignore_policy or IgnorePolicy()
        self.user_agent = user_agent

        # Semaphore for global concurrency
        self._global_semaphore = asyncio.Semaphore(max_concurrency)

        # Per-host semaphores
        self._host_semaphores: dict[str, asyncio.Semaphore] = {}

    async def check_links(self, urls: list[tuple[str, str]]) -> dict[str, LinkCheckResult]:
        """
        Check multiple external URLs concurrently.

        Args:
            urls: List of (url, first_ref) tuples where first_ref is the page
                  that first referenced this URL

        Returns:
            Dict mapping URL to LinkCheckResult
        """
        # Group URLs by destination and count references
        url_refs: dict[str, list[str]] = {}
        for url, ref in urls:
            if url not in url_refs:
                url_refs[url] = []
            url_refs[url].append(ref)

        # Create httpx client with connection pooling
        limits = httpx.Limits(
            max_connections=self.max_concurrency,
            max_keepalive_connections=self.per_host_limit,
        )
        timeout = httpx.Timeout(self.timeout)

        async with httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent},
        ) as client:
            # Check all URLs concurrently
            tasks = [self._check_url(client, url, refs) for url, refs in url_refs.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result dict
        result_dict: dict[str, LinkCheckResult] = {}
        for url, result in zip(url_refs.keys(), results, strict=True):
            if isinstance(result, Exception):
                logger.error(
                    "link_check_exception",
                    url=url,
                    error=str(result),
                    error_type=type(result).__name__,
                )
                result_dict[url] = LinkCheckResult(
                    url=url,
                    kind=LinkKind.EXTERNAL,
                    status=LinkStatus.ERROR,
                    first_ref=url_refs[url][0] if url_refs[url] else None,
                    ref_count=len(url_refs[url]),
                    error_message=str(result),
                )
            else:
                result_dict[url] = result

        return result_dict

    async def _check_url(
        self, client: httpx.AsyncClient, url: str, refs: list[str]
    ) -> LinkCheckResult:
        """
        Check a single URL with retries and backoff.

        Args:
            client: httpx AsyncClient
            url: URL to check
            refs: List of pages that reference this URL

        Returns:
            LinkCheckResult
        """
        # Check ignore policy
        should_ignore, ignore_reason = self.ignore_policy.should_ignore_url(url)
        if should_ignore:
            logger.debug("ignoring_url", url=url, reason=ignore_reason)
            return LinkCheckResult(
                url=url,
                kind=LinkKind.EXTERNAL,
                status=LinkStatus.IGNORED,
                first_ref=refs[0] if refs else None,
                ref_count=len(refs),
                ignored=True,
                ignore_reason=ignore_reason,
            )

        # Get per-host semaphore
        try:
            from urllib.parse import urlparse

            host = urlparse(url).netloc
            if host not in self._host_semaphores:
                self._host_semaphores[host] = asyncio.Semaphore(self.per_host_limit)
            host_semaphore = self._host_semaphores[host]
        except Exception as e:
            logger.warning("failed_to_parse_url", url=url, error=str(e))
            return LinkCheckResult(
                url=url,
                kind=LinkKind.EXTERNAL,
                status=LinkStatus.ERROR,
                first_ref=refs[0] if refs else None,
                ref_count=len(refs),
                error_message=f"Failed to parse URL: {e}",
            )

        # Acquire global and per-host semaphores
        async with self._global_semaphore, host_semaphore:
            return await self._check_with_retries(client, url, refs)

    async def _check_with_retries(
        self, client: httpx.AsyncClient, url: str, refs: list[str]
    ) -> LinkCheckResult:
        """
        Check URL with exponential backoff retries.

        Args:
            client: httpx AsyncClient
            url: URL to check
            refs: List of pages that reference this URL

        Returns:
            LinkCheckResult
        """
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                # Try HEAD first (lightweight)
                response = await client.head(url)

                # Some servers don't support HEAD - fallback to GET on 405/501
                if response.status_code in (405, 501):
                    logger.debug(
                        "head_not_supported_fallback_to_get",
                        url=url,
                        status=response.status_code,
                    )
                    response = await client.get(url)

                # Check status code
                status_code = response.status_code
                is_success = 200 <= status_code < 400

                # Check if status should be ignored
                should_ignore_status, ignore_reason = self.ignore_policy.should_ignore_status(
                    status_code
                )

                if should_ignore_status:
                    logger.debug(
                        "ignoring_status", url=url, status=status_code, reason=ignore_reason
                    )
                    return LinkCheckResult(
                        url=url,
                        kind=LinkKind.EXTERNAL,
                        status=LinkStatus.IGNORED,
                        status_code=status_code,
                        first_ref=refs[0] if refs else None,
                        ref_count=len(refs),
                        ignored=True,
                        ignore_reason=ignore_reason,
                    )

                if is_success:
                    logger.debug("link_ok", url=url, status=status_code)
                    return LinkCheckResult(
                        url=url,
                        kind=LinkKind.EXTERNAL,
                        status=LinkStatus.OK,
                        status_code=status_code,
                        reason=response.reason_phrase,
                        first_ref=refs[0] if refs else None,
                        ref_count=len(refs),
                    )
                else:
                    logger.debug("link_broken", url=url, status=status_code)
                    return LinkCheckResult(
                        url=url,
                        kind=LinkKind.EXTERNAL,
                        status=LinkStatus.BROKEN,
                        status_code=status_code,
                        reason=response.reason_phrase,
                        first_ref=refs[0] if refs else None,
                        ref_count=len(refs),
                    )

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.retries:
                    backoff = self._calculate_backoff(attempt)
                    logger.debug(
                        "timeout_retry",
                        url=url,
                        attempt=attempt + 1,
                        backoff=backoff,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.warning("timeout_final", url=url, attempts=attempt + 1)

            except httpx.RequestError as e:
                last_error = e
                if attempt < self.retries:
                    backoff = self._calculate_backoff(attempt)
                    logger.debug(
                        "request_error_retry",
                        url=url,
                        error=str(e),
                        attempt=attempt + 1,
                        backoff=backoff,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.warning(
                        "request_error_final", url=url, error=str(e), attempts=attempt + 1
                    )

            except Exception as e:
                last_error = e
                logger.error("unexpected_error", url=url, error=str(e))
                break

        # All retries failed
        return LinkCheckResult(
            url=url,
            kind=LinkKind.EXTERNAL,
            status=LinkStatus.ERROR,
            first_ref=refs[0] if refs else None,
            ref_count=len(refs),
            error_message=str(last_error) if last_error else "Unknown error",
        )

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff with jitter.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Backoff time in seconds
        """
        # Exponential backoff: base * (2 ^ attempt)
        backoff = self.retry_backoff * (2**attempt)

        # Add jitter (±25%)
        jitter = backoff * 0.25
        backoff += random.uniform(-jitter, jitter)

        return max(0.1, backoff)  # Minimum 0.1 seconds

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> AsyncLinkChecker:
        """
        Create AsyncLinkChecker from config dict.

        Args:
            config: Configuration dict

        Returns:
            Configured AsyncLinkChecker instance
        """
        ignore_policy = IgnorePolicy.from_config(config)

        return cls(
            max_concurrency=config.get("max_concurrency", 20),
            per_host_limit=config.get("per_host_limit", 4),
            timeout=config.get("timeout", 10.0),
            retries=config.get("retries", 2),
            retry_backoff=config.get("retry_backoff", 0.5),
            ignore_policy=ignore_policy,
        )
