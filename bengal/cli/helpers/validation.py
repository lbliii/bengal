"""
Validation helpers for CLI commands.

.. deprecated::
    This module has been moved to :mod:`bengal.cli.utils.validation`.
    Import from there instead::

        # New (preferred)
        from bengal.cli.utils import validate_mutually_exclusive, validate_flag_conflicts

        # Old (deprecated, still works for backward compatibility)
        from bengal.cli.helpers.validation import validate_mutually_exclusive

This re-export exists for backward compatibility.

See Also:
- bengal/cli/utils/validation.py: Canonical location

"""

from __future__ import annotations

from bengal.cli.utils.validation import validate_flag_conflicts, validate_mutually_exclusive

__all__ = [
    "validate_flag_conflicts",
    "validate_mutually_exclusive",
]
