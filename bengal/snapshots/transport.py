"""
Transport helpers for moving the frozen render world across heap boundaries.

Issue #350, saga S2 — make the ``SiteSnapshot`` graph shareable by separate-heap
render workers. Two transport vehicles are supported by the isolated render
backend (``bengal/orchestration/render/isolated/``):

- **fork + copy-on-write** (the efficient path): a forked worker inherits the
  whole parsed-site graph for free. The catch under free-threading is that merely
  *reading* a Python object writes its refcount, which dirties the shared page and
  triggers a copy-on-write — defeating the sharing. :func:`immortalize_snapshot`
  marks the frozen read-set immortal (``_Py_SetImmortal``) so reads write nothing
  and the COW pages stay shared. Immortalization leaks for the life of the
  process, which is fine for a one-shot CLI/CI build but never the dev server.

- **spawn + serialization** (the portable path): the snapshot's config views are
  ``MappingProxyType``, which does not pickle. :func:`proxy_to_plain` deep-copies
  the proxy layers into plain ``dict`` for transport.

Everything here is best-effort and guarded: if the interpreter does not expose
``_Py_SetImmortal``, immortalization is a no-op and the fork backend still renders
correctly — just with more copy-on-write traffic.
"""

from __future__ import annotations

import ctypes
import dataclasses
import gc
import sys
from types import (
    BuiltinFunctionType,
    BuiltinMethodType,
    FunctionType,
    MappingProxyType,
    MethodType,
    ModuleType,
)
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.snapshots.types import SiteSnapshot

__all__ = [
    "immortalize",
    "immortalize_snapshot",
    "is_immortal",
    "proxy_to_plain",
    "supports_immortalization",
]

# Immortal objects carry a sentinel refcount well above any real count. The exact
# value differs across builds (free-threaded vs default), so we test against a
# threshold rather than an exact constant.
_IMMORTAL_REFCNT_THRESHOLD = 1 << 30

# Only recurse the object graph through the frozen snapshot's own data structures
# and plain containers. This is the load-bearing safety boundary: snapshot types
# embed a NavTree whose nodes reference the *mutable* Site/Page graph, and config
# values can be arbitrary user frontmatter. Recursing generically would escape
# into the whole interpreter (and immortalize the mutable world). We immortalize
# any object we reach, but only follow referents of these container kinds.
_RECURSE_CONTAINERS = (tuple, list, set, frozenset, dict, MappingProxyType)
_RECURSE_DATACLASS_MODULES = frozenset(
    {
        "bengal.snapshots.types",
        "bengal.snapshots.render_plan",  # PageView/RenderPlan graph (issue #350, S11)
        "bengal.config.snapshot",
    }
)

# Code objects we must never immortalize even if one is reachable as a leaf in
# config/data (immortalizing leaks them for the process lifetime). `type` covers
# classes; the rest cover modules and callables.
_NEVER_IMMORTAL = (
    type,
    ModuleType,
    FunctionType,
    BuiltinFunctionType,
    MethodType,
    BuiltinMethodType,
)


def _resolve_set_immortal() -> Any | None:
    """Return the ``_Py_SetImmortal`` C function, or None if unavailable."""
    fn = getattr(ctypes.pythonapi, "_Py_SetImmortal", None)
    if fn is None:
        return None
    fn.argtypes = [ctypes.py_object]
    fn.restype = None
    return fn


_SET_IMMORTAL = _resolve_set_immortal()


def supports_immortalization() -> bool:
    """Whether this interpreter exposes a usable immortalization entry point."""
    return _SET_IMMORTAL is not None


def is_immortal(obj: object) -> bool:
    """
    Best-effort check whether ``obj`` is immortal (refcount frozen).

    Uses the sentinel-refcount heuristic; ``getrefcount`` itself adds a temporary
    reference, but an immortal object's count is astronomically above the
    threshold so the +1 is irrelevant.
    """
    try:
        return sys.getrefcount(obj) >= _IMMORTAL_REFCNT_THRESHOLD
    except TypeError:
        return False


def immortalize(obj: object) -> bool:
    """
    Mark a single object immortal so its refcount never changes again.

    Returns True if the object is immortal afterward, False if the operation is
    unsupported on this interpreter. Idempotent and safe to call on any object.
    """
    if _SET_IMMORTAL is None:
        return False
    try:
        _SET_IMMORTAL(ctypes.py_object(obj))
    except Exception:
        return False
    return True


def _should_recurse(obj: object) -> bool:
    """Whether to follow ``obj``'s referents (bounded to the frozen world)."""
    if isinstance(obj, _RECURSE_CONTAINERS):
        return True
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return type(obj).__module__ in _RECURSE_DATACLASS_MODULES
    return False


def immortalize_snapshot(snapshot: SiteSnapshot) -> int:
    """
    Immortalize the frozen ``SiteSnapshot`` graph for copy-on-write fork sharing.

    Walks the snapshot's frozen data graph (pages, sections, config/params/data
    views, navigation/taxonomy/schedule plans and their leaf strings/tuples) and
    marks every reached object immortal, so a forked worker's reads never dirty
    the shared COW pages. Traversal is bounded to snapshot dataclasses and plain
    containers (see ``_RECURSE_*``) so it cannot escape into the mutable Site
    graph reachable via NavTree nodes.

    Args:
        snapshot: The frozen site snapshot to immortalize.

    Returns:
        Count of objects immortalized (0 if the interpreter has no
        ``_Py_SetImmortal``).
    """
    if _SET_IMMORTAL is None:
        return 0

    seen: set[int] = set()
    stack: list[object] = [snapshot]
    count = 0

    # Disable GC during the walk: we're handing the collector a large, briefly
    # inconsistent worklist and there is no allocation pressure to relieve.
    gc_was_enabled = gc.isenabled()
    if gc_was_enabled:
        gc.disable()
    try:
        while stack:
            obj = stack.pop()
            oid = id(obj)
            if oid in seen:
                continue
            seen.add(oid)

            # Never touch types/modules/functions — only data. (Normally
            # unreachable given the bounded traversal, but a stray callable in
            # config/data must not be immortalized/leaked.)
            if obj is None or isinstance(obj, _NEVER_IMMORTAL):
                continue

            if immortalize(obj):
                count += 1

            if _should_recurse(obj):
                stack.extend(gc.get_referents(obj))
    finally:
        if gc_was_enabled:
            gc.enable()

    return count


def proxy_to_plain(obj: Any) -> Any:
    """
    Recursively convert ``MappingProxyType`` views to plain dicts for pickling.

    The snapshot's ``config``/``params``/``data`` are ``MappingProxyType`` (and
    may nest more proxies), which ``pickle`` cannot serialize. This produces a
    picklable deep copy of the *mapping structure*; leaf scalars are shared, not
    copied. Tuples and lists are walked so nested proxies inside them are
    converted too.

    Use this on the spawn transport path. The fork path does not need it (workers
    inherit the proxies directly via COW).
    """
    if isinstance(obj, MappingProxyType):
        return {k: proxy_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, dict):
        return {k: proxy_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [proxy_to_plain(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(proxy_to_plain(v) for v in obj)
    return obj
