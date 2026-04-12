# Bengal Roadmap — Next 10 Epics

**Created**: 2026-04-12
**Updated**: 2026-04-12 (audit pass — verified all claims against codebase)
**Baseline**: maturity-assessment.md (2026-03-13), plan-production-maturity.md
**Goal**: Every user journey at **5.0 (Production)** — resilient, documented, CI-validated
**Version Target**: v0.4.0 (beta)

---

## Current State

Bengal v0.3.0 is Alpha. 9 of 13 journeys are above 4.0. The critical gaps are concentrated in 4 areas: autodoc coverage, multi-version polish, architecture debt, and ecosystem readiness.

| Journey | Score | Status |
|---------|:-----:|--------|
| 12. Internationalization | **5.0** | Production |
| 1. Build from Markdown | **4.8** | Production |
| 5. Taxonomy/Tagging | **4.6** | Production |
| 6. Links/Assets/Navigation | **4.6** | Production |
| 13. Output Formats/Deployment | **4.5** | Mature |
| 3. Incremental Rebuilds | **4.4** | Mature |
| 2. Customize Theme/Templates | **4.4** | Mature |
| 9. Health Checking/Validation | **4.4** | Mature |
| 10. Developer Experience/CLI | **4.3** | Mature |
| 4. Custom Directives/Filters | **4.2** | Mature |
| 11. Search/Content Discovery | **4.0** | Mature |
| 7. API Documentation (Autodoc) | **3.9** | Functional |
| 8. Multi-Version Docs | **3.9** | Functional |

**Completed epics this cycle**: i18n production readiness, ty diagnostic reduction, stale code refresh, incremental dependency wiring, immutable page pipeline (sprints 0-5)

---

## The 10 Epics

### Sequencing Rationale

Ordered by: **user-facing impact x effort efficiency**. Architecture work is interleaved — not front-loaded — so each sprint ships user value.

| # | Epic | Lifts | Gap | Effort | Risk |
|---|------|-------|-----|--------|------|
| 1 | Delete the Page Class | J3 | arch | 6-8h | Low |
| 2 | Autodoc Test Coverage & Polish | J7 | +1.1 | 20-30h | Medium |
| 3 | Multi-Version Test Hardening & Status Enum | J8 | +1.1 | 8-12h | Low |
| 4 | Mistune Reference Cleanup | J1, J4 | arch | 2-3h | Low |
| 5 | Theme Ecosystem Phase 1 | J2 | +0.6 | 16-20h | Low |
| 6 | Search Backend Adapters | J11 | +1.0 | 16-24h | Medium |
| 7 | Plugin Integration Wiring | J4 | +0.8 | 16-24h | Medium |
| 8 | Template HMR & Effect Visualization | J3 | +0.6 | 16-24h | Medium |
| 9 | Protocol Migration Completion | all | arch | 12-16h | Low |
| 10 | Output Formats: Atom, JSON-LD, Social Cards | J13 | +0.5 | 12-16h | Low |

**Total estimated effort**: 125-177 hours

---

## Epic 1: Delete the Page Class

**Lifts**: J3 (Incremental Rebuilds), architecture
**Predecessor**: epic-immutable-page-pipeline.md (Sprints 0-5 complete)
**Effort**: 6-8h | **Risk**: Low

Sprint 6 of the immutable page pipeline. SourcePage, ParsedPage, RenderedPage, and SiteSnapshot exist. PageProxy is deleted. The mutable Page class (947 lines, 4 mixins) still has mutation sites across source files and 66 test files. Delete it.

**Why now**: Smallest delta, biggest architectural payoff. Every subsequent epic benefits from a clean immutable pipeline. Free-threading safety guaranteed once mutable Page is gone.

**Key tasks**:
- Replace 7 active `Page()` instantiation sites with immutable record constructors
- Migrate mutation hotspots to produce new records instead of mutating
- Update 66 test files (bulk: search-replace Page -> PageLike or use fixtures)
- Delete `bengal/core/page/__init__.py` (947 lines)

