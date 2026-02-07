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

Immutable Snapshot Evaluation
-----------------------------
Bengal already has a mature snapshot system (``bengal/snapshots/``) that creates
frozen dataclasses after content discovery (Phase 5) and before rendering.
``SiteSnapshot``, ``PageSnapshot``, ``SectionSnapshot``, ``CascadeSnapshot``,
and ``TemplateSnapshot`` are all ``frozen=True, slots=True`` and provide
lock-free access to core site data during parallel rendering.

This evaluation assesses which *remaining* lock-protected mutable state could
be converted to immutable snapshots, and where the snapshot pattern is
impractical.

**What is already snapshotted (no further action needed):**

- Page lists (``pages``, ``regular_pages``): ``SiteSnapshot.pages``
- Section tree with navigation: ``SiteSnapshot.sections``, ``SectionSnapshot``
- Taxonomy data (tag → pages): ``SiteSnapshot.taxonomies``
- Cascade metadata: ``CascadeSnapshot`` with O(1) pre-merged resolution
- Template dependency graph: ``SiteSnapshot.templates``, ``template_dependents``
- Config and site params: ``SiteSnapshot.config``, ``ConfigSnapshot``
- Menu structure: ``SiteSnapshot.menus``
- Scheduling structures: ``topological_order``, ``template_groups``, etc.

**HIGH benefit — Tier 3 (Rendering) locks eliminable via snapshots:**

1. **NavTreeCache** (``_lock`` + ``_build_locks``, 2 locks)

   The navigation tree is built from section/page data that is fully determined
   at snapshot time.  Pre-computing the NavTree inside ``create_site_snapshot()``
   would eliminate both the class-level site-invalidation lock and the
   per-version ``PerKeyLockManager`` locks.

   - Data: ``NavTree`` objects keyed by version_id
   - Lock eliminated: ``NavTreeCache._lock`` (Tier 3), ``NavTreeCache._build_locks``
   - Memory overhead: Negligible (~1-10 KB HTML per version)
   - Feasibility: **HIGH** — NavTree depends solely on sections/pages, already
     frozen in ``SectionSnapshot``.  The ``NavTree.build()`` call can move into
     the snapshot builder.

2. **NavScaffoldCache** (``_lock`` + ``_render_locks``, 2 locks)

   Identical pattern to NavTreeCache.  Scaffold HTML is rendered from navigation
   data, which is fully available at snapshot time.

   - Lock eliminated: ``NavScaffoldCache._lock``, ``NavScaffoldCache._render_locks``
   - Memory overhead: Small (~1-5 KB per scaffold)
   - Feasibility: **HIGH** — purely derived from snapshotted navigation data.

3. **Renderer._cache_lock** (1 lock)

   Protects lazy initialization of ``_top_level_cache`` and ``_tag_pages_cache``.
   Both are deterministic views of site data (filter pages by section membership,
   filter taxonomy pages by type).  Pre-computing these in the snapshot builder
   would eliminate the double-checked locking pattern.

   - Lock eliminated: ``Renderer._cache_lock`` (Tier 3)
   - Memory overhead: Negligible (already cached; only moving *when* computed)
   - Feasibility: **HIGH** — top-level content and tag page filtering are pure
     functions of page/section/taxonomy data.

4. **_global_context_cache** / ``_context_lock`` (1 lock)

   Caches four stateless context wrappers (``SiteContext``, ``ConfigContext``,
   ``ThemeContext``, ``MenusContext``) per site instance.  These could be created
   once during the snapshot phase and stored as a frozen field.

   - Lock eliminated: ``_context_lock`` (Tier 3)
   - Memory overhead: 4 wrapper objects — negligible
   - Feasibility: **HIGH** — trivial to pre-create during snapshot.

5. **_directive_cache** / ``_config_lock`` (1 lock)

   The ``_config_lock`` only guards replacement of the global ``DirectiveCache``
   instance.  The ``DirectiveCache`` itself uses ``LRUCache`` with its own
   internal ``RLock``.  Snapshotting the configuration at build start would
   eliminate the need to reconfigure mid-build.

   - Lock eliminated: ``_config_lock`` (Tier 3)
   - Internal ``LRUCache._lock`` remains (needed for LRU eviction)
   - Feasibility: **MEDIUM** — config changes are rare; the internal LRU lock
     persists regardless.

   *Subtotal: 7 locks eliminable (Tier 3).*

**MODERATE benefit — Tier 1 (Cache Infrastructure) locks reducible:**

6. **TaxonomyIndex._lock** (RLock)

   During rendering, ``TaxonomyIndex`` is read-only; writes happen exclusively
   during content discovery (Phase 5).  The read-side lock could be eliminated
   if rendering consumed taxonomy data from ``SiteSnapshot.taxonomies`` instead
   of querying the mutable ``TaxonomyIndex``.

   - Lock impact: RLock contention eliminated during render phase
   - Memory overhead: None — ``SiteSnapshot.taxonomies`` already duplicates this
   - Feasibility: **MEDIUM** — the ``TaxonomyIndex`` is also a persistent cache
     that writes to disk; its lock is still needed for the write path and for
     incremental builds.  The render-phase benefit is already partially captured
     by ``SiteSnapshot.taxonomies``.

