# Plan: Production Maturity Across All Journeys

> **Date:** 2026-03-13
> **Goal:** Bring every user journey to a solid **5 (Production)** — resilient, well-documented, CI-validated, polished UX
> **Baseline:** [maturity-assessment.md](maturity-assessment.md)
> **Existing RFCs referenced inline** where prior design work applies

---

## Scoring Context

| Journey | Current | Gap | Phase |
|---------|:-------:|:---:|:-----:|
| 12. Internationalization | 2.8 | 2.2 | 1 |
| 7. API Documentation (Autodoc) | 3.9 | 1.1 | 2 |
| 8. Multi-Version Docs | 3.9 | 1.1 | 2 |
| 11. Search/Content Discovery | 4.0 | 1.0 | 3 |
| 4. Custom Directives/Filters | 4.2 | 0.8 | 3 |
| 10. Developer Experience/CLI | 4.3 | 0.7 | 4 |
| 2. Customize Theme/Templates | 4.4 | 0.6 | 4 |
| 3. Incremental Rebuilds | 4.4 | 0.6 | 4 |
| 9. Health Checking/Validation | 4.4 | 0.6 | 4 |
| 13. Output Formats/Deployment | 4.5 | 0.5 | 5 |
| 5. Taxonomy/Tagging | 4.6 | 0.4 | 5 |
| 6. Correct Links/Assets/Nav | 4.6 | 0.4 | 5 |
| 1. Build from Markdown | 4.8 | 0.2 | 5 |

---

## Phase 0: Cross-Cutting Foundation

*Work that lifts multiple journeys simultaneously. Do first because everything else benefits.*

### 0A. E2E Test Framework

**Lifts:** J1, J3, J6, J9, J10, J12, J13
**Gap:** `tests/e2e` referenced in pytest config but doesn't exist

| Work Item | Detail |
|-----------|--------|
| Create `tests/e2e/` directory and conftest | Fixture that runs `bengal build` on a root, then inspects output HTML/assets as a real user would |
| Smoke E2E: build + validate + check links | Covers the golden path across build, health, and output |
| Dev server E2E: serve → modify → verify reload | Starts dev server, writes a file, confirms SSE reload fires and output updates |
| Versioned build E2E | Builds multi-version site, verifies all version paths resolve |
| i18n E2E | Builds multi-language site, verifies per-locale outputs and hreflang |
| CI integration | Add `e2e` job to `tests.yml`, run on every PR |

**Exit criteria:** `pytest tests/e2e/ -m e2e` passes with 10+ scenarios covering all 13 journeys.

### 0B. Documentation-Code Alignment

**Lifts:** J4, J7, J10
**Prior art:** `rfc-documentation-completeness.md` (Draft)

| Work Item | Detail |
|-----------|--------|
| Fix directive naming mismatch | Docs say `BengalDirective`, code says `DirectiveHandler` — unify to one name |
| Auto-generate config reference | Script that reads `DEFAULTS` dict and writes config docs |
| Auto-generate template function reference | Script that reads `register_all()` registrations and writes filter/function docs |
| Extension guide rewrite | Accurate walkthrough for custom directives, filters, and shortcodes with working examples |

**Exit criteria:** Zero naming mismatches between docs and code. Config reference and template function reference auto-generated on each build.

### 0C. CommonMark Compliance ✅ COMPLETE

**Lifts:** J1
**Prior art:** `rfc-patitas-commonmark-compliance.md` (Active)

| Work Item | Detail | Status |
|-----------|--------|--------|
| Run CommonMark 0.31 spec suite against Patitas | Identify every failing example | ✅ 652/652 passing (100%) |
| Fix high-impact failures | Prioritize by real-world frequency | ✅ N/A (no failures) |
| Add spec examples as regression tests | Each fix paired with a test from the spec | ✅ `patitas/tests/test_commonmark_spec.py` |
| Document known intentional deviations | If any CommonMark behaviors are deliberately different, document why | ✅ See `plan/commonmark-deviations.md` |

**Exit criteria:** 95%+ CommonMark 0.31 spec pass rate. Remaining failures documented as intentional deviations. **Achieved:** 100% pass rate.

**Run:** `poe test-commonmark` (from Bengal workspace) or `cd patitas && pytest tests/test_commonmark_spec.py -m commonmark`

---

