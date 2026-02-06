# Epic: Protocol Migration — v0.2.x

**Status**: Ready  
**Created**: 2026-02-06  
**Target**: v0.2.0  
**Phase**: 1 of 4 (v2 Architecture Roadmap)  
**Estimated Effort**: 12-16 hours  
**Dependencies**: None  
**Predecessor**: Site God Object Decomposition (BuildState consolidation)  
**Successor**: Epic: Canonical Config (Phase 2)

---

## Why This Is Next

The v2 architecture roadmap (`rfc-bengal-v2-architecture.md`) defines four phases:

| Phase | Epic | Status | Depends On |
|-------|------|--------|------------|
| **1** | **Protocol Migration** | **← YOU ARE HERE** | None |
| 2 | Canonical Config | Planned | None (parallel OK) |
| 3 | Service Extraction | Planned | Phase 2 |
| 4 | Effect-Traced Builds | Planned | Phase 3 |

Protocol migration is the foundation. It has no dependencies, lowest effort, and unlocks type safety across the entire codebase. The BuildState consolidation you just completed moved mutable state off `Site`, making protocols easier to adopt since functions interact with a thinner surface area.

---

## Current State (measured 2026-02-06)

### Protocol Adoption

| Type Annotation | Concrete Usages | Protocol Usages | Adoption Rate |
|-----------------|-----------------|-----------------|---------------|
| `site: Site` | ~223 | `site: SiteLike` ~149 | **40%** |
| `page: Page` | ~258 | `page: PageLike` ~40 | **13%** |
| `section: Section` | ~97 | `section: SectionLike` 2 | **2%** |

### ty Error Baseline

| Error Type | Count | Root Cause |
|------------|-------|------------|
| `invalid-argument-type` | 105 | Concrete type expected, protocol passed |
| `unresolved-attribute` | 55 | Missing attributes after `hasattr` checks |
| `unused-ignore-comment` | 42 | Stale `# type: ignore` directives |
| `invalid-assignment` | 24 | Type annotation mismatches |
| `call-non-callable` | 22 | `hasattr` doesn't narrow to callable |
| Other | 91 | Various |
| **Total** | **339** | |

---

## Success Criteria

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Site protocol adoption | 40% | 85%+ | ≥80% |
| Page protocol adoption | 13% | 85%+ | ≥80% |
| Section protocol adoption | 2% | 80%+ | ≥80% |
| ty errors (total) | 339 | <200 | <200 |
| `invalid-argument-type` errors | 105 | <30 | <30 |
| `unused-ignore-comment` errors | 42 | 0 | 0 |
| New concrete type annotations in PRs | N/A | 0 | 0 |

---

## Sprint Breakdown

### Sprint 1: Protocol Extensions (2-3 hours)

Extend existing protocols to cover attributes used by consumers before migrating signatures.

#### Task 1.1: Extend PageLike with missing attributes

**File**: `bengal/protocols/core.py`

Add `metadata`, `tags`, and any other properties that template functions/renderers access on Page but aren't on PageLike yet.

```python
@runtime_checkable
class PageLike(Protocol):
    # ... existing ...
    @property
    def metadata(self) -> dict[str, Any]: ...
    @property
    def tags(self) -> list[str] | None: ...
```

**Validation**: `isinstance(Page(...), PageLike)` returns True.

**Commit**: `core: extend PageLike protocol with metadata and tags`

#### Task 1.2: Extend SiteLike with missing attributes

**File**: `bengal/protocols/core.py`

Add `output_dir`, `dev_mode`, and other properties accessed by orchestration/rendering code.

```python
@runtime_checkable
class SiteLike(Protocol):
    # ... existing ...
    @property
    def output_dir(self) -> Path: ...
    @property
    def dev_mode(self) -> bool: ...
```

**Commit**: `core: extend SiteLike protocol with output_dir and dev_mode`

#### Task 1.3: Extend SectionLike with missing attributes

**File**: `bengal/protocols/core.py`

Audit `Section` usages to find all properties/methods consumed, ensure `SectionLike` covers them.

