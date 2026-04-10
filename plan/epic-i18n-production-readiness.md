# Epic: i18n Production Readiness — Close the 2.2-Point Gap

**Status**: Draft
**Created**: 2026-04-09
**Target**: v0.4.x
**Estimated Effort**: 40-55 hours
**Dependencies**: None (independent of all other Phase 1-5 work per production maturity plan)
**Source**: Codebase exploration (2026-04-09), plan-production-maturity.md Phase 1, bengal/i18n/ module analysis

---

## Why This Matters

Bengal's i18n system is **60% built but 0% production-ready**. The infrastructure exists — Catalog, POLoader, MOLoader, 5 CLI commands, 6 template functions — but critical gaps block any non-English-primary site from shipping.

1. **No plural forms in templates** — `Catalog.ngettext()` exists (catalog.py:46) but zero template functions expose it. Any language with non-trivial plurals (Polish has 3 forms, Arabic has 6) cannot translate quantity strings.
2. **No RTL layout support** — `direction()` returns `'rtl'` for 9 locales but nothing consumes it. No `dir="rtl"` on `<html>`, no CSS logical properties, no bidirectional text handling. Arabic/Hebrew sites are unusable.
3. **Incomplete config schema** — `I18nConfig` TypedDict has 3 fields (config/types.py:221-226); actual config supports `languages` array, `fallback_to_default`, `share_taxonomies` — none in the schema.
4. **Locale absent from immutable pipeline** — `ParsedPage` has 0 i18n fields (records.py:27-47). `RenderedPage` has 0 i18n fields (records.py:91-107). Locale flows only through mutable context, not the frozen records that define the pipeline.
5. **No RTL test infrastructure** — 3 test roots for i18n exist but none for RTL layout validation. No visual regression baseline.

### Evidence Table

| Source | Key Finding | Proposal Impact |
|--------|-------------|-----------------|
| catalog.py:46 | `ngettext()` implemented but not wired to templates | **FIXES** — Sprint 1 wires `nt()` template function |
| records.py:27-107 | ParsedPage, RenderedPage carry 0 i18n fields | **FIXES** — Sprint 0 designs locale threading through pipeline |
| config/types.py:221-226 | I18nConfig TypedDict missing languages, fallback, share_taxonomies | **FIXES** — Sprint 1 completes schema |
| template_functions/i18n.py | `direction()` returns 'rtl' but nothing in theme consumes it | **FIXES** — Sprint 2 wires RTL through theme layer |
| tests/roots/ | No test-i18n-rtl fixture | **FIXES** — Sprint 2 adds RTL test root + visual baselines |
| plan-production-maturity.md:86-136 | Phase 1A-1B "partially done", 1C-1D "not started" | **FIXES** — This epic completes all four sub-phases |

### Three Invariants

These must remain true throughout or we stop and reassess:

1. **Existing i18n tests stay green.** The 279 existing i18n test cases must pass at every sprint boundary. No regressions in dict-based translation, PO/MO loading, or per-locale outputs.
2. **LTR sites are unaffected.** Zero behavioral change for sites that don't set `i18n.strategy`. RTL is additive, not a mode switch.
3. **Pipeline records stay frozen.** Any i18n fields added to `ParsedPage` or `RenderedPage` must be immutable. No locks, no mutable containers.

---

## Target Architecture

### Locale in the Immutable Pipeline

```
SourcePage        → lang, translation_key             (EXISTS today)
ParsedPage        → lang                              (NEW — carried forward)
RenderedPage      → lang, output_locale_path           (NEW — locale-aware output)
```

### Template Functions (Complete Set)

```
t(key, **params)          — Singular translation       (EXISTS)
nt(singular, plural, n)   — Plural-aware translation   (NEW)
current_lang()            — Current locale code        (EXISTS)
direction()               — 'rtl' or 'ltr'            (EXISTS)
languages()               — Configured language list   (EXISTS)
alternate_links(page)     — hreflang alternates        (EXISTS)
locale_date(date, fmt)    — Localized date             (EXISTS)
```

### RTL Theme Integration

```html
<html lang="{{ current_lang() }}" dir="{{ direction() }}">
  <!-- CSS uses logical properties: margin-inline-start, padding-block-end -->
  <!-- <bdi> wraps user-generated content in mixed-direction contexts -->
</html>
```

