"""
Cacheable Protocol - Type-safe cache contracts for Bengal.

This module re-exports the Cacheable protocol from bengal.protocols.
All imports should now use bengal.protocols.Cacheable directly.

For implementation details and documentation, see:
- bengal/protocols/infrastructure.py: Canonical protocol definition

Migration:
    # Old (deprecated)
    from bengal.cache.cacheable import Cacheable
    
    # New (preferred)
    from bengal.protocols import Cacheable

"""

from __future__ import annotations

# Re-export from canonical location for backwards compatibility
from bengal.protocols.infrastructure import Cacheable

# Re-export TypeVar for generic return types
from typing import TypeVar

T = TypeVar("T", bound="Cacheable")

__all__ = ["Cacheable", "T"]
