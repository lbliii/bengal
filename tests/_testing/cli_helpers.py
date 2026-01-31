"""Test utilities for CLI commands."""

from __future__ import annotations

from typing import Any

import click
from click.testing import CliRunner, Result


def run_command(
    cmd: click.Command | click.Group, args: list[str] | None = None, input: str | None = None
) -> Result:
    """
    Run a CLI command and return the result.

    Args:
        cmd: Click command or group to run
        args: Command arguments (default: empty list)
        input: Input to send to command (for prompts)

    Returns:
        Click test result with exit_code and output

    Example:
        from bengal.cli.commands.build import build

        result = run_command(build, ["--help"])
        assert_command_success(result)
        assert "Build the static site" in result.output

    """
    runner = CliRunner()
    args = args or []
    return runner.invoke(cmd, args, input=input)


def assert_command_success(result: Result, message: str | None = None) -> None:
    """
    Assert that a command succeeded.

    Args:
        result: Click test result
        message: Optional custom error message

    Raises:
        AssertionError: If command failed

    Example:
        result = run_command(build, ["--help"])
        assert_command_success(result)

    """
    if result.exit_code != 0:
        error_msg = message or f"Command failed with exit code {result.exit_code}"
        error_msg += f"\nOutput:\n{result.output}"
        if result.exception:
            error_msg += f"\nException: {result.exception}"
        raise AssertionError(error_msg)


def assert_command_error(
    result: Result, expected_error: str | None = None, exit_code: int = 1
) -> None:
    """
    Assert that a command failed with expected error.

    Args:
        result: Click test result
        expected_error: Optional expected error message substring
        exit_code: Expected exit code (default: 1)

    Raises:
        AssertionError: If command succeeded or error doesn't match

    Example:
        result = run_command(build, ["--invalid-flag"])
        assert_command_error(result, "No such option")

    """
    if result.exit_code == 0:
        raise AssertionError(f"Command succeeded but expected failure. Output: {result.output}")

    if result.exit_code != exit_code:
        raise AssertionError(
            f"Expected exit code {exit_code}, got {result.exit_code}. Output: {result.output}"
        )

    if expected_error and expected_error not in result.output:
        raise AssertionError(
            f"Expected error '{expected_error}' not found in output:\n{result.output}"
        )


def assert_output_contains(result: Result, text: str) -> None:
    """
    Assert that command output contains specified text.

    Args:
        result: Click test result
        text: Text that should appear in output

    Raises:
        AssertionError: If text not found

    Example:
        result = run_command(build, ["--help"])
        assert_output_contains(result, "Build the static site")

    """
    if text not in result.output:
        raise AssertionError(f"Expected text '{text}' not found in output:\n{result.output}")


def assert_output_not_contains(result: Result, text: str) -> None:
    """
    Assert that command output does not contain specified text.

    Args:
        result: Click test result
        text: Text that should not appear in output

    Raises:
        AssertionError: If text found

    Example:
        result = run_command(build, ["--quiet"])
        assert_output_not_contains(result, "Building site")

    """
    if text in result.output:
        raise AssertionError(f"Unexpected text '{text}' found in output:\n{result.output}")


def create_test_site(tmp_path: Any, content: dict[str, str] | None = None) -> Any:
    """
    Create a minimal test site structure.

    Args:
        tmp_path: pytest tmp_path fixture
        content: Optional dict of {relative_path: content} for content files

    Returns:
        Path to test site root

    Example:
        site_path = create_test_site(tmp_path, {
            "index.md": "# Home",
            "about.md": "# About"
        })

    """
    site_path = tmp_path / "test_site"
    site_path.mkdir()

    # Create basic structure
    (site_path / "content").mkdir()
    (site_path / "config").mkdir()
    (site_path / "config" / "_default").mkdir()

    # Create minimal config
    import yaml

    config = {
        "site": {"title": "Test Site", "baseurl": "http://localhost:8000"},
        "build": {"output_dir": "public"},
    }
    (site_path / "config" / "_default" / "site.yaml").write_text(
        yaml.dump(config, default_flow_style=False)
    )

    # Create content files
    if content:
        for rel_path, file_content in content.items():
            file_path = site_path / "content" / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_content)

    return site_path