### Config Schema (Complete)

```python
class I18nConfig(TypedDict, total=False):
    strategy: str | None          # "subdir" | "domain" | None
    default_language: str         # "en"
    default_in_subdir: bool       # False
    languages: list[LanguageConfig]  # NEW
    fallback_to_default: bool     # NEW — True
    share_taxonomies: bool        # NEW — True
```

---

## Sprint Structure

| Sprint | Focus | Effort | Risk | Ships Independently? |
|--------|-------|--------|------|---------------------|
| **0** | Design: locale threading, RTL strategy, config schema | 4-6h | Low | Yes (RFC only) |
| **1** | Plural forms + config schema completion | 8-10h | Low | Yes |
| **2** | RTL layout: dir attribute, CSS logical properties, theme | 12-16h | Medium | Yes |
| **3** | RTL navigation + bidirectional text | 8-10h | Medium | Yes |
| **4** | Test hardening + visual regression baselines | 4-6h | Low | Yes |
| **5** | Documentation: quickstart, RTL guide, translator guide | 4-6h | Low | Yes |

---

## Sprint 0: Design & Validate ✅ COMPLETE

**Goal**: Solve three design questions on paper before writing code.

### Task 0.1 — Design locale threading through ParsedPage/RenderedPage ✅

**Decision: Option B — keep lang only on SourcePage; rendering context carries it.**

Rationale: Page object always carries lang during rendering. Kida adapter explicitly injects
page context for i18n template functions. No concrete case today where standalone ParsedPage
needs lang — ParsedPage from cache is only ever used when the Page object is also present.
RenderedPage is purely output-focused and never needs lang.

Revisit if: cache server, standalone record use cases, or generic template engine support emerges.

### Task 0.2 — RTL CSS migration strategy ✅

**Audit results: 497 physical directional properties across 65+ CSS files; 109 logical properties already in use (~22% migrated).**

| Category | Physical Count | Logical Already | Remaining |
|----------|:-----------:|:----------:|:--------:|
| margin-left/right | 95 | 11 | 84 |
| padding-left/right | 75 | 29 | 46 |
| text-align left/right | 25 | 0 | 25 |
| float left/right | 2 | 0 | 2 |
| border-left/right | 141 | 62 | 79 |
| left:/right: positioning | ~369 | 7 | ~362 |

**Critical hotspots**: cards.css (55 border-left), utilities.css (14 directional classes), toc.css (10), code.css (15+).
**Already partially migrated**: admonitions.css (28 logical), resume.css (11), changelog.css (11).

**Decision: Blanket migration to logical properties, split Sprint 2 into sub-sprints by component** (>100 properties confirmed, per risk register trigger). Positioning properties (left:/right:) require careful filtering — many are layout-structural, not directional.

### Task 0.3 — Config schema completion ✅

**12 config keys used in code; 3 in TypedDict. Full mapping:**

| Key | In TypedDict? | Default | Type |
|-----|:---:|---------|------|
| i18n.strategy | Yes | None | str \| None |
| i18n.default_language | Yes | "en" | str |
| i18n.default_in_subdir | Yes | False | bool |
| i18n.languages | **No** | [] | list[str \| LanguageConfig] |
| i18n.share_taxonomies | **No** | False | bool |
| i18n.fallback_to_default | **No** | True | bool |
| i18n.content_structure | **No** | "dir" | str |
| languages[].code | **No** | — | str |
| languages[].name | **No** | (code) | str |
| languages[].hreflang | **No** | (code) | str |
| languages[].weight | **No** | 0 | int |
| languages[].baseurl | **No** | None | str \| None |
| languages[].rtl | **No** | (auto) | bool \| None |

**Target TypedDict** requires both `I18nConfig` (7 fields) and `LanguageConfig` (6 fields).

---

## Sprint 1: Plural Forms + Config Schema ✅ COMPLETE

**Goal**: Wire `ngettext()` to templates so quantity strings work in all languages. Complete the config schema so type checkers cover all i18n options.

### Task 1.1 — Add `nt()` template function

Wire `Catalog.ngettext()` through the template adapter layer, mirroring how `t()` works.

