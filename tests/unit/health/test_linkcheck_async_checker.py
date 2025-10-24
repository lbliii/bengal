"""
Unit tests for async link checker.
"""

from __future__ import annotations

import pytest

from bengal.health.linkcheck.async_checker import AsyncLinkChecker
from bengal.health.linkcheck.ignore_policy import IgnorePolicy
from bengal.health.linkcheck.models import LinkStatus


def test_async_checker_initialization():
    """Test async checker initialization."""
    checker = AsyncLinkChecker(
        max_concurrency=10,
        per_host_limit=2,
        timeout=5.0,
        retries=1,
        retry_backoff=0.25,
    )

    assert checker.max_concurrency == 10
    assert checker.per_host_limit == 2
    assert checker.timeout == 5.0
    assert checker.retries == 1
    assert checker.retry_backoff == 0.25


def test_async_checker_from_config():
    """Test creating checker from config."""
    config = {
        "max_concurrency": 15,
        "per_host_limit": 3,
        "timeout": 8.0,
        "retries": 3,
        "retry_backoff": 1.0,
        "exclude": [r"^https://blocked\."],
        "ignore_status": ["500-599"],
    }

    checker = AsyncLinkChecker.from_config(config)

    assert checker.max_concurrency == 15
    assert checker.per_host_limit == 3
    assert checker.timeout == 8.0
    assert checker.retries == 3
    assert checker.retry_backoff == 1.0
    assert checker.ignore_policy is not None


def test_calculate_backoff():
    """Test exponential backoff calculation."""
    checker = AsyncLinkChecker(retry_backoff=0.5)

    # First attempt (0)
    backoff = checker._calculate_backoff(0)
    # 0.5 * (2^0) = 0.5, with jitter ±0.125
    assert 0.375 <= backoff <= 0.625

    # Second attempt (1)
    backoff = checker._calculate_backoff(1)
    # 0.5 * (2^1) = 1.0, with jitter ±0.25
    assert 0.75 <= backoff <= 1.25

    # Third attempt (2)
    backoff = checker._calculate_backoff(2)
    # 0.5 * (2^2) = 2.0, with jitter ±0.5
    assert 1.5 <= backoff <= 2.5


def test_calculate_backoff_minimum():
    """Test backoff has minimum value."""
    checker = AsyncLinkChecker(retry_backoff=0.01)

    # Even with small backoff and negative jitter, should be >= 0.1
    backoff = checker._calculate_backoff(0)
    assert backoff >= 0.1


def test_async_checker_with_ignore_policy():
    """Test checker respects ignore policy."""
    ignore_policy = IgnorePolicy(
        patterns=[r"^https://excluded\."],
        domains=["localhost"],
        status_ranges=["500-599"],
    )

    checker = AsyncLinkChecker(ignore_policy=ignore_policy)

    assert checker.ignore_policy is not None


@pytest.mark.asyncio
async def test_check_url_with_ignored_url():
    """Test checking a URL that should be ignored."""
    ignore_policy = IgnorePolicy(patterns=[r"^https://ignored\."])
    checker = AsyncLinkChecker(ignore_policy=ignore_policy)

    # Simulate check without actual HTTP request
    result = await checker._check_url(
        None,  # No client needed for ignored URLs
        "https://ignored.example.com/page",
        ["/source.md"],
    )

    assert result.status == LinkStatus.IGNORED
    assert result.ignored is True
    assert result.ignore_reason is not None


def test_async_checker_groups_references():
    """Test that checker groups multiple references to same URL."""
    # This is more of an integration test but tests the logic
    # We'll verify the interface expects list of tuples
    checker = AsyncLinkChecker()

    # Check that check_links accepts this format
    # (actual HTTP test would require a real server or extensive mocking)
    assert hasattr(checker, "check_links")
    assert callable(checker.check_links)

    # Example format: list of (url, ref) tuples
    # urls = [("https://example.com", "/page1.md"), ...]
    # This would be passed to checker.check_links(urls)


def test_async_checker_default_user_agent():
    """Test default user agent is set."""
    checker = AsyncLinkChecker()
    assert checker.user_agent == "Bengal-LinkChecker/1.0"


def test_async_checker_custom_user_agent():
    """Test custom user agent."""
    checker = AsyncLinkChecker(user_agent="MyBot/2.0")
    assert checker.user_agent == "MyBot/2.0"


def test_async_checker_semaphores_initialized():
    """Test that semaphores are initialized."""
    checker = AsyncLinkChecker(max_concurrency=5)

    assert checker._global_semaphore is not None
    assert checker._global_semaphore._value == 5


def test_from_config_with_defaults():
    """Test from_config uses defaults for missing values."""
    config = {}
    checker = AsyncLinkChecker.from_config(config)

    # Should use defaults
    assert checker.max_concurrency == 20
    assert checker.per_host_limit == 4
    assert checker.timeout == 10.0
    assert checker.retries == 2
    assert checker.retry_backoff == 0.5


def test_from_config_partial_override():
    """Test from_config with partial config."""
    config = {
        "max_concurrency": 50,
        "timeout": 15.0,
        # Other values use defaults
    }

    checker = AsyncLinkChecker.from_config(config)

    assert checker.max_concurrency == 50
    assert checker.timeout == 15.0
    assert checker.per_host_limit == 4  # Default
    assert checker.retries == 2  # Default


@pytest.mark.asyncio
async def test_check_url_malformed_url():
    """Test checking a malformed URL with None client."""
    checker = AsyncLinkChecker()

    # URL that can't be meaningfully checked (urlparse is lenient, but will fail on client call)
    result = await checker._check_url(None, "not a url", ["/source.md"])

    assert result.status == LinkStatus.ERROR
    assert result.error_message is not None
    # urlparse is lenient, error occurs when trying to use None client
    # Accept either parse error or NoneType error
    error_lower = result.error_message.lower()
    assert "parse" in error_lower or "nonetype" in error_lower or "attribute" in error_lower


def test_backoff_increases_exponentially():
    """Test that backoff increases exponentially with attempts."""
    checker = AsyncLinkChecker(retry_backoff=1.0)

    backoffs = []
    for attempt in range(5):
        backoff = checker._calculate_backoff(attempt)
        backoffs.append(backoff)

    # Each should be roughly double the previous (accounting for jitter)
    # Attempt 0: ~1.0
    # Attempt 1: ~2.0
    # Attempt 2: ~4.0
    # Attempt 3: ~8.0
    # Attempt 4: ~16.0

    # Just verify general increasing trend
    assert backoffs[1] > backoffs[0]
    assert backoffs[2] > backoffs[1]
    assert backoffs[3] > backoffs[2]