**Commit**: `core: extend SectionLike protocol for full consumer coverage`

#### Task 1.4: Add ConfigLike protocol

**File**: `bengal/protocols/core.py`

```python
@runtime_checkable
class ConfigLike(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...
    def __getitem__(self, key: str) -> Any: ...
    def __contains__(self, key: object) -> bool: ...
```

**Commit**: `core: add ConfigLike protocol for config access`

#### Task 1.5: Add capability protocols + TypeGuards

**File**: `bengal/protocols/capabilities.py` (new)

TypeGuard functions for `hasattr`-based patterns that ty can't narrow:

```python
@runtime_checkable
class HasClearTemplateCache(Protocol):
    def clear_template_cache(self, names: list[str]) -> None: ...

def has_clear_template_cache(obj: object) -> TypeGuard[HasClearTemplateCache]:
    return hasattr(obj, "clear_template_cache")
```

**Commit**: `core: add capability protocols with TypeGuard functions`

---

### Sprint 2: Section Protocol Migration (2-3 hours)

Section has the **worst adoption (2%)** and **highest impact** — 97 concrete usages across 36 files, but only 2 protocol usages.

#### Task 2.1: Migrate `orchestration/section.py` (19 instances)

The biggest single file. All `section: Section` params become `section: SectionLike`.

**Commit**: `orchestration: migrate section.py to SectionLike protocol`

#### Task 2.2: Migrate `content_types/` (15 instances)

- `content_types/strategies.py` (7)
- `content_types/utils.py` (6)
- `content_types/base.py` (2)

**Commit**: `content: migrate content_types to SectionLike protocol`

#### Task 2.3: Migrate `content/discovery/` (13 instances)

- `content/discovery/content_discovery.py` (6)
- `content/discovery/section_builder.py` (5)
- `content/discovery/directory_walker.py` (1)
- `content/discovery/page_factory.py` (2 — Section in return types)

**Commit**: `content: migrate discovery to SectionLike protocol`

#### Task 2.4: Migrate `core/section/` (8 instances)

Internal section module — these may legitimately need concrete types for mutation. Audit each usage.

- `core/section/queries.py` (1)
- `core/section/navigation.py` (1)
- `core/section/hierarchy.py` (2)
- `core/section/ergonomics.py` (1)
- `core/section/utils.py` (1)
- `core/section/weighted.py` (1)

**Commit**: `core: migrate section submodule to SectionLike where safe`

#### Task 2.5: Migrate remaining Section consumers

- `core/nav_tree.py` (3)
- `core/registry.py` (3)
- `core/site/discovery.py` (4)
- `rendering/template_functions/navigation/` (7)
- `rendering/template_functions/openapi.py` (4)
- `snapshots/types.py` (3)
- Other scattered files (8)

**Commit**: `rendering: migrate remaining Section consumers to SectionLike`

---

### Sprint 3: Page Protocol Migration (3-4 hours)

Page is at **13% adoption** — 258 concrete usages, 40 protocol usages.

#### Task 3.1: Migrate `rendering/pipeline/core.py` (14 instances)

Highest-concentration file. Core render pipeline.

**Commit**: `rendering: migrate pipeline/core.py to PageLike protocol`

#### Task 3.2: Migrate `rendering/renderer.py` (11 instances)

**Commit**: `rendering: migrate renderer.py to PageLike protocol`

#### Task 3.3: Migrate `debug/explainer.py` (16 instances)

Highest raw count. Debug tool — all reads, no mutation.

**Commit**: `debug: migrate explainer.py to PageLike protocol`

#### Task 3.4: Migrate `rendering/pipeline/` (remaining ~30 instances)

- `pipeline/output.py` (10)
- `pipeline/cache_checker.py` (10)
- `pipeline/json_accumulator.py` (8)
- `pipeline/write_behind.py` (2)
- `pipeline/autodoc_renderer.py` (2)
- `pipeline/toc.py` (1)

**Commit**: `rendering: migrate pipeline modules to PageLike protocol`

#### Task 3.5: Migrate `postprocess/` (~25 instances)

