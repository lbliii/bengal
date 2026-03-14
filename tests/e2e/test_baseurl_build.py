"""Baseurl E2E: build with path-based baseurl produces correct URLs.

Plan: plan-production-maturity.md Phase 0A
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
def test_baseurl_build_produces_prefixed_urls(built_site):
    """J6: Baseurl — HTML contains baseurl-prefixed asset links."""
    _, output_dir, result = built_site("test-baseurl")
    if result.returncode != 0:
        pytest.skip(f"test-baseurl build failed: {result.stderr}")
    html = (output_dir / "index.html").read_text(encoding="utf-8")
    # test-baseurl has baseurl=/site
    assert 'href="/site/' in html or 'href="/site/' in html


@pytest.mark.e2e
def test_baseurl_build_succeeds(built_site):
    """J6: Build with baseurl completes."""
    _, output_dir, result = built_site("test-baseurl")
    assert result.returncode == 0, f"Build failed: {result.stderr}"
    assert (output_dir / "index.html").exists()
