"""Versioned build E2E: multi-version site builds and paths resolve.

Plan: plan-production-maturity.md Phase 0A
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
def test_versioned_build_succeeds(built_site):
    """J8: Multi-version docs — versioned site builds successfully."""
    _, output_dir, result = built_site("test-versioned")
    assert result.returncode == 0, f"Versioned build failed: {result.stderr}"
    assert (output_dir / "versions.json").exists()


@pytest.mark.e2e
def test_versioned_paths_resolve(built_site):
    """J8: Versioned docs paths resolve to existing output."""
    _, output_dir, result = built_site("test-versioned")
    assert result.returncode == 0
    # test-versioned has docs/v1 and docs/v2
    assert (output_dir / "docs" / "v1" / "index.html").exists()
    assert (output_dir / "docs" / "v2" / "index.html").exists()