- `postprocess/social_cards.py` (10)
- `postprocess/xref_index.py` (8)
- `postprocess/output_formats/utils.py` (5)
- `postprocess/output_formats/*.py` (various)
- `postprocess/sitemap.py`, `rss.py`, `speculation.py`

**Commit**: `postprocess: migrate to PageLike protocol`

#### Task 3.6: Migrate `rendering/template_functions/` (~25 instances)

- `template_functions/seo.py` (5)
- `template_functions/get_page.py` (2)
- `template_functions/navigation/scaffold.py` (7)
- `template_functions/navigation/tree.py` (2)
- `template_functions/version_url.py` (2)
- `template_functions/i18n.py` (3)
- ~15 other files with 1-2 instances each

**Commit**: `rendering: migrate template_functions to PageLike protocol`

#### Task 3.7: Migrate remaining Page consumers (~30 instances)

- `health/validators/links.py` (7)
- `analysis/graph/knowledge_graph.py` (16 — likely needs concrete for mutation)
- `core/section/queries.py` (5)
- `core/nav_tree.py` (5)
- `effects/render_integration.py` (4), `effects/block_diff.py` (4)
- `cache/query_index.py` (4)
- `build/provenance/filter.py` (6)
- Various scattered

**Commit**: `core: migrate remaining Page consumers to PageLike protocol`

---

### Sprint 4: Site Protocol Migration (2-3 hours)

Site is at **40% adoption** — 223 concrete, 149 protocol. Push to 85%+.

#### Task 4.1: Migrate `rendering/template_functions/` (~40 instances)

~40 files with 1-2 instances each. Mechanical — same pattern everywhere:

```python
# Before
from bengal.core import Site
def register_functions(env: TemplateEnvironment, site: Site) -> None:

# After
from bengal.protocols import SiteLike
def register_functions(env: TemplateEnvironment, site: SiteLike) -> None:
```

**Commit**: `rendering: migrate template_functions to SiteLike protocol`

#### Task 4.2: Migrate `health/validators/` (~30 instances)

- `health/validators/navigation.py` (7)
- `health/validators/taxonomy.py` (5)
- `health/validators/links.py` (4)
- `health/validators/rendering.py` (4)
- `health/validators/performance.py` (4)
- ~10 other validator files

**Commit**: `health: migrate validators to SiteLike protocol`

#### Task 4.3: Migrate `orchestration/` (~25 instances)

- `orchestration/css_optimizer.py` (5)
- `orchestration/build/provenance_filter.py` (8)
- `orchestration/render/orchestrator.py` (3)
- `orchestration/build/__init__.py` (3)
- Other orchestration files

**Commit**: `orchestration: migrate to SiteLike protocol`

#### Task 4.4: Migrate `postprocess/` (~15 instances)

- `postprocess/xref_index.py` (3)
- `postprocess/sitemap.py` (3)
- `postprocess/rss.py` (3)
- `postprocess/output_formats/` (8)
- Other files

**Commit**: `postprocess: migrate to SiteLike protocol`

#### Task 4.5: Migrate remaining Site consumers (~25 instances)

- `snapshots/builder.py` (12)
- `rendering/context/__init__.py` (6)
- `rendering/engines/` (5)
- `core/nav_tree.py` (5)
- `autodoc/orchestration/` (6)
- Various scattered

**Commit**: `core: migrate remaining Site consumers to SiteLike protocol`

---

### Sprint 5: Cleanup & Type Hygiene (2-3 hours)

#### Task 5.1: Remove stale `# type: ignore` comments (42 instances)

Run `uv run ty check` and remove all `unused-ignore-comment` errors.

**Commit**: `chore: remove 42 stale type: ignore comments`

#### Task 5.2: Guard `__file__` access (14 instances)

Add `assert module.__file__ is not None` before `Path(module.__file__)`.

- `cli/commands/theme.py` (5)
- `build/detectors/template.py` (2)
- `assets/pipeline.py` (2)
- Other files (5)

**Commit**: `chore: guard __file__ access across codebase`

#### Task 5.3: Apply TypeGuard patterns for `hasattr` (22 instances)

