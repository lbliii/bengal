# Bengal Roadmap — Next 10 Epics

**Created**: 2026-04-12
**Baseline**: maturity-assessment.md (2026-03-13), plan-production-maturity.md
**Goal**: Every user journey at **5.0 (Production)** — resilient, documented, CI-validated
**Version Target**: v0.4.0 (beta)

---

## Current State

Bengal v0.3.0 is Alpha. 9 of 13 journeys are above 4.0. The critical gaps are concentrated in 4 areas: autodoc coverage, multi-version polish, architecture debt, and ecosystem readiness.

| Journey | Score | Status |
|---------|:-----:|--------|
| 12. Internationalization | **5.0** | Production ✅ (completed 2026-04-09) |
| 1. Build from Markdown | **4.8** | Production ✅ |
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

Ordered by: **user-facing impact × effort efficiency**. Architecture work is interleaved — not front-loaded — so each sprint ships user value.

| # | Epic | Lifts | Gap | Effort | Risk |
|---|------|-------|-----|--------|------|
| 1 | Delete the Page Class | J3 | arch | 6-8h | Low |
| 2 | Autodoc Test Coverage & Polish | J7 | +1.1 | 20-30h | Medium |
| 3 | Multi-Version Docs: Banners & Redirects | J8 | +1.1 | 12-16h | Low |
| 4 | Mistune Deprecation | J1, J4 | arch | 16-24h | Medium |
| 5 | Theme Ecosystem Phase 1 | J2 | +0.6 | 16-20h | Low |
| 6 | Search Backend Adapters | J11 | +1.0 | 16-24h | Medium |
| 7 | Plugin Discovery & Extension API | J4 | +0.8 | 20-30h | Medium |
| 8 | Effect-Traced Incremental Builds | J3 | +0.6 | 40-60h | High |
| 9 | Protocol Migration Completion | all | arch | 12-16h | Low |
| 10 | Output Formats: Atom, JSON-LD, Social Cards | J13 | +0.5 | 12-16h | Low |

**Total estimated effort**: 170-244 hours

---

## Epic 1: Delete the Page Class

**Lifts**: J3 (Incremental Rebuilds), architecture
**Predecessor**: epic-immutable-page-pipeline.md (Sprints 0-5 complete)
**Effort**: 6-8h | **Risk**: Low

Sprint 6 of the immutable page pipeline. SourcePage, ParsedPage, RenderedPage, and SiteSnapshot exist. PageProxy is deleted. The mutable Page class (857 lines, 4 mixins) still has 34 mutation sites across 13 source files and 65 test files. Delete it.

**Why now**: Smallest delta, biggest architectural payoff. Every subsequent epic benefits from a clean immutable pipeline. Free-threading safety guaranteed once mutable Page is gone.

**Key tasks**:
- Replace 5 active `Page()` instantiation sites with immutable record constructors
- Migrate 34 mutation hotspots to produce new records instead of mutating
- Update 65 test files (bulk: search-replace Page → PageLike or use fixtures)
- Delete `bengal/core/page/__init__.py` (857 lines)

**Acceptance**: `rg 'class Page' bengal/core/page/` returns zero hits. Full test suite passes.

**Existing RFC**: epic-immutable-page-pipeline.md (Sprint 6)

---

## Epic 2: Autodoc Test Coverage & Polish

**Lifts**: J7 (API Documentation, 3.9 → 5.0)
**Effort**: 20-30h | **Risk**: Medium

Autodoc extractors (Python, CLI, OpenAPI) have ~7% test coverage. This blocks production use for API documentation. The framework is solid — 32 files, virtual page system, incremental caching — but extractors are fragile without tests.

**Key tasks**:
- Sprint 0: Audit extractor edge cases (nested classes, overloaded methods, complex schemas)
- Sprint 1: Python extractor tests (target 80% coverage on `bengal/autodoc/extractors/`)
- Sprint 2: OpenAPI extractor tests + external `$ref` resolution
- Sprint 3: CLI extractor tests (milo-cli introspection)
- Sprint 4: Interactive API explorer prototype (stretch)

**Acceptance**: `pytest tests/unit/autodoc/ --cov=bengal/autodoc/extractors --cov-fail-under=80` passes.

