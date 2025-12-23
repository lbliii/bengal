# RFC: Docs Navigation Rendering Optimization (Sidebar Cache + Active Trail)

**Status**: Implemented (Both Phases)  
**Created**: 2025-12-23  
**Implemented**: 2025-12-23  
**Author**: AI Assistant  
**Subsystems**: `bengal/themes/default/templates/`, `bengal/rendering/template_functions/navigation/`, `bengal/core/nav_tree.py`, `bengal/core/page/`, `bengal/rendering/context.py`  
**Confidence**: 80% 🟢  
**Priority**: P1 (High)  

---

## Executive Summary

Doc builds have regressed 2–3× due to expensive per-page rendering of the docs sidebar navigation. Even though Bengal caches the **NavTree structure** (`NavTreeCache`), we still (a) render a full recursive tree for every doc page and (b) pay repeated per-page lookups for `page._section`.

This RFC proposes a best-in-class approach used by large docs systems:

1. **Make `page._section` O(1) within a build** by memoizing the resolved `Section` on the page instance (safe, low-risk win).
2. **Stop rendering the full nav tree per page** by adopting one of:
   - Option A: SSR “active-trail-only” rendering + shallow depth (minimal HTML, zero-JS baseline).
   - **Option B2 (recommended end-state)**: cached full-tree scaffold per scope + small progressive-enhancement overlay for active/trail state.
   - Option C: Emit nav JSON once and render client-side.

Success is measured by reducing `doc/single.html` average render time from ~782ms to <150ms (5× improvement) on `site/`.

### Update (2025-12-23): Phase 1 implemented

Phase 1 has been implemented in-tree:
- `Page._section` now memoizes the resolved `Section` per `(site, section_path, section_url)` to avoid repeated registry normalization work.
- Docs sidebar no longer renders deep non-trail subtrees by default (renders children for active trail + shallow depth).

Measured on `site/`:
- Rendering phase: ~29.5s → ~16.8s
- Total build: ~54.6s → ~35.8s

Tradeoff: From a page outside a branch, expanding arbitrary deep branches may not show their children unless we either render deeper levels or add a lazy-expand mechanism.

### Update (2025-12-23): Phase 2 implemented

Phase 2 (scaffold + progressive overlay) has been implemented:

**New files:**
- `bengal/rendering/template_functions/navigation/scaffold.py` - Scaffold cache infrastructure
- `bengal/themes/default/templates/partials/docs-nav-scaffold.html` - Scaffold nav template
- `bengal/themes/default/templates/partials/docs-nav-scaffold-node.html` - Scaffold node template
- `bengal/themes/default/assets/js/enhancements/docs-nav-scaffold.js` - Client-side active state application

**How it works:**
1. When `docs.sidebar.scaffold_mode` feature is enabled, nav renders without active state classes
2. Templates emit `data-nav-path` attributes on all nav items
3. Nav container includes `data-current-path` and `data-active-trail` JSON data
4. Client-side JS applies `.active`, `.is-in-trail`, `aria-current`, `aria-expanded` at runtime
5. Full tree is rendered (no pruning), enabling expand-all behavior

**To enable:**
```yaml
# bengal.yaml
theme:
  features:
    - docs.sidebar.scaffold_mode
```

**Benefits:**
- Full nav tree available for arbitrary expansion
- Clean separation: semantic HTML + minimal JS for state
- HTML caching per scope (version_id, root_url)
- Proxy property caching eliminates repeated computation

**Measured on `site/` (1137 pages):**

| Mode | Build Time | Notes |
|------|-----------|-------|
| Phase 1 (pruned tree) | 46.7s | Renders nav per page |
| Scaffold (no cache) | 77.1s | Full tree, no caching |
| **Scaffold + caching** | **43.8s** | Full tree + HTML/proxy caching ✅ |

**Key optimization:** `NavNodeProxy` property caching eliminated millions of redundant
property computations per build. Properties like `is_current`, `is_in_trail`, `href`
are now computed once per proxy, not on every access.

**Recommendation:**
- **Scaffold mode** is now fastest AND provides full tree (enable by default)
- Phase 1 available as fallback if JS is not acceptable

