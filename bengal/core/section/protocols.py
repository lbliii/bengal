"""
Protocol definitions for section and site-like objects.

.. deprecated:: 0.2.0
    Import from :mod:`bengal.protocols` instead::
    
        # Old (deprecated)
        from bengal.core.section.protocols import SectionLike
        
        # New (preferred)
        from bengal.protocols import SectionLike

This module re-exports protocols from :mod:`bengal.protocols` for
backwards compatibility. Deprecation warnings are emitted on import.

See Also:
- :mod:`bengal.protocols`: Canonical protocol definitions
- :mod:`bengal.protocols.core`: PageLike, SectionLike, SiteLike

"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

# Re-export from canonical location
from bengal.protocols.core import (
    NavigableSection as _NavigableSection,
    QueryableSection as _QueryableSection,
    SectionLike as _SectionLike,
    SiteLike as _SiteLike,
)

if TYPE_CHECKING:
    # For type checkers, provide direct access without warnings
    from bengal.protocols.core import (
        NavigableSection,
        QueryableSection,
        SectionLike,
        SiteLike,
    )


def __getattr__(name: str) -> type:
    """Emit deprecation warning for old import paths."""
    _exports = {
        "SectionLike": _SectionLike,
        "SiteLike": _SiteLike,
        "NavigableSection": _NavigableSection,
        "QueryableSection": _QueryableSection,
    }
    
    if name in _exports:
        warnings.warn(
            f"Import {name} from bengal.protocols instead of "
            f"bengal.core.section.protocols. "
            f"This import path will be removed in version 1.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _exports[name]
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SectionLike",
    "SiteLike",
    "NavigableSection",
    "QueryableSection",
]
