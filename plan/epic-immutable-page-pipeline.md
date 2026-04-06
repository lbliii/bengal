# Epic: Immutable Page Pipeline — Snapshots All The Way Down

**Status**: Draft
**Created**: 2026-04-06
**Target**: v0.4.x
**Estimated Effort**: 60-80 hours
**Dependencies**: Epic: Protocol Migration (Phase 1 in progress), Epic: Architecture Audit Remediation (Sprint 1-2)
**Source**: Layered Review (2026-04-06), rfc-bengal-v2-architecture.md (Phase 3-4)

---

## Why This Matters

Bengal's Page object is a mutable bag that **14 distinct modules** write to across **~90+ assignment sites**. This creates:

1. **Ownership chaos** — no module owns the Page lifecycle; anyone can set any field at any time
2. **Dual data model** — mutable Page and frozen PageSnapshot coexist, with rendering reading from both
3. **900-line PageProxy** — mirrors ~50 Page properties for incremental builds; every new Page property requires a parallel implementation
4. **5-step metadata conversion** — YAML → dict → PageCore → dict → CascadeView → CascadingParamsContext
5. **Free-threading unsafety** — `@cached_property` writes to `__dict__` without synchronization (undefined behavior under Python 3.14)
6. **6 intermediate representations** per page (PageCore, Page/PageProxy, CascadeView, PageSnapshot, context dict, Renderer caches)

The fix: replace mutable Page with **typed immutable records** at each pipeline stage. Each stage produces a new frozen record. No mutation, no locks, no caches, no proxy.

### Evidence (from layered review)

| Layer | Key Finding | Proposal Assessment |
|-------|-------------|---------------------|
| Architecture | 14 modules mutate Page; ~90 mutation sites | **FIXES** — each stage owns its record |
| Flow | 6 intermediate representations; 4 full traversals | **FIXES** — 3 records, 2 traversals |
| Interaction | PageProxy duplicates 50 properties; metadata round-trips 5x | **FIXES** — proxy eliminated, metadata resolved once |
| Micro | `@cached_property` unsafe under free-threading; slot access 2-15x faster | **FIXES** — frozen+slots is ideal for 3.14 |

### Three Invariants

These must remain true throughout migration or we stop and reassess:

1. **Incremental builds stay O(changed).** Per-stage content-addressed memoization ensures unchanged pages reuse previous records.
2. **SitePlan stays decomposed.** No monolith — NavigationPlan, TaxonomyPlan, RenderSchedule are separate frozen types.
3. **Templates never break.** Each sprint ships with full template compatibility verified by the existing test suite.

---

## Target Architecture

```
Stage 1 — Discover
  Read files → SourcePage(source_path, frontmatter, content_hash)
  Lightweight. No raw content loaded yet.

Stage 2 — Plan
  All SourcePages → SitePlan(NavigationPlan, TaxonomyPlan, RenderSchedule, CascadeMap)
  Cross-page relationships resolved. Pure function.

Stage 3 — Parse
  SourcePage + CascadeMap → ParsedPage(…source fields, html, toc, toc_items, excerpt, metadata)
  Embarrassingly parallel. Content loaded and parsed here.

Stage 4 — Render
  ParsedPage + SitePlan + Templates → RenderedPage(output_path, html, dependencies)
  Pure function. No mutation of any input.

Stage 5 — Write
  RenderedPage[] → disk
```

---

## Sprint Structure

| Sprint | Focus | Effort | Risk | Ships Independently? |
|--------|-------|--------|------|---------------------|
| **0** | Design: record types, `get_page()` solution, incremental strategy | 6-8h | Low | Yes (RFC only) |
| **1** | Introduce ParsedPage; rendering reads it instead of mutating Page | 12-16h | Medium | Yes |
| **2** | Introduce RenderedPage; eliminate `page.rendered_html` mutation | 8-10h | Medium | Yes |
| **3** | Decompose SitePlan; replace snapshot builder | 8-12h | Medium | Yes |
| **4** | Introduce SourcePage; replace Page at discovery | 10-14h | High | Yes |
| **5** | Delete PageProxy; cache stores typed records | 6-8h | Medium | Yes (after Sprint 4) |
| **6** | Delete Page class; cleanup, final migration | 6-8h | Low | Yes (after Sprint 5) |