## Phase 1: Internationalization (J12: 2.8 → 5.0)

*Biggest single gap. Blocks international adoption entirely. No other journey depends on this, so it can run in parallel with Phase 0.*

### 1A. Translation File Format

**Current:** `t` filter in templates with unclear translation loading
**Target:** Standard gettext/PO workflow

| Work Item | Detail |
|-----------|--------|
| `bengal/i18n/` package | `Catalog`, `POLoader`, `MOLoader` classes |
| PO file discovery | `i18n/{locale}/LC_MESSAGES/{domain}.po` convention |
| Catalog compilation | `bengal i18n compile` to generate `.mo` files |
| Kida integration | Wire `t` filter to loaded catalog with fallback to key |
| Plural forms | `ngettext` support via PO plural rules |
| Extraction command | `bengal i18n extract` to scan templates for `t()` calls and generate `.pot` |
| Test root | `test-i18n-gettext` root with English/Spanish/Arabic content |

**Exit criteria:** Full PO→MO→template roundtrip with plural support and extraction CLI.

### 1B. Translation Status Tracking

| Work Item | Detail |
|-----------|--------|
| Translation coverage report | Per-locale percentage of translated strings |
| Missing translation warnings | Build-time warnings for untranslated keys (non-strict) |
| `bengal i18n status` CLI | Shows coverage per locale with color coding |
| CI gate | Optional `--fail-on-missing-translations` flag for strict builds |

**Exit criteria:** `bengal i18n status` shows per-locale coverage. CI can gate on translation completeness.

### 1C. RTL Layout Support

| Work Item | Detail |
|-----------|--------|
| `dir="rtl"` on `<html>` | Set from locale metadata |
| CSS logical properties | Audit theme CSS: replace `margin-left` → `margin-inline-start`, etc. |
| RTL-aware navigation | Menu, breadcrumbs, sidebar render correctly in RTL |
| Bidirectional text | `<bdi>` tags for mixed-direction content |
| Test root | `test-i18n-rtl` root with Arabic or Hebrew content |
| Visual regression | Screenshot comparison for RTL vs LTR layouts |

**Exit criteria:** Arabic/Hebrew site renders correctly with proper reading direction, navigation, and spacing.

### 1D. i18n Documentation

| Work Item | Detail |
|-----------|--------|
| i18n quickstart guide | PO file setup, locale config, translation workflow |
| RTL guide | CSS authoring guidelines for bidirectional sites |
| Translator contributor guide | How to contribute translations, PO file conventions |

**Exit criteria:** A new user can set up a bilingual site following only the docs.

---

## Phase 2: Autodoc and Versioning (J7: 3.9 → 5.0, J8: 3.9 → 5.0)

*Both at 3.9, both critical for the technical documentation use case. Natural to tackle together since versioned autodoc is a common need.*

### 2A. Autodoc Test Coverage

**Current:** ~7% coverage on extractors
**Prior art:** `rfc-autodoc-incremental-caching.md` (Draft), `rfc-autodoc-unified-endpoint-api.md` (Implemented)

| Work Item | Detail |
|-----------|--------|
| Python extractor test suite | 50+ test cases: classes, functions, methods, properties, decorators, dataclasses, protocols, overloads, `__all__`, re-exports |
| OpenAPI extractor test suite | Fixtures for 3.0 and 3.1 specs: nested `$ref`, `allOf`/`anyOf`/`oneOf`, circular refs, discriminators |
| CLI extractor test suite | Click, argparse, typer: nested groups, options, arguments, help text |
| Docstring parser tests | Google, NumPy, Sphinx styles: edge cases in param parsing, return types, cross-refs |
| Error path tests | Malformed specs, missing files, invalid Python, syntax errors — verify graceful fallback |

**Exit criteria:** Autodoc extractor coverage ≥ 80%. All three formats (Python, OpenAPI, CLI) have dedicated test suites.

### 2B. External $ref Resolution

| Work Item | Detail |
|-----------|--------|
| File-relative `$ref` | `$ref: ./schemas/User.yaml` resolves relative to spec file |
| URL `$ref` | `$ref: https://example.com/schemas/Pet.yaml` with caching |
| Circular `$ref` detection | Detect and break cycles with clear error message |
| `$ref` resolution tests | 20+ cases covering relative, absolute, URL, and circular patterns |