**Acceptance**: `rg 'class Page' bengal/core/page/` returns zero hits. Full test suite passes.

**Existing RFC**: epic-immutable-page-pipeline.md (Sprint 6)

---

## Epic 2: Autodoc Test Coverage & Polish

**Lifts**: J7 (API Documentation, 3.9 -> 5.0)
**Effort**: 20-30h | **Risk**: Medium

Autodoc extractors (Python, CLI, OpenAPI) need test coverage to reach production confidence. The framework is solid — 33 source files, virtual page system, incremental caching — but extractors need edge-case hardening.

**Key tasks**:
- Sprint 0: Audit extractor edge cases (nested classes, overloaded methods, complex schemas)
- Sprint 1: Python extractor tests (target 80% coverage on `bengal/autodoc/extractors/`)
- Sprint 2: OpenAPI extractor tests + external `$ref` resolution
- Sprint 3: CLI extractor tests (milo-cli introspection)
- Sprint 4: Interactive API explorer prototype (stretch)

**Acceptance**: `pytest tests/unit/autodoc/ --cov=bengal/autodoc/extractors --cov-fail-under=80` passes.

**Existing RFCs**: rfc-autodoc-incremental-caching.md, epic-openapi-rest-layout-upgrade.md

---

## Epic 3: Multi-Version Test Hardening & Status Enum

**Lifts**: J8 (Multi-Version Docs, 3.9 -> 5.0)
**Effort**: 8-12h | **Risk**: Low

Core multi-version features are implemented: deprecation banners (`version-banner.html`), redirects (`write_root_redirect()`), version selector dropdown, and a `deprecated: bool` field on Version. What's missing: test coverage for these components, a richer version status model, and integration validation.

**Key tasks**:
- Sprint 1: Add `VersionStatus` enum (`current`, `legacy`, `deprecated`, `preview`, `eol`) replacing the boolean `deprecated` field
- Sprint 2: Version banner template tests (HTML output, i18n, conditional visibility)
- Sprint 3: Version selector component tests (dropdown rendering, navigation, deprecated styling)
- Sprint 4: Version-aware redirect integration tests + wire unused `release_date`/`end_of_life` fields into templates

**Acceptance**: `pytest tests/ -k version` covers banner rendering, selector, redirects, and status enum transitions. `VersionStatus` enum used in config and templates.

---

## Epic 4: Mistune Reference Cleanup

**Lifts**: J1, J4 (Build from Markdown, Custom Directives) — housekeeping
**Effort**: 2-3h | **Risk**: Low

The Mistune backend was already deleted. What remains: 1 deprecation shim in `bengal/parsing/__init__.py`, ~30 test/benchmark files with mistune comparison code, and scattered comments. Clean them up.

**Key tasks**:
- Remove the `engine == "mistune"` deprecation shim and warning from `create_markdown_parser()`
- Delete `tests/migration/` directory (mistune-vs-patitas comparison tests, no longer needed)
- Remove mistune benchmark comparisons from `benchmarks/test_patitas_performance.py` and `benchmarks/test_patitas_memory.py`
- Clean up stale mistune references in comments across ~10 files

**Acceptance**: `rg 'mistune' bengal/ tests/ benchmarks/ --type py` returns zero hits (excluding changelogs/plan docs).

**Existing RFC**: rfc-mistune-deprecation.md (status: complete, this is cleanup)

---

## Epic 5: Theme Ecosystem Phase 1

**Lifts**: J2 (Customize Theme/Templates, 4.4 -> 5.0)
**Effort**: 16-20h | **Risk**: Low

Bengal has one built-in theme (`default`). Library providers and directive template overrides (swizzle system) are implemented. Rich theme CLI exists (`theme list`, `theme validate`, `theme swizzle`, `theme assets`, etc.). Now: ship a second theme, theme preview command, and token documentation.

**Key tasks**:
- Sprint 1: `bengal theme preview` command — live-reloading theme development mode
- Sprint 2: Second built-in theme (minimal/documentation-focused, using Kida library providers)
- Sprint 3: CSS token contract documentation (design tokens, customization guide)
- Sprint 4: Theme test coverage for existing CLI commands

