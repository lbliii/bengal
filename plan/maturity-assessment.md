# Bengal Maturity Assessment

> **Date:** 2026-03-13
> **Scope:** Full codebase audit across `bengal/core/`, `bengal/orchestration/`, `bengal/rendering/`, `bengal/cache/`, `bengal/cli/`, `bengal/config/`, `bengal/themes/`, `bengal/health/`, `bengal/directives/`, and `tests/`
> **Method:** Deep code inspection of implementation depth, error handling, test coverage, thread-safety, and documentation

---

## Maturity Scale

| Level | Label | Meaning |
|-------|-------|---------|
| 1 | Nascent | Concept exists, code is stubbed or early prototype |
| 2 | Emerging | Core logic works but gaps in coverage, no polish |
| 3 | Functional | Works end-to-end, some rough edges, limited validation |
| 4 | Mature | Solid implementation, good error handling, tested |
| 5 | Production | Resilient, well-documented, CI-validated, polished UX |

---

## Journey 1: Build a Static Site from Markdown with Minimal Configuration

> *As a user, I want to write markdown files, run one command, and get a complete static site.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **Content discovery** | 5 | `ContentOrchestrator` walks content dirs, discovers pages/sections/assets. 973 lines. Handles nested sections, virtual sections, index pages. Tested across 23 test roots. |
| **Markdown parsing** | 4 | Patitas parser with full CommonMark support plus GFM tables, footnotes, math, task lists. Error fallback renders `<div class="markdown-error">` instead of crashing. Missing: some CommonMark edge cases per `rfc-patitas-commonmark-compliance.md`. |
| **Page model** | 5 | `Page` (921 lines) + `PageCore` (375 lines, frozen) + `PageProxy` (893 lines, lazy). Full type annotations, cache serialization, cascade metadata, diagnostics. Property-based tests. |
| **Build pipeline** | 5 | 21-phase orchestrated build in `BuildOrchestrator`. Phases: fonts → discovery → cache → config → incremental filter → sections → taxonomies → indexes → menus → parsing → snapshot → assets → render → postprocess → health → finalize. |
| **Default theme** | 4 | Full-featured default theme with `theme.yaml`, appearance config (light/dark/system), palette tokens, CSS manifest. Swizzle system for overrides. Missing: theme marketplace/ecosystem. |
| **Configuration defaults** | 5 | `DEFAULTS` dict covers all options. `UnifiedConfigLoader` supports file and directory config. `validate_config()` checks required keys (`site.title`, `build.output_dir`, `build.content_dir`). Deprecation migration. Env overrides for baseurl. |
| **CLI build command** | 5 | `bengal build` with lazy loading, aliases (`b`), themed help, fuzzy command matching, `@handle_cli_errors` decorator. Upgrade notification post-hook. |
| **Output generation** | 5 | `RenderOrchestrator` with parallel rendering, wave scheduling, block caching. `WriteBehindCollector` for async writes. Strict/non-strict modes with fallback HTML. |

**Overall Score: 4.8 — Production**

**Strongest:** Build pipeline orchestration (21 phases, parallel execution, early exit optimization)
**Weakest:** Markdown CommonMark compliance has known edge-case gaps

---

## Journey 2: Customize Theme and Templates

> *As a user, I want to override templates, change appearance, and create custom layouts.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **Theme resolution chain** | 4 | `resolve_theme_chain()` walks site → installed → bundled themes. `theme.toml` supports `extends` for inheritance. |
| **Template override (swizzle)** | 5 | `SwizzleManager` with checksums, atomic writes, provenance tracking in `.bengal/themes/sources.json`. `ModificationStatus` enum (NOT_SWIZZLED, FILE_MISSING, UNCHANGED, MODIFIED). |
| **Appearance config** | 4 | `AppearanceConfig`: mode (light/dark/system), palette, feature flags. `validate_enum_field` for mode/palette. CSS custom properties via `generate_web_css()`. |
| **Template engine** | 5 | Kida engine with bytecode cache, fragment cache, block introspection, pipeline operators, pattern matching. Jinja2 fallback with per-template locks. 80+ template functions across 10 phases. |
| **Shortcodes** | 4 | Hugo-style `{{< name >}}` and `{{% name %}}` with `ShortcodeContext` (Get, GetInt, GetBool, Ref, RelRef, Inner, Params). Recursive expansion (max depth 20). Strict/non-strict error modes. |
| **Template functions/filters** | 5 | 80+ functions: strings, collections, math, dates, URLs, content, data, images, icons, SEO, taxonomies, navigation, autodoc, OpenAPI, blog, changelog, authors. `coerce_int` for YAML type safety. `@template_safe` decorator. |
| **Design tokens** | 4 | `BengalPalette`, `BengalMascots` in `tokens.py`. `generate_web_css()` writes CSS custom properties. TCSS validation. |
| **Icon system** | 4 | `IconConfig` with library and aliases. `render_svg_icon()` integration in admonitions and templates. |