**Exit criteria:** External `$ref` resolves correctly for file-relative and URL references. Circular refs emit a diagnostic instead of crashing.

### 2C. Interactive API Explorer

| Work Item | Detail |
|-----------|--------|
| "Try it" panel in explorer layout | Request builder with method, URL, headers, body |
| Response viewer | Syntax-highlighted JSON/XML response with status code |
| Authentication config | API key, Bearer, OAuth2 configuration in `bengal.toml` |
| Client-side only | No server required — uses `fetch()` directly |
| Opt-in via config | `autodoc.openapi.interactive: true` |

**Exit criteria:** Users can send real API requests from the docs page. Works without a backend proxy.

### 2D. Version Deprecation Workflow

**Current:** No deprecation banners or automatic redirects

| Work Item | Detail |
|-----------|--------|
| `VersionBanner` deprecation state | Add `deprecated`, `eol` states to existing `VersionBanner` enum |
| Deprecation banner template | Dismissible banner: "This version is deprecated. View the latest version." |
| Automatic redirects | Generate `<meta http-equiv="refresh">` pages for deprecated version URLs pointing to latest |
| `version_config.deprecation_policy` | Config: `redirect_after: 90d`, `show_banner: true`, `banner_message: "..."` |
| Version lifecycle docs | Guide for managing version deprecation and retirement |

**Exit criteria:** Deprecated versions show banners and optionally redirect. Lifecycle is configurable.

### 2E. Version Polish

| Work Item | Detail |
|-----------|--------|
| Cross-version search | Search index includes version metadata; results show version badge |
| Git-based version hardening | Error handling for missing branches, detached HEAD, shallow clones |
| Version comparison page | Template showing what changed between versions |
| Warm-build tests for versioned sites | Extend `rfc-warm-build-test-expansion.md` to cover version-specific incremental scenarios |

**Exit criteria:** Versioned sites have cross-version search, robust git integration, and warm-build test coverage.

---

## Phase 3: Extensions and Search (J4: 4.2 → 5.0, J11: 4.0 → 5.0)

*Plugin ecosystem enables community growth. Search is a key differentiator for large sites.*

### 3A. Plugin Discovery System

**Current:** Custom directives/filters require code modification
**Prior art:** `rfc-theme-ecosystem.md` (Draft)

| Work Item | Detail |
|-----------|--------|
| Entry-point-based plugin discovery | `[project.entry-points."bengal.plugins"]` in `pyproject.toml` |
| Plugin protocol | `BengalPlugin` with `register_directives(registry_builder)`, `register_filters(env, site)`, `register_shortcodes(registry)` |
| Config-based plugin activation | `plugins: [bengal-mermaid, bengal-math]` in `bengal.toml` |
| Plugin validation | Version compatibility check, conflict detection, load-order resolution |
| Plugin scaffolding | `bengal new plugin` generates project skeleton with tests |

**Exit criteria:** Third-party plugins installable via pip and activated via config. No core code changes needed.

### 3B. Plugin and Extension Documentation

| Work Item | Detail |
|-----------|--------|
| Plugin author guide | Full walkthrough from `bengal new plugin` to PyPI publish |
| Directive authoring guide | Accurate guide using `DirectiveHandler`, contracts, typed options |
| Filter authoring guide | `register()` pattern, `@template_safe`, `coerce_int` |
| Shortcode guide | Template conventions, context variables, Markdown parsing |
| API reference for extension points | Auto-generated from protocols and contracts |

**Exit criteria:** A developer can create, test, and publish a Bengal plugin following only the docs.

### 3C. Community Theme Support

**Prior art:** `rfc-theme-ecosystem.md` (Draft)

| Work Item | Detail |
|-----------|--------|
| Theme package spec | `pyproject.toml` `[project.entry-points."bengal.themes"]` |
| Theme validation CLI | `bengal theme validate` checks required templates, assets, config |
| Theme install from pip | `pip install bengal-theme-minimal` + `theme.name: minimal` in config |
| Starter theme scaffold | `bengal new theme` generates minimal theme skeleton |
| Theme developer contract | Document required templates, optional templates, expected variables |

**Exit criteria:** Community themes installable via pip. `bengal new theme` produces a valid starting point.

### 3D. Search Backend Adapters

**Current:** Client-side Lunr only. No server-side search.