---

## Problem Statement

### Current State

We have strong structure caching:
- `NavTreeCache` builds `NavTree` once per `(site, version_id)` and reuses it.

But doc templates render the docs sidebar on every doc page:
- `doc/single.html` includes `partials/docs-nav.html`
- `docs-nav.html` calls `get_nav_context(page, root_section=...)` and recursively includes `docs-nav-node.html`
- `docs-nav-node.html` traverses `item.children` recursively, producing proxies and HTML for the entire tree

### Measured Impact (Evidence)

Using `bengal build --profile-templates` on `/site`:

| Template | Count | Total (ms) | Avg (ms) |
|----------|-------|------------|----------|
| `doc/single.html` | 130 | 101,646.80 | 781.898 |
| `doc/list.html` | 39 | 15,039.00 | 385.615 |

`doc/single.html` alone accounts for ~81% of total template time.

### Root Causes

1. **Full-tree SSR per page**: recursive sidebar rendering scales as \(O(N_{nav})\) per doc page.
2. **Repeated `page._section` lookups during rendering**:
   - `page._section` performs a registry lookup on each access.
   - Section registry normalizes paths via `Path.resolve()` (filesystem work), which shows up in profiling.
3. **No fragment caching**: template inheritance organizes markup but does not memoize expensive expressions or includes.

### Why this matters

Docs sites commonly scale to hundreds/thousands of pages; full-tree SSR per page yields quadratic-ish work:
\[
T \approx O(N_{pages} \cdot N_{nav})
\]

---

## Goals

1. **Reduce doc template cost**: bring `doc/single.html` avg from ~782ms to <150ms (target), ideally <75ms (stretch).
2. **Preserve UX**:
   - Active trail highlighting must remain correct.
   - Sidebar expand/collapse behavior remains or improves.
3. **Maintain correctness** across:
   - versioned docs (`_versions/`)
   - `nav_root` boundaries
   - autodoc pages that scope navigation
4. **Avoid breaking template APIs** where possible; changes should be additive and backward-compatible.
5. **Keep incremental builds correct**: changes must not introduce stale nav state across rebuilds.

## Non-Goals

- Replacing NavTree architecture (it’s already good).
- Rewriting the theme system or moving away from Jinja2.
- Fully eliminating sidebar HTML (some sites want zero-JS; we support that via SSR options).

---

## Design Options

### Option 0: “O(1) `page._section`” Memoization (Foundational, recommended in all cases)

Memoize the resolved `Section` object on the `Page` instance after first lookup:
- On first access, resolve via `get_section_by_path()` / `get_section_by_url()`
- Cache the result in a private field (e.g. `_section_cached`) for the rest of the build
- Invalidate on site rebuild/reset or when page’s section reference changes

**Pros**
- Very low risk
- Benefits all templates, not just docs
- Reduces repeated `Path.resolve()` / normalization

**Cons**
- Must respect the “stable section references across rebuilds” contract:
  - Caching should be per-build, not persisted across long-lived Site instances unless invalidated.

**Effort**: ~1–2 hours  
**Risk**: Low

---

### Option A: Active-Trail-Only SSR for Docs Sidebar (Quick win; Phase 1)

Render only:
- top-level nav entries
- children for nodes in the active trail (expanded path)
- optionally a limited number of siblings around the active node

Everything else is output as collapsed nodes without rendering their children.

Implementation approaches:
- **A1 (template-only)**: modify `docs-nav-node.html` to only recurse into children when `item.is_in_trail` (and maybe `depth <= k`).
- **A2 (data-level)**: provide a template function that returns a pruned `NavNodeProxy` tree for the current page:
  - `get_docs_nav_tree(page, root_section=None, max_depth=None, expand_trail_only=True)`

Optional enhancement:
- client-side expand on demand (fetch JSON for subtree or embed full tree JSON once).

**Pros**
- Huge win: per-page work becomes roughly \(O(depth)\), not \(O(N_{nav})\)
- SSR remains primary; can be zero-JS
- Minimal changes to core data structures

