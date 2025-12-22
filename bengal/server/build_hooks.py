"""
Pre and post build hook execution for external tool integration.

Enables running custom shell commands before and after Bengal builds,
allowing integration with external build tools like npm, Tailwind CSS,
esbuild, or any custom scripts.

Features:
    - Sequential command execution with output capture
    - Configurable timeout per command (default: 30s)
    - stdout/stderr logging for debugging
    - Graceful failure handling (non-zero exit logged, not fatal)
    - Cross-platform subprocess execution

Functions:
    run_hooks: Execute a list of shell commands sequentially
    run_pre_build_hooks: Convenience wrapper for pre-build hooks
    run_post_build_hooks: Convenience wrapper for post-build hooks

Configuration (bengal.toml):
    ```toml
    [dev_server]
    pre_build_hooks = [
        "npm run build:icons",
        "tailwindcss -i src/input.css -o assets/style.css"
    ]
    post_build_hooks = [
        "echo 'Build complete!'"
    ]
    hook_timeout = 60  # seconds per command
    ```

Use Cases:
    - CSS preprocessing (Sass, Less, Tailwind)
    - JavaScript bundling (esbuild, webpack, Vite)
    - Asset optimization (imagemin, svgo)
    - Icon generation (svg-sprite, fontello)
    - Custom validation scripts

Related:
    - bengal/server/build_trigger.py: Calls hooks during build cycle
    - bengal/server/dev_server.py: Reads hook configuration
    - bengal.toml [dev_server] section: Hook configuration
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def run_hooks(
    hooks: list[str],
    hook_type: str,
    cwd: Path,
    *,
    timeout: float = 60.0,
    stop_on_failure: bool = True,
) -> bool:
    """
    Run a list of shell commands as hooks.

    Executes commands sequentially, capturing output for logging.
    By default, stops execution on first failure.

    Args:
        hooks: List of shell commands to run
        hook_type: Type of hook for logging ('pre_build' or 'post_build')
        cwd: Working directory for commands
        timeout: Maximum time per command in seconds (default: 60s)
        stop_on_failure: Whether to stop on first failed hook (default: True)

    Returns:
        True if all hooks succeeded, False if any hook failed

    Example:
        >>> run_hooks(
        ...     ["npm run build:css", "echo 'Done'"],
        ...     "pre_build",
        ...     Path("/project"),
        ...     timeout=30.0,
        ... )
        True

    Note:
        Commands are parsed using shlex.split() for safety, which handles
        quoted arguments correctly but does not support shell features like
        pipes, redirects, or environment variable expansion.
    """
    if not hooks:
        return True

    success_count = 0
    failure_count = 0

    for command in hooks:
        logger.info(f"{hook_type}_hook_running", command=command)

        try:
            # Parse command safely (no shell=True)
            args = shlex.split(command)

            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                failure_count += 1

                # Truncate stderr for logging
                stderr_preview = result.stderr[:500] if result.stderr else None

                logger.error(
                    f"{hook_type}_hook_failed",
                    command=command,
                    returncode=result.returncode,
                    stderr=stderr_preview,
                )

                if stop_on_failure:
                    return False
            else:
                success_count += 1

                # Log success with output line count
                stdout_lines = len(result.stdout.splitlines()) if result.stdout else 0

                logger.debug(
                    f"{hook_type}_hook_success",
                    command=command,
                    stdout_lines=stdout_lines,
                )

        except subprocess.TimeoutExpired:
            failure_count += 1
            logger.error(
                f"{hook_type}_hook_timeout",
                command=command,
                timeout=timeout,
            )

            if stop_on_failure:
                return False

        except FileNotFoundError as e:
            failure_count += 1
            logger.error(
                f"{hook_type}_hook_not_found",
                command=command,
                error=str(e),
            )

            if stop_on_failure:
                return False

        except Exception as e:
            failure_count += 1
            logger.error(
                f"{hook_type}_hook_error",
                command=command,
                error=str(e),
                error_type=type(e).__name__,
            )

            if stop_on_failure:
                return False

    # Log summary if multiple hooks
    if len(hooks) > 1:
        logger.info(
            f"{hook_type}_hooks_complete",
            total=len(hooks),
            success=success_count,
            failed=failure_count,
        )

    return failure_count == 0


def run_pre_build_hooks(config: dict, cwd: Path, *, timeout: float = 60.0) -> bool:
    """
    Run pre-build hooks from config.

    Convenience function to extract and run pre_build hooks from config.

    Args:
        config: Site configuration dict
        cwd: Working directory for commands
        timeout: Maximum time per command in seconds

    Returns:
        True if all hooks succeeded or no hooks configured, False otherwise
    """
    dev_server = config.get("dev_server", {})
    hooks = dev_server.get("pre_build", [])

    if not hooks:
        return True

    return run_hooks(hooks, "pre_build", cwd, timeout=timeout)


def run_post_build_hooks(config: dict, cwd: Path, *, timeout: float = 60.0) -> bool:
    """
    Run post-build hooks from config.

    Convenience function to extract and run post_build hooks from config.

    Args:
        config: Site configuration dict
        cwd: Working directory for commands
        timeout: Maximum time per command in seconds

    Returns:
        True if all hooks succeeded or no hooks configured, False otherwise
    """
    dev_server = config.get("dev_server", {})
    hooks = dev_server.get("post_build", [])

    if not hooks:
        return True

    return run_hooks(hooks, "post_build", cwd, timeout=timeout)
