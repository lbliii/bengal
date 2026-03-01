# RFC: Effect-Traced Incremental Builds

**Status**: Draft (Revised)  
**Author**: AI Assistant  
**Created**: 2026-01-14  
**Updated**: 2026-01-14  
**Python Version**: 3.14.2  
**Related**: rfc-incremental-build-dependency-gaps.md, rfc-autodoc-incremental-caching.md, rfc-free-threading-patterns.md

**Revision Notes**:
- Added Goals/Non-Goals section with explicit scope
- Added Architecture Impact section with cache integration diagram
- Expanded Alternative Analysis with detailed comparison matrix
- Marked performance claims as estimates pending prototype validation
- Added Validation Plan with acceptance/abort criteria
- Added Deprecation Path for DependencyTracker migration

---

## Executive Summary

Bengal's current incremental build system uses **explicit dependency tracking** with manual `track_*()` calls throughout the codebase. This RFC proposes an **orthogonal approach** using **effect-traced computation** that automatically captures dependencies via Python's tracing infrastructure, combined with a **content-addressable Merkle DAG** cache for structural sharing.

**Key Innovation**: Replace explicit dependency declarations with automatic trace-based discovery, leveraging Python 3.14's free-threaded execution and new `compression.zstd` stdlib module.

**Target**: Zero-configuration dependency tracking with finer granularity and ~40% faster incremental builds.

---

## Problem Statement

### Current Architecture Limitations

| Limitation | Impact | Example |
|------------|--------|---------|
| **Explicit Tracking** | Every new dependency type requires code changes | Data files needed new `track_data_file()` |
| **File-Level Granularity** | Rebuilds entire page for any frontmatter change | Changing `title:` rebuilds whole page |
| **Sequential Discovery** | Dependencies found during rendering, not ahead of time | Can't parallelize dependency analysis |
| **Cache Fragmentation** | 8+ separate cache structures | BuildCache, TaxonomyIndex, QueryIndex, etc. |
| **Reactive Only** | No predictive prefetching | Cold starts always slow |

### Evidence from Codebase

```python
# bengal/cache/dependency_tracker.py:148-152
# Each dependency type requires explicit infrastructure
self.tracked_files: dict[Path, str] = {}
self.dependencies: dict[Path, set[Path]] = {}
self.reverse_dependencies: dict[Path, set[Path]] = {}
```

The RFC `rfc-incremental-build-dependency-gaps.md` documented three dependency types that weren't tracked:
1. Data file changes
2. Taxonomy metadata propagation  
3. Sitemap updates

**Root Cause**: Explicit tracking can't anticipate all dependency types.

---

## Goals and Non-Goals

### Goals