| Work Item | Detail |
|-----------|--------|
| Search adapter protocol | `SearchAdapter` with `build_index(pages)`, `get_client_config()` |
| Algolia adapter | Pushes index on build, injects Algolia client config |
| Meilisearch adapter | Local/self-hosted option, pushes index on build |
| Pagefind adapter | Static search (zero-JS alternative to Lunr) |
| Config | `search.backend: lunr | algolia | meilisearch | pagefind` |
| Adapter package convention | `bengal-search-algolia` as separate pip package |

**Exit criteria:** At least two search backends beyond Lunr available as adapters. Config-switchable.

### 3E. Search UI Polish

| Work Item | Detail |
|-----------|--------|
| Keyboard navigation | Arrow keys, Enter to select, Escape to close |
| Search result snippets | Highlighted matching text with context |
| Faceted results | Filter by section, version, content type |
| Recent searches | LocalStorage-based search history |
| Search analytics hook | Optional callback for tracking search queries |

**Exit criteria:** Search UI supports keyboard navigation, highlighted snippets, and faceted filtering.

---

## Phase 4: Near-Production Polish (J2, J3, J9, J10: 4.3–4.4 → 5.0)

*These journeys are already strong. Targeted improvements to close the last 0.6–0.7 gap.*

### 4A. Theme and Templates (J2: 4.4 → 5.0)

| Work Item | Lifts | Detail |
|-----------|-------|--------|
| Second built-in theme | Theme resolution | "Minimal" theme — clean, fast, no-JS baseline for API docs and READMEs |
| Theme preview command | Appearance config | `bengal theme preview` opens browser with theme switcher |
| Shortcode validation | Shortcodes | Build-time warnings for unknown shortcodes in non-strict mode |
| Icon library expansion | Icon system | Verify all Material Design Icons render. Add Lucide as alternative |
| Design token documentation | Design tokens | Document all CSS custom properties and their purpose |

**Exit criteria:** Two built-in themes. Shortcode validation. Full icon and token documentation.

### 4B. Incremental Rebuilds (J3: 4.4 → 5.0)

**Prior art:** `rfc-effect-traced-incremental-builds.md` (Draft), `rfc-incremental-build-contracts.md` (Evaluated), `rfc-reactive-dev-sequel.md` (Implemented), `rfc-dev-server-buffer-hardening.md` (Draft)

| Work Item | Lifts | Detail |
|-----------|-------|--------|
| Template-granular HMR | Live reload | When only a partial/block changes, push targeted update via SSE instead of full reload |
| Effect-traced dependency graph | Effect detection | Implement `rfc-effect-traced-incremental-builds.md` — Merkle DAG for precise invalidation |
| Incremental contract tests | Selective re-rendering | Implement `rfc-incremental-build-contracts.md` — canonical path keys, immutable results, phase state machine |
| Dev server buffer hardening | Serve-first | Implement `rfc-dev-server-buffer-hardening.md` — eliminate asset 404s and torn content |
| Warm-build test expansion | Build cache | Implement `rfc-warm-build-test-expansion.md` — 30+ warm-build scenarios in CI |

**Exit criteria:** Template-level HMR. Effect-traced invalidation. Zero asset 404s during dev. Warm-build CI suite.

### 4C. Health Checking and Validation (J9: 4.4 → 5.0)

| Work Item | Lifts | Detail |
|-----------|-------|--------|
| Deep accessibility validation | Accessibility | Heading hierarchy, alt text, color contrast (WCAG AA), ARIA landmarks, form labels |
| Output format validation | Output validation | Validate JSON-LD, RSS schema, sitemap XSD, `llms.txt` format |
| Autofix expansion | Autofix | Autofix for heading hierarchy, missing alt text, broken image paths |
| Validation result caching | Tiered execution | Cache validator results per-file for instant re-validation of unchanged files |
| Health check documentation | CI integration | Document every validator: what it checks, how to fix, how to suppress |

**Exit criteria:** WCAG AA level accessibility checks. Output format schema validation. Every validator documented.

### 4D. Developer Experience and CLI (J10: 4.3 → 5.0)

**Prior art:** `rfc-dx-graceful-error-communication.md` (Draft), `rfc-behavioral-test-hardening.md` (Implementing)

