# Epic: Protocol Migration — v0.2.x

**Status**: In Progress  
**Created**: 2026-02-06  
**Updated**: 2026-02-06  
**Target**: v0.2.0  
**Phase**: 1 of 4 (v2 Architecture Roadmap)  
**Estimated Effort**: 8-12 hours remaining (Sprint 1 complete, Sprint 2 partially complete)  
**Dependencies**: Coordinate with Site Cleanup and Service Wiring (Phases 4-5 affect Sprint 4 scope)  
**Predecessor**: Site God Object Decomposition (BuildState consolidation)  
**Successor**: Epic: Canonical Config (Phase 2)

---

## Why This Is Next

The v2 architecture roadmap (`rfc-bengal-v2-architecture.md`) defines four phases:

| Phase | Epic | Status | Depends On |
|-------|------|--------|------------|
| **1** | **Protocol Migration** | **← IN PROGRESS** | None |
| 2 | Canonical Config | Planned | None (parallel OK) |
| 3 | Service Extraction | Planned | Phase 2 |
| 4 | Effect-Traced Builds | Planned | Phase 3 |

Protocol migration is the foundation. It has no hard dependencies, lowest effort, and unlocks type safety across the entire codebase. The BuildState consolidation moved mutable state off `Site`, and the ongoing **Site Cleanup and Service Wiring** work is further reducing `Site`'s surface area — both make protocol migration easier since functions interact with a thinner surface.

### Coordination: Site Cleanup and Service Wiring

The service wiring plan (Phases 0-2 complete, Phase 3 in progress, Phases 4-5 pending) is running concurrently:

- **Phase 1 (complete)**: Wired QueryService consumers in `orchestration/` and `rendering/` to `BuildContext.query_service`. These callers no longer need `site: SiteLike` at all — they use `ctx: BuildContext`.
- **Phase 2 (complete)**: Wired DataService, removing `Site._load_data_directory()`.
- **Phase 4 (pending)**: PageCacheManager extraction — will move 165 lines of cache logic out of Site.
- **Phase 5 (pending)**: Cascade extraction — will change how `build_cascade_snapshot()` is accessed.

**Impact**: Sprint 4 (Site migration) has reduced scope because some orchestration/rendering consumers were already moved off `site.method()` to `ctx.query_service.method()`. Sprint 4 tasks should be re-scoped after service wiring Phases 4-5 land.

---

## Current State (measured 2026-02-06)

### Protocol Adoption

| Type Annotation | Concrete Usages | Protocol Usages | Adoption Rate |
|-----------------|-----------------|-----------------|---------------|
| `site: Site` | ~214 | `site: SiteLike` ~165 | **44%** |
| `page: Page` | ~263 | `page: PageLike` ~71 | **21%** |
| `section: Section` | ~64 | `section: SectionLike` ~36 | **36%** |

### ty Error Baseline

Run `uv run ty check 2>&1 | grep -c "error\["` for a fresh count before starting each sprint.

| Error Type | Original Count | Root Cause |
|------------|---------------|------------|
| `invalid-argument-type` | 105 | Concrete type expected, protocol passed |
| `unresolved-attribute` | 55 | Missing attributes after `hasattr` checks |
| `unused-ignore-comment` | ~42 | Stale `# type: ignore` directives (re-measure) |
| `invalid-assignment` | 24 | Type annotation mismatches |
| `call-non-callable` | 22 | `hasattr` doesn't narrow to callable |
| Other | 91 | Various |
| **Total** | **~339** | Re-measure before each sprint |

**Note**: 156 total `# type: ignore` comments exist in the codebase. Only a subset are flagged as `unused-ignore-comment` by ty.

---

## Success Criteria

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Site protocol adoption | 44% | 85%+ | >=80% |
| Page protocol adoption | 21% | 85%+ | >=80% |
| Section protocol adoption | 36% | 80%+ | >=80% |
| ty errors (total) | ~339 | <200 | <200 |
| `invalid-argument-type` errors | 105 | <30 | <30 |
| `unused-ignore-comment` errors | ~42 | 0 | 0 |
| New concrete type annotations in PRs | N/A | 0 | 0 |

---

## Sprint Breakdown

### Sprint 1: Protocol Extensions — COMPLETE

All protocol definitions and capability protocols are in place:

- `PageLike` — 20+ attributes including `metadata`, `tags`, `description`, `toc`, `slug`, etc.
- `SiteLike` — 25+ attributes including `output_dir`, `dev_mode`, `theme_config`, `build_time`, etc.
- `SectionLike` — Full consumer coverage with identity, content, metadata, navigation properties
- `ConfigLike` — `get()`, `__getitem__()`, `__contains__()` at `bengal/protocols/core.py:487-514`
- `NavigableSection`, `QueryableSection` — Extended section protocols
- `bengal/protocols/capabilities.py` — 5 capability protocols with TypeGuard functions (`HasClearTemplateCache`, `HasActionRebuild`, `HasConfigChangedSignal`, `HasErrors`, `HasWalk`)