**Existing RFCs**: rfc-autodoc-incremental-caching.md, epic-openapi-rest-layout-upgrade.md

---

## Epic 3: Multi-Version Docs — Banners & Redirects

**Lifts**: J8 (Multi-Version Docs, 3.9 → 5.0)
**Effort**: 12-16h | **Risk**: Low

Version path structure and nav scoping work. Missing: deprecation banners ("You're viewing docs for v1.x — see latest"), automatic redirects from old version paths to latest, and version status metadata.

**Key tasks**:
- Sprint 1: Add `version_status` enum (current, legacy, deprecated, preview) to version config
- Sprint 2: Deprecation banner component in Kida templates, driven by version status
- Sprint 3: Auto-redirect generation for deprecated versions (HTML meta refresh + 301 config)
- Sprint 4: Version switcher dropdown component

**Acceptance**: `bengal build` on a 3-version test root produces deprecation banners on v1 pages and redirect stubs.

---

## Epic 4: Mistune Deprecation

**Lifts**: J1, J4 (Build from Markdown, Custom Directives)
**Effort**: 16-24h | **Risk**: Medium

Mistune-based directive processing adds ~15,000 LOC of technical debt. Patitas (the custom parser) is at 100% CommonMark compliance and handles all directive types. Remove the Mistune code path.

**Key tasks**:
- Sprint 0: Audit remaining Mistune-only features (if any survive beyond Patitas coverage)
- Sprint 1: Route all directive parsing through Patitas
- Sprint 2: Delete Mistune integration layer (~15,000 LOC)
- Sprint 3: Update config to remove `parser: mistune` option, add deprecation warning for bengal.toml

**Acceptance**: `rg 'mistune' bengal/ --type py` returns zero imports. `pytest tests/` fully green.

**Existing RFC**: rfc-mistune-deprecation.md

---

## Epic 5: Theme Ecosystem Phase 1

**Lifts**: J2 (Customize Theme/Templates, 4.4 → 5.0)
**Effort**: 16-20h | **Risk**: Low

Bengal has one built-in theme. Recent work (library providers, directive template overrides) built the foundation. Now: ship a second theme, theme preview command, and token documentation.

**Key tasks**:
- Sprint 1: `bengal theme preview` command — live-reloading theme development mode
- Sprint 2: Second built-in theme (minimal/documentation-focused, using Kida library providers)
- Sprint 3: CSS token contract documentation (design tokens, customization guide)
- Sprint 4: Theme validation CLI (`bengal theme validate` — checks required templates, tokens)

**Acceptance**: `bengal theme list` shows 2 themes. `bengal theme preview` starts a dev server with theme hot-reload.

**Existing RFC**: rfc-theme-ecosystem.md

---

## Epic 6: Search Backend Adapters

**Lifts**: J11 (Search/Content Discovery, 4.0 → 5.0)
**Effort**: 16-24h | **Risk**: Medium

Client-side Lunr search works out of the box. Production sites need server-side adapters (Algolia, Meilisearch, Pagefind). Design a search adapter protocol, ship 2 implementations.

**Key tasks**:
- Sprint 0: Design `SearchAdapter` protocol (index, query, configure methods)
- Sprint 1: Pagefind adapter (static, zero-config — best fit for SSGs)
- Sprint 2: Algolia adapter (requires API key config, index sync)
- Sprint 3: Search config in bengal.toml (`search.backend = "pagefind"`)
- Sprint 4: Integration tests with real adapters

**Acceptance**: `bengal build` with `search.backend = "pagefind"` produces a working search page.

---

## Epic 7: Plugin Discovery & Extension API

**Lifts**: J4 (Custom Directives/Filters, 4.2 → 5.0)
**Effort**: 20-30h | **Risk**: Medium

Bengal's directive and filter system is powerful but internal-only. No entry-point discovery, no plugin packaging conventions, no dynamic loading. This blocks community contribution.

**Key tasks**:
- Sprint 0: Design plugin manifest format and discovery protocol
- Sprint 1: Entry-point discovery (`bengal.plugins` entry point group)
- Sprint 2: Plugin lifecycle (load, validate, register directives/filters/shortcodes)
- Sprint 3: `bengal plugin list`, `bengal plugin validate` CLI commands
- Sprint 4: Plugin authoring guide with working example