**Files**: `bengal/rendering/template_functions/i18n.py`, adapter files
**Acceptance**:
- `nt("1 item", "{n} items", n)` returns correct plural form for English, Spanish, Arabic
- Tests in `tests/unit/rendering/test_i18n_template_functions.py` cover 2-form (en), 3-form (pl), and 6-form (ar) languages
- `rg 'def nt\b\|def _nt\b' bengal/rendering/` returns at least 1 hit

### Task 1.2 — Complete I18nConfig TypedDict

Add missing fields: `languages`, `fallback_to_default`, `share_taxonomies`.

**Files**: `bengal/config/types.py`, `bengal/orchestration/utils/i18n.py`
**Acceptance**:
- `ty` type checking passes with no new errors on i18n config usage
- Every key accessed via `config["i18n"][X]` has a corresponding TypedDict field

### Task 1.3 — ~~Add `lang` field to ParsedPage~~ SKIPPED (Sprint 0 chose Option B)

Sprint 0 analysis confirmed Page object always carries lang during rendering. No standalone
ParsedPage use case exists. Deferring to avoid unnecessary record churn.

---

## Sprint 2: RTL Layout Foundation ✅ COMPLETE

**Goal**: Arabic/Hebrew sites render with correct reading direction, spacing, and navigation.

### Task 2.1 — Wire `dir` attribute to `<html>` tag

Modify base template to set `dir="{{ direction() }}"` on the `<html>` element.

**Files**: Default theme base template(s)
**Acceptance**:
- Building with `lang: ar` produces `<html lang="ar" dir="rtl">`
- Building with `lang: en` produces `<html lang="en" dir="ltr">`
- `rg 'dir=' bengal/themes/` returns at least 1 hit in base template

### Task 2.2 — Migrate CSS to logical properties

Replace physical directional properties with logical equivalents in the default theme.

**Files**: Default theme CSS files
**Acceptance**:
- `rg 'margin-left|margin-right|padding-left|padding-right' bengal/themes/` returns 0 hits (excluding comments/docs)
- LTR sites render identically before and after (visual diff)
- RTL sites show correct mirrored layout

### Task 2.3 — Create `test-i18n-rtl` test root

Minimal fixture with Arabic content for RTL testing.

**Files**: `tests/roots/test-i18n-rtl/`
**Acceptance**:
- `pytest tests/integration/test_i18n_rtl.py` passes
- Tests verify: `dir="rtl"`, logical CSS properties applied, navigation order

---

## Sprint 3: RTL Navigation + Bidirectional Text ✅ COMPLETE

**Goal**: Menu, breadcrumbs, sidebar, and mixed-direction content handle RTL correctly.

### Task 3.1 — RTL-aware navigation components

Ensure menu, breadcrumbs, and sidebar render in correct reading order for RTL locales.

**Files**: Theme navigation templates, `bengal/rendering/template_engine/menu.py`
**Acceptance**:
- Menu items in Arabic site read right-to-left
- Breadcrumb separator direction flips in RTL
- Integration tests verify navigation order

### Task 3.2 — Bidirectional text isolation

Add `<bdi>` tags around user-generated content in mixed-direction contexts (e.g., English titles embedded in Arabic navigation).

**Files**: Theme templates where page titles/names appear
**Acceptance**:
- Mixed-direction navigation doesn't corrupt visual order
- `rg '<bdi>' bengal/themes/` returns hits in navigation templates

---

## Sprint 4: Test Hardening ✅ COMPLETE

**Goal**: Close coverage gaps and establish regression baselines.

### Task 4.1 — Plural form edge case tests

**Files**: `tests/unit/rendering/test_i18n_template_functions.py`
**Acceptance**:
- Tests cover: n=0, n=1, n=2, n=5, n=21 for languages with complex plural rules
- Tests cover: missing plural translation (fallback behavior)
- Tests cover: ngettext with PO file and with dict fallback

### Task 4.2 — RTL integration test suite

**Files**: `tests/integration/test_i18n_rtl.py`
**Acceptance**:
- E2E build of Arabic site produces correct HTML structure
- Navigation order verified programmatically
- CSS logical properties verified in output

### Task 4.3 — Config validation tests

**Files**: `tests/unit/config/`
**Acceptance**:
- Invalid `i18n.strategy` value produces clear error
- Missing `languages` with `strategy: subdir` warns
- `fallback_to_default: false` with missing translations warns at build time