**Acceptance**: `bengal theme list` shows 2 themes. `bengal theme preview` starts a dev server with theme hot-reload.

**Existing RFC**: rfc-theme-ecosystem.md

---

## Epic 6: Search Backend Adapters

**Lifts**: J11 (Search/Content Discovery, 4.0 -> 5.0)
**Effort**: 16-24h | **Risk**: Medium

Client-side Lunr search works out of the box (pre-built indices via `LunrIndexGenerator`). No pluggable adapter protocol exists. Production sites need server-side adapters (Pagefind, Algolia). Design a search adapter protocol, ship 2 implementations.

**Key tasks**:
- Sprint 0: Design `SearchAdapter` protocol (index, query, configure methods)
- Sprint 1: Pagefind adapter (static, zero-config — best fit for SSGs)
- Sprint 2: Algolia adapter (requires API key config, index sync)
- Sprint 3: Search config in bengal.toml (`search.backend = "pagefind"`)
- Sprint 4: Integration tests with real adapters

**Acceptance**: `bengal build` with `search.backend = "pagefind"` produces a working search page.

---

## Epic 7: Plugin Integration Wiring

**Lifts**: J4 (Custom Directives/Filters, 4.2 -> 5.0)
**Effort**: 16-24h | **Risk**: Medium

The plugin infrastructure exists: entry-point discovery (`bengal.plugins` group), `Plugin` protocol, `PluginRegistry`/`FrozenPluginRegistry`, and dynamic loading via `discover_plugins()`. Template extensions (functions, filters, tests) are wired and working. However, 4 integration stubs are defined but never called: `apply_plugin_directives()`, `apply_plugin_roles()`, `apply_plugin_content_sources()`, `apply_plugin_phase_hooks()`. No CLI commands, no tests, no working example plugin.

**Key tasks**:
- Sprint 1: Wire directive and role registration into the directive/role builders during orchestration
- Sprint 2: Wire content sources and phase hooks into the build lifecycle
- Sprint 3: `bengal plugin list`, `bengal plugin validate`, `bengal plugin info` CLI commands
- Sprint 4: Working example plugin (pip-installable, registers a custom directive) + comprehensive tests
- Sprint 5: Update docs to reflect actual vs. aspirational capabilities

**Acceptance**: A pip-installable test plugin registers a custom directive that renders in `bengal build`. `bengal plugin list` shows it. All 4 integration paths have tests.

---

## Epic 8: Template HMR & Effect Visualization

**Lifts**: J3 (Incremental Rebuilds, 4.4 -> 5.0)
**Effort**: 16-24h | **Risk**: Medium

The EffectBasedDetector unified 13 legacy detectors. Incremental builds work for content, data files, taxonomy, and cascade changes. The critical gap: **template changes always trigger full rebuilds** because `template_detector.py` was deleted during the effect-based refactoring, breaking the `_can_use_incremental_template_update()` code path in `build_trigger.py`. Kida supports `BLOCK_LEVEL_DETECTION` but nothing connects it to the dev server.

**Key tasks**:
- Sprint 1: Implement `TemplateChangeDetector` using EffectTracer data (which templates affect which pages)
- Sprint 2: Wire template-granular rebuild into `build_trigger.py` so only affected pages rebuild on template changes
- Sprint 3: `bengal build --show-effects` CLI command — dependency graph visualization
- Sprint 4: Benchmark template HMR (<100ms for single-template change on 1000-page site)

**Acceptance**: Template edits in dev server rebuild only affected pages (not full site). `bengal build --show-effects` produces a dependency graph.

**Existing RFCs**: rfc-effect-traced-incremental-builds.md, rfc-incremental-build-observability.md

---

## Epic 9: Protocol Migration Completion

**Lifts**: All journeys (architecture)
**Predecessor**: epic-protocol-migration.md (Sprint 1 complete, Sprint 2+ stale)
**Effort**: 12-16h | **Risk**: Low