| Work Item | Lifts | Detail |
|-----------|-------|--------|
| Interactive CLI test coverage | CLI framework | Increase from ~10% to 60%+ using Click's `CliRunner` |
| Graceful error communication | Error messages | Implement `rfc-dx-graceful-error-communication.md` — route background thread/ResourceManager errors through unified display |
| Scaffolding validation | Scaffolding | Validate generated scaffolds compile and build successfully |
| Dashboard polish | Dashboard | Error overlay, build progress bar, search within dashboard |
| Provenance stabilization | Debug tools | Move provenance from experimental to stable; add `bengal provenance show` |
| `bengal doctor` command | Diagnostics | One-command diagnostic that checks Python version, dependencies, config, theme, and cache health |

**Exit criteria:** CLI test coverage ≥ 60%. `bengal doctor` exists. All scaffold outputs validated.

---

## Phase 5: Final Mile (J1, J5, J6, J13: 4.5–4.8 → 5.0)

*Already near-production. Small, surgical improvements.*

### 5A. Build from Markdown (J1: 4.8 → 5.0)

| Work Item | Detail |
|-----------|--------|
| CommonMark compliance (from Phase 0C) | Must reach 95%+ spec pass rate |
| Theme resilience | Default theme degrades gracefully with missing optional config |
| Zero-config quickstart | `bengal init && bengal serve` works with a single `index.md` and no config file at all |

**Exit criteria:** CommonMark spec pass. Zero-config builds work. Default theme handles all edge cases.

### 5B. Taxonomy and Tagging (J5: 4.6 → 5.0)

| Work Item | Detail |
|-----------|--------|
| Hierarchical taxonomy | Support `categories: [Languages/Python, Languages/Rust]` with parent/child relationships |
| Taxonomy template functions | `taxonomy_tree`, `taxonomy_children`, `taxonomy_breadcrumb` filters |
| Taxonomy archive layouts | Year/month archive pages for date-based taxonomies |
| Taxonomy documentation | Guide for configuring custom taxonomies beyond tags |

**Exit criteria:** Hierarchical taxonomies render as trees. Archive layouts exist. Custom taxonomy guide published.

### 5C. Links, Assets, and Navigation (J6: 4.6 → 5.0)

**Prior art:** `rfc-cross-site-xref-link-previews.md` (Implemented)

| Work Item | Detail |
|-----------|--------|
| Baseurl footgun elimination | Template helper that always produces correct URLs regardless of baseurl config; deprecate raw `href` construction |
| Pretty URL edge cases | Handle `index.html` collisions, trailing slash normalization, query string passthrough |
| Relative link resolution in link checker | Fully resolve relative links (currently passed as OK with metadata) |
| Navigation label overrides | Implement `rfc-nav-labels.md` — custom labels in nav tree without changing page title |

**Exit criteria:** Zero baseurl-related bugs possible. Link checker resolves all relative links. Nav labels configurable.

### 5D. Output Formats and Deployment (J13: 4.5 → 5.0)

**Prior art:** `rfc-deployment-edge-cases.md` (Draft)

| Work Item | Detail |
|-----------|--------|
| Atom feed | Atom 1.0 alongside RSS 2.0; config to choose or generate both |
| JSON-LD structured data | `WebSite`, `Article`, `BreadcrumbList`, `FAQPage` schema.org types embedded in HTML |
| Social card incremental builds | Generate social cards incrementally (currently skipped on incremental) |
| Deployment edge cases | Implement `rfc-deployment-edge-cases.md` — disk exhaustion, concurrent builds, symlinks, permissions |
| HTML minification validation | Verify minified output preserves `<pre>`, `<code>`, `<script>` content |

**Exit criteria:** Atom feed generated. JSON-LD embedded. Social cards incremental. Deployment edge cases handled.

---

## Cross-Cutting: Runs Alongside All Phases

These are not phase-gated — they should be ongoing throughout.

### Module Health

**Prior art:** `rfc-module-coupling-reduction.md` (Draft), `rfc-remaining-coupling-fixes.md` (Draft)

| Work Item | Detail |
|-----------|--------|
| Coupling reduction | Fix 8 circular imports and 83 layer violations |
| File size reduction | Break files > 800 lines into focused modules (Page, ContentOrchestrator, BuildOrchestrator, MenuOrchestrator) |
| Protocol consolidation | Implement `rfc-protocol-consolidation.md` — fewer, clearer protocols |

