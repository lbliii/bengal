"""
Click extensions re-exports for backward compatibility.

This module provides re-exports of BengalCommand and BengalGroup from
bengal.cli.base for modules that may import from click_extensions.

Note:
    New code should import directly from bengal.cli.base.
    This module exists for backward compatibility only.

Related:
    - bengal/cli/base.py: Primary location of Click extensions
"""

from __future__ import annotations

from .base import BengalCommand, BengalGroup

# Re-export for compatibility if other modules import from click_extensions
__all__ = ["BengalGroup", "BengalCommand"]