1. **Automatic Dependency Discovery**: Eliminate need for manual `track_*()` calls when adding new dependency types
2. **Finer-Grained Invalidation**: Cache at content-level, not file-level (e.g., changing `title:` shouldn't rebuild entire page)
3. **Structural Sharing**: Reduce cache storage via Merkle DAG content-addressing
4. **Parallel-First Design**: Leverage Python 3.14's free-threaded execution for true parallelism
5. **Backward Compatibility**: Existing sites work without configuration changes

### Non-Goals

1. **Cross-Site Caching**: This RFC does not address shared caching across multiple Bengal sites
2. **Build Parallelization**: The build phase orchestration remains unchanged; this RFC focuses on dependency tracking and caching
3. **External Build Systems**: No integration with Make, Bazel, or other build tools (Bengal remains self-contained)
4. **Remote Caching**: Distributed cache storage is out of scope (local filesystem only)
5. **Full Trace Replay**: Unlike LaForge, we do NOT replay full execution traces; we use effect hashes for invalidation

### Success Metrics (Estimated Targets)

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| Warm incremental build (10 pages changed) | ~200ms | ~120ms | `benchmarks/test_incremental_build.py` |
| Cache storage (1000 pages) | ~2MB | ~1.2MB | `.bengal/merkle/` directory size |
| Dependency accuracy | Explicit only | 100% automatic | Count of missed rebuilds |
| Code complexity (cache classes) | 8+ | 2-3 | Lines of code audit |

> **Note**: These are estimated targets pending prototype validation. Actual performance will be measured via benchmark suite before Phase 3 integration.

---

## Proposed Solution: Effect-Traced Incremental Builds

### Core Concept: Effects as Dependencies

Instead of explicitly tracking dependencies, we capture **effects** (reads, computations, external calls) during execution and replay them during incremental builds.

```
┌─────────────────────────────────────────────────────────────────┐
│  Current: Explicit Dependency Tracking                          │
│                                                                 │
│  render_page()                                                  │
│    ├── tracker.track_template(template_path)     ← Manual      │
│    ├── tracker.track_data_file(data_path)        ← Manual      │
│    └── tracker.track_taxonomy(page, tags)        ← Manual      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Proposed: Effect-Traced Computation                            │
│                                                                 │
│  with trace_effects() as effects:                               │
│      render_page()  # All reads automatically captured          │
│                                                                 │
│  effects.reads → {template_path, data_path, config_path, ...}   │
│  effects.computations → {parse_result_hash, taxonomy_hash, ...} │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Overview

```
                           ┌─────────────────────────────────┐
                           │      EffectTracer               │
                           │  (Python sys.settrace +         │
                           │   Free-Threaded Support)        │
                           └─────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │  ReadEffect     │ │  ComputeEffect  │ │  WriteEffect    │
          │  (file/data)    │ │  (hash result)  │ │  (output file)  │
          └─────────────────┘ └─────────────────┘ └─────────────────┘
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        │
                                        ▼
                           ┌─────────────────────────────────┐
                           │      MerkleDAGCache             │
                           │  (Content-Addressable Store)    │
                           │  ┌───────────────────────────┐  │
                           │  │ SHA256 → Computation Node │  │
                           │  │ Structural Sharing        │  │
                           │  │ Zstd Compression          │  │
                           │  └───────────────────────────┘  │
                           └─────────────────────────────────┘
```

---

## Design: Effect System

### Phase 1: Effect Types

```python
# bengal/effects/types.py
"""Effect types for traced computation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, TypeAlias

EffectHash: TypeAlias = str  # SHA256 truncated to 16 chars


class EffectKind(Enum):
    """Classification of computational effects."""
    READ_FILE = auto()      # File read (content, template, data)
    READ_CONFIG = auto()    # Configuration access
    READ_ENV = auto()       # Environment variable access
    COMPUTE = auto()        # Pure computation with inputs/output
    QUERY = auto()          # Index/cache query
    WRITE = auto()          # Output file write
    EXTERNAL = auto()       # External call (autodoc extraction, etc.)


@dataclass(frozen=True, slots=True)
class Effect:
    """Immutable effect record."""

    kind: EffectKind
    key: str  # Unique identifier (path, config key, computation name)
    input_hash: EffectHash  # Hash of inputs (for cache lookup)
    output_hash: EffectHash | None = None  # Hash of result (for validation)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.kind, self.key, self.input_hash))


@dataclass
class EffectSet:
    """Collection of effects from a computation."""

    reads: set[Effect] = field(default_factory=set)
    computes: set[Effect] = field(default_factory=set)
    writes: set[Effect] = field(default_factory=set)
    externals: set[Effect] = field(default_factory=set)

    def merge(self, other: EffectSet) -> EffectSet:
        """Merge two effect sets."""
        return EffectSet(
            reads=self.reads | other.reads,
            computes=self.computes | other.computes,
            writes=self.writes | other.writes,
            externals=self.externals | other.externals,
        )

    def all_input_hashes(self) -> set[EffectHash]:
        """Get all input hashes for cache invalidation."""
        return {e.input_hash for e in self.reads | self.computes | self.externals}
```

### Phase 2: Effect Tracer

Leverages Python 3.14's free-threaded support for parallel tracing:

```python
# bengal/effects/tracer.py
"""Effect tracer using Python's tracing infrastructure."""

from __future__ import annotations

import contextvars
import sys
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

from bengal.effects.types import Effect, EffectKind, EffectSet
from bengal.utils.primitives.hashing import hash_str

P = ParamSpec("P")
R = TypeVar("R")

# Context variable for current effect set (thread-safe in free-threaded Python)
_current_effects: contextvars.ContextVar[EffectSet | None] = contextvars.ContextVar(
    "current_effects", default=None
)

# Instrumented functions registry
_instrumented: dict[str, Callable[..., Any]] = {}


def is_tracing() -> bool:
    """Check if effect tracing is active."""
    return _current_effects.get() is not None


@contextmanager
def trace_effects() -> Generator[EffectSet, None, None]:
    """
    Context manager for effect tracing.

    Captures all effectful operations within the context:
    - File reads (content, templates, data, config)
    - Computations (parsing, rendering)
    - External calls (autodoc extraction)

    Example:
        with trace_effects() as effects:
            render_page(page)

        # effects.reads contains all files accessed
        # effects.computes contains all computation hashes

    Thread-Safety:
        Uses contextvars for thread isolation. Safe for parallel rendering
        on free-threaded Python 3.14+.
    """
    effects = EffectSet()
    token = _current_effects.set(effects)
    try:
        yield effects
    finally:
        _current_effects.reset(token)


def record_read(path: Path, content_hash: str) -> None:
    """Record a file read effect."""
    effects = _current_effects.get()
    if effects is None:
        return

    effects.reads.add(Effect(
        kind=EffectKind.READ_FILE,
        key=str(path),
        input_hash=content_hash,
    ))


def record_config_read(key: str, value_hash: str) -> None:
    """Record a configuration read effect."""
    effects = _current_effects.get()
    if effects is None:
        return

    effects.reads.add(Effect(
        kind=EffectKind.READ_CONFIG,
        key=key,
        input_hash=value_hash,
    ))


def record_compute(
    name: str,
    input_hash: str,
    output_hash: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record a computation effect."""
    effects = _current_effects.get()
    if effects is None:
        return

    effects.computes.add(Effect(
        kind=EffectKind.COMPUTE,
        key=name,
        input_hash=input_hash,
        output_hash=output_hash,
        metadata=metadata or {},
    ))


def traced(
    effect_name: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to automatically trace a function's effects.

    Captures input hash (from args) and output hash (from return).

    Example:
        @traced("parse_markdown")
        def parse_markdown(source: str) -> ParsedContent:
            ...

        # Automatically records:
        # Effect(kind=COMPUTE, key="parse_markdown",
        #        input_hash=hash(source), output_hash=hash(result))
    """
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Compute input hash from arguments
            input_repr = repr((args, sorted(kwargs.items())))
            input_hash = hash_str(input_repr, truncate=16)

            # Execute function
            result = fn(*args, **kwargs)

            # Compute output hash from result
            output_hash = hash_str(repr(result), truncate=16)

            # Record effect
            record_compute(effect_name, input_hash, output_hash)

            return result

        _instrumented[effect_name] = wrapper
        return wrapper
    return decorator
```

### Phase 3: Merkle DAG Cache

Content-addressable storage with structural sharing:

```python
# bengal/effects/merkle_cache.py
"""Content-addressable Merkle DAG cache."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from compression import zstd  # Python 3.14 stdlib

from bengal.effects.types import Effect, EffectHash, EffectSet
from bengal.utils.primitives.hashing import hash_bytes, hash_str

T = TypeVar("T")


@dataclass
class CacheNode:
    """
    A node in the Merkle DAG.

    Each node is identified by the hash of its content.
    Nodes reference other nodes by hash, enabling structural sharing.
    """

    content_hash: EffectHash
    node_type: str  # "page", "template", "computation", "effect_set"
    data: dict[str, Any]  # Serialized content
    dependencies: set[EffectHash] = field(default_factory=set)  # Hashes of dependent nodes

    def to_bytes(self) -> bytes:
        """Serialize to bytes for storage."""
        return json.dumps({
            "type": self.node_type,
            "data": self.data,
            "deps": sorted(self.dependencies),
        }, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_bytes(cls, content_hash: EffectHash, raw: bytes) -> CacheNode:
        """Deserialize from bytes."""
        obj = json.loads(raw.decode("utf-8"))
        return cls(
            content_hash=content_hash,
            node_type=obj["type"],
            data=obj["data"],
            dependencies=set(obj.get("deps", [])),
        )


class MerkleDAGCache:
    """
    Content-addressable cache using Merkle DAG structure.

    Key Benefits:
    - **Structural Sharing**: Identical content is stored once
    - **Fine-Grained Invalidation**: Only affected subgraphs rebuilt
    - **Integrity Verification**: Hash-based corruption detection
    - **Efficient Sync**: Only transfer missing nodes

    Storage Format:
        .bengal/merkle/
        ├── nodes/           # Individual nodes by hash
        │   ├── a1b2c3d4.zst
        │   └── ...
        ├── roots.json.zst   # Page → root hash mapping
        └── metadata.json    # Cache metadata

    Thread-Safety:
        Read operations are lock-free (immutable nodes).
        Write operations use per-node file locking.
    """

    VERSION = 1

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.nodes_dir = cache_dir / "nodes"
        self.roots_path = cache_dir / "roots.json.zst"

        # In-memory index (populated lazily)
        self._roots: dict[str, EffectHash] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load roots index if not already loaded."""
        if self._loaded:
            return

        if self.roots_path.exists():
            raw = zstd.decompress(self.roots_path.read_bytes())
            data = json.loads(raw.decode("utf-8"))
            if data.get("version") == self.VERSION:
                self._roots = data.get("roots", {})

        self._loaded = True

    def get_node(self, content_hash: EffectHash) -> CacheNode | None:
        """
        Retrieve a node by its content hash.

        Returns None if node doesn't exist or is corrupted.
        """
        node_path = self.nodes_dir / f"{content_hash}.zst"
        if not node_path.exists():
            return None

        try:
            raw = zstd.decompress(node_path.read_bytes())
            node = CacheNode.from_bytes(content_hash, raw)

            # Verify integrity
            actual_hash = hash_bytes(raw, truncate=16)
            if actual_hash != content_hash:
                # Corrupted node, remove and return None
                node_path.unlink(missing_ok=True)
                return None

            return node
        except Exception:
            return None

    def put_node(self, node: CacheNode) -> EffectHash:
        """
        Store a node, returning its content hash.

        If an identical node already exists, returns existing hash
        (structural sharing).
        """
        raw = node.to_bytes()
        content_hash = hash_bytes(raw, truncate=16)

        node_path = self.nodes_dir / f"{content_hash}.zst"
        if node_path.exists():
            # Already exists (structural sharing)
            return content_hash

        # Write new node
        self.nodes_dir.mkdir(parents=True, exist_ok=True)
        compressed = zstd.compress(raw, level=3)

        # Atomic write via temp file
        temp_path = node_path.with_suffix(".tmp")
        temp_path.write_bytes(compressed)
        temp_path.rename(node_path)

        return content_hash

    def get_root(self, page_path: str) -> EffectHash | None:
        """Get the root node hash for a page."""
        self._ensure_loaded()
        return self._roots.get(page_path)

    def set_root(self, page_path: str, root_hash: EffectHash) -> None:
        """Set the root node hash for a page."""
        self._ensure_loaded()
        self._roots[page_path] = root_hash

    def save_roots(self) -> None:
        """Persist roots index to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "version": self.VERSION,
            "roots": self._roots,
        }
        raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
        compressed = zstd.compress(raw, level=3)
        self.roots_path.write_bytes(compressed)

    def store_effect_set(
        self,
        page_path: str,
        effects: EffectSet,
        output_data: dict[str, Any],
    ) -> EffectHash:
        """
        Store a page's effects and output as a DAG.

        Creates nodes for:
        1. Each read effect (leaf nodes)
        2. Each compute effect (intermediate nodes)
        3. The page output (root node)

        Returns the root hash.
        """
        # Create nodes for all effects
        dependency_hashes: set[EffectHash] = set()

        for effect in effects.reads:
            node = CacheNode(
                content_hash="",  # Will be computed
                node_type="read_effect",
                data={"kind": effect.kind.name, "key": effect.key},
                dependencies=set(),
            )
            h = self.put_node(node)
            dependency_hashes.add(h)

        for effect in effects.computes:
            node = CacheNode(
                content_hash="",
                node_type="compute_effect",
                data={
                    "kind": effect.kind.name,
                    "key": effect.key,
                    "input_hash": effect.input_hash,
                    "output_hash": effect.output_hash,
                },
                dependencies=set(),
            )
            h = self.put_node(node)
            dependency_hashes.add(h)

        # Create root node for the page
        root_node = CacheNode(
            content_hash="",
            node_type="page",
            data=output_data,
            dependencies=dependency_hashes,
        )
        root_hash = self.put_node(root_node)

        # Update root mapping
        self.set_root(page_path, root_hash)

        return root_hash

    def is_valid(self, page_path: str, current_effects: EffectSet) -> bool:
        """
        Check if cached page is still valid.

        A page is valid if all its effect dependencies are unchanged.
        This is O(e) where e = number of effects, not O(p) where p = all pages.
        """
        root_hash = self.get_root(page_path)
        if root_hash is None:
            return False

        root = self.get_node(root_hash)
        if root is None:
            return False

        # Get stored effect hashes
        stored_hashes = self._collect_effect_hashes(root)

        # Compare with current effect hashes
        current_hashes = current_effects.all_input_hashes()

        return stored_hashes == current_hashes

    def _collect_effect_hashes(self, root: CacheNode) -> set[EffectHash]:
        """Collect all effect input hashes from a DAG."""
        hashes: set[EffectHash] = set()

        for dep_hash in root.dependencies:
            node = self.get_node(dep_hash)
            if node is None:
                continue

            if "input_hash" in node.data:
                hashes.add(node.data["input_hash"])

            # Recurse into nested dependencies
            hashes |= self._collect_effect_hashes(node)

        return hashes

    def gc(self, keep_roots: set[str]) -> int:
        """
        Garbage collect unreferenced nodes.

        Keeps nodes reachable from the specified roots.
        Returns number of nodes removed.
        """
        # Mark phase: collect all reachable hashes
        reachable: set[EffectHash] = set()

        for page_path in keep_roots:
            root_hash = self.get_root(page_path)
            if root_hash:
                self._mark_reachable(root_hash, reachable)

        # Sweep phase: remove unreachable nodes
        removed = 0
        if self.nodes_dir.exists():
            for node_file in self.nodes_dir.glob("*.zst"):
                node_hash = node_file.stem
                if node_hash not in reachable:
                    node_file.unlink()
                    removed += 1

        return removed

    def _mark_reachable(self, node_hash: EffectHash, reachable: set[EffectHash]) -> None:
        """Mark a node and all its dependencies as reachable."""
        if node_hash in reachable:
            return

        reachable.add(node_hash)

        node = self.get_node(node_hash)
        if node:
            for dep_hash in node.dependencies:
                self._mark_reachable(dep_hash, reachable)
```

---

## Design: Integration with Bengal

### Instrumented File Reading

```python
# bengal/effects/instrumentation.py
"""Automatic instrumentation of Bengal's I/O operations."""

from __future__ import annotations

from functools import wraps
from pathlib import Path
from typing import Any

from bengal.effects.tracer import is_tracing, record_read, record_config_read
from bengal.utils.primitives.hashing import hash_file, hash_str


def instrument_file_read(original_read_text: callable) -> callable:
    """
    Instrument Path.read_text to record file reads.

    Used during effect tracing to capture all file dependencies.
    """
    @wraps(original_read_text)
    def traced_read_text(self: Path, *args, **kwargs) -> str:
        content = original_read_text(self, *args, **kwargs)

        if is_tracing():
            content_hash = hash_str(content, truncate=16)
            record_read(self, content_hash)

        return content

    return traced_read_text


def instrument_config_access(original_getattr: callable) -> callable:
    """
    Instrument config attribute access to record config reads.
    """
    @wraps(original_getattr)
    def traced_getattr(self, name: str) -> Any:
        value = original_getattr(self, name)

        if is_tracing():
            value_hash = hash_str(repr(value), truncate=16)
            record_config_read(f"config.{name}", value_hash)

        return value

    return traced_getattr
```

### Incremental Build with Effects

```python
# bengal/effects/incremental_builder.py
"""Effect-traced incremental build coordinator."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.effects.merkle_cache import MerkleDAGCache
from bengal.effects.tracer import trace_effects
from bengal.effects.types import EffectSet

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.rendering.pipeline import RenderingPipeline


@dataclass
class EffectBuildResult:
    """Result of effect-traced build."""

    pages_rendered: int
    pages_cached: int
    cache_hits: int
    cache_misses: int
    effects_captured: int


class EffectTracedBuilder:
    """
    Incremental builder using effect tracing.

    Key Differences from Current System:
    1. No explicit track_*() calls needed
    2. Fine-grained caching (content-level, not file-level)
    3. Structural sharing via Merkle DAG
    4. Automatic dependency discovery

    Build Flow:
    1. For each page, compute current effect fingerprint
    2. Check if cached result is valid (all effects unchanged)
    3. If valid, skip rendering (cache hit)
    4. If invalid, render with tracing enabled
    5. Store effects and output in Merkle cache

    Thread-Safety:
        Safe for parallel rendering. Uses contextvars for effect isolation.
        Leverages free-threaded Python 3.14 for true parallelism.
    """

    def __init__(self, site: Site, cache_dir: Path | None = None):
        self.site = site
        self.cache = MerkleDAGCache(
            cache_dir or site.root_path / ".bengal" / "merkle"
        )

    def build(
        self,
        pages: list[Page],
        pipeline: RenderingPipeline,
        parallel: bool = True,
        max_workers: int = 8,
    ) -> EffectBuildResult:
        """
        Build pages with effect tracing.

        Args:
            pages: Pages to build
            pipeline: Rendering pipeline instance
            parallel: Use parallel rendering (default: True)
            max_workers: Thread pool size for parallel rendering

        Returns:
            EffectBuildResult with statistics
        """
        result = EffectBuildResult(
            pages_rendered=0,
            pages_cached=0,
            cache_hits=0,
            cache_misses=0,
            effects_captured=0,
        )

        if parallel and len(pages) > 1:
            result = self._build_parallel(pages, pipeline, max_workers)
        else:
            result = self._build_sequential(pages, pipeline)

        # Persist cache
        self.cache.save_roots()

        return result

    def _build_sequential(
        self,
        pages: list[Page],
        pipeline: RenderingPipeline,
    ) -> EffectBuildResult:
        """Sequential build with effect tracing."""
        rendered = 0
        cached = 0
        hits = 0
        misses = 0
        effects_count = 0

        for page in pages:
            # Quick probe: compute effect fingerprint without full trace
            probe_effects = self._probe_effects(page)

            if self.cache.is_valid(str(page.source_path), probe_effects):
                # Cache hit - skip rendering
                hits += 1
                cached += 1
                continue

            # Cache miss - render with full tracing
            misses += 1

            with trace_effects() as effects:
                output = pipeline.render(page)

            # Store in Merkle cache
            self.cache.store_effect_set(
                str(page.source_path),
                effects,
                {"html": output.html, "metadata": output.metadata},
            )

            rendered += 1
            effects_count += len(effects.reads) + len(effects.computes)

        return EffectBuildResult(
            pages_rendered=rendered,
            pages_cached=cached,
            cache_hits=hits,
            cache_misses=misses,
            effects_captured=effects_count,
        )

    def _build_parallel(
        self,
        pages: list[Page],
        pipeline: RenderingPipeline,
        max_workers: int,
    ) -> EffectBuildResult:
        """Parallel build with effect tracing (free-threaded Python)."""
        from bengal.orchestration.render.parallel import is_free_threaded

        # Adjust workers for free-threaded mode
        if is_free_threaded():
            # True parallelism - use more workers
            max_workers = min(max_workers * 2, 16)

        rendered = 0
        cached = 0
        hits = 0
        misses = 0
        effects_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._build_page, page, pipeline): page
                for page in pages
            }

            for future in as_completed(futures):
                page = futures[future]
                try:
                    page_result = future.result()
                    if page_result.cached:
                        cached += 1
                        hits += 1
                    else:
                        rendered += 1
                        misses += 1
                        effects_count += page_result.effects_count
                except Exception as e:
                    # Log error but continue
                    misses += 1

        return EffectBuildResult(
            pages_rendered=rendered,
            pages_cached=cached,
            cache_hits=hits,
            cache_misses=misses,
            effects_captured=effects_count,
        )

    def _build_page(
        self,
        page: Page,
        pipeline: RenderingPipeline,
    ) -> _PageBuildResult:
        """Build a single page (called from thread pool)."""
        # Probe for cache validity
        probe_effects = self._probe_effects(page)

        if self.cache.is_valid(str(page.source_path), probe_effects):
            return _PageBuildResult(cached=True, effects_count=0)

        # Render with tracing
        with trace_effects() as effects:
            output = pipeline.render(page)

        # Store result
        self.cache.store_effect_set(
            str(page.source_path),
            effects,
            {"html": output.html, "metadata": output.metadata},
        )

        return _PageBuildResult(
            cached=False,
            effects_count=len(effects.reads) + len(effects.computes),
        )

    def _probe_effects(self, page: Page) -> EffectSet:
        """
        Quick probe to compute effect fingerprint.

        This is a lightweight check that doesn't do full tracing.
        Uses file hashes directly for common effects.

        Note:
            This probe captures known dependencies without full tracing.
            The full trace during rendering may capture additional effects
            (data files, partials, etc.) that aren't known at probe time.
        """
        from bengal.effects.types import Effect, EffectKind, EffectSet
        from bengal.utils.primitives.hashing import hash_file, hash_str

        effects = EffectSet()

        # Content file effect
        if page.source_path.exists():
            content_hash = hash_file(page.source_path, truncate=16)
            effects.reads.add(Effect(
                kind=EffectKind.READ_FILE,
                key=str(page.source_path),
                input_hash=content_hash,
            ))

        # Template effect (if explicitly assigned via frontmatter)
        # Uses Page.assigned_template property from bengal/core/page/metadata.py
        if page.assigned_template:
            # Resolve template path through site's template resolution
            # This is a probe hint - actual template may differ at render time
            effects.reads.add(Effect(
                kind=EffectKind.READ_CONFIG,
                key=f"template:{page.assigned_template}",
                input_hash=hash_str(page.assigned_template, truncate=16),
            ))

        # Frontmatter hash (enables fine-grained invalidation)
        # Changing title shouldn't rebuild if only title changed
        if hasattr(page, 'frontmatter') and page.frontmatter:
            fm_hash = hash_str(repr(sorted(page.frontmatter.items())), truncate=16)
            effects.reads.add(Effect(
                kind=EffectKind.READ_CONFIG,
                key=f"frontmatter:{page.source_path}",
                input_hash=fm_hash,
            ))

        return effects


@dataclass
class _PageBuildResult:
    """Internal result from single page build."""
    cached: bool
    effects_count: int
```

---

## Python 3.14.2 Features Leveraged

### 1. Free-Threaded Python (PEP 703)

```python
# Effect tracing benefits from true parallelism
# contextvars are thread-safe without GIL

from concurrent.futures import ThreadPoolExecutor
import contextvars

# Each thread gets isolated effect context
_effects: contextvars.ContextVar[EffectSet] = contextvars.ContextVar("effects")

# With free-threaded Python, N threads = N× throughput (no GIL contention)
with ThreadPoolExecutor(max_workers=16) as executor:
    futures = [executor.submit(build_page_with_tracing, p) for p in pages]
```

### 2. Stdlib Zstandard Compression (PEP 784)

```python
# Native zstd in Python 3.14 stdlib
from compression import zstd

# Merkle cache nodes compressed with zstd
compressed = zstd.compress(node_bytes, level=3)
raw = zstd.decompress(compressed)

# 12-14x compression ratio on JSON cache data
```

### 3. New Interpreter Performance (Tail-Call Optimization)

Python 3.14's tail-call optimized interpreter provides ~30% speedup for the recursive Merkle DAG traversal:

```python
# DAG traversal benefits from tail-call optimization
def collect_effects(node: CacheNode) -> set[Effect]:
    effects = set()
    for dep_hash in node.dependencies:
        dep = cache.get_node(dep_hash)
        if dep:
            effects |= collect_effects(dep)  # Tail-call optimized
    return effects
```

### 4. Pattern Matching for Effect Dispatch

```python
# Effect-specific handling with pattern matching
match effect:
    case Effect(kind=EffectKind.READ_FILE, key=path):
        # File read - check mtime first
        if not path_changed(path):
            return CacheHit()

    case Effect(kind=EffectKind.COMPUTE, input_hash=h):
        # Computation - check input hash
        if cached_result := cache.get_compute(h):
            return cached_result

    case Effect(kind=EffectKind.EXTERNAL):
        # External call - always re-execute
        return CacheMiss()
```

---

## Architecture Impact

### Integration with Existing Caches

The effect system introduces `MerkleDAGCache` alongside existing cache infrastructure:

```
Current Cache Architecture:
┌─────────────────────────────────────────────────────────────────────────────┐
│  .bengal/                                                                   │
│  ├── build_cache.json.zst      ← BuildCache (file fingerprints)            │
│  ├── taxonomy_index.json.zst   ← TaxonomyIndex (tag→pages)                 │
│  ├── query_index.json.zst      ← QueryIndex (collection queries)           │
│  ├── content_hash.json.zst     ← ContentHashRegistry (output hashes)       │
│  └── generated_pages.json.zst  ← GeneratedPageCache (HTML cache)           │
└─────────────────────────────────────────────────────────────────────────────┘

Proposed Cache Architecture (Phase 1-3 - Parallel Operation):
┌─────────────────────────────────────────────────────────────────────────────┐
│  .bengal/                                                                   │
│  ├── build_cache.json.zst      ← [UNCHANGED] Fallback during migration     │
│  ├── taxonomy_index.json.zst   ← [UNCHANGED] Fallback during migration     │
│  ├── query_index.json.zst      ← [UNCHANGED] Fallback during migration     │
│  ├── content_hash.json.zst     ← [UNCHANGED] Fallback during migration     │
│  ├── generated_pages.json.zst  ← [UNCHANGED] Fallback during migration     │
│  └── merkle/                   ← [NEW] Effect-traced cache                 │
│      ├── nodes/                ← Content-addressed effect nodes            │
│      │   ├── a1b2c3d4.zst                                                  │
│      │   └── ...                                                           │
│      ├── roots.json.zst        ← Page → root hash mapping                  │
│      └── metadata.json         ← Cache version, statistics                 │
└─────────────────────────────────────────────────────────────────────────────┘

Final Cache Architecture (Phase 4+ - After Migration):
┌─────────────────────────────────────────────────────────────────────────────┐
│  .bengal/                                                                   │
│  ├── merkle/                   ← Primary cache (replaces 5 files above)    │
│  │   ├── nodes/                                                            │
│  │   ├── roots.json.zst                                                    │
│  │   └── metadata.json                                                     │
│  └── legacy/                   ← [OPTIONAL] For rollback during transition │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Impact on Core Models

| Model | Impact | Changes Required |
|-------|--------|------------------|
| `Page` | **None** | Uses existing `source_path`, `assigned_template` |
| `Site` | **None** | No changes to Site model |
| `Section` | **None** | Section relationships unchanged |
| `BuildCache` | **Deprecated** (Phase 4) | Will be replaced by MerkleDAGCache |
| `DependencyTracker` | **Deprecated** (Phase 4) | Explicit tracking no longer needed |
| `TaxonomyIndex` | **Subsumed** | Effects capture taxonomy relationships automatically |
| `QueryIndex` | **Subsumed** | Query results cached as compute effects |

### Impact on Orchestration

```python
# Current flow (explicit tracking)
def build_page(page: Page, tracker: DependencyTracker) -> None:
    tracker.track_template(template_path)      # Manual
    tracker.track_data_file(page.path, data)   # Manual
    tracker.track_taxonomy(page.path, tags)    # Manual
    render(page)

# Proposed flow (effect tracing)
def build_page(page: Page) -> None:
    with trace_effects() as effects:
        render(page)  # All dependencies captured automatically
    cache.store_effect_set(page.source_path, effects, output)
```

### Backward Compatibility Strategy

1. **Phase 1-3**: Both systems run in parallel
   - Effect cache populates alongside existing caches
   - `--effect-trace` flag enables new system
   - Existing `DependencyTracker` continues working

2. **Phase 4**: Deprecation warnings
   - `track_*()` methods emit deprecation warnings
   - Existing caches marked as legacy
   - Config option to force legacy behavior

3. **Phase 5** (Future RFC): Removal
   - Legacy cache classes removed
   - `DependencyTracker` removed from public API
   - `.bengal/legacy/` directory cleanup

---

## Migration Path

### Phase 1: Parallel Infrastructure (Week 1)

Add effect system alongside existing `DependencyTracker`:

1. Create `bengal/effects/` package
2. Implement `EffectTracer` with contextvars
3. Implement `MerkleDAGCache`
4. Add basic instrumentation points

**No breaking changes** - existing incremental build continues working.

### Phase 2: Instrumentation (Week 2)

Instrument key I/O points:

1. `Path.read_text()` instrumentation
2. Config access instrumentation
3. Template loading instrumentation
4. Data file access instrumentation

**Backward compatible** - tracing is opt-in via `--effect-trace` flag.

### Phase 3: Build Integration (Week 3)

Integrate `EffectTracedBuilder`:

1. Add `effect_traced=True` option to BuildOptions
2. Parallel effect builder with ThreadPoolExecutor
3. Effect-based cache validation
4. Merkle cache persistence

**Opt-in** - enabled via `bengal.build.effect_traced: true` in config.

### Phase 4: Migration & Deprecation (Week 4+)

Migrate existing features to effect-traced system:

1. Migrate autodoc dependency tracking to effects
2. Migrate taxonomy tracking to effects
3. Deprecate explicit `track_*()` methods (see **Deprecation Path** in Success Criteria)
4. Document migration guide for plugin authors

**Config Option** (Phase 3+):
```yaml
# bengal.yaml
bengal:
  build:
    effect_traced: true  # Enable effect-traced builds (default: false)
    legacy_cache: false  # Disable legacy cache classes (default: true during migration)
```

---

## Performance Comparison (Estimated)

> **⚠️ Note**: These are **estimated projections** based on theoretical analysis. Actual performance will be validated via prototype benchmarks in Phase 2 before integration.

### Current System (Measured Baseline)

```
Build Phase                 Time (1000 pages)
─────────────────────────────────────────────
Content discovery           120ms
Dependency tracking         ~50ms (during render)
Cache validation            80ms (file-level)
Incremental filter          40ms
Rendering                   1800ms
Cache save                  60ms
─────────────────────────────────────────────
Total incremental           ~200ms (10 pages changed)
```

### Effect-Traced System (Projected Estimates)

```
Build Phase                 Time (1000 pages)
─────────────────────────────────────────────
Effect probe                30ms (parallel, hash-based)
Merkle cache validation     20ms (structural)
Rendering (cache misses)    180ms (10 pages)
Effect capture              ~5ms overhead
Merkle cache update         15ms (structural sharing)
─────────────────────────────────────────────
Total incremental           ~125ms (10 pages changed)
                            ~40% faster
```

### Target Improvements (To Be Validated)

| Metric | Current | Target | Confidence | Validation Method |
|--------|---------|--------|------------|-------------------|
| Cold start | ~2500ms | ~2400ms | Medium | Benchmark suite |
| Warm incremental | ~200ms | ~125ms | **Low** | Prototype required |
| Cache size | ~2MB | ~1.2MB | Medium | Directory measurement |
| Dependency accuracy | Explicit only | Automatic | High | Gap coverage test |
| Code complexity | 8+ cache classes | 2-3 classes | High | Code audit |

### Validation Plan

**Phase 2 Prototype Deliverables**:
1. Minimal `EffectTracer` + `MerkleDAGCache` implementation
2. Benchmark against `tests/roots/full_site/` (200+ pages)
3. Compare incremental build times vs current system
4. Measure actual structural sharing ratios

**Acceptance Criteria**:
- Warm incremental ≥25% faster (conservative target)
- Zero false negatives (no missed rebuilds)
- Cache size ≤ current size (no regression)

**Abort Criteria**:
- If prototype shows <15% improvement → RFC will be revised
- If cold build overhead >10% → design will be reconsidered

---

## Risks and Mitigations

### Risk 1: Tracing Overhead

**Risk**: Effect tracing adds overhead to every I/O operation.

**Mitigation**:
- Tracing is conditional (`is_tracing()` check is O(1))
- Probe phase uses direct hash without full tracing
- Heavy lifting done in parallel on free-threaded Python

### Risk 2: Cache Corruption

**Risk**: Merkle cache corruption causes incorrect builds.

**Mitigation**:
- Content-addressed storage provides integrity verification
- Corrupted nodes automatically detected and regenerated
- Hash mismatches trigger cache miss, not silent corruption

### Risk 3: Memory Usage

**Risk**: Merkle DAG requires more memory than flat cache.

**Mitigation**:
- Nodes are loaded lazily (only when accessed)
- Structural sharing reduces storage
- Garbage collection removes unreachable nodes

### Risk 4: Migration Complexity

**Risk**: Migrating from explicit tracking is disruptive.

**Mitigation**:
- Parallel operation during migration phase
- Opt-in flag allows gradual rollout
- Explicit tracking remains functional until removed

---

## Success Criteria

### Required (Must Pass)

1. **Automatic Dependency Discovery**: No manual `track_*()` calls needed for new dependency types
2. **Correctness**: Zero false negatives (never skip needed rebuilds)
3. **Backward Compatible**: Existing sites work without configuration changes

### Target (To Be Validated)

4. **Performance**: ≥25% faster warm incremental builds (conservative); ~40% target
5. **Cache Efficiency**: ≤ current cache size; ~40% reduction target via structural sharing

### Deprecation Path

**Phase 4: DependencyTracker Deprecation**

```python
# bengal/cache/dependency_tracker.py

import warnings

class DependencyTracker:
    def track_template(self, template_path: Path) -> None:
        """Record that the current page depends on a template.

        .. deprecated:: 0.2.0
            Use effect-traced builds instead. Enable with
            `bengal.build.effect_traced: true` in config.
            This method will be removed in version 0.3.0.
        """
        warnings.warn(
            "track_template() is deprecated. Enable effect-traced builds "
            "with `bengal.build.effect_traced: true` in config.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Legacy implementation continues working
        ...
```

**Migration Timeline**:
- **0.2.0**: Effect-traced builds available (opt-in via config)
- **0.2.x**: `track_*()` methods emit DeprecationWarning
- **0.3.0**: Legacy cache classes moved to `bengal.cache.legacy`
- **0.4.0**: Legacy cache classes removed (breaking change)

---

## Appendix: Comparison with Alternatives

### Alternative Comparison Matrix

| Criterion | Make | Shake/Pluto | LaForge | Salsa | **Effect-Traced (Proposed)** |
|-----------|------|-------------|---------|-------|------------------------------|
| **Dependency Discovery** | Manual | Manual + DSL | Automatic | Automatic | **Automatic** |
| **Granularity** | File-level | Rule-level | Instruction-level | Query-level | **Effect-level** |
| **Language** | Makefile | Haskell DSL | Python (patched) | Rust DSL | **Native Python** |
| **Integration Effort** | High (external tool) | High (new language) | Medium (runtime patch) | High (Rust FFI) | **Low (decorator/context)** |
| **Runtime Overhead** | None | None | High (~30%) | Medium (~10%) | **Low (~5%)** |
| **Structural Sharing** | No | No | No | Yes | **Yes (Merkle DAG)** |
| **Thread Safety** | N/A | Per-rule | No | Yes | **Yes (ContextVars)** |
| **Python 3.14 Ready** | N/A | N/A | No | N/A | **Yes** |
| **Bengal Fit** | Poor | Poor | Medium | Medium | **Excellent** |

### Alternative 1: Make (Declarative Dependencies)

```makefile
# Make requires explicit dependency declaration
output/page.html: content/page.md templates/base.html
    bengal render $< > $@
```

**Analysis**:
- ✅ Battle-tested, widely understood
- ❌ Requires manual dependency maintenance (exactly what we're trying to eliminate)
- ❌ Cannot capture runtime dependencies (data files, taxonomy)
- ❌ External tool dependency, not portable
- ❌ File-level granularity only

**Verdict**: Rejected — doesn't solve the core problem of automatic dependency discovery.

### Alternative 2: Shake/Pluto (Build Rules DSL)

```haskell
-- Shake uses Haskell DSL for build rules
"output/*.html" %> \out -> do
    need ["content/*.md", "templates/*.html"]
    cmd "bengal" "render"
```

**Analysis**:
- ✅ Powerful dependency tracking
- ✅ Supports dynamic dependencies via `need`
- ❌ Requires learning Haskell DSL
- ❌ Not Pythonic — breaks Bengal's "pure Python" philosophy
- ❌ Complex integration with existing codebase

**Verdict**: Rejected — requires separate build language, high adoption barrier.

### Alternative 3: LaForge (Full Trace Replay)

LaForge captures full execution trace and replays for incremental builds.

**Analysis**:
- ✅ Automatic dependency discovery
- ✅ Instruction-level granularity
- ❌ ~30% runtime overhead from full tracing
- ❌ Large trace files (proportional to execution length)
- ❌ Not compatible with free-threaded Python
- ⚠️ Academic project, not production-ready

**Verdict**: Partially adopted — we use effect-based tracing but with content-addressed hashing instead of full trace replay. This provides automatic discovery with lower overhead.

### Alternative 4: Salsa (Incremental Computation)

Salsa tracks computation graph and memoizes intermediate results.

**Analysis**:
- ✅ Fine-grained query-level caching
- ✅ Structural sharing via interning
- ✅ Proven in rust-analyzer (large codebase)
- ❌ Rust-based, requires FFI bridge
- ❌ Query-oriented model doesn't map cleanly to SSG page rendering
- ❌ Significant learning curve

**Verdict**: Partially adopted — Merkle DAG provides similar structural sharing benefits with native Python implementation.

### Why Effect-Traced for Bengal?

The proposed approach combines the best aspects of alternatives:

| Feature | Source |
|---------|--------|
| Automatic dependency discovery | LaForge |
| Content-addressed structural sharing | Salsa/Git |
| Native Python with decorators | Original |
| ContextVar thread isolation | Python 3.14 patterns |
| Zstandard compression | Python 3.14 stdlib |

**Bengal-Specific Advantages**:
1. **Zero external dependencies**: Pure Python, no FFI or external tools
2. **Free-threading ready**: Leverages existing `is_free_threaded()` infrastructure
3. **Incremental adoption**: Opt-in via `--effect-trace` flag
4. **Compression built-in**: Uses existing `bengal.cache.compression` patterns

---

## References

- [LaForge: Stateless Build Systems](https://arxiv.org/abs/2108.12469)
- [PEP 703: Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [PEP 784: Zstandard Compression in stdlib](https://peps.python.org/pep-0784/)
- [Salsa: Incremental Recomputation](https://salsa-rs.github.io/salsa/)
- Bengal RFC: `rfc-incremental-build-dependency-gaps.md`
- Bengal RFC: `rfc-autodoc-incremental-caching.md`