### Test Infrastructure

**Prior art:** `rfc-behavioral-test-hardening.md` (Implementing)

| Work Item | Detail |
|-----------|--------|
| Behavioral test migration | Replace over-mocked tests with integration-style behavioral checks |
| Mutation testing in CI | Add mutation testing job to catch tests that pass but don't actually verify behavior |
| Coverage floor increase | Raise from 85% to 90% |

### Documentation

| Work Item | Detail |
|-----------|--------|
| User guide completeness | Every config option documented with examples |
| Migration guides | From MkDocs, Sphinx, Pelican, Hugo |
| Troubleshooting guide | Top-20 error messages with causes and fixes |
| Architecture guide | For contributors: subsystem overview, data flow, extension points |

---

## Phase Sequencing and Dependencies

```
Phase 0 ──────────────────────────────────────────────────────────
  0A. E2E Tests          ◆━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶
  0B. Doc-Code Alignment ◆━━━━━━━━━━━━▶
  0C. CommonMark         ◆━━━━━━━━━━━━━━━━━━━━━▶

Phase 1 (parallel with 0) ────────────────────────────────────────
  1A. Translation Format       ◆━━━━━━━━━━━━━━━━━━▶
  1B. Translation Status              ◆━━━━━━━━━━▶
  1C. RTL Layout                            ◆━━━━━━━━━━━━━▶
  1D. i18n Docs                                    ◆━━━━━━▶

Phase 2 (after 0B) ──────────────────────────────────────────────
  2A. Autodoc Tests              ◆━━━━━━━━━━━━━━━━▶
  2B. External $ref                    ◆━━━━━━━━━━▶
  2C. API Explorer                           ◆━━━━━━━━━━━━━▶
  2D. Version Deprecation        ◆━━━━━━━━━━▶
  2E. Version Polish                   ◆━━━━━━━━━━━━━━━▶

Phase 3 (after 0B, parallel with 2) ─────────────────────────────
  3A. Plugin Discovery           ◆━━━━━━━━━━━━━━━━▶
  3B. Plugin Docs                      ◆━━━━━━━━━━▶
  3C. Community Themes                       ◆━━━━━━━━━━━━━▶
  3D. Search Adapters            ◆━━━━━━━━━━━━━━━━▶
  3E. Search UI                        ◆━━━━━━━━━━━━━━━▶

Phase 4 (after 0A) ──────────────────────────────────────────────
  4A. Theme Polish                     ◆━━━━━━━━━━▶
  4B. Incremental Polish               ◆━━━━━━━━━━━━━━━▶
  4C. Health Polish                    ◆━━━━━━━━━━▶
  4D. DX Polish                        ◆━━━━━━━━━━━━━━━▶

Phase 5 (after 0C, 4A–4D) ───────────────────────────────────────
  5A. Build Final Mile                             ◆━━━━━▶
  5B. Taxonomy Final Mile                          ◆━━━━━▶
  5C. Links Final Mile                             ◆━━━━━▶
  5D. Output Final Mile                            ◆━━━━━▶
```

### Key Dependencies

- **0A (E2E) → 4D (DX):** E2E framework needed before CLI test expansion
- **0B (Doc-Code) → 2A (Autodoc Tests), 3B (Plugin Docs):** Alignment needed before writing extension docs
- **0C (CommonMark) → 5A (Build Final Mile):** Spec compliance must precede final-mile claim
- **1A (Translation Format) → 1B (Status Tracking):** Can't track what doesn't exist yet
- **3A (Plugin Discovery) → 3C (Community Themes):** Theme packages use plugin infrastructure

---

## Projected Outcome

| Journey | Current | After Phase | Target |
|---------|:-------:|:-----------:|:------:|
| 12. Internationalization | 2.8 | Phase 1 | **5.0** |
| 7. Autodoc/OpenAPI | 3.9 | Phase 2 | **5.0** |
| 8. Multi-Version Docs | 3.9 | Phase 2 | **5.0** |
| 11. Search/Discovery | 4.0 | Phase 3 | **5.0** |
| 4. Custom Directives | 4.2 | Phase 3 | **5.0** |
| 10. Developer Exp/CLI | 4.3 | Phase 4 | **5.0** |
| 2. Theme/Templates | 4.4 | Phase 4 | **5.0** |
| 3. Incremental Builds | 4.4 | Phase 4 | **5.0** |
| 9. Health/Validation | 4.4 | Phase 4 | **5.0** |
| 13. Output/Deployment | 4.5 | Phase 5 | **5.0** |
| 5. Taxonomy/Tagging | 4.6 | Phase 5 | **5.0** |
| 6. Links/Assets/Nav | 4.6 | Phase 5 | **5.0** |
| 1. Build from Markdown | 4.8 | Phase 5 | **5.0** |