**Overall Score: 4.4 — Mature/Production**

**Strongest:** Template engine (Kida with bytecode cache, 80+ functions, block introspection)
**Weakest:** Theme ecosystem — only one built-in theme; no marketplace or community themes

---

## Journey 3: Fast Incremental Rebuilds During Development

> *As a user, I want sub-second rebuilds when I change a single file during development.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **File watching** | 4 | `WatcherRunner` uses `watchfiles` with async-to-sync bridge, 300ms debounce, event-type tracking. Watches content, assets, templates, data, static, i18n, theme, autodoc, config. |
| **Provenance-based filtering** | 5 | `phase_incremental_filter_provenance()` (924 lines) — content-addressed hashing to skip unchanged files. Parallel provenance checking. |
| **Effect-based detection** | 4 | `EffectBasedDetector` in `incremental/effect_detector.py` — tracks which pages depend on which content. |
| **Build cache** | 5 | `BuildCache` (schema v8): fingerprints, dependencies, taxonomy, autodoc, parsed/rendered output, validation. Atomic writes, file locking, Zstd compression (~93% reduction). Tolerant loading with version migration. |
| **Selective re-rendering** | 4 | `CacheCoordinator` invalidates page-level caches (rendered_output, parsed_content, fingerprints). Wave scheduler for dependency-ordered rendering. |
| **Early exit** | 5 | `filter_result is None` → return stats immediately. No work done when nothing changed. |
| **Live reload** | 4 | SSE-based hot reload. CSS/JS changes without full page refresh. `ReloadHint` enum (NONE, CSS_ONLY, FULL). Script injection into HTML. |
| **Serve-first startup** | 5 | Serves cached content immediately; background validation rebuilds if stale. |
| **Incremental postprocess** | 4 | Skips social cards, RSS, redirects on incremental builds. Always regenerates sitemap. |

**Overall Score: 4.4 — Mature/Production**

**Strongest:** Provenance-based filtering and early exit — zero work when nothing changed
**Weakest:** No true HMR (hot module replacement); live reload is full-page via SSE for non-CSS changes

---

## Journey 4: Extend with Custom Directives and Filters

> *As a user, I want to add domain-specific content blocks and template functions.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **Directive protocol** | 5 | `DirectiveHandler` with `names`, `token_type`, `parse()`, `render()`. `DirectiveParseOnly`, `DirectiveRenderOnly` for partial implementations. Stateless handlers safe for concurrent use. |
| **Directive contracts** | 5 | `DirectiveContract` with `requires_parent`, `allows_children`, `max_children`, `forbids_children`. `validate_parent()`, `validate_children()` → `ContractViolation`. Predefined contracts (STEPS, TAB_ITEM, CARDS). |
| **Typed directive options** | 4 | `DirectiveOptions.from_raw()` with type coercion (str, bool, int, float, `list[str]`). |
| **Built-in directives** | 5 | 40+ directives: admonitions (10), tabs, steps, cards, media, tables, video (YouTube, Vimeo, TikTok), embeds (Gist, CodePen, CodeSandbox, StackBlitz, Spotify), versioning (since, deprecated, changed), navigation, file I/O. |
| **Directive registry** | 4 | Immutable `DirectiveRegistry` with builder pattern. `create_default_registry()` for builtins. Custom registry requires code modification — no plugin discovery. |
| **Custom filters** | 4 | Register via `register(env, site)` pattern. `@template_safe` decorator for error resilience. `coerce_int` for YAML type safety. Well-documented in cursor rules. |
| **Shortcode extensibility** | 4 | Drop template in `templates/shortcodes/{name}.html`. Context injection via `ShortcodeContext`. |
| **Extension documentation** | 3 | `site/content/docs/extending/custom-directives.md` exists. Docs reference `BengalDirective` but implementation uses Patitas `DirectiveHandler` — naming mismatch. No formal plugin API docs. |

**Overall Score: 4.2 — Mature**

