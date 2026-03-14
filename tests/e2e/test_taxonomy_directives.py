"""Taxonomy and directives E2E: custom content builds successfully.

Plan: plan-production-maturity.md Phase 0A
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
def test_taxonomy_build_succeeds(built_site):
    """J5: Taxonomy — site with tags/categories builds."""
    _, output_dir, result = built_site("test-taxonomy")
    assert result.returncode == 0, f"Build failed: {result.stderr}"
    # test-taxonomy has posts, not root index; check post pages exist
    html_files = list(output_dir.rglob("*.html"))
    assert len(html_files) >= 1, "Expected at least one HTML output"


@pytest.mark.e2e
def test_directives_build_succeeds(built_site):
    """J4: Custom directives — site with directives builds."""
    _, output_dir, result = built_site("test-directives")
    assert result.returncode == 0, f"Build failed: {result.stderr}"
    assert (output_dir / "index.html").exists()