**Cons**
- Sidebar search / “expand all” behavior may change unless explicitly supported
- Requires careful UX alignment (expand/collapse defaults)

**Effort**: ~2–6 hours (A1 faster; A2 more robust)  
**Risk**: Low–Medium (template UX changes)

---

### Option B (Best-in-class): Cached Sidebar Scaffold + Per-Page Active Overlay (Recommended end-state)

Split docs sidebar into:
- **Static scaffold** (same for all pages in a scope): full tree HTML without per-page active/trail state
- **Per-page overlay**: apply `is_current` / `is_in_trail` / expansion state

Two sub-approaches:
- **B1 (SSR-only overlay)**: render the scaffold once per scope; on each page, emit a tiny active-path payload and use minimal template composition to mark the active path without re-rendering the full tree.
- **B2 (progressive enhancement overlay) (recommended)**: render the scaffold once per scope; on each page, emit a small `data-current-path` / `data-active-trail` payload and have a small JS module apply classes + `aria-expanded` at runtime.

**Pros**
- Keeps full-tree sidebar available (random expand still shows children)
- Per-page work becomes tiny (active overlay), while scaffold cost is paid once per scope
- Scales well even for very large nav trees

**Cons**
- Cache key correctness is subtle (theme config, features, icons, versioning)
- “Active trail” requires either DOM patching (JS) or careful SSR composition

**Effort**: ~1–2 days  
**Risk**: Medium (cache correctness + UX)

---

### Option C: JSON Nav + Client Render (Docs SPA-style sidebar)

Emit `docs-nav.json` once per scope and render sidebar with JS.
SSR includes only:
- container
- minimal page metadata (`current_path`, `version_id`, `root_section`)

**Pros**
- Fastest builds
- Most flexible UI (search, expand all, virtualization)

**Cons**
- JS requirement (not acceptable for all users)
- Requires a client component and stable schema

**Effort**: ~2–4 days  
**Risk**: Medium (client code, schema, accessibility)

---

## Recommended Approach

**Phase 1 (Implemented)**: Option 0 + Option A ✅
- Memoize `page._section` per build.
- Change docs sidebar recursion to render children only when needed (active trail + shallow depth).

**Phase 2 (Implemented)**: Option B2 (scaffold + progressive overlay) ✅
- Templates, JS, and data flow implemented
- HTML caching via `NavScaffoldCache` (renders once per scope)
- Render hooks system (`bengal/orchestration/render_hooks.py`) - Bengal's first render hook!
- Enabled via feature flag: `docs.sidebar.scaffold_mode`
- ~11% slower than Phase 1, but provides full tree expandability

Rationale:
- Highest ROI with lowest complexity.
- Aligns with best-in-class pattern: **do not render the full nav tree per page**.

---

## Detailed Design

### 1) `page._section` Memoization

Add a private cache field on `Page` (or in the section reference contract implementation):
- `Page._section_cached: Section | None | Sentinel`
- Cache “not found” results too (to avoid repeated negative lookups).

Invalidation:
- When `Page._site` changes (new build session)
- When `Page._section_path` / `_section_url` changes
- When `Site.reset_ephemeral_state()` is called (if pages persist across rebuilds)

### 2) Active-Trail-Only SSR (Template Change)

Modify `partials/docs-nav-node.html` recursion rule:
- Only recurse into `item.children` if `item.is_in_trail` (or depth under a max).

Example policy (tunable):
- Expand nodes in trail.
- Optionally expand the current node’s direct children.
- Optionally expand depth <= 1 regardless (to show top-level structure).

### 3) Template API Compatibility

No template API breaks required for Phase 1:
- `get_nav_context()` stays as is.
- Templates remain valid.

Phase 2 could add new helpers (pure additive):
- `get_docs_nav_tree(...)` or `get_pruned_nav_context(...)`.

### 4) Scaffold + Overlay (Phase 2)

Scope definition (cache key inputs):
- `root_section` boundary (includes `nav_root` semantics)
- `version_id` (if versioning is enabled)
- theme identity / feature set that impacts nav rendering (icons on/off, etc.)

