"""
Traceback configuration helper.

.. deprecated::
    This module has been moved to :mod:`bengal.cli.utils.traceback`.
    Import from there instead::

        # New (preferred)
        from bengal.cli.utils import configure_traceback

        # Old (deprecated, still works for backward compatibility)
        from bengal.cli.helpers.traceback import configure_traceback

This re-export exists for backward compatibility.

See Also:
- bengal/cli/utils/traceback.py: Canonical location

"""

from __future__ import annotations

from bengal.cli.utils.traceback import configure_traceback

__all__ = ["configure_traceback"]