No remaining work.

---

### Sprint 2: Section Protocol Migration (1-2 hours remaining)

Section is at **36% adoption** — 64 concrete usages across 31 files, 36 protocol usages. Push to >=80%.

#### Task 2.1: Migrate `orchestration/section.py` (10 remaining instances)

Partially done (was 19, now 10 concrete + 9 protocol). Finish migrating remaining params.

**Commit**: `orchestration: finish section.py SectionLike migration`

#### Task 2.2: Migrate `content/discovery/` (14 instances)

- `content/discovery/content_discovery.py` (6)
- `content/discovery/section_builder.py` (5)
- `content/discovery/page_factory.py` (2 — Section in return types)
- `content/discovery/directory_walker.py` (1)

**Note**: Discovery code runs pre-snapshot and may need concrete types for mutation. Audit each usage.

**Commit**: `content: migrate discovery to SectionLike protocol`

#### Task 2.3: Migrate `core/section/` (9 instances)

Internal section module — audit for mutation needs.

- `core/section/hierarchy.py` (2)
- `core/section/navigation.py` (1)
- `core/section/ergonomics.py` (1)
- `core/section/queries.py` (1)
- `core/section/utils.py` (1)
- `core/section/weighted.py` (1)
- `core/page/page_core.py` (1 — Section in Page field)
- `core/page/relationships.py` (3 — may need concrete)

**Commit**: `core: migrate section submodule to SectionLike where safe`

#### Task 2.4: Migrate `content_types/` (5 instances)

- `content_types/base.py` (1)
- `content_types/utils.py` (3) — already has 3 SectionLike, 3 concrete remain
- `content_types/registry.py` (1)

**Note**: `content_types/strategies.py` already uses SectionLike (7 instances).

**Commit**: `content: migrate content_types to SectionLike protocol`

#### Task 2.5: Migrate remaining Section consumers (~26 instances)

- `core/site/discovery.py` (4) — write-side, may need concrete
- `core/nav_tree.py` (1)
- `core/registry.py` (3)
- `snapshots/types.py` (3)
- `snapshots/builder.py` (1)
- `rendering/template_functions/openapi.py` (2)
- `rendering/template_functions/navigation/auto_nav.py` (1)
- `core/utils/config.py` (1), `core/diagnostics.py` (1), `output/icons.py` (1)
- `utils/paths/url_strategy.py` (1)
- `orchestration/build_context.py` (1)
- `health/utils.py` (1)
- `cache/indexes/section_index.py` (1)
- `core/page/navigation.py` (2)

**Commit**: `core: migrate remaining Section consumers to SectionLike`

---

### Sprint 3: Page Protocol Migration (3-4 hours)

Page is at **21% adoption** — 263 concrete usages, 71 protocol usages. The heaviest sprint.

#### Task 3.1: Migrate `rendering/pipeline/core.py` (14 instances)

Highest-concentration file. Core render pipeline.

**Commit**: `rendering: migrate pipeline/core.py to PageLike protocol`

#### Task 3.2: Migrate `rendering/renderer.py` (11 instances)

**Commit**: `rendering: migrate renderer.py to PageLike protocol`

#### Task 3.3: Migrate `debug/explainer.py` (16 instances)

Highest raw count. Debug tool — all reads, no mutation.

**Commit**: `debug: migrate explainer.py to PageLike protocol`

#### Task 3.4: Migrate `rendering/pipeline/` (remaining ~33 instances)

- `pipeline/output.py` (10)
- `pipeline/cache_checker.py` (10)
- `pipeline/json_accumulator.py` (8)
- `pipeline/autodoc_renderer.py` (2)
- `pipeline/write_behind.py` (2)
- `pipeline/toc.py` (1)

**Commit**: `rendering: migrate pipeline modules to PageLike protocol`

#### Task 3.5: Migrate `postprocess/` (~20 instances)

- `postprocess/xref_index.py` (8)
- `postprocess/social_cards.py` (5)
- `postprocess/output_formats/utils.py` (5)
- `postprocess/output_formats/txt_generator.py` (3)
- `postprocess/output_formats/json_generator.py` (2)
- `postprocess/sitemap.py` (2), `postprocess/rss.py` (1), `postprocess/redirects.py` (1)
- `postprocess/output_formats/index_generator.py` (1), `postprocess/__init__.py` (1)

**Commit**: `postprocess: migrate to PageLike protocol`