**Strongest:** Directive protocol with contracts and validation — well-designed extension point
**Weakest:** No dynamic plugin discovery; extending requires code changes, not config

---

## Journey 5: Taxonomy and Tagging for Content Organization

> *As a user, I want to tag content, generate tag pages, and browse by category.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **Tag collection** | 5 | `TaxonomyOrchestrator` (922 lines) collects tags from frontmatter, builds tag-to-pages index. |
| **Tag page generation** | 5 | Auto-generates tag listing pages and per-tag pages. Incremental updates — only regenerates changed tags. |
| **Taxonomy index** | 5 | `TaxonomyIndex` with O(1) reverse index (page → tags). `TagEntry` implements `Cacheable`. Persistent storage. |
| **Parallel tag processing** | 4 | `ThreadPoolExecutor` for `MIN_TAGS_FOR_PARALLEL=10` tags. |
| **Query indexes** | 4 | `QueryIndex` base class with section, author, category, date-range, series indexes. `IndexEntry` for O(1) lookups. |
| **Template integration** | 4 | Taxonomy template functions registered in rendering. `tag_url` filter. Tag-based navigation. |
| **Cascade metadata** | 5 | `CascadeView` (596 lines) for section-level defaults (tags, categories, etc.) flowing to pages. |

**Overall Score: 4.6 — Production**

**Strongest:** Full lifecycle from collection to page generation to index with incremental updates
**Weakest:** No hierarchical taxonomy (flat tags only based on visible API)

---

## Journey 6: Correct Rendering with Proper Links, Assets, and Navigation

> *As a user, I want all internal links to work, assets to be fingerprinted, and navigation to be accurate.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **URL ownership** | 5 | `URLRegistry` with `URLClaim` (frozen), priority resolution, `URLCollisionError` with context. Collision validation during build. |
| **Internal link resolution** | 4 | Cross-reference plugin: `[[path]]`, `[[v2:path]]`. `xref_index` for versioned links. Link validation during health check. |
| **Asset fingerprinting** | 5 | Hash-based fingerprinting, atomic writes with unique temp paths (pid+tid+uuid). CSS `@layer` bundling, SVG optimization, minification. Manifest tracking. |
| **Navigation tree** | 5 | `NavTree` (812 lines) with `NavNode`, `NavTreeCache` (lock + `PerKeyLockManager`), pre-computed trees for lock-free reads. Section+page URL merging. |
| **Menu system** | 5 | `MenuBuilder` (717 lines) with hierarchy, cycle detection, deduplication, deferred sorting. `MenuOrchestrator` with incremental caching and i18n support. |
| **Pretty URLs** | 4 | `build.pretty_urls` config. Page output path normalization. `_sanitize_string_list_with_report` for YAML edge cases. |
| **Baseurl handling** | 4 | Config `site.baseurl`. Env overrides for deployment. CI matrix tests baseurl variants. Template rule for `href` vs `path` footgun. |
| **Link checking** | 5 | Internal + external link checking. Async external with httpx, HEAD-first/GET-fallback, exponential backoff, concurrency limits. `IgnorePolicy`. Console + JSON reports. Autofix remediation. |

**Overall Score: 4.6 — Production**

**Strongest:** URL ownership system with collision detection and link checking pipeline
**Weakest:** Baseurl handling is correct but has known footgun documented in cursor rules

---

## Journey 7: API Documentation (Autodoc / OpenAPI)

> *As a user, I want to generate API reference docs from Python code or OpenAPI specs.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **Python autodoc** | 4 | AST-based extraction (no imports). Modules, classes, methods, functions, properties. Google/NumPy/Sphinx docstrings. |
| **OpenAPI rendering** | 4 | OpenAPI 3.0/3.1. YAML/JSON. Overview, endpoints, schemas. `$ref` and `allOf` resolution. Reference + explorer layouts. |
| **CLI autodoc** | 4 | Click/argparse/typer command documentation with command groups. |
| **Virtual page system** | 4 | Deferred rendering with full template context. `AutodocRenderer` for virtual/autodoc pages. |
| **Incremental autodoc** | 4 | `AutodocTracker` tracks source → page dependencies. `AutodocContentCacheMixin` for cached module data. Watches source dirs during dev. |
| **OpenAPI templates** | 4 | Full template suite: `reference.html`, `explorer.html`, `endpoint.html`, `schema.html`, `code-samples.html`, `request-body.html`, `responses.html`, `sidebar-nav.html`. |
| **Error handling** | 3 | Best-effort vs strict mode. Fallback to minimal HTML on template failure. Some complex AST extraction paths not fully covered in tests (~7% coverage per audit). |