**Acceptance**: A pip-installable test plugin registers a custom directive that renders in `bengal build`.

---

## Epic 8: Effect-Traced Incremental Builds

**Lifts**: J3 (Incremental Rebuilds, 4.4 → 5.0)
**Effort**: 40-60h | **Risk**: High

The largest epic. Replace legacy IncrementalOrchestrator with EffectTracer-driven dependency graph. Today's data file fix (Epic: Incremental Dependency Wiring) was a bridge; this epic makes the Effect system the single source of truth for all incremental decisions.

**Key tasks**:
- Sprint 0: Design effect-traced dependency graph (replace 13 legacy detectors fully)
- Sprint 1: Unify all detection through EffectTracer (templates, data, cascade, taxonomy)
- Sprint 2: Template-granular HMR (dev server reloads only changed template regions)
- Sprint 3: Effect visualization (`bengal build --show-effects` dependency graph)
- Sprint 4: Benchmark suite for incremental detection (<50ms for 1000-page sites)

**Acceptance**: `bengal build --incremental` uses only EffectTracer for change detection. Zero legacy detector classes remain.

**Existing RFCs**: rfc-effect-traced-incremental-builds.md, rfc-incremental-build-observability.md

---

## Epic 9: Protocol Migration Completion

**Lifts**: All journeys (architecture)
**Predecessor**: epic-protocol-migration.md (Sprint 1 complete, Sprint 2+ stale)
**Effort**: 12-16h | **Risk**: Low

Protocol adoption as of April 2026: Site 43%, Page 66%, Section 56%. Push all three above 80%. This enables type-safe interfaces across the entire codebase and unlocks cleaner service extraction.

**Key tasks**:
- Sprint 1: Re-measure adoption metrics (fresh counts)
- Sprint 2: Section migration (44 concrete → <10)
- Sprint 3: Site migration (312 concrete → <60)
- Sprint 4: Page migration cleanup (120 concrete → <25)

**Acceptance**: `rg 'site: Site[^L]' bengal/ --type py | wc -l` < 60. `rg 'section: Section[^L]' bengal/ --type py | wc -l` < 10.

**Existing RFC**: epic-protocol-migration.md

---

## Epic 10: Output Formats — Atom, JSON-LD, Social Cards

**Lifts**: J13 (Output Formats/Deployment, 4.5 → 5.0)
**Effort**: 12-16h | **Risk**: Low

RSS works. Missing: Atom feed (RFC 4287 compliance), JSON-LD structured data (SEO), and incremental social card generation (currently regenerates all).

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
                                              ├── Epic 8 (Effect-traced) benefits from clean pipeline
Epic 4 (Mistune deprecation) ─────────────────┘

Epic 2 (Autodoc) ─────── independent
Epic 3 (Multi-version) ── independent
Epic 5 (Theme ecosystem) ─ independent
Epic 6 (Search adapters) ── independent
Epic 7 (Plugin API) ─────── benefits from Epic 5 (theme conventions)
Epic 9 (Protocols) ──────── independent, but easier after Epic 1
Epic 10 (Output formats) ── independent
```

**Parallel lanes**:
- Lane A (architecture): Epics 1 → 4 → 8 → 9
- Lane B (user features): Epics 2, 3, 5, 6, 7, 10 (all independent)

---

## Success Metrics

| Metric | Current | After Epic 5 | After Epic 10 |
|--------|---------|--------------|---------------|
| Journeys at 5.0 | 2 | 5 | 13 |
| Journeys below 4.0 | 2 | 0 | 0 |
| Autodoc extractor coverage | ~7% | 80%+ | 80%+ |
| Protocol adoption (avg) | 55% | 55% | 80%+ |
| Mutable Page class | exists | deleted | deleted |
| Search backends | 1 (Lunr) | 1 | 3 (Lunr, Pagefind, Algolia) |
| Themes | 1 | 2 | 2+ |
| Community plugins | 0 | 0 | framework ready |
| Legacy detector classes | 13 | 13 | 0 |
| Version status | Alpha | Alpha | Beta |

---

## Changelog

- **2026-04-12**: Initial roadmap drafted from maturity assessment + production maturity plan + codebase investigation.
