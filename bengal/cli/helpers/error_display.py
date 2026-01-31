"""
Beautiful error display for CLI.

.. deprecated::
    This module has been moved to :mod:`bengal.errors.display`.
    Import from there instead::

        # New (preferred)
        from bengal.errors.display import display_bengal_error, beautify_common_exception

        # Old (deprecated, still works for backward compatibility)
        from bengal.cli.helpers.error_display import display_bengal_error

This re-export exists for backward compatibility. The module was moved
to fix layer violations (discovery importing from cli).

See Also:
- bengal/errors/display.py: New canonical location

"""

from __future__ import annotations

# Re-export from new canonical location for backward compatibility
from bengal.errors.display import beautify_common_exception, display_bengal_error

__all__ = [
    "beautify_common_exception",
    "display_bengal_error",
]