Protocol adoption as of April 2026: Site 43.6%, Page 66.5%, Section 52.2%. Push all three above 80%. This enables type-safe interfaces across the entire codebase and unlocks cleaner service extraction.

**Key tasks**:
- Sprint 1: Re-measure adoption metrics (fresh counts)
- Sprint 2: Section migration (~43 concrete -> <10)
- Sprint 3: Site migration (~304 concrete -> <60)
- Sprint 4: Page migration cleanup (~114 concrete -> <25)

**Acceptance**: `rg 'site: Site[^L]' bengal/ --type py | wc -l` < 60. `rg 'section: Section[^L]' bengal/ --type py | wc -l` < 10.

**Existing RFC**: epic-protocol-migration.md

---

## Epic 10: Output Formats — Atom, JSON-LD, Social Cards

**Lifts**: J13 (Output Formats/Deployment, 4.5 -> 5.0)
**Effort**: 12-16h | **Risk**: Low

RSS works (`bengal/postprocess/rss.py` — i18n-aware, visibility-respecting, top-20 pages). Missing: Atom feed (RFC 4287 compliance), JSON-LD structured data (SEO), and incremental social card generation.

**Key tasks**:
- Sprint 1: Atom feed generator (parallel to RSS, shared content model)
- Sprint 2: JSON-LD structured data (Article, BreadcrumbList, WebSite schemas)
- Sprint 3: Incremental social card generation (only regenerate for changed pages)
- Sprint 4: `bengal check --output-formats` validator for feed/structured data correctness

**Acceptance**: `bengal build` produces valid `atom.xml` (W3C Feed Validation) and `<script type="application/ld+json">` in HTML output.

---

## Dependencies & Sequencing

```
Epic 1 (Page deletion) ──────────────────────┐
                                              ├── Epic 8 (Template HMR) benefits from clean pipeline
Epic 4 (Mistune cleanup) ── independent       │
                                              │
Epic 7 (Plugin wiring) ─── benefits from ─────┘ clean immutable types
```

**Parallel lanes**:
- Lane A (architecture): Epics 1 -> 8 -> 9
- Lane B (user features): Epics 2, 3, 5, 6, 7, 10 (all independent)
- Lane C (quick wins): Epics 4 (2-3h), 3 (8-12h) — can be done anytime

---

## Success Metrics

| Metric | Current | After Epic 5 | After Epic 10 |
|--------|---------|--------------|---------------|
| Journeys at 5.0 | 2 | 5 | 13 |
| Journeys below 4.0 | 2 | 0 | 0 |
| Autodoc extractor coverage | needs audit | 80%+ | 80%+ |
| Protocol adoption (avg) | 54% | 54% | 80%+ |
| Mutable Page class | exists | deleted | deleted |
| Search backends | 1 (Lunr) | 1 | 3 (Lunr, Pagefind, Algolia) |
| Themes | 1 | 2 | 2+ |
| Plugin integration paths | 1/5 wired | 1/5 | 5/5 wired |
| Template HMR | broken (full rebuild) | broken | incremental |
| Version status | Alpha | Alpha | Beta |

---

## Changelog

- **2026-04-12 (v2)**: Audit pass — verified all epic claims against codebase. Corrected Epic 1 (947 lines, 7 instantiation sites). Replaced Epic 3 (features already exist, rescoped to test hardening + status enum, 12-16h -> 8-12h). Replaced Epic 4 (backend already deleted, rescoped to reference cleanup, 16-24h -> 2-3h). Replaced Epic 7 (infrastructure exists, rescoped to integration wiring, 20-30h -> 16-24h). Replaced Epic 8 (legacy detectors gone, rescoped to template HMR + effect viz, 40-60h -> 16-24h). Updated protocol adoption metrics to measured values. Total effort reduced from 170-244h to 125-177h.
- **2026-04-12 (v1)**: Initial roadmap drafted from maturity assessment + production maturity plan + codebase investigation.
