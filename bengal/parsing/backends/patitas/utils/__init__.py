"""Patitas utilities.

Provides shared utilities for the patitas backend:
- ContextVarManager: Generic ContextVar get/set/reset/context pattern
- ThreadLocalPool: Generic thread-local instance pooling
"""

from bengal.parsing.backends.patitas.utils.contextvar import (
    ContextVarManager,
    create_contextvar_manager,
)
from bengal.parsing.backends.patitas.utils.pool import ThreadLocalPool

__all__ = [
    "ContextVarManager",
    "ThreadLocalPool",
    "create_contextvar_manager",
]