Each sprint is a shippable PR. Later sprints can be deferred if earlier ones prove the model wrong.

---

## Sprint 0: Design & Validate

**Goal**: Finalize record type definitions, solve the three hardest problems on paper, get sign-off before writing code.

### Task 0.1 — Define frozen record types

Design `SourcePage`, `ParsedPage`, `RenderedPage` as frozen+slots dataclasses. Define exact field lists by auditing:
- Which fields are available after discovery (→ SourcePage)
- Which fields are available after parsing (→ ParsedPage)
- Which fields are produced by rendering (→ RenderedPage)

**Acceptance**: Type definitions written. Every current Page field mapped to exactly one record type.

### Task 0.2 — Design SitePlan decomposition

Split current `SiteSnapshot` into:
- `NavigationPlan` — prev/next/ancestors, nav trees, active trails
- `TaxonomyPlan` — tag→pages, category→pages mappings
- `RenderSchedule` — wave ordering, template groups, attention scores
- `CascadeMap` — pre-merged section cascade (replaces CascadeView)

**Acceptance**: Type definitions written. Every current SiteSnapshot field mapped to a plan type.

### Task 0.3 — Solve `get_page()` template function

`get_page()` currently parses content on-demand during rendering and mutates the page. Design the replacement:
- Option A: Pre-parse all pages before rendering; `get_page()` becomes a pure lookup into a `dict[Path, ParsedPage]`
- Option B: `get_page()` returns a lazy wrapper that triggers parsing on access (preserves current semantics but adds complexity)

Validate memory impact of Option A for 1,000 and 10,000 page sites.

**Acceptance**: Decision documented with memory benchmarks.

### Task 0.4 — Design per-stage memoization

Define how incremental builds reuse records:
- SourcePage: reuse if file hash unchanged
- SitePlan components: reuse if input SourcePages unchanged (hash of all source hashes)
- ParsedPage: reuse if SourcePage hash + parser version unchanged
- RenderedPage: reuse if ParsedPage hash + template hash unchanged

**Acceptance**: Cache key definitions for each stage. Benchmark showing incremental builds stay under 200ms for 1-page change in 500-page site.

### Task 0.5 — Design `__getattr__` for custom frontmatter

Templates access arbitrary frontmatter via `page.brand`, `page.sku`, etc. (product-jsonld.html uses 12 custom attributes). Frozen dataclasses don't support `__getattr__` by default.

Options:
- A: Add `__getattr__` that delegates to `metadata` dict (works but bypasses slots benefits for custom fields)
- B: Require templates to use `page.metadata.brand` or `page.params.brand` (breaking change)
- C: Use `__getattr__` on a thin wrapper, not the record itself

**Acceptance**: Decision documented. Template compatibility verified against all theme templates.

---

## Sprint 1: Introduce ParsedPage

**Goal**: Rendering consumes `ParsedPage` instead of mutating `Page`. Page still exists but rendering no longer writes to it.

### Task 1.1 — Create ParsedPage frozen dataclass

Define in `bengal/core/records.py` (new file):
```python
@dataclass(frozen=True, slots=True)
class ParsedPage:
    source_path: Path
    title: str
    html_content: str
    toc: str
    toc_items: tuple[TocItem, ...]  # TocItem is a frozen dataclass (level, id, text, children)
    excerpt: str
    meta_description: str
    metadata: MappingProxyType[str, Any]
    # ... all fields from current PageSnapshot
```

**Acceptance**: Type exists. Mypy/ty passes.

### Task 1.2 — Build ParsedPage in rendering pipeline

After markdown parsing in `RenderingPipeline._process_page_impl()`, construct a `ParsedPage` from the parsed results instead of mutating `page.html_content`, `page.toc`, etc.

**Files**: `bengal/rendering/pipeline/core.py`
**Acceptance**: ParsedPage constructed. Page fields still set (dual-write) for backward compatibility.