#### Task 3.6: Migrate `rendering/template_functions/` (~8 instances)

Most template functions already use `PageLike` (71 protocol usages). Remaining concrete:

- `rendering/template_functions/navigation/scaffold.py` (1)
- `rendering/template_functions/navigation/breadcrumbs.py` (1)
- `rendering/template_functions/taxonomies.py` (1)
- `rendering/template_functions/sharing.py` (1)
- `rendering/template_functions/changelog.py` (1)
- `rendering/template_functions/blog.py` (1)
- `rendering/template_functions/autodoc.py` (1)
- `rendering/template_functions/__init__.py` (1)

**Commit**: `rendering: migrate remaining template_functions to PageLike`

#### Task 3.7: Migrate remaining Page consumers (~60 instances)

Major files:

- `analysis/graph/knowledge_graph.py` (16 — likely needs concrete for mutation, skip if so)
- `cache/path_registry.py` (6)
- `build/provenance/filter.py` (6)
- `core/section/queries.py` (5)
- `core/nav_tree.py` (5)
- `postprocess/output_formats/utils.py` (5 — PageLike already, verify)
- `content_types/utils.py` (4), `content_types/base.py` (3), `content_types/templates.py` (2)
- `cache/query_index.py` (4)
- `effects/render_integration.py` (4), `effects/block_diff.py` (4)
- `rendering/template_tests.py` (4), `rendering/content_cache.py` (4)
- `parsing/backends/patitas/request_context.py` (4)
- `snapshots/types.py` (4), `snapshots/builder.py` (3), `snapshots/utils.py` (3)
- `orchestration/render/orchestrator.py` (3), `orchestration/related_posts.py` (3)
- Various scattered files with 1-2 instances each

**Commit**: `core: migrate remaining Page consumers to PageLike protocol`

---

### Sprint 4: Site Protocol Migration (2-3 hours)

Site is at **44% adoption** — 214 concrete, 165 protocol. Push to >=80%.

**Note**: Scope may shrink further as the service wiring plan's Phases 4-5 complete. Re-audit before starting.

#### Task 4.1: Migrate `rendering/template_functions/` (~35 instances)

The largest batch. ~35 files with 1-2 instances each. Mechanical — same pattern everywhere:

```python
# Before
from bengal.core import Site
def register_functions(env: TemplateEnvironment, site: Site) -> None:

# After
from bengal.protocols import SiteLike
def register_functions(env: TemplateEnvironment, site: SiteLike) -> None:
```

Includes: `i18n.py` (6), `version_url.py` (6), `get_page.py` (5), `memo.py` (3), `navigation/__init__.py` (1), `seo.py` (2), `urls.py` (2), `sharing.py` (2), `resources.py` (2), `collections.py` (2), and ~25 more files with 1 instance each.

**Commit**: `rendering: migrate template_functions to SiteLike protocol`

#### Task 4.2: Migrate `health/` (~30 instances)

- `health/validators/navigation.py` (7)
- `health/validators/taxonomy.py` (5)
- `health/validators/links.py` (4)
- `health/validators/rendering.py` (4)
- `health/validators/tracks.py` (2)
- `health/validators/connectivity.py` (1), `health/validators/cross_ref.py` (1), `health/validators/anchors.py` (2), `health/validators/accessibility.py` (1)
- `health/utils.py` (3)
- `health/linkcheck/internal_checker.py` (2), `health/linkcheck/orchestrator.py` (2)

**Commit**: `health: migrate validators to SiteLike protocol`

#### Task 4.3: Migrate `orchestration/` (~20 instances)

Some callers already wired to `BuildContext.query_service` via service wiring. Remaining:

- `orchestration/build/provenance_filter.py` (4)
- `orchestration/css_optimizer.py` (3)
- `orchestration/build/__init__.py` (3)
- `orchestration/render/orchestrator.py` (3)
- `orchestration/asset.py` (3)
- `orchestration/content.py` (2)
- `orchestration/taxonomy.py` (2)
- `orchestration/section.py` (2)

**Commit**: `orchestration: migrate to SiteLike protocol`

#### Task 4.4: Migrate `postprocess/` (~18 instances)

- `postprocess/xref_index.py` (3)
- `postprocess/sitemap.py` (3)
- `postprocess/rss.py` (3)
- `postprocess/social_cards.py` (2)
- `postprocess/output_formats/utils.py` (4)
- `postprocess/output_formats/__init__.py` (2), `postprocess/output_formats/json_generator.py` (2)
- `postprocess/output_formats/llm_generator.py` (2), `postprocess/output_formats/txt_generator.py` (2)
- `postprocess/output_formats/index_generator.py` (2), `postprocess/output_formats/lunr_index_generator.py` (1)
- `postprocess/speculation.py` (2)

