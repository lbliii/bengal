"""
Lock ordering convention and concurrency documentation for Bengal.

Bengal uses threading.Lock / threading.RLock primitives for thread safety under
free-threading (PEP 703, Python 3.14t).  This module documents every lock in the
codebase, the data it protects, and the **global acquisition order** that all
code must follow to prevent deadlocks.

Rule
----
When acquiring more than one lock, always acquire in **ascending tier order**.
Never acquire a lock from a lower-numbered tier while holding one from a
higher-numbered tier.

Tier 0  →  Tier 1  →  Tier 2  →  …  →  Tier 7  (safe)
Tier 3  →  Tier 1  (DEADLOCK RISK — violates ordering)

Within the same tier, locks are independent (never nest with each other).

Lock Inventory
--------------

Tier 0 — Build Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
These locks gate entire builds or guard lock-factory meta-structures.
They are acquired first and released last.

+-----------------------------------------------+--------+--------------------------------------------+
| Lock                                          | Type   | Protects                                   |
+===============================================+========+============================================+
| BuildTrigger._build_lock                      | Lock   | Serializes dev-server rebuild cycles       |
|   server/build_trigger.py:141                 |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| BuildState._locks_guard                       | Lock   | Guards creation of named locks in          |
|   orchestration/build_state.py:120            |        | BuildState._locks dict                     |
+-----------------------------------------------+--------+--------------------------------------------+

Tier 1 — Cache Infrastructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Persistent caches and indexes that span the entire build.

+-----------------------------------------------+--------+--------------------------------------------+
| Lock                                          | Type   | Protects                                   |
+===============================================+========+============================================+
| ProvenanceStore._lock                         | Lock   | In-memory provenance index & records       |
|   build/provenance/store.py:67                |        | (_index, _records, _subvenance)            |
+-----------------------------------------------+--------+--------------------------------------------+
| ContentHashRegistry._lock                     | RLock  | Source/output hash maps, dirty flag        |
|   cache/content_hash_registry.py:108          |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| TaxonomyIndex._lock                           | RLock  | Tag entries and page→tags reverse index    |
|   cache/taxonomy_index.py:132                 |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| QueryIndex._lock                              | RLock  | Index entries and page→keys reverse index  |
|   cache/query_index.py:173                    |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| GeneratedPageCache._lock                      | Lock   | Cached HTML entries for generated pages    |
|   cache/generated_page_cache.py:185           |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| Site._asset_manifest_fallbacks_lock           | Lock   | Fallback warning dedup set on Site         |
|   core/site/__init__.py:223                   |        | (legacy path; prefer BuildState named lock)|
+-----------------------------------------------+--------+--------------------------------------------+

Tier 2 — Build Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~
Per-build state that tracks dependencies, provenance, and effects.

+-----------------------------------------------+--------+--------------------------------------------+
| Lock                                          | Type   | Protects                                   |
+===============================================+========+============================================+
| DependencyTracker.lock                        | Lock   | tracked_files, dependencies,               |
|   build/tracking/tracker.py:151               |        | reverse_dependencies, pending fingerprints |
+-----------------------------------------------+--------+--------------------------------------------+
| ProvenanceFilter._session_lock                | Lock   | Per-session file hash & provenance caches  |
|   build/provenance/filter.py:125              |        | (_file_hashes, _computed_provenance)       |
+-----------------------------------------------+--------+--------------------------------------------+
| EffectTracer._lock                            | Lock   | Effect list & dependency/output indexes    |
|   effects/tracer.py:58                        |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| BuildEffectTracer._lock (class-level)         | Lock   | Singleton instance access                  |
|   effects/render_integration.py:195           |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+

Tier 3 — Rendering
~~~~~~~~~~~~~~~~~~~
Locks acquired during parallel page rendering.

+-----------------------------------------------+--------+--------------------------------------------+
| Lock                                          | Type   | Protects                                   |
+===============================================+========+============================================+
| Renderer._cache_lock                          | Lock   | _top_level_cache, _tag_pages_cache         |
|   rendering/renderer.py:103                   |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| NavTreeCache._lock (class-level)              | Lock   | Site-change invalidation of NavTree cache  |
|   core/nav_tree.py:698                        |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| NavTreeCache._build_locks                     | PKL*   | Per-version NavTree build serialization    |
|   core/nav_tree.py:699                        |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| NavScaffoldCache._lock (class-level)          | Lock   | Site-change invalidation of scaffold cache |
|   rendering/.../navigation/scaffold.py:87     |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| NavScaffoldCache._render_locks                | PKL*   | Per-scaffold render serialization          |
|   rendering/.../navigation/scaffold.py:88     |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| _context_lock (module-level)                  | Lock   | _global_context_cache dict                 |
|   rendering/context/__init__.py:118           |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| _config_lock (module-level)                   | Lock   | _directive_cache global replacement        |
|   cache/directive_cache.py:129                |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| BuildState._locks["asset_manifest_fallbacks"] | Lock   | Fallback warning dedup set (via get_lock)  |
|   orchestration/build_state.py:148            |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+

*PKL = PerKeyLockManager (bengal/utils/concurrency/concurrent_locks.py).
 Internally uses a _meta_lock (Lock) to guard key→RLock creation,
 then the per-key RLock is held for the critical section.

Tier 4 — Component / Utility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Leaf-level locks for icons, counters, registries.  These are never
held while acquiring another lock.

+-----------------------------------------------+--------+--------------------------------------------+
| Lock                                          | Type   | Protects                                   |
+===============================================+========+============================================+
| _icon_lock (module-level)                     | Lock   | _search_paths, _icon_cache, _not_found,    |
|   icons/resolver.py:43                        |        | _initialized flag                          |
+-----------------------------------------------+--------+--------------------------------------------+
| _site_lock (module-level)                     | Lock   | _site_instance (theme icon config)         |
|   rendering/template_functions/icons.py:42    |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| _warned_lock (module-level)                   | Lock   | _warned_icons dedup set                    |
|   rendering/template_functions/icons.py:37    |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| _cell_lock (module-level)                     | Lock   | _cell_counter for Marimo cell IDs          |
|   parsing/.../directives/builtins/marimo.py:44|        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| _registry_lock (module-level)                 | Lock   | Scaffold TemplateRegistry singleton        |
|   scaffolds/registry.py:255                   |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| LRUCache._lock (per-instance)                 | RLock  | Internal OrderedDict + stats               |
|   utils/primitives/lru_cache.py:89            |        | (self-contained, never calls out)          |
+-----------------------------------------------+--------+--------------------------------------------+
| ThreadSafeCacheMixin._lock (per-instance)     | RLock  | Subclass data (TaxonomyIndex, QueryIndex,  |
|   cache/utils/thread_safety.py:57             |        | ContentHashRegistry inherit this)          |
+-----------------------------------------------+--------+--------------------------------------------+
| PerKeyLockManager._meta_lock (per-instance)   | Lock   | Internal _locks dict in PerKeyLockManager  |
|   utils/concurrency/concurrent_locks.py:91    |        | (held only for dict lookup/creation)       |
+-----------------------------------------------+--------+--------------------------------------------+

Tier 5 — Progress / I/O
~~~~~~~~~~~~~~~~~~~~~~~~~
Write-path locks for disk I/O and progress reporting.

+-----------------------------------------------+--------+--------------------------------------------+
| Lock                                          | Type   | Protects                                   |
+===============================================+========+============================================+
| ProgressUpdater._lock                         | Lock   | _completed_count, _pending_updates,        |
|   orchestration/utils/parallel.py:98          |        | _last_update_time, _last_item              |
+-----------------------------------------------+--------+--------------------------------------------+
| ThreadSafeProgressUpdater._lock               | Lock   | _count, _last_update progress counter      |
|   snapshots/utils.py:184                      |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| WriteBehindBuffer._writes_lock                | Lock   | _writes_completed counter                  |
|   rendering/pipeline/write_behind.py:105      |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| WriteBehindBuffer._created_dirs_lock          | Lock   | _created_dirs set (mkdir dedup)            |
|   rendering/pipeline/write_behind.py:107      |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| ResourceProcessor._write_lock                 | Lock   | Image cache directory writes               |
|   core/resources/processor.py:99              |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| RenderOrchestrator (local lock in             | Lock   | completed_count progress counter           |
|   _render_pages_parallel)                     |        | (function-scoped, not an attribute)        |
|   orchestration/render/orchestrator.py:870    |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+

Tier 6 — Server (dev server only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Locks used exclusively by the live-reload dev server.
Not held during production builds.

+-----------------------------------------------+--------+--------------------------------------------+
| Lock                                          | Type   | Protects                                   |
+===============================================+========+============================================+
| WatcherRunner._changes_lock                   | Lock   | _pending_changes, _pending_event_types     |
|   server/watcher_runner.py:102                |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| ReloadController._config_lock                 | RLock  | Runtime config (intervals, globs, hashing) |
|   server/reload_controller.py:213             |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| LiveReloadMixin._html_cache_lock (class-level)| Lock   | _html_cache dict (injected page cache)     |
|   server/live_reload.py:269                   |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| LiveReloadMixin._asset_cache_lock (class-level)| Lock  | _asset_cache dict (CSS/JS serving cache)   |
|   server/live_reload.py:276                   |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| ResourceManager._lock                         | Lock   | _resources list, _cleanup_done flag        |
|   server/resource_manager.py:107              |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+

Tier 7 — Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~
Locks for error recording, always acquired last.

+-----------------------------------------------+--------+--------------------------------------------+
| Lock                                          | Type   | Protects                                   |
+===============================================+========+============================================+
| ErrorSession._lock                            | Lock   | _patterns, _errors_by_*, _total_errors     |
|   errors/session.py:180                       |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+
| SingletonContainer._lock                      | Lock   | _instance (lazy singleton creation)        |
|   errors/utils.py:531                         |        |                                            |
+-----------------------------------------------+--------+--------------------------------------------+

Inter-Process Locks (Orthogonal)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
File-based locks for multi-process safety.  These use OS-level
``fcntl.flock()`` / ``msvcrt.locking()`` and do NOT interact with
in-process threading locks.

+-----------------------------------------------+--------+--------------------------------------------+
| Lock                                          | Type   | Protects                                   |
+===============================================+========+============================================+
| file_lock(path, exclusive=True/False)         | flock  | BuildCache disk reads/writes               |
|   utils/io/file_lock.py:46                    |        | (.bengal/ cache JSON files)                |
+-----------------------------------------------+--------+--------------------------------------------+

Known Nesting Sequences
-----------------------
The following are the **only** legal multi-lock acquisition paths in Bengal.
Each arrow means "then acquire":

1. ``NavTreeCache._lock`` → ``PerKeyLockManager._meta_lock``
     → per-key ``RLock``
   (core/nav_tree.py — site invalidation check, then per-version build)

2. ``NavScaffoldCache._lock`` → ``PerKeyLockManager._meta_lock``
     → per-key ``RLock``
   (rendering/.../navigation/scaffold.py — same pattern as NavTree)

3. ``BuildState._locks_guard`` → ``BuildState._locks[name]``
   (orchestration/build_state.py — meta-lock for named lock creation)

4. ``BuildTrigger._build_lock`` → any Tier 1-7 lock
   (server/build_trigger.py — entire build runs under build lock)

All other locks are **leaf locks** — they are acquired alone and do not
call into code that acquires another lock while held.

Design Principles
-----------------
- **Prefer leaf locks**: Most locks protect a single data structure and
  release before calling external code.  This eliminates nesting entirely.
- **PerKeyLockManager for fan-out**: When many keys need independent
  serialization (templates, nav versions), use PerKeyLockManager instead
  of a single global lock.
- **RLock for reentrant paths**: TaxonomyIndex, QueryIndex, ContentHashRegistry,
  and LRUCache use RLock because their public methods may call each other.
- **ContextVar over locks**: Where possible, use ``contextvars.ContextVar``
  for per-task state instead of shared mutable state + locks.
- **Immutable by default**: Frozen dataclasses and tuples eliminate the
  need for locks on read-heavy data (Page, Section, Theme, etc.).

"""

