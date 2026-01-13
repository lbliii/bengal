"""
CLI test utilities for Bengal.

Provides helpers for testing CLI commands with proper output capture
and sanitization.
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass

# ANSI escape code pattern
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    return ANSI_RE.sub("", text)


@dataclass
class CLIResult:
    """Result from CLI command execution."""

    returncode: int
    stdout: str
    stderr: str

    def assert_ok(self):
        """Assert that command succeeded (returncode == 0)."""
        assert self.returncode == 0, f"CLI failed: {self.stderr}"

    def assert_fail_with(self, code: int | None = None):
        """Assert that command failed, optionally with specific code."""
        assert self.returncode != 0, "Expected CLI to fail but it succeeded"
        if code is not None:
            assert self.returncode == code, f"Expected code {code}, got {self.returncode}"

    def assert_stdout_contains(self, text: str):
        """Assert that stdout contains the given text."""
        assert text in self.stdout, f"'{text}' not in stdout"

    def assert_stderr_contains(self, text: str):
        """Assert that stderr contains the given text."""
        assert text in self.stderr, f"'{text}' not in stderr"


def run_cli(
    args: list[str],
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    capture_ansi: bool = False,
    timeout: int = 30,
) -> CLIResult:
    """
    Run bengal CLI as subprocess with output sanitization.
    
    Args:
        args: CLI arguments (e.g., ["site", "build"])
        cwd: Working directory (defaults to current)
        env: Environment variables (merged with os.environ)
        capture_ansi: If False (default), strip ANSI codes for easier assertions
        timeout: Command timeout in seconds
    
    Returns:
        CLIResult with returncode, stdout, stderr
    
    Example:
        result = run_cli(["site", "build"], cwd="/path/to/site")
        result.assert_ok()
        result.assert_stdout_contains("Build complete")
        
    """
    result = subprocess.run(
        [sys.executable, "-m", "bengal.cli", *args],
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    stdout = result.stdout if capture_ansi else strip_ansi(result.stdout)
    stderr = result.stderr if capture_ansi else strip_ansi(result.stderr)

    return CLIResult(returncode=result.returncode, stdout=stdout, stderr=stderr)