7. **QueryIndex._lock** (RLock)

   Same pattern as ``TaxonomyIndex``.  Read-only during rendering, writable
   during discovery.  Render-phase reads could use snapshot data.

   - Feasibility: **MEDIUM** — same analysis as TaxonomyIndex.

8. **Icon resolver** / ``_icon_lock`` (Lock)

   Read-heavy with lazy population.  Could pre-load all icons at snapshot time,
   converting ``_icon_cache`` and ``_not_found_cache`` into frozen dicts.

   - Lock eliminated: ``_icon_lock`` (Tier 4)
   - Memory overhead: Small (~100-500 SVG strings, typically <50 KB total)
   - Feasibility: **MEDIUM** — requires knowing which icons are used before
     rendering starts.  A ``preload=True`` path already exists; snapshotting
     would formalize it.

   *Subtotal: 2-3 locks reducible (contention eliminated during render).*

**LOW / NO benefit — snapshot pattern impractical:**

9. **ContentHashRegistry._lock** (RLock, Tier 1)

   Updated *during* rendering (output hashes written as pages render) AND read
   for incremental decisions.  Writes and reads are interleaved in the hot path.

   - Why not: Inherently mutable during the render phase.  A snapshot would be
     stale immediately.

10. **ProvenanceStore._lock** (Lock, Tier 1)

    Written during rendering (provenance records created per page), read for
    incremental build decisions.  Writes are interleaved with rendering.

    - Why not: Write-heavy workload during rendering.

11. **GeneratedPageCache._lock** (Lock, Tier 1)

    Needs mutation during rendering — generated pages (tag pages, archive pages)
    check and update this cache as they render.

    - Why not: Fundamentally a write-through cache during the render phase.

12. **DependencyTracker.lock** (Lock, Tier 2)

    Tracks file dependencies discovered during rendering.  New dependencies are
    registered as templates include files or pages reference assets.

    - Why not: Dependency tracking is inherently append-only during rendering.

13. **EffectTracer._lock** (Lock, Tier 2)

    Records build effects (files written, dirs created) during rendering.

    - Why not: Inherently mutable — accumulates effects as they happen.

14. **Progress/IO locks** (Tier 5, all locks)

    Track mutable counters (``_completed_count``, ``_writes_completed``).
    Cannot be pre-computed.

    - Why not: Progress counters are inherently mutable.

15. **Server locks** (Tier 6, all locks)

    Dev server locks handle real-time file change events and cache invalidation.
    They operate outside the build lifecycle.

    - Why not: Real-time mutation by definition.

16. **Error session locks** (Tier 7)

    Accumulate errors during rendering.  Cannot be pre-computed.

    - Why not: Error recording is inherently append-only.

**Estimated lock reduction summary:**

+------------------------------+-------+-----------------------------------+
| Category                     | Locks | Impact                            |
+==============================+=======+===================================+
| Already snapshotted          | —     | Core site data: no locks needed   |
+------------------------------+-------+-----------------------------------+
| Eliminable (Tier 3 hot path) | ~7    | NavTree(2), NavScaffold(2),       |
|                              |       | Renderer(1), context(1),          |
|                              |       | directive_config(1)               |
+------------------------------+-------+-----------------------------------+
| Reducible (render-phase)     | ~2-3  | TaxonomyIndex, QueryIndex, icons  |
+------------------------------+-------+-----------------------------------+
| Impractical                  | ~30   | Write-heavy, counters, server,    |
|                              |       | error tracking, dependency graph  |
+------------------------------+-------+-----------------------------------+

Of ~40 total locks, ~7 are eliminable and ~2-3 more are reducible.  The
absolute count (~20-25% of locks) understates the impact: the eliminable
locks are concentrated in **Tier 3 (Rendering)**, which is the hottest
contention path because all render threads compete for these caches
simultaneously.

**Recommended next steps (priority order):**

1. **Pre-compute NavTree at snapshot time** (eliminates 4 locks, highest ROI).
   Add a ``nav_trees: MappingProxyType[str, NavTree]`` field to ``SiteSnapshot``.
   The ``NavTreeCache.get()`` method becomes a simple dict lookup on the snapshot.

2. **Pre-compute tag pages and top-level content in snapshot builder** (eliminates
   1 lock).  Add ``top_level_pages``, ``top_level_sections``, and a tag-pages
   mapping to ``SiteSnapshot``.  Renderer reads these directly instead of
   lazy-computing under lock.

3. **Create global context wrappers during snapshot phase** (eliminates 1 lock).
   Store pre-built ``SiteContext``, ``ConfigContext``, ``ThemeContext``,
   ``MenusContext`` alongside the snapshot.

4. **Pre-load icons at snapshot time** (eliminates 1 lock, optional).
   Formalize the existing ``preload=True`` path into the snapshot lifecycle.

5. **Route render-phase taxonomy reads through SiteSnapshot** (reduces
   contention on ``TaxonomyIndex._lock``).  This is partially done already
   but not consistently enforced.

Steps 1-3 can be done incrementally without breaking changes.  Each step
is independently shippable and testable.

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