from __future__ import annotations

import logging
import threading
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lock tiers — numeric constants for ordering validation
# ---------------------------------------------------------------------------

TIER_BUILD_SERIALIZATION = 0
TIER_CACHE_INFRASTRUCTURE = 1
TIER_BUILD_TRACKING = 2
TIER_RENDERING = 3
TIER_COMPONENT_UTILITY = 4
TIER_PROGRESS_IO = 5
TIER_SERVER = 6
TIER_ERROR_HANDLING = 7

_TIER_NAMES: dict[int, str] = {
    TIER_BUILD_SERIALIZATION: "Build Serialization",
    TIER_CACHE_INFRASTRUCTURE: "Cache Infrastructure",
    TIER_BUILD_TRACKING: "Build Tracking",
    TIER_RENDERING: "Rendering",
    TIER_COMPONENT_UTILITY: "Component/Utility",
    TIER_PROGRESS_IO: "Progress/IO",
    TIER_SERVER: "Server",
    TIER_ERROR_HANDLING: "Error Handling",
}

# ---------------------------------------------------------------------------
# Debug-mode lock ordering validator
# ---------------------------------------------------------------------------

# Thread-local stack of held lock tiers (only active when DEBUG_LOCK_ORDER=True)
_held_tiers: ContextVar[list[tuple[int, str]]] = ContextVar("_held_tiers")