### Task 1.3 — Render context reads from ParsedPage

Modify `build_page_context()` to accept `ParsedPage` and read content/toc/metadata from it rather than from the mutable Page.

**Files**: `bengal/rendering/context/__init__.py`
**Acceptance**: Context builder uses ParsedPage. Templates produce identical output (diff test).

### Task 1.4 — CacheChecker produces ParsedPage

When cache hits, `CacheChecker` constructs a `ParsedPage` from cached data instead of mutating Page fields.

**Files**: `bengal/rendering/pipeline/cache_checker.py`
**Acceptance**: Cache-hit path returns ParsedPage. No Page mutation on cache hit.

### Task 1.5 — Remove Page mutation from rendering

Delete the dual-write from Task 1.2. Rendering no longer sets `page.html_content`, `page.toc`, `page._excerpt`, `page._meta_description`, `page._ast_cache`.

**Files**: `bengal/rendering/pipeline/core.py`, `bengal/rendering/pipeline/autodoc_renderer.py`
**Acceptance**: `rg 'page\.html_content\s*=' bengal/rendering/` returns zero hits. Full test suite passes.

---

## Sprint 2: Introduce RenderedPage ✅

**Goal**: Rendering produces `RenderedPage` instead of mutating `page.rendered_html` and `page.output_path`.
**Status**: Complete (dual-write). `RenderedPage` record is constructed in all render paths and
passed to `write_output()`. Page mutation retained for backward compatibility with
`json_accumulator`, `cache_checker.cache_rendered_output`, and autodoc paths.

### Task 2.1 — Create RenderedPage frozen dataclass ✅

```python
@dataclass(frozen=True, slots=True)
class RenderedPage:
    source_path: Path
    output_path: Path
    rendered_html: str
    render_time_ms: float
    dependencies: frozenset[str] = frozenset()
```

**File**: `bengal/core/records.py`

### Task 2.2 — Pipeline builds RenderedPage ✅

`RenderingPipeline._render_and_write()` constructs `RenderedPage` after template rendering
and `format_html()`. Passes it to `write_output()`. Dual-writes `page.rendered_html` for
backward compatibility.

**Files**: `bengal/rendering/pipeline/core.py`

### Task 2.3 — Write phase consumes RenderedPage ✅

`write_output()` accepts optional `RenderedPage` parameter. When provided, reads
`rendered_html` and `output_path` from the immutable record instead of from the
mutable Page object. `_track_and_record()` likewise accepts an `output_path` override.

**Files**: `bengal/rendering/pipeline/output.py`

### Task 2.4 — CacheChecker produces RenderedPage ✅

Both `try_rendered_cache()` and `try_parsed_cache()` construct `RenderedPage` records
and pass them to `write_output()`.

**Files**: `bengal/rendering/pipeline/cache_checker.py`

### Deferred to later sprint

- **Remove dual-write**: Eliminate `page.rendered_html = ...` once `json_accumulator`
  and `cache_checker.cache_rendered_output` are updated to accept `RenderedPage`.
- **WaveScheduler collects RenderedPage**: Worker threads return `RenderedPage` instead
  of mutated Page objects. Blocked on removing dual-write first.

---

## Sprint 3: Decompose SitePlan ✅

**Goal**: Replace monolithic `SiteSnapshot` with composed, focused plan types.
**Status**: Complete. SiteSnapshot decomposed into NavigationPlan, TaxonomyPlan, and
RenderSchedule. All consumers migrated. Flat fields removed. `SitePlan` alias added.

### Task 3.1 — Extract NavigationPlan ✅

`NavigationPlan` frozen dataclass contains `menus`, `nav_trees`, `top_level_pages`,
`top_level_sections`. Accessed via `snapshot.navigation.*`.

**Files**: `bengal/snapshots/types.py`, `bengal/snapshots/builder.py`

### Task 3.2 — Extract TaxonomyPlan ✅

`TaxonomyPlan` frozen dataclass contains `taxonomies`, `tag_pages`.
Accessed via `snapshot.taxonomy.*`.

