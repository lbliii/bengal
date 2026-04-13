"""Tests for build command flag conflict validation.

Verifies that mutually exclusive flag combinations are caught
at parse time with clear error messages.
"""

from __future__ import annotations

import pytest


class TestBuildFlagConflicts:
    """Tests for mutually exclusive build flag validation."""

    @pytest.mark.parametrize(
        ("kwargs", "expected_msg"),
        [
            (
                {"verbose": True, "quiet": True},
                "--verbose and --quiet cannot be used together",
            ),
            (
                {"dev": True, "profile": "writer"},
                "--dev is shorthand for --profile dev",
            ),
            (
                {"theme_dev": True, "profile": "writer"},
                "--theme-dev is shorthand for --profile theme-dev",
            ),
            (
                {"incremental": True, "no_incremental": True},
                "--incremental and --no-incremental cannot be used together",
            ),
            (
                {"assets_pipeline": True, "no_assets_pipeline": True},
                "--assets-pipeline and --no-assets-pipeline cannot be used together",
            ),
            (
                {"memory_optimized": True, "perf_profile": "/tmp/profile.stats"},
                "--memory-optimized and --perf-profile cannot be used together",
            ),
        ],
        ids=[
            "verbose+quiet",
            "dev+profile",
            "theme-dev+profile",
            "incremental+no-incremental",
            "assets-pipeline+no-assets-pipeline",
            "memory-optimized+perf-profile",
        ],
    )
    def test_conflicting_flags_exit_with_error(self, kwargs, expected_msg):
        """Mutually exclusive flags should cause SystemExit(2)."""
        from bengal.cli.milo_commands.build import build

        with pytest.raises(SystemExit) as exc_info:
            build(**kwargs)

        assert exc_info.value.code == 2
