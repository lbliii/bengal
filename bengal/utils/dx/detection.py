"""
Environment detection for DX hints.

Stateless, side-effect-free functions for detecting Docker, Kubernetes,
WSL, and CI environments. Used by the hints system to surface contextual tips.

No logging, minimal I/O. Safe to call from config loading and CLI.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path


def is_docker() -> bool:
    """
    Detect if running inside a Docker container.

    Checks for /.dockerenv or docker in /proc/self/cgroup.

    Returns:
        True if running in Docker, False otherwise.
    """
    if Path("/.dockerenv").exists():
        return True

    cgroup = Path("/proc/self/cgroup")
    if cgroup.is_file():
        try:
            content = cgroup.read_text()
            return "/docker" in content or "docker" in content
        except (OSError, UnicodeDecodeError):
            pass

    return False


def is_kubernetes() -> bool:
    """
    Detect if running inside a Kubernetes pod.

    K8s injects KUBERNETES_SERVICE_HOST into every pod.

    Returns:
        True if running in Kubernetes, False otherwise.
    """
    return bool(os.environ.get("KUBERNETES_SERVICE_HOST"))


def is_wsl() -> bool:
    """
    Detect if running on Windows Subsystem for Linux.

    Checks for microsoft-standard in kernel release.

    Returns:
        True if running on WSL, False otherwise.
    """
    try:
        release = platform.uname().release
        return "microsoft-standard" in release.lower()
    except (AttributeError, OSError):
        return False


def is_wsl_windows_drive(path: str | Path) -> bool:
    """
    Detect if path is on a Windows drive mounted in WSL (e.g. /mnt/c/...).

    File watching on 9p mounts can be unreliable; hints may suggest polling.

    Args:
        path: Path to check (e.g. cwd or project root).

    Returns:
        True if on WSL and path is under /mnt/[a-z]/, False otherwise.
    """
    if not is_wsl():
        return False

    resolved = Path(path).resolve()
    parts = resolved.parts

    # /mnt/c/... or /mnt/d/...
    if len(parts) >= 3 and parts[1] == "mnt" and len(parts[2]) == 1:
        return parts[2].islower() and parts[2].isalpha()

    return False


def is_ci() -> bool:
    """
    Detect if running in a CI environment.

    Returns:
        True if CI=true or GITHUB_ACTIONS=true, False otherwise.
    """
    return os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
