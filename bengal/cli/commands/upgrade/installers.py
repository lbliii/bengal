"""
Installer detection for bengal upgrade command.

Detects how Bengal was installed and generates appropriate upgrade command.
Supports: uv, pip, pipx, conda, and fallback to pip with --user.

Detection priority:
1. uv.lock exists → uv
2. pipx list shows bengal → pipx
3. Virtual environment active → pip in venv
4. CONDA_PREFIX set → conda
5. Fallback → pip (user install)

Related:
- bengal/cli/commands/upgrade/command.py: Uses this for upgrade execution
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
    """
    Detect how Bengal was installed.
    
    Attempts detection in priority order:
    1. uv (preferred for Bengal projects)
    2. pipx (isolated CLI tools)
    3. conda (Anaconda/Miniconda environments)
    4. pip in venv (standard virtual environments)
    5. pip --user (fallback for global installs)
    
    Returns:
        InstallerInfo with name and appropriate upgrade command.
    """
    # Check for uv (preferred for Bengal)
    if _is_uv_project():
        return InstallerInfo(
            name="uv",
            command=["uv", "pip", "install", "--upgrade", "bengal"],
            display_command="uv pip install --upgrade bengal",
        )

    # Check for pipx
    if _is_pipx_install():
        return InstallerInfo(
            name="pipx",
            command=["pipx", "upgrade", "bengal"],
            display_command="pipx upgrade bengal",
        )

    # Check for conda
    if os.environ.get("CONDA_PREFIX"):
        return InstallerInfo(
            name="conda",
            command=["conda", "update", "-y", "bengal"],
            display_command="conda update bengal",
        )

    # Check for virtual environment
    if sys.prefix != sys.base_prefix:
        return InstallerInfo(
            name="pip (venv)",
            command=[sys.executable, "-m", "pip", "install", "--upgrade", "bengal"],
            display_command="pip install --upgrade bengal",
        )

    # Fallback to pip with --user
    return InstallerInfo(
        name="pip",
        command=[sys.executable, "-m", "pip", "install", "--upgrade", "--user", "bengal"],
        display_command="pip install --upgrade --user bengal",
    )


def _is_uv_project() -> bool:
    """
    Check if current directory is a uv-managed project.
    
    Looks for:
    - uv.lock in current directory or parent directories
    - UV_* environment variables (UV_CACHE_DIR, UV_PYTHON)
    
    Returns:
        True if uv project detected.
    """
    # Check for uv.lock in current directory or parents
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / "uv.lock").exists():
            return True
        if parent == parent.parent:  # Root reached
            break

    # Check for UV environment variables
    return bool(os.environ.get("UV_CACHE_DIR") or os.environ.get("UV_PYTHON"))


def _is_pipx_install() -> bool:
    """
    Check if Bengal was installed via pipx.
    
    Runs `pipx list --short` and checks if 'bengal' appears in output.
    Uses a 5s timeout to avoid hanging on slow systems.
    
    Returns:
        True if Bengal appears in pipx list.
    """
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
