"""
Click extensions re-exports for backward compatibility.

.. deprecated::
    This module exists solely for backward compatibility.
    New code should import directly from :mod:`bengal.cli.base`.

Related:
- bengal/cli/base.py: Primary location of Click extensions

"""

from __future__ import annotations

from bengal.cli.base import BengalCommand, BengalGroup

__all__ = ["BengalCommand", "BengalGroup"]
