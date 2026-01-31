"""
Syntax highlighting backend protocol definition.

.. deprecated:: 0.2.0
    Import from :mod:`bengal.protocols` instead::

        # Old (deprecated)
        from bengal.rendering.highlighting.protocol import HighlightBackend

        # New (preferred)
        from bengal.protocols import HighlightService

    Note: HighlightBackend has been renamed to HighlightService for consistency.
    Both names are exported from bengal.protocols for backwards compatibility.

This module re-exports protocols from :mod:`bengal.protocols` for
backwards compatibility. Deprecation warnings are emitted on import.

See Also:
- :mod:`bengal.protocols`: Canonical protocol definitions
- :mod:`bengal.protocols.rendering`: HighlightService protocol

"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

# Re-export from canonical location
from bengal.protocols.rendering import (
    HighlightBackend as _HighlightBackend,
)
from bengal.protocols.rendering import (
    HighlightService as _HighlightService,
)

if TYPE_CHECKING:
    # For type checkers, provide direct access without warnings
    from bengal.protocols.rendering import (
        HighlightBackend,
        HighlightService,
    )


def __getattr__(name: str):
    """Emit deprecation warning for old import paths."""
    _exports = {
        "HighlightBackend": _HighlightBackend,
        "HighlightService": _HighlightService,
    }

    if name in _exports:
        warnings.warn(
            f"Import {name} from bengal.protocols instead of "
            f"bengal.rendering.highlighting.protocol. "
            f"This import path will be removed in version 1.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "HighlightBackend",
    "HighlightService",
]
