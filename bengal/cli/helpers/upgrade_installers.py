"""
Installer detection for bengal upgrade command.

Detects how Bengal was installed and generates appropriate upgrade command.
Supports: uv, pip, pipx, conda, and fallback to pip with --user.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InstallerInfo:
    """Information about detected installer."""

    name: str
    command: list[str]
    display_command: str

    @property
    def is_available(self) -> bool:
        """Check if the installer executable is available in PATH."""
        return shutil.which(self.command[0]) is not None


def detect_installer() -> InstallerInfo:
    """Detect how Bengal was installed."""
    if _is_uv_project():
        return InstallerInfo(
            name="uv",
            command=["uv", "pip", "install", "--upgrade", "bengal"],
            display_command="uv pip install --upgrade bengal",
        )

    if _is_pipx_install():
        return InstallerInfo(
            name="pipx",
            command=["pipx", "upgrade", "bengal"],
            display_command="pipx upgrade bengal",
        )

    if os.environ.get("CONDA_PREFIX"):
        return InstallerInfo(
            name="conda",
            command=["conda", "update", "-y", "bengal"],
            display_command="conda update bengal",
        )

    if sys.prefix != sys.base_prefix:
        return InstallerInfo(
            name="pip (venv)",
            command=[sys.executable, "-m", "pip", "install", "--upgrade", "bengal"],
            display_command="pip install --upgrade bengal",
        )

    return InstallerInfo(
        name="pip",
        command=[sys.executable, "-m", "pip", "install", "--upgrade", "--user", "bengal"],
        display_command="pip install --upgrade --user bengal",
    )


def _is_uv_project() -> bool:
    """Check if current directory is a uv-managed project."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / "uv.lock").exists():
            return True
        if parent == parent.parent:
            break

    return bool(os.environ.get("UV_CACHE_DIR") or os.environ.get("UV_PYTHON"))


def _is_pipx_install() -> bool:
    """Check if Bengal was installed via pipx."""
    if not shutil.which("pipx"):
        return False

    try:
        result = subprocess.run(
            ["pipx", "list", "--short"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "bengal" in result.stdout
    except Exception:
        return False