Implementation sketch:
- During the first page render in a scope, compute and cache a **static scaffold** of the tree:
  - HTML includes stable identifiers: `data-nav-path="/docs/..."` and `id="nav-node-..."` for toggles.
  - No per-page “active” classes.
- For each page render:
  - emit `data-current-path` + `data-active-trail` (list of ancestor paths) onto the sidebar container.
  - apply classes and `aria-expanded` with:
    - **B1**: SSR composition that only touches nodes in the active trail (harder in Jinja if scaffold is pre-rendered),
    - **B2**: a small JS module that walks the DOM and applies classes (cleanest).

---

## Alignment with “clean HTML/CSS/JS” philosophy

Option B2 aligns strongly with Bengal’s “clean HTML/CSS/JS” philosophy if implemented as **progressive enhancement**:
- **HTML**: semantic markup with `data-*` attributes only (no inline JS, no complex template logic).
- **CSS**: classes control presentation (`.active`, `.is-in-trail`, `.is-expanded`).
- **JS**: a small, isolated module that:
  - reads `data-current-path` / `data-active-trail`,
  - toggles the relevant classes and `aria-expanded`,
  - does not own navigation data (tree is still server-built).

If no-JS is required, Option B1 preserves clean separation but pushes complexity into templates; Phase 1 (Option A) preserves a zero-JS baseline.

---

## Performance & Correctness Considerations

### Thread Safety

Builds may be parallel. Memoization must be safe:
- Page objects are typically rendered once per build, but may be accessed concurrently in edge cases.
- Use simple per-instance caching; accept benign races (same result).
- Avoid global mutable caches keyed by page object identity.

### Versioning

NavTreeCache already separates by `version_id`. Our scope keys must include:
- `version_id` if used
- root section scoping (`Section.root`, `nav_root`)

### Autodoc

Autodoc pages may set `is_autodoc` and rely on scoped navigation; this must keep working:
- `docs-nav.html` already branches on `is_autodoc` for version selector, and uses `root_section` scoping.

---

## Rollout Plan

1. Implement `page._section` memoization behind a small, testable mechanism.
2. Modify docs sidebar recursion to expand active-trail-only by default.
3. Add a theme-level feature flag / config toggle to preserve old behavior if needed:
   - e.g. `theme.features` includes `docs.sidebar.render_full_tree`
4. Measure:
   - `bengal build --profile-templates` before/after
   - ensure doc/single avg time drops substantially
5. If needed, proceed to Phase 2 (pruned tree helper or scaffold caching).

---

## Success Metrics

Primary:
- `doc/single.html` avg render time: **~782ms → <150ms** (target) on `/site`.

Secondary:
- Total template time reduction: 124,920ms → <50,000ms on `/site` (target).
- No regressions in:
  - active trail correctness
  - versioned docs sidebar scoping
  - navigation accessibility (ARIA attributes)

---

## Testing Plan

1. Unit tests:
   - `Page._section` memoization returns correct section and does not re-run normalization repeatedly.
   - `Section.root` + `nav_root` boundaries remain correct.
2. Snapshot tests (theme):
   - Ensure a representative docs page sidebar shows correct active trail and expands expected nodes.
3. Performance regression test:
   - Add or extend a benchmark scenario that measures `doc/single.html` template time (via TemplateProfiler).

---

## Risks & Mitigations

**Risk: UX change (less-expanded sidebar)**
- Mitigation: feature flag to restore full-tree rendering.

**Risk: Stale memoized section across rebuilds in dev server**
- Mitigation: invalidate memoized section on `Site.reset_ephemeral_state()` / site identity change.

**Risk: Hard-to-choose defaults**
- Mitigation: start with conservative expansion (trail + one level), iterate based on feedback.

---

## Open Questions

1. Should “full-tree sidebar” remain the default for smaller sites, with active-trail-only only for large nav trees?
2. Should we add a global `docs.sidebar.max_nodes` / `docs.sidebar.max_depth` config?
3. Do we want JS-assisted “expand all / search” now (Option C), or keep SSR-only for now?
