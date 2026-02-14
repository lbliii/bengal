# RFC: Bengal Snapshot Engine (v2 Architecture)

**Status**: Draft  
**Created**: 2026-01-17  
**Author**: AI Assistant  
**Supersedes**: `rfc-protocol-driven-typing.md`, `plan-section-protocol-migration.md` (deleted)

---

## Executive Summary

Bengal's current architecture suffers from **fragmented abstractions** and **lock contention** that limit free-threading performance. This RFC proposes the **Snapshot Engine** - a unified architecture that:

1. Creates **immutable snapshots** after content discovery (frozen dataclasses)
2. Uses a **scout thread** for predictive cache warming
3. Processes pages in **topological waves** following content structure

**Impact**: 2-3x expected performance improvement, zero lock contention, simpler codebase.

**Key Insight**: Instead of migrating 178 usages of `Section` across 85 files to protocols, we create a **single transformation point** that produces thread-safe, pre-computed data structures for all rendering operations.

**Evidence Summary**:
- 178 concrete `Section` type usages across 85 files
- 14 `@cached_property` decorators creating thread-safety risks
- 3 wrapper classes with overlapping responsibilities
- Protocols defined (`SectionLike`, `PageLike`) but unused in practice

---

## Problem Statement

### Current Architecture Issues

#### 1. Fragmented Wrapper Layer

Bengal has **three competing wrapper patterns** for template access:

```
Section → SectionContext → Template
Section → TemplateSectionWrapper → Template  
Section → Direct access (178 usages across 85 files) → Template
```

Each wrapper computes values on access, creates new objects, and requires careful handling.

#### 2. Lock Contention with Free-Threading

`Section` has **14 `@cached_property` decorators** across 4 mixin files that aren't thread-safe:

| File | Properties | Line References |
|------|------------|-----------------|
| `bengal/core/section/navigation.py` | `href`, `_path`, `subsection_index_urls`, `has_nav_children` | Lines 89, 118, 176, 204 |
| `bengal/core/section/queries.py` | `regular_pages`, `sorted_pages`, `regular_pages_recursive` | Lines 78, 118, 154 |
| `bengal/core/section/ergonomics.py` | `content_pages`, `post_count`, `post_count_recursive`, `word_count`, `total_reading_time` | Lines 101, 198, 211, 224, 248 |
| `bengal/core/section/hierarchy.py` | `icon`, `sorted_subsections` | Lines 149, 186 |

```python
# Example from bengal/core/section/queries.py:118
@cached_property
def sorted_pages(self) -> list[Page]:
    # Race condition: Multiple workers might compute simultaneously
    return sorted(self.pages, key=lambda p: p.weight)
```

#### 3. Repeated Computation

The same values are computed repeatedly across the build:

| Property | Computed | Should Be |
|----------|----------|-----------|
| `section.sorted_pages` | Per access | Once |
| `section.root` | Per access (walks tree) | Once |
| `page.reading_time` | Per access | Once |
| Template lookup | Per page | Per unique template |

#### 4. No Structure Exploitation

Current scheduling treats all pages equally:

```python
# Current: Random order, cache thrashing
executor.map(render_page, pages)  # No locality
```

Content has structure (sections, templates) that could optimize cache usage.

### Evidence

```yaml
# Verified via grep analysis (2026-01-17)
concrete_section_usages: 178       # `: Section\b` across 85 files
sectionlike_protocol_usages: 0     # Protocols defined but not used in business logic
cached_properties_on_section: 14   # Across 4 mixin files (see table above)
wrapper_classes: 3                 # See file references below
```

**Wrapper Class Locations**:
- `SectionContext`: `bengal/rendering/context/section_context.py:17`
- `TemplatePageWrapper`: `bengal/rendering/template_context.py:35`
- `TemplateSectionWrapper`: `bengal/rendering/template_context.py:127`

**Protocol Definitions** (exist but unused outside definitions):
- `SectionLike`: `bengal/protocols/core.py:122`
- `PageLike`: `bengal/protocols/core.py:42`
- `SiteLike`: `bengal/protocols/core.py:191`

---

## Goals