Replace `hasattr(obj, "method")` → `isinstance(obj, Protocol)` using the capability protocols from Sprint 1, Task 1.5.

**Commit**: `core: apply TypeGuard patterns for hasattr narrowing`

#### Task 5.4: Fix async override mismatches (5 instances)

- `cli/dashboard/base.py:123` — `action_quit` sync → async
- `cli/dashboard/serve.py:501` — same

**Commit**: `cli: fix async override mismatches in dashboard`

#### Task 5.5: Fix protocol Self-type annotations (8 instances)

Remove explicit `self: Protocol` annotations from renderer methods.

**Commit**: `parsing: fix protocol Self-type annotations in renderers`

---

## Dependency Graph

```
Sprint 1 (Protocol Extensions)
├─→ Sprint 2 (Section Migration)
├─→ Sprint 3 (Page Migration)
├─→ Sprint 4 (Site Migration)
└─→ Sprint 5 (Cleanup)

Sprint 2, 3, 4 are independent of each other (can be parallelized).
Sprint 5 depends on Sprints 2-4 (cleanup after migration).
```

---

## Implementation Rules

1. **Never migrate types that need mutation access** — if a function calls `page.some_mutable_method()` not on the protocol, keep concrete
2. **Verify `isinstance` still works** — protocols are `@runtime_checkable`, test after each sprint
3. **Run full test suite after each sprint** — `uv run pytest tests/ -x -q`
4. **Run ty after each sprint** — `uv run ty check 2>&1 | grep -c "error\["`
5. **One atomic commit per task** — revertable units

---

## Verification Commands

```bash
# After each sprint — count remaining errors
uv run ty check 2>&1 | grep -c "error\["

# Measure protocol adoption
rg "site: Site[^L]" bengal/ --type py -c | awk -F: '{s+=$2} END {print s}'
rg "site: SiteLike" bengal/ --type py -c | awk -F: '{s+=$2} END {print s}'
rg "page: Page[^CLl]" bengal/ --type py -c | awk -F: '{s+=$2} END {print s}'
rg "page: PageLike" bengal/ --type py -c | awk -F: '{s+=$2} END {print s}'
rg "section: Section[^LR]" bengal/ --type py -c | awk -F: '{s+=$2} END {print s}'
rg "section: SectionLike" bengal/ --type py -c | awk -F: '{s+=$2} END {print s}'

# Full test suite
uv run pytest tests/ -x -q
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Protocol missing attributes → runtime AttributeError | Medium | High | Sprint 1 gap analysis before migration |
| Functions needing concrete types for mutation | Low | Medium | Audit each `setattr`/mutation; keep concrete where needed |
| `isinstance` checks break with protocols | Low | High | All protocols are `@runtime_checkable`; test in Sprint 1 |
| Test mocks break with protocol signatures | Medium | Low | Update test fixtures to use protocol-compatible mocks |
| Import cycles from protocol imports | Low | Medium | Use `TYPE_CHECKING` blocks for protocol imports |

---

## Related RFCs

| RFC | Relationship |
|-----|-------------|
| `rfc-bengal-v2-architecture.md` | Master roadmap — this is Phase 1 |
| `rfc-protocol-driven-typing.md` | Detailed strategy for ty compliance |
| `plan-protocol-driven-typing.md` | Task-level implementation plan |
| `rfc-orchestration-type-architecture.md` | 48 orchestration-specific type errors |
| `rfc-ty-type-hardening.md` | Broader type system improvements |

---

## What Comes After

Once protocol adoption reaches ≥80% for all three types:

1. **Phase 2: Canonical Config** (`rfc-config-architecture-v2.md`) — Unify config to nested-only structure with typed accessor class. 20-30 hours.
2. **Phase 3: Service Extraction** (`rfc-aggressive-cleanup.md`) — Replace the 10 Site mixins with composed services. 40-60 hours. Depends on Phase 2.
3. **Phase 4: Effect-Traced Builds** (`rfc-effect-traced-incremental-builds.md`) — Replace 13 detectors with declarative effects. 50-70 hours. Depends on Phase 3.
