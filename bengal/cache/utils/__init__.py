"""
Cache utilities for reducing redundancy across cache modules.

This package provides reusable mixins and utilities for common cache patterns:

- PersistentCacheMixin: Standardized load/save with compression and versioning
- ValidityTrackingMixin: Entry validity tracking with invalidation
- ThreadSafeCacheMixin: Thread-safe operations with RLock
- check_bidirectional_invariants: Verify forward/reverse index consistency
- CacheStatsMixin: Cache statistics generation

Usage:
    from bengal.cache.utils import (
        PersistentCacheMixin,
        ValidityTrackingMixin,
        ThreadSafeCacheMixin,
        check_bidirectional_invariants,
    )

    class MyCache(PersistentCacheMixin, ValidityTrackingMixin):
        VERSION = 1
        ...

"""

from __future__ import annotations

from bengal.cache.utils.bidirectional import check_bidirectional_invariants
from bengal.cache.utils.persistence import PersistentCacheMixin
from bengal.cache.utils.stats import compute_validity_stats
from bengal.cache.utils.thread_safety import ThreadSafeCacheMixin
from bengal.cache.utils.validity import ValidityTrackingMixin

__all__ = [
    "PersistentCacheMixin",
    "ValidityTrackingMixin",
    "ThreadSafeCacheMixin",
    "check_bidirectional_invariants",
    "compute_validity_stats",
]
