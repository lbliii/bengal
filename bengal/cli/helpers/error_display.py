"""
Beautiful error display for CLI.

.. deprecated::
    This module has been moved to :mod:`bengal.errors.display`.
    Import from there instead::

        # New (preferred)
        from bengal.errors.display import display_bengal_error, beautify_common_exception

        # Old (deprecated, still works for backward compatibility)
        from bengal.cli.helpers.error_display import display_bengal_error

This re-export exists for backward compatibility.

See Also:
- bengal/errors/display.py: Canonical location

"""

from __future__ import annotations

from bengal.errors.display import beautify_common_exception, display_bengal_error

__all__ = [
    "beautify_common_exception",
    "display_bengal_error",
]