# Global flag — set to True to enable lock-ordering checks at runtime.
# This adds overhead and should only be used during development or CI.
DEBUG_LOCK_ORDER: bool = False


def _get_held() -> list[tuple[int, str]]:
    """Return the current thread's held-lock stack."""
    try:
        return _held_tiers.get()
    except LookupError:
        stack: list[tuple[int, str]] = []
        _held_tiers.set(stack)
        return stack


class OrderedLock:
    """
    A ``threading.Lock`` wrapper that validates acquisition order in debug mode.

    In normal mode (``DEBUG_LOCK_ORDER = False``), this is a zero-overhead
    wrapper — ``acquire`` / ``release`` delegate directly to the inner lock.

    In debug mode, every ``acquire`` checks that no lock from a **higher**
    tier is already held on the current thread.  Violations are logged as
    warnings (not exceptions) so they surface in CI without crashing builds.

    Args:
        tier: Numeric tier from the constants above.
        name: Human-readable label (e.g. ``"ProvenanceStore._lock"``).
        lock: Optional pre-existing lock to wrap.  If ``None``, a new
              ``threading.Lock()`` is created.

    Example::

        from bengal.concurrency import OrderedLock, TIER_CACHE_INFRASTRUCTURE

        class MyCache:
            def __init__(self) -> None:
                self._lock = OrderedLock(
                    TIER_CACHE_INFRASTRUCTURE,
                    "MyCache._lock",
                )

            def get(self, key: str) -> str | None:
                with self._lock:
                    return self._data.get(key)

    """

    __slots__ = ("_inner", "_name", "_tier")

    def __init__(
        self,
        tier: int,
        name: str,
        lock: threading.Lock | None = None,
    ) -> None:
        self._tier = tier
        self._name = name
        self._inner = lock if lock is not None else threading.Lock()

    # -- context-manager protocol ------------------------------------------

    def __enter__(self) -> OrderedLock:
        self.acquire()
        return self

    def __exit__(self, *_: Any) -> None:
        self.release()

    # -- lock protocol -----------------------------------------------------

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        """Acquire the lock, checking tier ordering in debug mode."""
        if DEBUG_LOCK_ORDER:
            self._check_order()
        result = self._inner.acquire(blocking=blocking, timeout=timeout)
        if result and DEBUG_LOCK_ORDER:
            _get_held().append((self._tier, self._name))
        return result

    def release(self) -> None:
        """Release the lock and pop from the held stack in debug mode."""
        self._inner.release()
        if DEBUG_LOCK_ORDER:
            stack = _get_held()
            # Pop the most recent entry for this lock (LIFO)
            for i in range(len(stack) - 1, -1, -1):
                if stack[i] == (self._tier, self._name):
                    stack.pop(i)
                    break

    def locked(self) -> bool:
        """Return whether the lock is currently held."""
        return self._inner.locked()

    # -- internals ---------------------------------------------------------

    def _check_order(self) -> None:
        """Warn if acquiring this lock would violate tier ordering."""
        stack = _get_held()
        for held_tier, held_name in stack:
            if held_tier > self._tier:
                logger.warning(
                    "LOCK ORDER VIOLATION: acquiring %s (tier %d: %s) "
                    "while holding %s (tier %d: %s)",
                    self._name,
                    self._tier,
                    _TIER_NAMES.get(self._tier, "?"),
                    held_name,
                    held_tier,
                    _TIER_NAMES.get(held_tier, "?"),
                )

    def __repr__(self) -> str:
        tier_label = _TIER_NAMES.get(self._tier, f"tier-{self._tier}")
        return f"OrderedLock({tier_label!r}, {self._name!r})"


