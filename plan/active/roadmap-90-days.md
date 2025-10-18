## Bengal 90-Day Roadmap (Autodoc/DX Moat)

### Objectives
- Ship parity-plus autodoc (alias detection, inherited member controls) while keeping AST-based robustness.
- Add pragmatic PDF export from HTML (no LaTeX dependency).
- Deliver integrity tooling (link checker) suitable for CI.
- Improve i18n/URL flexibility (unicode slugs) without breaking existing sites.
- Enable cross-project references (HTML-first, lightweight Intersphinx-style).

### Success Criteria
- Aliases and inherited display controls configurable and covered by tests.
- One-click HTML→PDF CLI works for typical docs sites; document limitations.
- Link checker runs in CI, supports ignore rules (including 5xx), emits JSON.
- Unicode slug/permalink mode behind config flag; migration guidance provided.
- Cross-project reference index published/consumed; templates render external refs.

### High-Level Timeline
- Weeks 1–4: Autodoc parity upgrades; design PDF and linkcheck; RFCs for slugs/xref.
- Weeks 5–8: Implement PDF export and linkcheck; ship unicode slugs; start xref index.
- Weeks 9–12: Cross-project refs complete; docs, examples, migration guide; polish & bugs.

---

### Workstreams and Deliverables

#### 1) Autodoc Parity Upgrades (Weeks 1–4)
Owner: Core

Deliverables:
- Alias detection: treat simple assignment aliases (`alias = original`) as documented symbols.
- Inherited member controls: config to include/exclude inherited members per element type.
- Tests: unit+integration snapshots for modules/classes/functions.
- Docs: configuration reference + examples.

Key Tasks:
- Extend Python AST visitor to capture function-valued assignments and bind alias metadata.
- Add `autodoc.python.include_inherited` and per-type overrides.
- Template updates to reflect alias badges and inherited member flags.

Risks/Mitigations:
- Over-documenting internals → scope to public API by default; add `include_private` guard.

#### 2) HTML→PDF Export (Weeks 5–6)
Owner: Tooling

Deliverables:
- `bengal pdf` CLI: Playwright/Chromium-based export, TOC, header/footer, page numbers.
- Config: page size, margins, cover page URL, exclude/include patterns.
- Docs: “Good-enough PDF” guide; limitations vs LaTeX.

Key Tasks:
- Implement site crawl or index-driven render to a single PDF (per section and/or site-wide).
- Add CSS print styles to default theme to optimize pagination.

Risks/Mitigations:
- Large sites memory usage → chunked export by section; stream merges.

#### 3) Link Checker (Weeks 6–8)
Owner: Health

Deliverables:
- `bengal health linkcheck` with concurrency, retries, timeouts.
- Ignore policy: patterns, status ranges (e.g., 5xx), and per-domain rules.
- Outputs: CLI summary + JSON for CI annotations.

Key Tasks:
- Implement async HTTP checker with caching.
- Provide `--external-only`, `--internal-only`, `--exclude`, `--max-concurrency` flags.

Risks/Mitigations:
- Flaky external endpoints → default retry/backoff + ignore rules.

#### 4) Unicode Slugs/Permalinks (Weeks 5–7)
Owner: Core

Deliverables:
- Config: `urls.keep_unicode_slugs` and `urls.slug_strategy` (ascii|unicode|custom).
- Slug utilities: percent-encoding where needed; safe routing.
- Tests: multilingual pages (Chinese, Japanese, Arabic), round-trip permalinks.
- Docs: migration notes, SEO considerations.

Key Tasks:
- Extend slugify utility to preserve unicode under flag and ensure permalink stability.
- Update sitemap/rss generators and validators.

Risks/Mitigations:
- Backward incompatibility → flag default off; clear migration doc.

#### 5) Cross-Project References (Weeks 7–11)
Owner: Rendering

Deliverables:
- Exporter: `bengal xref export` produces a small JSON index (paths, anchors, titles).
- Import/resolve: `xref.import` setting to consume remote/local indexes.
- Template filter/function: `xref(path, text?)` to link to external symbols.
- Docs: how-to and caching strategy.

Key Tasks:
- Define minimal index schema; implement exporter.
- Add resolver service with cache + fallback.

Risks/Mitigations:
- Stale indexes → support versioned URLs and cache-busting via ETag.

#### 6) Migration Guide from Sphinx (Weeks 8–12)
Owner: Docs

Deliverables:
- “Sphinx → Bengal” guide: autodoc parity table, sample diffs, pitfalls.
- Examples repo branch with before/after.

Key Tasks:
- Map Sphinx configs to Bengal equivalents; provide scripts for content moves.

---

### Milestones
- M1 (End W4): Aliases + inherited controls shipped; design docs for PDF/linkcheck/xref.
- M2 (End W8): PDF export + linkcheck + unicode slugs in main; theme print CSS tuned.
- M3 (End W12): Cross-project refs + migration guide published; stabilization.

### Metrics
- Adoption of autodoc features (config usage telemetry opt‑in, or proxy metrics via tests/examples).
- Linkcheck CI integration count (docs to instrument with badges).
- PDF command usage in CLI analytics (opt‑in).
- Issue velocity: <3 business days median to first response; target 0 regressions.

### Out of Scope
- Full LaTeX pipeline; domain-specific Sphinx extensions parity.

### Dependencies
- Playwright/headless Chromium for PDF; aiohttp/httpx for linkcheck.

### Communication
- Weekly changelog entries; publish a mid-cycle blog post at M2.