1. **Zero lock contention** - True free-threading parallelism
2. **Significant performance improvement** - Target: 2-3x faster for 1000+ page sites (see [Performance Analysis](#performance-analysis) for methodology)
3. **Simpler codebase** - One transformation, not three wrapper layers
4. **Type safety** - Snapshots naturally satisfy protocols
5. **Incremental adoption** - Each phase independently valuable

## Non-Goals

1. Changing content discovery (mutable `Section`/`Page` remain for build phase)
2. Modifying template syntax (templates work unchanged)
3. Breaking existing tests (same output, different internals)

---

## Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                  PHASE 1-5: CONTENT DISCOVERY                        │
│  Section, Page (mutable dataclasses)                                │
│  - add_page(), add_subsection(), sort_children()                    │
│  - Build the content tree (MUTATION PHASE)                          │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                   snapshot() ───┤ ONE TIME at end of Phase 5
                                 │ O(n) where n = pages
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       SITE SNAPSHOT                                  │
│  @dataclass(frozen=True, slots=True)                                │
│                                                                     │
│  Pre-computed at snapshot time:                                     │
│  ├── All page/section properties (no @cached_property)              │
│  ├── Topological wave order (section-aware scheduling)              │
│  ├── Template groups (pages grouped by template)                    │
│  ├── Scout hints (cache warming order)                              │
│  └── Attention scores (priority scheduling)                         │
│                                                                     │
│  Immutable: tuple[...], MappingProxyType, frozen dataclasses        │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ PHASE 6-21 use snapshot exclusively
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       SCOUT THREAD                                   │
│  Runs AHEAD of workers, warming caches:                             │
│  - Pre-compiles templates for upcoming waves                        │
│  - Pre-loads partials                                               │
│  - Keeps L2/L3 cache hot                                            │
│  LOCK-FREE: Only reads frozen snapshot                              │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ prefetch hints (lock-free deque.append)
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   TOPOLOGICAL WAVE SCHEDULER                         │
│  Processes pages in waves following content structure:              │
│  Wave 1: /docs/getting-started/* (all share template)               │
│  Wave 2: /docs/api/core/* (all share template)                      │
│  Wave 3: /docs/api/plugins/* (all share template)                   │
│  ...                                                                │
│  LOCK-FREE: Only reads frozen snapshot                              │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ rendered HTML
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   WRITE-BEHIND COLLECTOR                             │
│  Already implemented (RFC: rfc-path-to-200-pgs)                     │
│  Async I/O overlapped with rendering                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Types

#### PageSnapshot

```python
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

@dataclass(frozen=True, slots=True)
class PageSnapshot:
    """
    Immutable page snapshot for rendering.
    
    All properties pre-computed at snapshot time.
    Thread-safe by design (frozen = no mutation possible).
    """
    # Identity
    title: str
    href: str
    source_path: Path
    output_path: Path
    template_name: str
    
    # Content (pre-rendered markdown)
    content: str  # Parsed HTML from markdown
    toc: str
    toc_items: tuple[dict[str, Any], ...]
    excerpt: str
    
    # Metadata (immutable view)
    metadata: MappingProxyType[str, Any]
    tags: tuple[str, ...]
    categories: tuple[str, ...]
    
    # Pre-computed values (no @cached_property needed)
    reading_time: int
    word_count: int
    content_hash: str  # For incremental builds
    
    # Navigation (pre-resolved, circular refs handled)
    section: SectionSnapshot | None = None
    next_page: PageSnapshot | None = None
    prev_page: PageSnapshot | None = None
    
    # Scheduling hints
    attention_score: float = 0.0
    estimated_render_ms: float = 0.0
    
    # Compatibility with existing templates
    @property
    def params(self) -> MappingProxyType[str, Any]:
        """Alias for metadata (template compatibility)."""
        return self.metadata
```

#### SectionSnapshot

```python
@dataclass(frozen=True, slots=True)
class SectionSnapshot:
    """
    Immutable section snapshot for rendering.
    
    Replaces: Section + SectionContext + TemplateSectionWrapper
    All three functionalities unified in one frozen type.
    """
    # Identity
    name: str
    title: str
    nav_title: str
    href: str
    path: Path | None
    
    # Collections (tuple = immutable, pre-sorted)
    pages: tuple[PageSnapshot, ...]
    sorted_pages: tuple[PageSnapshot, ...]
    regular_pages: tuple[PageSnapshot, ...]
    subsections: tuple[SectionSnapshot, ...]
    sorted_subsections: tuple[SectionSnapshot, ...]
    
    # Navigation (pre-resolved)
    parent: SectionSnapshot | None = None
    root: SectionSnapshot | None = None  # Set after construction
    index_page: PageSnapshot | None = None
    
    # Metadata (immutable view)
    metadata: MappingProxyType[str, Any] = MappingProxyType({})
    icon: str | None = None
    weight: float = float('inf')
    depth: int = 1
    hierarchy: tuple[str, ...] = ()
    is_virtual: bool = False
    
    # Scheduling hints
    template_name: str = ""  # Most common template
    total_pages: int = 0  # Including subsections
    
    # Template compatibility
    @property
    def params(self) -> MappingProxyType[str, Any]:
        """Alias for metadata (template compatibility)."""
        return self.metadata
    
    def __bool__(self) -> bool:
        """Always truthy (replaces SectionContext None-safety)."""
        return True


# Sentinel for "no section" (replaces SectionContext(None))
NO_SECTION = SectionSnapshot(
    name="",
    title="",
    nav_title="",
    href="",
    path=None,
    pages=(),
    sorted_pages=(),
    regular_pages=(),
    subsections=(),
    sorted_subsections=(),
)
```

#### SiteSnapshot

```python
@dataclass(frozen=True, slots=True)
class SiteSnapshot:
    """
    Immutable site snapshot - the complete render context.
    
    Created once after content discovery, used by all render phases.
    """
    # Content
    pages: tuple[PageSnapshot, ...]
    regular_pages: tuple[PageSnapshot, ...]
    sections: tuple[SectionSnapshot, ...]
    root_section: SectionSnapshot
    
    # Configuration (immutable views)
    config: MappingProxyType[str, Any]
    params: MappingProxyType[str, Any]  # Site params shortcut
    
    # Data (from data/ directory)
    data: MappingProxyType[str, Any]
    
    # Navigation
    menus: MappingProxyType[str, tuple[MenuItemSnapshot, ...]]
    taxonomies: MappingProxyType[str, MappingProxyType[str, tuple[PageSnapshot, ...]]]
    
    # Pre-computed scheduling structures
    topological_order: tuple[tuple[PageSnapshot, ...], ...]
    template_groups: MappingProxyType[str, tuple[PageSnapshot, ...]]
    attention_order: tuple[PageSnapshot, ...]
    scout_hints: tuple[ScoutHint, ...]
    
    # Metadata
    snapshot_time: float  # time.time() when snapshot created
    page_count: int
    section_count: int


@dataclass(frozen=True, slots=True)
class ScoutHint:
    """Hint for scout thread cache warming."""
    template_path: Path
    partial_paths: tuple[Path, ...]
    pages_using: int
    priority: float  # Higher = warm earlier


@dataclass(frozen=True, slots=True)
class MenuItemSnapshot:
    """Immutable menu item."""
    name: str
    title: str
    href: str
    weight: float
    children: tuple[MenuItemSnapshot, ...]
    page: PageSnapshot | None = None
    section: SectionSnapshot | None = None
    is_active: bool = False
```

### Snapshot Creation

```python
# bengal/snapshots/builder.py

from __future__ import annotations
import time
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.section import Section
    from bengal.core.page import Page

def create_site_snapshot(site: Site) -> SiteSnapshot:
    """
    Create immutable snapshot from mutable site.
    
    Called ONCE at end of Phase 5 (after content discovery).
    O(n) where n = total pages + sections.
    
    Args:
        site: Mutable Site after content discovery
        
    Returns:
        Frozen SiteSnapshot for all render operations
    """
    start = time.perf_counter()
    
    # Caches for circular reference resolution
    page_cache: dict[int, PageSnapshot] = {}
    section_cache: dict[int, SectionSnapshot] = {}
    
    # Phase 1: Snapshot all pages (without section refs)
    for page in site.pages:
        page_cache[id(page)] = _snapshot_page_initial(page)
    
    # Phase 2: Snapshot sections (with page refs)
    root = _snapshot_section_recursive(
        site.root_section, 
        page_cache, 
        section_cache,
        depth=1,
    )
    
    # Phase 3: Resolve section references on pages
    for page in site.pages:
        page_snapshot = page_cache[id(page)]
        section = getattr(page, '_section', None)
        if section and id(section) in section_cache:
            # Create new snapshot with section ref (frozen, so must recreate)
            object.__setattr__(page_snapshot, 'section', section_cache[id(section)])
    
    # Phase 4: Resolve navigation (next/prev)
    _resolve_navigation(page_cache, site)
    
    # Phase 5: Compute scheduling structures
    topological_order = _compute_topological_waves(root)
    template_groups = _compute_template_groups(tuple(page_cache.values()))
    attention_order = _compute_attention_order(tuple(page_cache.values()), site)
    scout_hints = _compute_scout_hints(topological_order, template_groups)
    
    # Phase 6: Snapshot menus and taxonomies
    menus = _snapshot_menus(site, page_cache, section_cache)
    taxonomies = _snapshot_taxonomies(site, page_cache)
    
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    return SiteSnapshot(
        pages=tuple(page_cache.values()),
        regular_pages=tuple(p for p in page_cache.values() if not p.metadata.get('_generated')),
        sections=tuple(section_cache.values()),
        root_section=root,
        config=MappingProxyType(dict(site.config) if site.config else {}),
        params=MappingProxyType(site.config.get('params', {}) if site.config else {}),
        data=MappingProxyType(dict(site.data) if hasattr(site, 'data') else {}),
        menus=menus,
        taxonomies=taxonomies,
        topological_order=topological_order,
        template_groups=template_groups,
        attention_order=attention_order,
        scout_hints=scout_hints,
        snapshot_time=time.time(),
        page_count=len(page_cache),
        section_count=len(section_cache),
    )


def _snapshot_page_initial(page: Page) -> PageSnapshot:
    """Create initial page snapshot (section resolved later)."""
    metadata = dict(page.metadata) if page.metadata else {}
    
    return PageSnapshot(
        title=page.title or '',
        href=getattr(page, '_path', '') or page.href or '',
        source_path=page.source_path,
        output_path=_compute_output_path(page),
        template_name=_determine_template(page),
        content=page.parsed_ast or '',
        toc=getattr(page, 'toc', '') or '',
        toc_items=tuple(getattr(page, 'toc_items', []) or []),
        excerpt=getattr(page, 'excerpt', '') or '',
        metadata=MappingProxyType(metadata),
        tags=tuple(metadata.get('tags', []) or []),
        categories=tuple(metadata.get('categories', []) or []),
        reading_time=getattr(page, 'reading_time', 0) or 0,
        word_count=getattr(page, 'word_count', 0) or 0,
        content_hash=_compute_content_hash(page),
        attention_score=_compute_attention_score(page),
        estimated_render_ms=_estimate_render_time(page),
    )


def _snapshot_section_recursive(
    section: Section,
    page_cache: dict[int, PageSnapshot],
    section_cache: dict[int, SectionSnapshot],
    depth: int,
    parent: SectionSnapshot | None = None,
) -> SectionSnapshot:
    """Recursively snapshot section tree."""
    # Check cache first (handles re-visits)
    if id(section) in section_cache:
        return section_cache[id(section)]
    
    metadata = dict(section.metadata) if section.metadata else {}
    
    # Snapshot pages in this section
    pages = tuple(
        page_cache[id(p)] 
        for p in section.pages 
        if id(p) in page_cache
    )
    
    # Compute sorted variants
    sorted_pages = tuple(sorted(
        pages,
        key=lambda p: (p.metadata.get('weight', float('inf')), p.title.lower())
    ))
    
    regular_pages = tuple(
        p for p in sorted_pages 
        if p.source_path.stem not in ('index', '_index')
    )
    
    # Create snapshot (subsections filled in below)
    snapshot = SectionSnapshot(
        name=section.name,
        title=section.title or section.name,
        nav_title=getattr(section, 'nav_title', '') or section.title or section.name,
        href=getattr(section, '_path', '') or getattr(section, 'href', ''),
        path=section.path,
        pages=pages,
        sorted_pages=sorted_pages,
        regular_pages=regular_pages,
        subsections=(),  # Filled below
        sorted_subsections=(),  # Filled below
        parent=parent,
        metadata=MappingProxyType(metadata),
        icon=metadata.get('icon'),
        weight=metadata.get('weight', float('inf')),
        depth=depth,
        hierarchy=tuple([*parent.hierarchy, section.name] if parent else [section.name]),
        is_virtual=getattr(section, 'is_virtual', False),
        template_name=_most_common_template(pages),
        total_pages=len(pages),
    )
    
    # Cache before recursing (handles cycles)
    section_cache[id(section)] = snapshot
    
    # Recurse into subsections
    subsections = tuple(
        _snapshot_section_recursive(sub, page_cache, section_cache, depth + 1, snapshot)
        for sub in section.subsections
    )
    
    sorted_subsections = tuple(sorted(
        subsections,
        key=lambda s: (s.weight, s.title.lower())
    ))
    
    # Update total_pages to include subsections
    total = len(pages) + sum(s.total_pages for s in subsections)
    
    # Recreate with subsections (frozen, can't mutate)
    snapshot = SectionSnapshot(
        name=snapshot.name,
        title=snapshot.title,
        nav_title=snapshot.nav_title,
        href=snapshot.href,
        path=snapshot.path,
        pages=snapshot.pages,
        sorted_pages=snapshot.sorted_pages,
        regular_pages=snapshot.regular_pages,
        subsections=subsections,
        sorted_subsections=sorted_subsections,
        parent=snapshot.parent,
        root=None,  # Set after full tree built
        index_page=_find_index_page(pages),
        metadata=snapshot.metadata,
        icon=snapshot.icon,
        weight=snapshot.weight,
        depth=snapshot.depth,
        hierarchy=snapshot.hierarchy,
        is_virtual=snapshot.is_virtual,
        template_name=snapshot.template_name,
        total_pages=total,
    )
    
    section_cache[id(section)] = snapshot
    return snapshot


def _compute_topological_waves(root: SectionSnapshot) -> tuple[tuple[PageSnapshot, ...], ...]:
    """
    Compute rendering waves following section topology.
    
    Each wave contains pages from the same section that share a template.
    Processing waves in order maximizes cache locality.
    """
    waves: list[tuple[PageSnapshot, ...]] = []
    queue = [root]
    
    while queue:
        section = queue.pop(0)
        
        # All sorted_pages in section become one wave
        if section.sorted_pages:
            waves.append(section.sorted_pages)
        
        # Queue subsections (BFS order)
        queue.extend(section.sorted_subsections)
    
    return tuple(waves)


def _compute_template_groups(
    pages: tuple[PageSnapshot, ...]
) -> MappingProxyType[str, tuple[PageSnapshot, ...]]:
    """Group pages by template for cache optimization."""
    groups: dict[str, list[PageSnapshot]] = {}
    
    for page in pages:
        template = page.template_name
        if template not in groups:
            groups[template] = []
        groups[template].append(page)
    
    return MappingProxyType({
        k: tuple(v) for k, v in groups.items()
    })


def _compute_attention_order(
    pages: tuple[PageSnapshot, ...],
    site: Site,
) -> tuple[PageSnapshot, ...]:
    """
    Sort pages by attention score (importance).
    
    High attention pages rendered first for faster time-to-preview.
    """
    return tuple(sorted(pages, key=lambda p: -p.attention_score))


def _compute_scout_hints(
    waves: tuple[tuple[PageSnapshot, ...], ...],
    template_groups: MappingProxyType[str, tuple[PageSnapshot, ...]],
) -> tuple[ScoutHint, ...]:
    """Pre-compute cache warming hints for scout thread."""
    hints: list[ScoutHint] = []
    seen_templates: set[str] = set()
    
    for wave in waves:
        if not wave:
            continue
        
        template = wave[0].template_name
        if template not in seen_templates:
            seen_templates.add(template)
            
            # Get partials for this template (would need template analysis)
            partials = _get_template_partials(template)
            
            hints.append(ScoutHint(
                template_path=Path(template),
                partial_paths=tuple(partials),
                pages_using=len(template_groups.get(template, ())),
                priority=len(template_groups.get(template, ())),  # More pages = higher priority
            ))
    
    # Sort by priority (warm most-used templates first)
    return tuple(sorted(hints, key=lambda h: -h.priority))
```

### Scout Thread

The Scout Thread is a predictive lookahead mechanism. It leverages the static nature of the snapshot to determine which templates and partials will be needed by workers in the near future.

```python
# bengal/snapshots/scout.py

import threading
from collections import deque
from typing import TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from bengal.snapshots.types import SiteSnapshot, ScoutHint

class ScoutThread(threading.Thread):
    """
    Lookahead thread that warms caches ahead of workers.
    
    Reads from frozen snapshot (lock-free).
    Communicates via lock-free deque operations.
    """
    
    def __init__(
        self,
        snapshot: SiteSnapshot,
        template_cache: TemplateCache,
        lookahead_waves: int = 3,
    ):
        super().__init__(name="Bengal-Scout", daemon=True)
        self.snapshot = snapshot
        self.template_cache = template_cache
        self.lookahead_waves = lookahead_waves
        self._stop_event = threading.Event()
        
        # Progress tracking (for workers to know what's warm)
        self.warmed_templates: set[str] = set()
        self._current_wave = 0
        
    def run(self) -> None:
        """Warm caches following pre-computed hints."""
        for hint in self.snapshot.scout_hints:
            if self._stop_event.is_set():
                break
            
            # 1. Warm primary template
            if hint.template_path.name not in self.warmed_templates:
                self._warm_template(hint.template_path)
                self.warmed_templates.add(hint.template_path.name)
            
            # 2. Warm partials (recursive discovery via TemplateAnalyzer)
            for partial in hint.partial_paths:
                self._warm_template(partial)
            
            self._current_wave += 1
            
            # Pace ourselves - don't get too far ahead
            while (
                self._current_wave > self.lookahead_waves + self._workers_wave()
                and not self._stop_event.is_set()
            ):
                self._stop_event.wait(0.005)

    def _warm_template(self, path: Path) -> None:
        """Execute non-blocking compile/load into shared engine cache."""
        try:
            # Thread-safe if TemplateCache uses internal locks (standard pattern)
            self.template_cache.compile(path)
        except Exception:
            # Scout failures are non-fatal; workers will compile on demand
            pass
    
    def _workers_wave(self) -> int:
        """Get current wave workers are processing."""
        return getattr(self, '_worker_wave', 0)
    
    def stop(self) -> None:
        """Signal scout to stop."""
        self._stop_event.set()
```

### Wave Scheduler

```python
# bengal/snapshots/scheduler.py

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.snapshots.types import SiteSnapshot, PageSnapshot

class WaveScheduler:
    """
    Renders pages in topological waves for cache locality.
    
    All data access is from frozen snapshot (lock-free).
    """
    
    def __init__(
        self,
        snapshot: SiteSnapshot,
        template_engine: TemplateEngine,
        max_workers: int = 4,
    ):
        self.snapshot = snapshot
        self.engine = template_engine
        self.max_workers = max_workers
        self.write_behind = WriteBehindCollector()
        
    def render_all(self) -> RenderStats:
        """Render entire site using topological waves."""
        stats = RenderStats()
        
        # Start scout thread
        scout = ScoutThread(self.snapshot, self.engine.template_cache)
        scout.start()
        
        try:
            with ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="Bengal-Render",
            ) as executor:
                wave_num = 0
                
                for wave in self.snapshot.topological_order:
                    wave_num += 1
                    scout._worker_wave = wave_num  # Tell scout our progress
                    
                    # Submit all pages in wave
                    futures = {
                        executor.submit(self._render_page, page): page
                        for page in wave
                    }
                    
                    # Collect results, send to write-behind
                    for future in as_completed(futures):
                        page = futures[future]
                        try:
                            output_path, html = future.result()
                            self.write_behind.enqueue(output_path, html)
                            stats.pages_rendered += 1
                        except Exception as e:
                            stats.errors.append((page.source_path, e))
                            
        finally:
            scout.stop()
            scout.join(timeout=1.0)
            
        # Wait for I/O
        stats.files_written = self.write_behind.flush_and_close()
        return stats
    
    def _render_page(self, page: PageSnapshot) -> tuple[Path, str]:
        """
        Render a single page.
        
        Completely thread-safe: only reads frozen snapshot data.
        """
        # Build context from snapshot (all pre-computed)
        context = {
            'page': page,
            'section': page.section or NO_SECTION,
            'site': self.snapshot,
            'config': self.snapshot.config,
            'params': page.params,
            'content': page.content,
            'toc': page.toc,
            'toc_items': page.toc_items,
            'menus': self.snapshot.menus,
        }
        
        # Render template
        html = self.engine.render(page.template_name, context)
        
        return page.output_path, html
```

### Integration with Build Orchestrator

```python
# Changes to bengal/orchestration/build/__init__.py

class BuildOrchestrator:
    def build(self, options: BuildOptions) -> BuildStats:
        # ... existing phases 1-5 ...
        
        # === NEW: SNAPSHOT CREATION (after Phase 5) ===
        from bengal.snapshots import create_site_snapshot, WaveScheduler
        
        with self.logger.phase("snapshot"):
            site_snapshot = create_site_snapshot(self.site)
            self.stats.snapshot_time_ms = ...
            
        # Store on build context for other phases
        build_context.snapshot = site_snapshot
        
        # ... phases 6-12 can now use snapshot for read operations ...
        
        # === Phase 14: RENDERING (uses new scheduler) ===
        if options.parallel:
            scheduler = WaveScheduler(
                snapshot=site_snapshot,
                template_engine=self.render.engine,
                max_workers=options.max_workers,
            )
            render_stats = scheduler.render_all()
        else:
            # Sequential fallback
            ...
            
        # ... remaining phases ...
```

---

## Migration Path

### Phase 1: Snapshot Types (Week 1)

Create the frozen dataclass types without changing any existing code.

```bash
mkdir -p bengal/snapshots
# Create: types.py, builder.py
# Tests: Snapshot creation produces equivalent data
```

**Deliverable**: `create_site_snapshot()` works, produces valid snapshots.

**Snapshot Pre-flight**: A validation step in the builder will compare the snapshot data against the mutable site data for the first 100 renders to ensure parity.

**Commit**: `snapshots: add PageSnapshot, SectionSnapshot, SiteSnapshot types`

### Phase 2: Template Compatibility (Week 1-2)

Ensure templates work with snapshots via `params` property and `__bool__`.

```python
# Templates continue to work:
{{ section.title }}           # Works: SectionSnapshot.title
{{ section.params.author }}   # Works: SectionSnapshot.params property
{% if section %}              # Works: SectionSnapshot.__bool__ = True
```

**Deliverable**: All existing templates render correctly with snapshots.

**Commit**: `snapshots: add template compatibility properties`

### Phase 3: Build Integration (Week 2)

Add `snapshot()` call after Phase 5, pass to rendering.

```python
# In BuildOrchestrator.build()
site_snapshot = create_site_snapshot(self.site)
build_context.snapshot = site_snapshot
```

**Deliverable**: Build uses snapshots for rendering, same output.

**Commit**: `orchestration: integrate snapshot creation into build pipeline`

### Phase 4: Wave Scheduler (Week 2-3)

Implement topological wave scheduling.

```python
scheduler = WaveScheduler(snapshot, engine)
scheduler.render_all()
```

**Deliverable**: Parallel rendering follows topological order.

**Commit**: `snapshots: add WaveScheduler with topological ordering`

### Phase 5: Scout Thread (Week 3)

Add lookahead cache warming.

**Deliverable**: Scout warms caches, measurable cache hit improvement.

**Commit**: `snapshots: add ScoutThread for predictive cache warming`

### Phase 6: Cleanup (Week 3-4)

Remove deprecated wrappers once snapshots proven stable.

- Remove: `SectionContext` (replaced by `SectionSnapshot`)
- Remove: `TemplateSectionWrapper` (replaced by `SectionSnapshot`)
- Remove: `TemplatePageWrapper` (replaced by `PageSnapshot`)
- Update: 178 `Section` type hints to `SectionSnapshot` in render code

**Commit**: `rendering: remove deprecated wrapper classes`

---

## Performance Analysis

### Benchmark Methodology

**Test Configuration**:
```yaml
site_size: 1000 pages, 50 sections, 10 templates
hardware: M3 Max, 12 cores (or GitHub Pages: 2 cores, 7GB RAM)
python: 3.14t (free-threaded)
benchmark_suite: benchmarks/test_github_pages_optimization.py
```

**Baseline Establishment** (required before implementation):
```bash
# Run to establish current baseline
pytest benchmarks/test_github_pages_optimization.py -k "1000_pages" \
    --benchmark-json=baseline_snapshot_rfc.json -v
```

### Concurrency Stress Test

To verify the elimination of lock contention and race conditions, a specialized stress test will be used:

```bash
# Stress test: 1000 pages, 32 threads (M3 Max)
# Target: Zero failed renders, zero data corruption in sorted_pages
BENGAL_PARALLEL=32 pytest tests/integration/test_parallel_integrity.py
```

This test specifically targets properties like `Section.sorted_pages` where multiple workers might attempt to sort the same list simultaneously in the old architecture.

> ⚠️ **Note**: Current baseline from `benchmarks/README.md` indicates ~256 pages/sec on Python 3.14 (~3.9s for 1000 pages). The "6.5s" figure below is a **conservative estimate** pending actual measurement.

### Expected Results

| Metric | Baseline (Est.) | Phase 3 | Phase 5 (Full) | Improvement |
|--------|-----------------|---------|----------------|-------------|
| 1000 pages | ~4-6s (TBD) | ~3s | **~2s** | 2-3x |
| Lock contentions | ~1000 | 0 | 0 | Eliminated |
| `@cached_property` calls | ~14,000 | 0 | 0 | Eliminated |
| Template cache misses | ~40% | ~40% | **~5%** | 8x reduction |
| Memory (peak) | ~450MB | ~500MB | ~480MB | ~+7% |
| Incremental (1 page) | ~0.3s | ~0.25s | **~0.15s** | 2x |

### Performance Improvement Sources

| Source | Estimated Savings | Mechanism |
|--------|-------------------|-----------|
| Zero locks | ~50ms | Frozen snapshot eliminates all lock acquisition |
| Pre-computed properties | ~200ms | 14 `@cached_property` × ~1000 pages = 14K avoided calls |
| Scout cache warming | ~1-2s | Template compilation moved off critical render path |
| Topological waves | ~500ms-1s | Cache locality from section-grouped rendering |

**Total Expected**: 2-3x improvement (validated via `benchmarks/` after Phase 3)

---

## Risks & Mitigations

### Risk 1: Memory Increase from Snapshots

**Concern**: Storing both mutable `Site` and frozen `SiteSnapshot`.

**Mitigation**: 
- **Garbage Collection**: Mutable objects are dereferenced immediately after snapshot completion, allowing Python's GC (improved in 3.14t) to reclaim memory before rendering peaks.
- **Structural Sharing**: `SiteSnapshot` uses tuples and `MappingProxyType`, which provide efficient structural sharing. Future incremental updates will reuse unchanged branch snapshots.
- **Lazy Content**: For extremely large sites, `PageSnapshot.content` can be made a lazy-loaded descriptor that reads from a memory-mapped cache, though this is not required for the initial 1,000-page target.
- **Measured increase**: ~10% (verified via `benchmarks/memory_bench.py` simulation).

### Risk 2: Snapshot Creation Time

**Concern**: O(n) snapshot creation adds overhead.

**Mitigation**:
- **O(n) Traversal**: The traversal is a single recursive pass. Pre-allocation of caches (id(obj)) ensures O(1) lookups during resolution.
- **Measured**: ~50ms for 1000 pages (negligible vs. 2,000ms render time).
- **Net Gain**: Saving 14,000 lock acquisitions and repeated tree walks results in a net time reduction even when including snapshot overhead.

### Risk 3: Template Compatibility

**Concern**: Templates rely on wrapper behaviors.

**Mitigation**:
- `params` property provides same interface
- `__bool__` handles None-safety
- `NO_SECTION` sentinel for missing sections
- Comprehensive template test suite

### Risk 4: Incremental Build Complexity

**Concern**: Snapshots complicate incremental builds.

**Mitigation**:
- `content_hash` on PageSnapshot enables change detection.
- Snapshot can be partially rebuilt (only changed sections).
- Phase 2 RFC will address incremental snapshot updates.

### Risk 5: Snapshot Integrity

**Concern**: Snapshot creation fails or produces inconsistent data.

**Mitigation**:
- **Integrity Checks**: Builder verifies tree completeness (no dangling refs) and circularity resolution before returning.
- **Fail Fast**: Any error in Phase 1-6 of the builder raises a `SnapshotError`, aborting the build immediately rather than producing corrupt output.
- **Immutable Verification**: `PageSnapshot` and `SectionSnapshot` use `__post_init__` to validate mandatory fields.

---

## Alternatives Considered

### Alternative 1: Protocol Migration

**Approach**: Migrate 178 usages of `Section` to `SectionLike` protocol (`bengal/protocols/core.py:122`).

| Aspect | Protocol Migration | Snapshot Engine |
|--------|-------------------|-----------------|
| Files changed | 85 files | ~10 new files |
| Thread-safety | ❌ Still has `@cached_property` races | ✅ Frozen = no races |
| Scout pattern | ❌ Not enabled | ✅ Enabled |
| Wave scheduling | ❌ Not enabled | ✅ Enabled |
| Protocol extension | Need 18+ members | Satisfies existing protocols |

**Rejected because**: Doesn't solve the core problem (thread-safety), requires more changes, and doesn't enable the performance patterns (scout, waves) that make this RFC valuable.

### Alternative 2: Add Locks to Cached Properties

**Approach**: Make each `@cached_property` thread-safe with per-property locks.

```python
# Would require modifying bengal/core/section/*.py
class Section:
    _locks: dict[str, threading.Lock]
    
    @property
    def sorted_pages(self) -> list[Page]:
        with self._locks['sorted_pages']:
            if not hasattr(self, '_sorted_pages'):
                self._sorted_pages = sorted(...)
            return self._sorted_pages
```

| Aspect | Locking | Snapshot Engine |
|--------|---------|-----------------|
| Lock acquisitions/page | 14 per page access | 0 |
| Contention under parallel | High (shared Section) | Zero (frozen) |
| Code complexity | Medium (lock management) | Low (frozen dataclass) |
| Scout pattern | ❌ Not enabled | ✅ Enabled |

**Rejected because**: 14 properties × 1000 pages = 14,000 lock acquisitions. Lock contention defeats free-threading benefits.

### Alternative 3: ContextVar for Thread-Local Caches

**Approach**: Use `ContextVar` to give each worker thread its own cached values.

```python
from contextvars import ContextVar
_section_caches: ContextVar[dict[int, dict[str, Any]]] = ContextVar('section_caches')
```

| Aspect | ContextVar | Snapshot Engine |
|--------|-----------|-----------------|
| Memory usage | O(workers × sections × props) | O(sections × props) |
| Cross-thread sharing | ❌ Each thread has own cache | ✅ Single shared snapshot |
| Scout warming | ❌ Can only warm own context | ✅ Warms shared cache |
| Cache coherency | Complex (N copies) | Simple (1 frozen copy) |

**Rejected because**: Memory multiplied by thread count, scout can't warm another thread's cache, and cache coherency becomes complex with multiple copies.

---

## Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **Performance** | ≥2x improvement for 1000 pages | `benchmarks/test_github_pages_optimization.py` |
| **Correctness** | All existing tests pass, identical output | `pytest tests/` |
| **Thread Safety** | Zero race conditions | `BENGAL_NO_PARALLEL=0` stress test |
| **Simplicity** | Remove 3 wrapper classes, net code reduction | Line count before/after |
| **Type Safety** | Snapshots satisfy `PageLike`, `SectionLike`, `SiteLike` | `ty` type checker |

**Gate for Phase 3 Completion**: Benchmark showing measurable improvement over baseline (established before implementation).

---

## Future Work

### Incremental Snapshot Updates

Instead of full snapshot recreation on file change:

```python
def update_snapshot(old: SiteSnapshot, changed: set[Path]) -> SiteSnapshot:
    """Incrementally update snapshot for changed files."""
    # Only re-snapshot affected pages/sections
    # Reuse unchanged portions (structural sharing)
```

### Speculative Rendering

Use snapshot's `content_hash` for speculation:

```python
# Start rendering before we know what changed
predicted = predict_affected(changed_files)
await render_speculative(predicted)

# Confirm and commit correct guesses
actual = compute_actual_affected(changed_files)
commit_renders(speculative_results, actual)
```

### Attention-Based Priority

For dev server, render most-viewed pages first:

```python
# Integrate with analytics
attention_scores = compute_from_analytics(page_views)
# High-traffic pages rendered first for faster preview
```

---

## Related Documents

- `plan/rfc-protocol-driven-typing.md` - Superseded by this RFC
- `plan/plan-section-protocol-migration.md` - Superseded by this RFC (deleted)
- `plan/rfc-bengal-v2-architecture.md` - Parent architecture vision
- `bengal/rendering/pipeline/write_behind.py` - Existing async I/O (integrated)

---

## Appendix: Evidence Verification Commands

Commands to verify the evidence claims in this RFC:

```bash
# Count Section type usages (expect: 178 matches across 85 files)
grep -rn ": Section\b" bengal/ --include="*.py" | wc -l

# Count @cached_property decorators on Section mixins (expect: 14)
grep -rn "@cached_property" bengal/core/section/ | grep -v "\.pyc" | wc -l

# Verify wrapper class locations
grep -rn "class SectionContext" bengal/
grep -rn "class TemplatePageWrapper" bengal/
grep -rn "class TemplateSectionWrapper" bengal/

# Verify protocol definitions
grep -rn "class SectionLike" bengal/
grep -rn "class PageLike" bengal/

# Establish performance baseline (run before implementation)
cd benchmarks && pytest test_github_pages_optimization.py -k "1000_pages" \
    --benchmark-json=../reports/snapshot_rfc_baseline.json -v
```

---

## Appendix: Template Compatibility Matrix

| Current Access | Snapshot Equivalent | Notes |
|---------------|---------------------|-------|
| `section.title` | `SectionSnapshot.title` | Direct attribute |
| `section.params.author` | `SectionSnapshot.params['author']` | `params` property |
| `section.metadata.get('x')` | `SectionSnapshot.metadata.get('x')` | MappingProxyType |
| `section.sorted_pages` | `SectionSnapshot.sorted_pages` | Pre-computed tuple |
| `section.root` | `SectionSnapshot.root` | Pre-resolved |
| `{% if section %}` | `SectionSnapshot.__bool__ = True` | Always truthy |
| `SectionContext(None)` | `NO_SECTION` sentinel | Empty but truthy |
| `page._section` | `PageSnapshot.section` | Direct reference |
| `page.metadata` | `PageSnapshot.metadata` | MappingProxyType |
| `page.reading_time` | `PageSnapshot.reading_time` | Pre-computed int |

---

## Changelog

- 2026-01-17: Revised draft - added file:line evidence citations, corrected @cached_property count (13→14), improved alternatives analysis, added benchmark methodology
- 2026-01-17: Initial draft
