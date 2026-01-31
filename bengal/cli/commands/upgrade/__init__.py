"""
Upgrade command package for Bengal CLI.

Provides:
- PyPI version checking with caching
- Automatic installer detection
- Interactive upgrade command

Usage:
    bengal upgrade           # Interactive upgrade
    bengal upgrade -y        # Skip confirmation
    bengal upgrade --dry-run # Show command without running

Related:
- bengal/cli/__init__.py: CLI registration
- bengal/output/: Output formatting
"""

from __future__ import annotations

from bengal.cli.commands.upgrade.check import UpgradeInfo, check_for_upgrade
from bengal.cli.commands.upgrade.command import upgrade
from bengal.cli.commands.upgrade.installers import InstallerInfo, detect_installer

__all__ = [
    "InstallerInfo",
    "UpgradeInfo",
    "check_for_upgrade",
    "detect_installer",
    "upgrade",
]
