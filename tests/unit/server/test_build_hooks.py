"""
Unit tests for build hooks module.

Tests:
    - Successful hook execution
    - Failed hook (non-zero exit code)
    - Hook timeout
    - Multiple hooks in sequence
    - Hook execution stops on first failure
    - Convenience functions for pre/post build hooks
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from bengal.server.build_hooks import (
    run_hooks,
    run_post_build_hooks,
    run_pre_build_hooks,
)


class TestRunHooks:
    """Tests for run_hooks function."""

    def test_successful_hook(self, tmp_path: Path) -> None:
        """Test that successful hooks return True."""
        result = run_hooks(
            ["echo hello"],
            "pre_build",
            tmp_path,
        )

        assert result is True

    def test_multiple_successful_hooks(self, tmp_path: Path) -> None:
        """Test that multiple successful hooks return True."""
        result = run_hooks(
            ["echo first", "echo second", "echo third"],
            "pre_build",
            tmp_path,
        )

        assert result is True

    def test_empty_hooks_returns_true(self, tmp_path: Path) -> None:
        """Test that empty hook list returns True."""
        result = run_hooks(
            [],
            "pre_build",
            tmp_path,
        )

        assert result is True

    def test_failed_hook_returns_false(self, tmp_path: Path) -> None:
        """Test that failed hooks return False."""
        # Use Python to ensure cross-platform failure
        result = run_hooks(
            [f'{sys.executable} -c "exit(1)"'],
            "pre_build",
            tmp_path,
        )

        assert result is False

    def test_stops_on_first_failure(self, tmp_path: Path) -> None:
        """Test that execution stops on first failure by default."""
        # Create a marker file to track execution
        marker = tmp_path / "marker.txt"

        result = run_hooks(
            [
                f'{sys.executable} -c "exit(1)"',
                f"{sys.executable} -c \"open('{marker}', 'w').write('executed')\"",
            ],
            "pre_build",
            tmp_path,
            stop_on_failure=True,
        )

        assert result is False
        # Second hook should not have executed
        assert not marker.exists()

    def test_continues_after_failure_when_disabled(self, tmp_path: Path) -> None:
        """Test that execution continues after failure when stop_on_failure=False."""
        marker = tmp_path / "marker.txt"

        result = run_hooks(
            [
                f'{sys.executable} -c "exit(1)"',
                f"{sys.executable} -c \"open(r'{marker}', 'w').write('executed')\"",
            ],
            "pre_build",
            tmp_path,
            stop_on_failure=False,
        )

        # Should return False (had failure)
        assert result is False
        # But second hook should have executed
        assert marker.exists()

    def test_timeout_returns_false(self, tmp_path: Path) -> None:
        """Test that timed out hooks return False."""
        # Use a very short timeout with a sleep command
        result = run_hooks(
            [f'{sys.executable} -c "import time; time.sleep(5)"'],
            "pre_build",
            tmp_path,
            timeout=0.1,
        )

        assert result is False

    def test_not_found_command_returns_false(self, tmp_path: Path) -> None:
        """Test that non-existent commands return False."""
        result = run_hooks(
            ["definitely_not_a_real_command_xyz123"],
            "pre_build",
            tmp_path,
        )

        assert result is False

    def test_hooks_run_in_cwd(self, tmp_path: Path) -> None:
        """Test that hooks run in the specified working directory."""
        # Create a file that the hook will check for
        marker = tmp_path / "exists.txt"
        marker.write_text("marker")

        # Use Python to check for the file
        result = run_hooks(
            [
                f"{sys.executable} -c \"import os; assert os.path.exists('exists.txt'), 'File not found'\""
            ],
            "pre_build",
            tmp_path,
        )

        assert result is True

    def test_hooks_with_arguments(self, tmp_path: Path) -> None:
        """Test that hooks with arguments work correctly."""
        output = tmp_path / "output.txt"

        result = run_hooks(
            [f"{sys.executable} -c \"open(r'{output}', 'w').write('arg1 arg2')\""],
            "pre_build",
            tmp_path,
        )

        assert result is True
        assert output.read_text() == "arg1 arg2"


class TestPreBuildHooks:
    """Tests for run_pre_build_hooks convenience function."""

    def test_runs_pre_build_hooks_from_config(self, tmp_path: Path) -> None:
        """Test that pre_build hooks are extracted from config."""
        config = {
            "dev_server": {
                "pre_build": ["echo pre-build"],
            }
        }

        result = run_pre_build_hooks(config, tmp_path)

        assert result is True

    def test_returns_true_with_no_hooks(self, tmp_path: Path) -> None:
        """Test that missing pre_build hooks return True."""
        config: dict = {}

        result = run_pre_build_hooks(config, tmp_path)

        assert result is True

    def test_returns_true_with_empty_hooks(self, tmp_path: Path) -> None:
        """Test that empty pre_build hooks list returns True."""
        config = {
            "dev_server": {
                "pre_build": [],
            }
        }

        result = run_pre_build_hooks(config, tmp_path)

        assert result is True


class TestPostBuildHooks:
    """Tests for run_post_build_hooks convenience function."""

    def test_runs_post_build_hooks_from_config(self, tmp_path: Path) -> None:
        """Test that post_build hooks are extracted from config."""
        config = {
            "dev_server": {
                "post_build": ["echo post-build"],
            }
        }

        result = run_post_build_hooks(config, tmp_path)

        assert result is True

    def test_returns_true_with_no_hooks(self, tmp_path: Path) -> None:
        """Test that missing post_build hooks return True."""
        config: dict = {}

        result = run_post_build_hooks(config, tmp_path)

        assert result is True

    def test_returns_true_with_empty_hooks(self, tmp_path: Path) -> None:
        """Test that empty post_build hooks list returns True."""
        config = {
            "dev_server": {
                "post_build": [],
            }
        }

        result = run_post_build_hooks(config, tmp_path)

        assert result is True


class TestHookEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_hook_with_quoted_arguments(self, tmp_path: Path) -> None:
        """Test that hooks with quoted arguments are parsed correctly."""
        output = tmp_path / "output.txt"

        result = run_hooks(
            [f"{sys.executable} -c \"open(r'{output}', 'w').write('hello world')\""],
            "pre_build",
            tmp_path,
        )

        assert result is True
        assert output.read_text() == "hello world"

    def test_hook_stderr_is_captured(self, tmp_path: Path) -> None:
        """Test that stderr output is captured (for logging)."""
        # This hook writes to stderr but exits 0
        result = run_hooks(
            [f"{sys.executable} -c \"import sys; sys.stderr.write('warning'); exit(0)\""],
            "pre_build",
            tmp_path,
        )

        # Should still succeed
        assert result is True

    @pytest.mark.parametrize(
        "hook_type",
        ["pre_build", "post_build", "custom_type"],
    )
    def test_hook_type_is_used_for_logging(self, tmp_path: Path, hook_type: str) -> None:
        """Test that different hook types work correctly."""
        result = run_hooks(
            ["echo test"],
            hook_type,
            tmp_path,
        )

        assert result is True


