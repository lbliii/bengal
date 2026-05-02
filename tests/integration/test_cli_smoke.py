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
        """Verify 'bengal build' works without interface errors."""
        result = run_cli(["build"], cwd=str(site.root_path))
        result.assert_ok()
        # Look for the 'Built' success message
        assert "Built" in result.stdout

    def test_validate_command(self, site):
        """Verify 'bengal check' works (checks fix for cache redefinition)."""
        # Run build first to ensure output and cache exist
        run_cli(["build"], cwd=str(site.root_path)).assert_ok()

        # Test full validation
        result = run_cli(["check"], cwd=str(site.root_path))
        result.assert_ok()

        # Test incremental validation (checks our fix in validate.py)
        result = run_cli(["check", "--incremental"], cwd=str(site.root_path))
        result.assert_ok()

    def test_theme_debug_command(self, site):
        """Verify 'bengal theme debug' works (checks fix for _find_template_path)."""
        result = run_cli(["theme", "debug"], cwd=str(site.root_path))
        result.assert_ok()

    def test_check_command_smoke(self, site):
        """Verify 'bengal check' runs without crashing."""
        run_cli(["build"], cwd=str(site.root_path)).assert_ok()
        result = run_cli(["check"], cwd=str(site.root_path))
        # Should complete without crashing (exit 0 or 1 for warnings)
        assert result.returncode in (0, 1), (
            f"Unexpected exit code {result.returncode}: {result.stderr}"
        )

    def test_cache_hash_command(self, site):
        """Verify 'bengal cache hash' executes, not just renders help."""
        result = run_cli(["cache", "hash"], cwd=str(site.root_path))

        result.assert_ok()
        cache_hash = result.stdout.strip().splitlines()[-1]
        assert len(cache_hash) == 16
        assert all(ch in "0123456789abcdef" for ch in cache_hash)

    def test_cache_hash_includes_absolute_autodoc_sources(self, tmp_path):
        """Absolute autodoc input paths must contribute to the runtime hash."""
        source_dir = tmp_path / "src" / "pkg"
        source_dir.mkdir(parents=True)
        source_file = source_dir / "__init__.py"
        source_file.write_text("VALUE = 1\n")

        site_root = tmp_path / "site"
        (site_root / "content").mkdir(parents=True)
        (site_root / "content" / "index.md").write_text("---\ntitle: Home\n---\n# Home\n")
        (site_root / "bengal.toml").write_text(
            "\n".join(
                [
                    "[site]",
                    'title = "Hash Site"',
                    "",
                    "[autodoc.python]",
                    "enabled = true",
                    f'source_dirs = ["{source_dir.as_posix()}"]',
                    "",
                ]
            )
        )

        result1 = run_cli(["cache", "hash"], cwd=str(site_root))
        result1.assert_ok()
        source_file.write_text("VALUE = 2\n")
        result2 = run_cli(["cache", "hash"], cwd=str(site_root))
        result2.assert_ok()

        assert result1.stdout.strip().splitlines()[-1] != result2.stdout.strip().splitlines()[-1]
