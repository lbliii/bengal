"""
Site loading helper.

.. deprecated::
    This module has been moved to :mod:`bengal.cli.utils.site`.
    Import from there instead::

        # New (preferred)
        from bengal.cli.utils import load_site_from_cli

        # Old (deprecated, still works for backward compatibility)
        from bengal.cli.helpers.site_loader import load_site_from_cli

This re-export exists for backward compatibility.

See Also:
- bengal/cli/utils/site.py: Canonical location

"""

from __future__ import annotations

from bengal.cli.utils.site import load_site_from_cli

__all__ = ["load_site_from_cli"]