```
                     1    2    3    4    5
                     |    |    |    |    |
Build from MD        ========================[====]▸ 5.0
Taxonomy/Tagging     =======================[===]━▸ 5.0
Links/Assets/Nav     =======================[===]━▸ 5.0
Output/Deployment    ======================[===]━━▸ 5.0
Theme/Templates      =====================[==]━━━▸ 5.0
Incremental Builds   =====================[==]━━━▸ 5.0
Health/Validation    =====================[==]━━━▸ 5.0
Developer Exp/CLI    ====================[==]━━━━▸ 5.0
Custom Directives    ===================[=]━━━━━━▸ 5.0
Search/Discovery     ==================[=]━━━━━━━▸ 5.0
Autodoc/OpenAPI      =================[=]━━━━━━━━▸ 5.0
Multi-Version Docs   =================[=]━━━━━━━━▸ 5.0
i18n                 ============[]━━━━━━━━━━━━━━▸ 5.0
```

---

## Validation Strategy

Each journey's 5.0 claim requires **all four** of these conditions:

1. **Resilient** — Error paths tested. Graceful degradation. No crashes on bad input.
2. **Well-documented** — User-facing guide. Config reference. Troubleshooting section.
3. **CI-validated** — Automated tests covering the journey end-to-end. Regression tests for every fixed bug.
4. **Polished UX** — Clear error messages. Sensible defaults. No footguns.

### Per-Phase Validation Gates

| Phase | Gate |
|-------|------|
| 0 | E2E suite green. Doc-code alignment script passes. CommonMark ≥ 95%. |
| 1 | PO roundtrip E2E. RTL visual regression passes. i18n guide reviewed by non-English speaker. |
| 2 | Autodoc extractor coverage ≥ 80%. External `$ref` test suite passes. Version deprecation E2E. |
| 3 | Plugin installed from pip and activated via config. Two search backends pass integration tests. |
| 4 | Warm-build suite ≥ 30 scenarios. Accessibility checks at WCAG AA. CLI coverage ≥ 60%. |
| 5 | All 13 E2E journey tests green. Coverage ≥ 90%. Zero known footguns. |

---

## Existing RFC Alignment

These RFCs are directly consumed by this plan:

| RFC | Status | Used In |
|-----|--------|---------|
| `rfc-patitas-commonmark-compliance` | Active | Phase 0C |
| `rfc-documentation-completeness` | Draft | Phase 0B |
| `rfc-theme-ecosystem` | Draft | Phase 3A, 3C |
| `rfc-autodoc-incremental-caching` | Draft | Phase 2A |
| `rfc-effect-traced-incremental-builds` | Draft | Phase 4B |
| `rfc-incremental-build-contracts` | Evaluated | Phase 4B |
| `rfc-dev-server-buffer-hardening` | Draft | Phase 4B |
| `rfc-warm-build-test-expansion` | Draft | Phase 4B |
| `rfc-behavioral-test-hardening` | Implementing | Cross-cutting |
| `rfc-module-coupling-reduction` | Draft | Cross-cutting |
| `rfc-remaining-coupling-fixes` | Draft | Cross-cutting |
| `rfc-dx-graceful-error-communication` | Draft | Phase 4D |
| `rfc-deployment-edge-cases` | Draft | Phase 5D |
| `rfc-nav-labels` | Draft | Phase 5C |
| `rfc-search-enabled-by-default` | Implemented | Phase 3 baseline |
| `rfc-cross-site-xref-link-previews` | Implemented | Phase 5C baseline |
| `rfc-directive-base-css` | Implemented | Phase 3 baseline |
| `rfc-error-handling-consolidation` | Implemented | Phase 4D baseline |

RFCs marked **Draft** need promotion to **Active** before their phase begins. RFCs marked **Implemented** provide the foundation that this plan builds on.