**Commit**: `postprocess: migrate to SiteLike protocol`

#### Task 4.5: Migrate remaining Site consumers (~50 instances)

- `snapshots/builder.py` (8)
- `utils/paths/url_strategy.py` (8)
- `rendering/context/__init__.py` (6)
- `rendering/pipeline/output.py` (4), `pipeline/core.py` (3), `pipeline/json_accumulator.py` (2), `pipeline/cache_checker.py` (2), `pipeline/write_behind.py` (1), `pipeline/autodoc_renderer.py` (2)
- `rendering/template_engine/environment.py` (4)
- `rendering/engines/jinja.py` (3), `rendering/engines/kida.py` (1)
- `core/nav_tree.py` (5)
- `core/resources/processor.py` (4)
- `cli/dashboard/serve.py` (4), `cli/dashboard/screens.py` (4), `cli/commands/validate.py` (4)
- `autodoc/orchestration/page_builders.py` (4), `autodoc/orchestration/section_builders.py` (2)
- `orchestration/utils/virtual_pages.py` (4), `orchestration/menu.py` (4), `orchestration/postprocess.py` (3)
- `rendering/assets.py` (3), `themes/swizzle.py` (3)
- Various scattered (30+)

**Commit**: `core: migrate remaining Site consumers to SiteLike protocol`

---

### Sprint 5: Cleanup & Type Hygiene (2-3 hours)

#### Task 5.1: Remove stale `# type: ignore` comments

Run `uv run ty check` and remove all `unused-ignore-comment` errors. Re-measure count before starting — original was 42, likely lower now.

**Commit**: `chore: remove stale type: ignore comments`

#### Task 5.2: Guard `__file__` access (14 instances)

Add `assert module.__file__ is not None` before `Path(module.__file__)`.

- `cli/commands/theme.py` (5)
- `build/detectors/template.py` (2)
- `assets/pipeline.py` (2)
- Other files (5)

**Commit**: `chore: guard __file__ access across codebase`

#### Task 5.3: Apply TypeGuard patterns for `hasattr` (22 instances)

Replace `hasattr(obj, "method")` with `isinstance(obj, Protocol)` using the capability protocols in `bengal/protocols/capabilities.py`.

**Commit**: `core: apply TypeGuard patterns for hasattr narrowing`

#### Task 5.4: Fix async override mismatches (5 instances)

- `cli/dashboard/base.py:123` — `action_quit` sync -> async
- `cli/dashboard/serve.py:501` — same

**Commit**: `cli: fix async override mismatches in dashboard`

#### Task 5.5: Fix protocol Self-type annotations (8 instances)

Remove explicit `self: Protocol` annotations from renderer methods.

**Commit**: `parsing: fix protocol Self-type annotations in renderers`

---

## Dependency Graph

```
Sprint 1 (Protocol Extensions) ✅ COMPLETE
├─→ Sprint 2 (Section Migration) — ~40% done, 1-2h remaining
├─→ Sprint 3 (Page Migration) — ~8% done, 3-4h remaining
├─→ Sprint 4 (Site Migration) — coordinate with service wiring, 2-3h remaining
└─→ Sprint 5 (Cleanup) — after Sprints 2-4

Sprints 2, 3, 4 are independent of each other (can be parallelized).
Sprint 4 should coordinate with Site Cleanup Phases 4-5 (PageCacheManager, Cascade).
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
| Protocol missing attributes -> runtime AttributeError | Low | High | Sprint 1 complete; protocols have full coverage |
| Functions needing concrete types for mutation | Low | Medium | Audit each `setattr`/mutation; keep concrete where needed |
| `isinstance` checks break with protocols | Low | High | All protocols are `@runtime_checkable`; test after each sprint |
| Test mocks break with protocol signatures | Medium | Low | Update test fixtures to use protocol-compatible mocks |
| Import cycles from protocol imports | Low | Medium | Use `TYPE_CHECKING` blocks for protocol imports |
| Service wiring changes Site surface area mid-sprint | Medium | Low | Coordinate Sprint 4 timing with service wiring Phases 4-5 |

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

Once protocol adoption reaches >=80% for all three types:

1. **Phase 2: Canonical Config** (`rfc-config-architecture-v2.md`) — Unify config to nested-only structure with typed accessor class. 20-30 hours.
2. **Phase 3: Service Extraction** (`evaluated/rfc-aggressive-cleanup.md`) — Replace the 10 Site mixins with composed services. 40-60 hours. Depends on Phase 2.
3. **Phase 4: Effect-Traced Builds** (`rfc-effect-traced-incremental-builds.md`) — Replace 13 detectors with declarative effects. 50-70 hours. Depends on Phase 3.
