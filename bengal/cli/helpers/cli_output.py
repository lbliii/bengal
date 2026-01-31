"""
CLI output helper.

.. deprecated::
    This module has been moved to :mod:`bengal.cli.utils.output`.
    Import from there instead::

        # New (preferred)
        from bengal.cli.utils import get_cli_output

        # Old (deprecated, still works for backward compatibility)
        from bengal.cli.helpers.cli_output import get_cli_output

This re-export exists for backward compatibility.

See Also:
- bengal/cli/utils/output.py: Canonical location

"""

from __future__ import annotations

from bengal.cli.utils.output import get_cli_output

__all__ = ["get_cli_output"]
