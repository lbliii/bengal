"""
Unit tests for linkcheck ignore policy.
"""

from __future__ import annotations

from bengal.health.linkcheck.ignore_policy import IgnorePolicy


def test_ignore_policy_empty():
    """Test empty ignore policy allows everything."""
    policy = IgnorePolicy()

    should_ignore, reason = policy.should_ignore_url("https://example.com")
    assert not should_ignore
    assert reason is None

    should_ignore, reason = policy.should_ignore_status(404)
    assert not should_ignore
    assert reason is None


def test_ignore_policy_domain_exact_match():
    """Test domain exclusion with exact match."""
    policy = IgnorePolicy(domains=["localhost", "127.0.0.1"])

    should_ignore, reason = policy.should_ignore_url("http://localhost:8000/page")
    assert should_ignore
    assert "localhost" in reason

    should_ignore, reason = policy.should_ignore_url("http://127.0.0.1/api")
    assert should_ignore
    assert "127.0.0.1" in reason

    should_ignore, reason = policy.should_ignore_url("https://example.com")
    assert not should_ignore


def test_ignore_policy_domain_substring():
    """Test domain exclusion with substring match."""
    policy = IgnorePolicy(domains=["example.com"])

    should_ignore, _reason = policy.should_ignore_url("https://www.example.com/page")
    assert should_ignore

    should_ignore, _reason = policy.should_ignore_url("https://api.example.com")
    assert should_ignore

    should_ignore, _reason = policy.should_ignore_url("https://different.org")
    assert not should_ignore


def test_ignore_policy_pattern_match():
    """Test URL pattern exclusion."""
    policy = IgnorePolicy(patterns=[r"^/api/preview/", r"\.pdf$"])

    should_ignore, reason = policy.should_ignore_url("/api/preview/draft")
    assert should_ignore
    assert "pattern" in reason

    should_ignore, reason = policy.should_ignore_url("/download/document.pdf")
    assert should_ignore

    should_ignore, reason = policy.should_ignore_url("/api/public/resource")
    assert not should_ignore


def test_ignore_policy_status_single():
    """Test single status code ignoring."""
    policy = IgnorePolicy(status_ranges=["403", "429"])

    should_ignore, reason = policy.should_ignore_status(403)
    assert should_ignore
    assert "403" in reason

    should_ignore, reason = policy.should_ignore_status(429)
    assert should_ignore

    should_ignore, reason = policy.should_ignore_status(404)
    assert not should_ignore


def test_ignore_policy_status_range():
    """Test status code range ignoring."""
    policy = IgnorePolicy(status_ranges=["500-599"])

    # All 5xx should be ignored
    for code in [500, 502, 503, 504, 599]:
        should_ignore, reason = policy.should_ignore_status(code)
        assert should_ignore, f"Status {code} should be ignored"
        assert str(code) in reason

    # 4xx and 3xx should not be ignored
    for code in [400, 404, 301]:
        should_ignore, reason = policy.should_ignore_status(code)
        assert not should_ignore, f"Status {code} should NOT be ignored"


def test_ignore_policy_status_multiple_ranges():
    """Test multiple status ranges."""
    policy = IgnorePolicy(status_ranges=["400-404", "500-503"])

    ignored_codes = [400, 401, 402, 403, 404, 500, 501, 502, 503]
    for code in ignored_codes:
        should_ignore, _ = policy.should_ignore_status(code)
        assert should_ignore, f"Status {code} should be ignored"

    not_ignored = [405, 410, 429, 504, 599]
    for code in not_ignored:
        should_ignore, _ = policy.should_ignore_status(code)
        assert not should_ignore, f"Status {code} should NOT be ignored"


def test_ignore_policy_mixed():
    """Test combining multiple ignore rules."""
    policy = IgnorePolicy(
        patterns=[r"^/admin/"],
        domains=["localhost"],
        status_ranges=["500-599"],
    )

    # Pattern match
    should_ignore, _ = policy.should_ignore_url("/admin/dashboard")
    assert should_ignore

    # Domain match
    should_ignore, _ = policy.should_ignore_url("http://localhost/page")
    assert should_ignore

    # Status match
    should_ignore, _ = policy.should_ignore_status(502)
    assert should_ignore

    # No matches
    should_ignore, _ = policy.should_ignore_url("https://example.com/page")
    assert not should_ignore

    should_ignore, _ = policy.should_ignore_status(404)
    assert not should_ignore


def test_ignore_policy_from_config():
    """Test creating policy from config dict."""
    config = {
        "exclude": [r"^/api/", r"\.draft$"],
        "exclude_domain": ["staging.example.com", "dev.local"],
        "ignore_status": ["403", "500-503"],
    }

    policy = IgnorePolicy.from_config(config)

    # Pattern
    should_ignore, _ = policy.should_ignore_url("/api/resource")
    assert should_ignore

    should_ignore, _ = policy.should_ignore_url("/page.draft")
    assert should_ignore

    # Domain
    should_ignore, _ = policy.should_ignore_url("https://staging.example.com/page")
    assert should_ignore

    # Status
    should_ignore, _ = policy.should_ignore_status(403)
    assert should_ignore

    should_ignore, _ = policy.should_ignore_status(502)
    assert should_ignore


def test_ignore_policy_from_empty_config():
    """Test creating policy from empty config."""
    config = {}
    policy = IgnorePolicy.from_config(config)

    should_ignore, _ = policy.should_ignore_url("https://example.com")
    assert not should_ignore

    should_ignore, _ = policy.should_ignore_status(404)
    assert not should_ignore


def test_ignore_policy_pattern_regex_special_chars():
    """Test patterns with regex special characters."""
    policy = IgnorePolicy(patterns=[r"\?preview=true", r"#comment-\d+"])

    should_ignore, _ = policy.should_ignore_url("/page?preview=true")
    assert should_ignore

    should_ignore, _ = policy.should_ignore_url("/article#comment-123")
    assert should_ignore

    should_ignore, _ = policy.should_ignore_url("/page?published=true")
    assert not should_ignore


def test_ignore_policy_case_sensitive():
    """Test that patterns are case-sensitive by default."""
    policy = IgnorePolicy(patterns=[r"^/API/"])

    should_ignore, _ = policy.should_ignore_url("/API/resource")
    assert should_ignore

    should_ignore, _ = policy.should_ignore_url("/api/resource")
    assert not should_ignore


def test_ignore_policy_status_edge_cases():
    """Test status code edge cases."""
    # Single digit status
    policy = IgnorePolicy(status_ranges=["0"])
    should_ignore, _ = policy.should_ignore_status(0)
    assert should_ignore

    # Large status codes
    policy = IgnorePolicy(status_ranges=["1000"])
    should_ignore, _ = policy.should_ignore_status(1000)
    assert should_ignore

    # Range with same start and end
    policy = IgnorePolicy(status_ranges=["404-404"])
    should_ignore, _ = policy.should_ignore_status(404)
    assert should_ignore
    should_ignore, _ = policy.should_ignore_status(405)
    assert not should_ignore