**Overall Score: 3.9 — Mature**

**Strongest:** Multi-format support (Python, OpenAPI, CLI) with incremental caching
**Weakest:** Test coverage for autodoc extractors is sparse; external `$ref` not supported; no interactive API explorer

---

## Journey 8: Multi-Version Documentation

> *As a user, I want to publish multiple versions of my docs side by side.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **Version config** | 4 | `VersionConfig` with folder/git modes. `GitBranchPattern` for branch-based versions. `VersionBanner` for status display. |
| **Path structure** | 4 | `_versions/<id>/` content. Latest at `/docs/about/`, older at `/docs/v1/about/`. |
| **Version scoping** | 4 | `--version v2` on serve command. Build input filtering. Per-version output formats. |
| **Shared content** | 4 | `version_config.shared` for cross-version content. Shared content changes trigger full version rebuild. |
| **Nav tree versioning** | 4 | `NavTreeCache` with per-version builds via `PerKeyLockManager`. Version filtering in tree construction. |
| **Version switching UI** | 3 | Version selector in templates. No explicit deprecation banners or automatic redirects from old versions. |
| **Test coverage** | 4 | `test-versioned` root in test suite. Integration tests for versioned builds. |

**Overall Score: 3.9 — Mature**

**Strongest:** Clean path-based versioning with shared content and nav tree scoping
**Weakest:** No version deprecation workflow; no automatic redirects from old→new versions

---

## Journey 9: Health Checking and Validation

> *As a user, I want to know my site is correct before deploying.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **Validator framework** | 5 | `BaseValidator` abstract interface. 20+ validators. `HealthCheck` orchestrator with parallel execution. |
| **Tiered execution** | 5 | build (<100ms), full (~500ms), ci (~30s). Configurable thresholds. |
| **Link validation** | 5 | Internal + external. Async. Anchor validation. Code block exclusion. Reports + autofix. |
| **Content validation** | 5 | Config, URL collisions, ownership policy, rendering, directives, navigation, menus, taxonomy, tracks, cross-references. |
| **Output validation** | 4 | RSS, sitemap, fonts, assets. Cache validation. |
| **Performance checks** | 4 | `PerformanceValidator`. Connectivity analysis (orphans, bridges). Graph analysis CLI. |
| **Accessibility** | 3 | `AccessibilityValidator` exists but coverage is limited. |
| **Autofix** | 4 | `remediation/autofix.py` for link fixes. `bengal fix` CLI command. |
| **CI integration** | 5 | `--ci` flag. `--watch` mode for continuous validation. Exit codes for CI gates. |

**Overall Score: 4.4 — Mature/Production**

**Strongest:** 20+ validators with tiered execution and CI integration
**Weakest:** Accessibility validation is shallow

---

## Journey 10: Developer Experience and CLI

> *As a user, I want an intuitive CLI with helpful errors and scaffolding.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **CLI framework** | 5 | Click-based with `BengalCommand`/`BengalGroup`. Themed help, fuzzy matching, typo detection. Lazy command loading. |
| **Scaffolding** | 4 | `bengal new` for site/page/layout/partial/theme. Interactive prompts. |
| **Error messages** | 5 | `ErrorContext` + `enrich_error` + `ErrorCode`. Rich console display with `display_template_error()`. `ErrorDeduplicator` for batch rendering. Strict vs non-strict modes. |
| **Diagnostics** | 4 | `emit_diagnostic` across models. Build stats collection. Phase timing. |
| **Dashboard** | 4 | Textual TUI dashboard. Optional web dashboard via textual-serve. Snapshot tests. |
| **Config inspection** | 4 | `bengal config show/validate`. `bengal explain` for page introspection. |
| **Graph analysis** | 4 | Orphans, bridges, communities, pagerank, report. |
| **Upgrade notification** | 4 | Post-command hook, cached 24h, skipped in CI/non-TTY. |
| **Debug tools** | 4 | Debug commands. Profiling support. Provenance (experimental). |

**Overall Score: 4.3 — Mature**

**Strongest:** Error enrichment with context, codes, and Rich display
**Weakest:** E2E directory referenced in config but doesn't exist; some interactive CLI paths have low test coverage (~10%)

---

## Journey 11: Search and Content Discovery

