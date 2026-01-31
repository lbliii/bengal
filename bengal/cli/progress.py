"""
Live progress display system with profile-aware output.

.. deprecated::
    This module has been moved to :mod:`bengal.utils.observability.cli_progress`.
    Import from there instead::

        # New (preferred)
        from bengal.utils.observability.cli_progress import LiveProgressManager

        # Old (deprecated, still works for backward compatibility)
        from bengal.cli.progress import LiveProgressManager

This re-export exists for backward compatibility. The module was moved
to fix layer violations (orchestration importing from cli).

See Also:
- bengal/utils/observability/cli_progress.py: New canonical location

"""

from __future__ import annotations

# Re-export from new canonical location for backward compatibility
from bengal.utils.observability.cli_progress import (
    LiveProgressManager,
    PhaseProgress,
    PhaseStatus,
)

__all__ = [
    "LiveProgressManager",
    "PhaseProgress",
    "PhaseStatus",
]