def check_lock_order(tier: int, name: str) -> None:
    """
    Standalone ordering check for code that uses plain ``threading.Lock``.

    Call this immediately before acquiring a lock when you cannot swap in
    ``OrderedLock`` (e.g. third-party code or hot paths where the wrapper
    overhead is unacceptable).

    Does nothing when ``DEBUG_LOCK_ORDER`` is ``False``.

    Args:
        tier: The tier of the lock about to be acquired.
        name: Human-readable lock name for diagnostics.

    """
    if not DEBUG_LOCK_ORDER:
        return
    stack = _get_held()
    for held_tier, held_name in stack:
        if held_tier > tier:
            logger.warning(
                "LOCK ORDER VIOLATION: acquiring %s (tier %d: %s) "
                "while holding %s (tier %d: %s)",
                name,
                tier,
                _TIER_NAMES.get(tier, "?"),
                held_name,
                held_tier,
                _TIER_NAMES.get(held_tier, "?"),
            )


def held_locks() -> list[tuple[int, str]]:
    """
    Return a snapshot of locks held by the current thread (debug mode only).

    Returns an empty list when ``DEBUG_LOCK_ORDER`` is ``False``.

    Returns:
        List of ``(tier, name)`` tuples in acquisition order.

    """
    if not DEBUG_LOCK_ORDER:
        return []
    return list(_get_held())