> *As a user, I want visitors to find content through search.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **Index generation** | 5 | `index.json` with pages, sections, tags, excerpts, metadata. Version-scoped and i18n-aware. |
| **Lunr prebuilt index** | 4 | `LunrIndexGenerator` builds `search-index.json` at build time. Field boosts (title 10x, keywords 8x, description 5x). Optional dependency. |
| **Content signals** | 4 | `search_exclude`, `draft` frontmatter. `contentsignals.org` compliance in robots.txt. |
| **LLM-friendly output** | 4 | `llm-full.txt`, `llms.txt`, `agent.json` output formats. |
| **Search UI** | 3 | Client-side search with runtime index fallback. No server-side search. |

**Overall Score: 4.0 — Mature**

**Strongest:** Comprehensive index generation with field boosts and content signals
**Weakest:** No server-side search integration (Algolia, Meilisearch, etc.)

---

## Journey 12: Internationalization

> *As a user, I want to publish my site in multiple languages.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **i18n config** | 3 | `i18n_config` with `strategy`, `default_language`, `default_in_subdir`. Prefix URL strategy. |
| **Template translation** | 3 | `t` function in templates. `reset_translation_warnings()` for build isolation. Translation loading in Kida engine. |
| **Per-locale outputs** | 4 | `get_i18n_output_path()` for per-locale index.json, search-index.json. Sitemap hreflang. RSS per-locale feeds. |
| **Menu i18n** | 4 | `MenuOrchestrator` handles i18n for navigation. |
| **Content translation** | 2 | No gettext/PO file support. No machine translation integration. No translation status tracking. |
| **RTL support** | 1 | No explicit RTL layout support found. |

**Overall Score: 2.8 — Functional**

**Strongest:** Per-locale output formats and sitemap hreflang integration
**Weakest:** No formal translation file format (gettext/PO); no RTL support

---

## Journey 13: Output Formats and Deployment

> *As a user, I want RSS feeds, sitemaps, and deployment-ready output.*

### Capability Breakdown

| Capability | Score | Evidence / Notes |
|------------|:-----:|------------------|
| **Sitemap** | 5 | XML with lastmod, changefreq, priority. Sitemap index for large sites. i18n hreflang alternates. |
| **RSS** | 4 | RSS 2.0 with top-20 recent pages. RFC 822 dates. Per-locale feeds. No Atom feed. |
| **robots.txt** | 5 | Auto-generated with content-signal directives per contentsignals.org. |
| **Redirects** | 4 | HTML redirect pages for page aliases. |
| **Social cards** | 4 | OG images (1200x630px) with caching. Skipped on incremental builds. |
| **JSON/LLM output** | 5 | Per-page JSON, site-wide index.json, llm-full.txt, llms.txt, agent.json, changelog.json. |
| **Asset optimization** | 5 | CSS bundling (`@layer`), JS bundling, SVG optimization, image optimization, minification, fingerprinting, atomic writes. |
| **HTML minification** | 4 | `build.minify_html` config option. |

**Overall Score: 4.5 — Production**

**Strongest:** Comprehensive output format suite with modern LLM/agent-friendly formats
**Weakest:** No Atom feed; no JSON-LD structured data

---

## Summary Heat Map

| Journey | Score | Level |
|---------|:-----:|-------|
| 1. Build from Markdown | **4.8** | Production |
| 2. Customize Theme/Templates | **4.4** | Mature/Production |
| 3. Incremental Rebuilds | **4.4** | Mature/Production |
| 4. Custom Directives/Filters | **4.2** | Mature |
| 5. Taxonomy/Tagging | **4.6** | Production |
| 6. Correct Links/Assets/Nav | **4.6** | Production |
| 7. API Documentation (Autodoc) | **3.9** | Mature |
| 8. Multi-Version Docs | **3.9** | Mature |
| 9. Health Checking/Validation | **4.4** | Mature/Production |
| 10. Developer Experience/CLI | **4.3** | Mature |
| 11. Search/Content Discovery | **4.0** | Mature |
| 12. Internationalization | **2.8** | Functional |
| 13. Output Formats/Deployment | **4.5** | Production |

```
                     1    2    3    4    5
                     |    |    |    |    |
Build from MD        ========================[====] 4.8
Taxonomy/Tagging     =======================[===]   4.6
Links/Assets/Nav     =======================[===]   4.6
Output/Deployment    ======================[===]    4.5
Theme/Templates      =====================[==]     4.4
Incremental Builds   =====================[==]     4.4
Health/Validation    =====================[==]     4.4
Developer Exp/CLI    ====================[==]      4.3
Custom Directives    ===================[=]        4.2
Search/Discovery     ==================[=]         4.0
Autodoc/OpenAPI      =================[=]          3.9
Multi-Version Docs   =================[=]          3.9
Internationalization ============[]                 2.8
```