---

## Sprint 5: Documentation

**Goal**: A new user can set up a bilingual site (including RTL) following only the docs.

### Task 5.1 — i18n quickstart guide

PO file setup, locale config, translation workflow, deployment.

**Files**: `site/content/guides/i18n-quickstart.md` (or equivalent docs location)
**Acceptance**: Guide covers: config setup → init → extract → translate → compile → build → verify

### Task 5.2 — RTL authoring guide

CSS patterns for bidirectional sites: logical properties, `<bdi>`, testing.

**Files**: `site/content/guides/rtl-authoring.md`
**Acceptance**: Guide covers: theme CSS conventions, testing RTL, mixed-direction content

### Task 5.3 — Translator contributor guide

How to contribute translations: PO file conventions, testing translations locally, CI gate.

**Files**: `site/content/guides/translator-guide.md`
**Acceptance**: A non-developer can follow the guide to translate strings and verify locally

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CSS logical properties break LTR layout | Medium | High | Sprint 2 runs full visual comparison before/after for LTR. Sprint 0 audits property count first. |
| Plural forms differ across gettext implementations | Low | Medium | Sprint 1 tests against 3 plural-rule families (2-form, 3-form, 6-form). Uses Python stdlib `gettext`. |
| ~~`ParsedPage.lang` breaks cache compatibility~~ | — | — | ELIMINATED: Sprint 0 chose Option B; no record changes needed. |
| RTL navigation order is template-dependent | Medium | Medium | Sprint 3 tests against default theme specifically. Custom themes documented as "must handle dir attribute". |
| Theme CSS churn too large for one PR | Medium | Low | Sprint 0 audits property count; if >100 properties, split Sprint 2 into sub-sprints by component. |

---

## Success Metrics

| Metric | Current | After Sprint 2 | After Sprint 5 |
|--------|---------|----------------|----------------|
| Maturity score (J12) | 2.8 | 4.0 | 5.0 |
| I18nConfig TypedDict fields | 3 | 6 | 6 |
| Template i18n functions | 6 | 7 (+ nt) | 7 |
| RTL test cases | 0 | 15+ | 25+ |
| i18n documentation pages | 0 | 0 | 3 |
| CSS physical properties in theme | 497 (Sprint 0 audit) | 0 | 0 |
| Plural form test languages | 0 | 3+ | 3+ |

---

## Relationship to Existing Work

- **plan-production-maturity.md Phase 1** — This epic *implements* Phase 1A-1D. The maturity plan scopes the work; this epic sequences it.
- **epic-immutable-page-pipeline** — Sprint 0-1 may add `lang` to `ParsedPage`, extending the immutable record pattern. Must follow the same frozen+slots convention.
- **Phase 0A E2E tests** — i18n E2E already passes. Sprint 4 extends it with RTL scenarios.
- **No blocking dependencies** — i18n runs in parallel with all other phases per the maturity plan.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-09 | Initial draft from codebase exploration |
| 2026-04-09 | Sprint 0 complete: Option B for locale threading (no record changes), 497 CSS physical properties audited, 12 config keys mapped. Sprint 1 Task 1.3 skipped. |
| 2026-04-09 | Sprint 1 complete: `nt()` wired through Kida + generic adapters (5 tests). I18nConfig expanded 3→7 fields + LanguageConfig TypedDict (6 fields). All 38 i18n tests + 358 config tests pass. |
| 2026-04-09 | Sprint 2 complete: 39 CSS files migrated to logical properties (497→0 physical directional props in theme). `dir` attribute already wired in base.html. `test-i18n-rtl` test root + 10 integration tests created. |
| 2026-04-09 | Sprint 3 complete: `<bdi>` tags added to docs-nav, action-bar, base.html, navigation-components. RTL breadcrumb separator (‹) and nav arrow flip (scaleX(-1)) CSS added. 5 bidi isolation tests pass. Total: 15 RTL integration tests. |
| 2026-04-09 | Sprint 4 complete: 13 plural edge case tests (TestNtEdgeCases + TestCatalogNgettext), 5 RTL integration expansion tests (TestRTLTemplateIntegration), 16 config validation tests (test_i18n_config.py). Total: 59 tests across 3 files, all passing. |
