"""
Smoke tests for CLI commands to prevent interface drift bugs.

These tests run real CLI commands in subprocesses against a standard
test site fixture to ensure that:
1. Commands can be initialized (no circular imports or missing dependencies)
2. Commands correctly interface with Core models (no AttributeError/TypeError)
3. Entry points and command decorators work as expected

The tests use 'run_cli' which invokes Bengal via 'python -m bengal.cli'.
"""

import pytest

from tests._testing.cli import run_cli


@pytest.mark.bengal(testroot="test-basic")
class TestCLICommandSmoke:
    """Smoke tests for various CLI command groups."""

    def test_build_command(self, site):
        """Verify 'bengal site build' works without interface errors."""
        result = run_cli(["site", "build"], cwd=str(site.root_path))
        result.assert_ok()
        # Look for the 'Built' success message
        assert "Built" in result.stdout

    def test_validate_command(self, site):
        """Verify 'bengal validate' works (checks fix for cache redefinition)."""
        # Run build first to ensure output and cache exist
        run_cli(["site", "build"], cwd=str(site.root_path)).assert_ok()

        # Test full validation
        result = run_cli(["validate"], cwd=str(site.root_path))
        result.assert_ok()
        assert "Validation passed" in result.stdout

        # Test incremental validation (checks our fix in validate.py)
        result = run_cli(["validate", "--incremental"], cwd=str(site.root_path))
        result.assert_ok()
        assert "Validation passed" in result.stdout

    def test_theme_debug_command(self, site):
        """Verify 'bengal theme debug' works (checks fix for _find_template_path)."""
        result = run_cli(["theme", "debug"], cwd=str(site.root_path))
        result.assert_ok()
        assert "Theme Inheritance Chain" in result.stdout
        assert "Template Resolution Paths" in result.stdout
        # This was the specific crash point
        assert "Common Template Sources" in result.stdout

    def test_provenance_lineage_command(self, site):
        """Verify 'bengal provenance lineage' works (checks fix for CacheKey normalization)."""
        # Provenance requires a build to generate records
        run_cli(["site", "build"], cwd=str(site.root_path)).assert_ok()

        # Test lineage for the index page
        # Note: test-basic has content/index.md
        result = run_cli(["provenance", "lineage", "content/index.md"], cwd=str(site.root_path))

        # If the fix for CacheKey normalization works, this should succeed
        result.assert_ok()
        assert "Provenance for content/index.md" in result.stdout
        assert "Combined hash:" in result.stdout
        assert "Inputs" in result.stdout

    def test_health_linkcheck_smoke(self, site):
        """Verify 'bengal health linkcheck' works (checks fix for BuildOptions)."""
        # This command triggers a build if output is missing
        # test-basic has a broken link (/index.txt), so we expect failure
        result = run_cli(["health", "linkcheck", "--internal-only"], cwd=str(site.root_path))

        # We expect it to FAIL because of broken links, but not CRASH with AttributeError
        result.assert_fail_with()
        assert "Link Check Report" in result.stdout
        assert "Broken Links" in result.stdout