---

## Top Investment Opportunities

Ranked by **impact × current gap** (largest opportunity first):

### 1. Internationalization (Gap: 2.2 → target 5.0)

**Impact: High** — Blocks international adoption entirely.

| Investment | Effort | Lift |
|------------|--------|------|
| Gettext/PO file support | Medium | +1.0 |
| Translation status tracking | Medium | +0.5 |
| RTL layout support | Medium | +0.5 |
| Machine translation hooks | Low | +0.2 |

### 2. Autodoc/OpenAPI Polish (Gap: 1.1 → target 5.0)

**Impact: High** — API docs are a primary use case for technical documentation.

| Investment | Effort | Lift |
|------------|--------|------|
| Test coverage for extractors (currently ~7%) | Medium | +0.4 |
| External `$ref` resolution | Medium | +0.3 |
| Interactive API explorer (Swagger UI or custom) | High | +0.3 |
| Error path hardening | Low | +0.1 |

### 3. Multi-Version Docs Polish (Gap: 1.1 → target 5.0)

**Impact: Medium** — Important for projects with multiple release lines.

| Investment | Effort | Lift |
|------------|--------|------|
| Version deprecation workflow + banners | Low | +0.4 |
| Automatic redirects (old → latest) | Low | +0.3 |
| Git-based version discovery hardening | Medium | +0.2 |
| Cross-version search | Medium | +0.2 |

### 4. Plugin/Extension Ecosystem (Gap: 0.8 → target 5.0)

**Impact: Medium** — Enables community contributions without core changes.

| Investment | Effort | Lift |
|------------|--------|------|
| Plugin discovery (entry points or config) | Medium | +0.3 |
| Plugin API documentation | Low | +0.3 |
| Community theme support | Medium | +0.2 |

### 5. Search Enhancement (Gap: 1.0 → target 5.0)

**Impact: Medium** — Differentiator for large documentation sites.

| Investment | Effort | Lift |
|------------|--------|------|
| Algolia/Meilisearch adapter | Medium | +0.4 |
| Search analytics | Low | +0.2 |
| Faceted search | Medium | +0.2 |
| Search results UI polish | Low | +0.2 |

### 6. Dev Experience Gaps (Gap: 0.7 → target 5.0)

**Impact: Low-Medium** — Quality-of-life improvements.

| Investment | Effort | Lift |
|------------|--------|------|
| E2E test suite (referenced but missing) | Medium | +0.2 |
| Interactive CLI test coverage | Medium | +0.2 |
| HMR for templates/partials | High | +0.2 |
| Accessibility validator depth | Medium | +0.1 |

---

## Cross-Cutting Observations

### Strengths

- **Architecture discipline**: Clean separation between passive core models and active orchestrators. `bengal/core/` has no I/O.
- **Thread-safety**: Frozen dataclasses, locks, `PerKeyLockManager`, atomic writes with pid+tid+uuid temp paths, `ContentRegistry.freeze()` before concurrent reads.
- **Error handling**: `ErrorContext` + `enrich_error` + `ErrorCode` pattern is consistent. `ErrorAggregator` prevents log flooding. Strict/non-strict modes throughout.
- **Test infrastructure**: ~756 test files, ~2,297 tests, 115 Hypothesis property tests, 23 reusable test roots, 85% coverage floor, 4-shard CI integration.
- **Incremental builds**: Provenance-based filtering, content-addressed hashing, build cache with Zstd compression, early exit optimization.

### Areas to Watch

- **Codebase size**: ~80,000+ lines across orchestration alone. Some files exceed 900 lines (Page, ContentOrchestrator, BuildOrchestrator). Complexity management is a concern.
- **CommonMark compliance**: `rfc-patitas-commonmark-compliance.md` exists, indicating known gaps in markdown parsing edge cases.
- **Documentation-code drift**: Directive docs reference `BengalDirective` but code uses `DirectiveHandler`. Extension docs need alignment.
- **E2E gap**: `tests/e2e` is referenced in pytest config but doesn't exist. This is a gap for full-stack confidence.
- **Module coupling**: `rfc-module-coupling-reduction.md` and `rfc-remaining-coupling-fixes.md` indicate recognized coupling debt.