**Files**: `bengal/snapshots/types.py`, `bengal/snapshots/builder.py`

### Task 3.3 — Extract RenderSchedule ✅

`RenderSchedule` frozen dataclass contains `topological_order`, `template_groups`,
`attention_order`, `scout_hints`, `templates`, `template_dependency_graph`,
`template_dependents`. Accessed via `snapshot.schedule.*`.

**Files**: `bengal/snapshots/types.py`, `bengal/snapshots/builder.py`

### Task 3.4 — Extract CascadeMap (deferred to Sprint 4)

CascadeSnapshot and CascadeView are already well-designed separate frozen types.
Eager cascade resolution into record metadata belongs to the SourcePage sprint.

### Task 3.5 — Compose SitePlan from components ✅

`SiteSnapshot` now composes `NavigationPlan`, `TaxonomyPlan`, and `RenderSchedule`
as component fields. Cross-cutting fields (`pages`, `sections`, `config`, etc.) stay
top-level. `SitePlan = SiteSnapshot` alias added for forward compatibility.

**Consumers migrated**: `scheduler.py`, `scout.py`, `speculative.py`, `templates.py`,
`renderer.py`, `build/__init__.py`, `tracer.py`, `block_diff.py`

---

## Sprint 4: Introduce SourcePage

**Goal**: Discovery produces `SourcePage` instead of mutable `Page`. This is the highest-risk sprint.

### Task 4.1 — Create SourcePage frozen dataclass

Lightweight record: path + parsed frontmatter + content hash. No raw content loaded.

```python
@dataclass(frozen=True, slots=True)
class SourcePage:
    source_path: Path
    title: str
    slug: str
    date: datetime | None
    tags: tuple[str, ...]
    metadata: MappingProxyType[str, Any]
    content_hash: str
    section_path: str
    # ... remaining frontmatter fields from PageCore
```

**Acceptance**: Type exists. All PageCore fields mapped.

### Task 4.2 — ContentDiscovery produces SourcePage

Modify discovery phase to produce `SourcePage` records instead of mutable `Page` objects.

**Files**: `bengal/content/discovery/content_discovery.py`, `bengal/core/site/discovery.py`
**Acceptance**: Discovery returns `list[SourcePage]`. No mutable Page created during discovery.

### Task 4.3 — Orchestration phases consume SourcePage

Section finalization, taxonomy generation, menu building, related posts indexing — all currently mutate Page. Convert to consume `SourcePage` and produce plan components.

**Files**: `bengal/orchestration/section.py`, `bengal/orchestration/taxonomy.py`, `bengal/orchestration/menu.py`, `bengal/orchestration/related_posts.py`
**Acceptance**: No orchestration phase mutates page records.

### Task 4.4 — Virtual page creation via factory functions

Replace `Page.create_virtual()` with `SourcePage.create_virtual()` or factory functions that produce complete SourcePage records.

**Files**: `bengal/orchestration/taxonomy.py`, `bengal/autodoc/orchestration/page_builders.py`
**Acceptance**: Virtual pages created as SourcePage. `Page.create_virtual()` deleted.

### Task 4.5 — Dev server hot-reload reconstructs records

Replace `page._raw_content = ...` mutation with record reconstruction: detect change → rebuild SourcePage → re-parse → re-render.

**Files**: `bengal/server/reactive/handler.py`
**Acceptance**: Dev server rebuilds via record reconstruction. No in-place mutation.

---

## Sprint 5: Delete PageProxy

**Goal**: Cache stores `ParsedPage` records. No proxy needed.

### Task 5.1 — Cache serialization for ParsedPage

Extend BuildCache to serialize/deserialize `ParsedPage` records (content, toc, metadata).

**Files**: `bengal/cache/`, `bengal/rendering/pipeline/cache_checker.py`
**Acceptance**: ParsedPage round-trips through cache correctly.

### Task 5.2 — Incremental discovery loads cached ParsedPage

For unchanged files, load `ParsedPage` from cache instead of creating PageProxy.

**Files**: `bengal/content/discovery/content_discovery.py`, `bengal/orchestration/incremental/`
**Acceptance**: Unchanged pages use cached ParsedPage. No PageProxy created.

### Task 5.3 — Delete PageProxy

Remove `bengal/core/page/proxy.py` (900 lines) and all references.

**Acceptance**: `proxy.py` deleted. `rg 'PageProxy' bengal/` returns zero hits outside tests/comments. All tests pass.

---

## Sprint 6: Delete Page Class

**Goal**: Remove the mutable Page dataclass entirely. Final cleanup.

### Task 6.1 — Audit remaining Page references

Search all 71 files that import Page. Convert remaining references to appropriate record types.

**Acceptance**: `rg 'from bengal.core.page import Page' bengal/` returns zero hits.

### Task 6.2 — Delete Page class and mixins

Remove `bengal/core/page/__init__.py` (Page class), `metadata.py` (PageMetadataMixin), `content.py` (PageContentMixin), `relationships.py` (PageRelationshipsMixin).

**Acceptance**: Page class deleted. Mixin files deleted. All tests pass.

### Task 6.3 — Update protocols

Update `PageLike` protocol to match the new record types. Or replace with a union type / protocol that SourcePage and ParsedPage both satisfy.

**Files**: `bengal/protocols/core.py`
**Acceptance**: Protocol updated. Type checker passes across codebase.

### Task 6.4 — Delete stale caches and locks

Remove `_init_lock`, `_warnings_lock`, `_load_lock`, all manual `_cache` fields, `update_frozen` helper (if no longer used).

**Acceptance**: `rg '_init_lock\|_load_lock\|_cache' bengal/core/page/` returns zero hits.

### Task 6.5 — Update documentation and architecture docs

Update `rfc-bengal-v2-architecture.md`, design principles, and any internal docs referencing the old Page model.

**Acceptance**: Docs reflect new architecture.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Incremental builds regress to O(all) | Medium | High | Sprint 0 designs memoization before any code. Benchmark gate on each sprint. |
| Template breakage from custom frontmatter access | Medium | High | Sprint 0 solves `__getattr__`. Full template test suite gates every sprint. |
| `get_page()` memory spike (pre-parsing all pages) | Low | Medium | Sprint 0 benchmarks Option A. Fallback to lazy wrapper if memory exceeds 2x. |
| Sprint 4 blast radius too large | Medium | High | Can defer Sprints 4-6 indefinitely. Sprints 1-3 deliver value independently. |
| Virtual page / autodoc incompatibility | Low | Medium | Sprint 4.4 addresses explicitly. Autodoc has its own test suite. |
| Circular import breakage | Medium | Medium | Per project memory: Bengal has fragile circular imports. Each sprint runs full import smoke test. |

---

## Success Metrics

| Metric | Current | After Sprint 3 | After Sprint 6 |
|--------|---------|-----------------|-----------------|
| Modules that mutate Page | 14 | 6 (orchestration only) | 0 |
| Intermediate page representations | 6 | 4 | 3 |
| PageProxy lines | 900 | 900 | 0 |
| Lock sites on page objects | 15 | 8 | 0 |
| Manual cache fields on page | 6 | 3 | 0 |
| `@cached_property` on page | 12 | 12 | 0 |
| Free-threading safe | No (`cached_property` UB) | Partially | Yes |
| Warm incremental build (1-page change, 500 pages) | <200ms | <200ms | <200ms |

---

## Relationship to Existing Epics

- **Epic: Protocol Migration** (Phase 1) — prerequisite. PageLike protocol must be adopted before we can introduce new record types that satisfy it.
- **Epic: Architecture Audit Remediation** — Sprint 1-2 (core model purity, boundary violations) should land first to reduce circular import risk.
- **rfc-bengal-v2-architecture.md** Phase 3 (Service Extraction) — this epic supersedes the Page-related portions of Phase 3. Service extraction for Site can proceed in parallel.
- **rfc-effect-traced-incremental-builds.md** — Sprint 0.4 (per-stage memoization) is a stepping stone toward effect-traced builds. The content-addressed cache keys designed here feed directly into the Merkle DAG approach.
