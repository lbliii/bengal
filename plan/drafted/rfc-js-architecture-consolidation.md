# RFC: JavaScript Architecture Consolidation

**Status:** Draft  
**Created:** 2025-12-06  
**Author:** AI Assistant  
**Priority:** Medium  
**Estimated Effort:** 4-6 hours

---

## Executive Summary

Bengal's JavaScript has grown organically into a **60% cohesive / 40% fragmented** state. Good infrastructure exists (`utils.js`, `bengal-enhance.js`) but isn't consistently adopted. This RFC proposes consolidating to a single, clear architecture.

---

## Problem Statement

### Current Issues

1. **Duplicate Modules**: Same functionality exists in both root and `enhancements/` directories
2. **Overlapping Responsibilities**: TOC highlighting in 2 places, scroll spy in 2 places
3. **Inconsistent Patterns**: Some modules use enhancement system, most don't
4. **Scattered Features**: 4 search files, 2 holo files, 2 graph files

### Evidence

| Module | Root | enhancements/ | Uses Utils | Uses Enhance | Notes |
|--------|------|---------------|------------|--------------|-------|
| TOC | ✅ | ✅ | ✅ | ❌ | Root version (568 lines) more complete than enhancements/ (155 lines) |
| Mobile Nav | ✅ | ✅ | ❌ | Partial | Root version registers with enhance, enhancements/ version doesn't |
| Tabs | ✅ | ✅ | ❌ | ✅ | Root version registers with enhance |
| Theme Toggle | ✅ | ✅ | ❌ | ✅ | Root version registers with enhance |
| Holo | ✅ | ❌ | ❌ | ❌ | No utils dependency, no enhancement registration |
| Interactive | ✅ | ❌ | ✅ | ❌ | Multiple responsibilities (back-to-top, reading-progress, docs-nav scroll spy) |
| Main | ✅ | ❌ | ✅ | ❌ | Contains TOC highlighting (overlaps with toc.js) |
| Search | ✅ (4 files) | ❌ | ✅ | ❌ | Fragmented: search.js, search-modal.js, search-page.js, search-preload.js |
| Theme Init | ✅ | ❌ | ❌ | ❌ | Separate 40-line file, currently inlined in base.html `<head>` |

---

## Proposed Architecture

### Design Principles

1. **Single Source of Truth**: One canonical location per feature
2. **Layered Enhancement**: HTML works → CSS enhances → JS elevates
3. **Declarative First**: Prefer `data-bengal` attributes over manual init
4. **Consistent Patterns**: All modules follow same structure

### Module Categories

```text
assets/js/
├── utils.js                    # Foundation (load first)
├── bengal-enhance.js           # Enhancement registry (load second)
├── main.js                     # Core bootstrapper (orchestrates everything)
│
├── core/                       # Always-loaded, non-optional modules
│   ├── theme.js               # Theme toggle (merged from theme-toggle.js + theme-init.js)
│   ├── search.js              # Search (merged from search-*.js)
│   ├── nav-dropdown.js        # Navigation dropdown menus (always needed)
│   └── session-path-tracker.js # Session tracking (always needed)
│
├── enhancements/              # Lazy-loaded via data-bengal attributes
│   ├── toc.js                 # Table of contents
│   ├── tabs.js                # Tabbed content
│   ├── mobile-nav.js          # Mobile navigation
│   ├── lightbox.js            # Image lightbox
│   ├── holo.js                # Holographic effects (merged from holo.js + holo-cards.js)
│   ├── interactive.js         # Back-to-top, reading-progress, docs-nav scroll spy
│   ├── copy-link.js           # Copy link functionality
│   ├── action-bar.js          # Action bar component
│   ├── data-table.js          # Data table enhancements
│   └── lazy-loaders.js        # Lazy loading (Mermaid, D3, etc.)
│
└── vendor/                    # Third-party (unchanged)
    ├── lunr.min.js
    └── tabulator.min.js
```

**Note**: Graph modules (`graph-contextual.js`, `graph-minimap.js`) remain in root as they're lazy-loaded via `BENGAL_LAZY_ASSETS` configuration.

### Loading Strategy

**Current State**: Theme init is inlined in `<head>` (`base.html:156-174`) to prevent FOUC.

**Proposed Strategy**:

```html
<!-- Critical: Load synchronously in <head> to prevent FOUC -->
<script src="{{ asset_url('js/utils.js') }}"></script>
<script src="{{ asset_url('js/bengal-enhance.js') }}"></script>
<!-- Theme init must be synchronous to prevent flash of unstyled content -->
<script src="{{ asset_url('js/core/theme.js') }}"></script>

<!-- Non-critical: Load deferred -->
<script src="{{ asset_url('js/main.js') }}" defer></script>
<script src="{{ asset_url('js/core/search.js') }}" defer></script>
<script src="{{ asset_url('js/core/nav-dropdown.js') }}" defer></script>
<script src="{{ asset_url('js/core/session-path-tracker.js') }}" defer></script>

<!-- Enhancements: Auto-loaded by bengal-enhance.js when elements detected -->
<!-- No manual <script> tags needed for enhancements/ -->
<!-- bengal-enhance.js lazy-loads from /assets/js/enhancements/{name}.js -->
```

**Alternative FOUC Prevention**: If synchronous loading causes issues, keep theme init inline in `<head>` (current approach) and load `core/theme.js` deferred for toggle functionality only.

### Standard Module Template

```javascript
/**
 * Bengal Enhancement: [Name]
 * [Description]
 *
 * @requires utils.js
 * @requires bengal-enhance.js
 */
(function() {
  'use strict';

  // ============================================================
  // Dependencies
  // ============================================================

  if (!window.BengalUtils) {
    console.error('[Bengal] utils.js required');
    return;
  }

  const { log, ready, throttleScroll, debounce } = window.BengalUtils;

  // ============================================================
  // State
  // ============================================================

  let isInitialized = false;
  const cleanupHandlers = [];

  // ============================================================
  // Private Functions
  // ============================================================

  function privateHelper() {
    // ...
  }

  // ============================================================
  // Public API
  // ============================================================

  function init(el, options = {}) {
    if (isInitialized) return;
    isInitialized = true;

    // Setup...
    log('[ModuleName] initialized');
  }

  function cleanup() {
    cleanupHandlers.forEach(fn => fn());
    cleanupHandlers.length = 0;
    isInitialized = false;
  }

  // ============================================================
  // Registration
  // ============================================================

  // Register with enhancement system (primary method)
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('module-name', init);
  }

  // Export public API
  window.BengalModuleName = {
    init,
    cleanup,
    // other public methods...
  };

})();
```

---

## Migration Plan

### Phase 1: Consolidate Duplicates (2 hours)

**Goal**: Single canonical location for each feature

| Action | From | To | Notes |
|--------|------|-----|-------|
| Delete | `enhancements/toc.js` | — | Root version is more complete |
| Delete | `enhancements/mobile-nav.js` | — | Root version is more complete |
| Delete | `enhancements/tabs.js` | — | Keep root, add enhancement registration |
| Delete | `enhancements/theme-toggle.js` | — | Keep root, add enhancement registration |
| Merge | `search-*.js` (4 files) | `core/search.js` | Combine into single module |
| Merge | `holo.js` + `holo-cards.js` | `enhancements/holo.js` | Combine effects |
| Merge | `theme-toggle.js` + `theme-init.js` | `core/theme.js` | Single theme module |

### Phase 2: Standardize Patterns (2 hours)

**Goal**: All modules follow standard template

1. **Add utils dependency** to modules that lack it:
   - `mobile-nav.js`
   - `tabs.js`
   - `theme-toggle.js`
   - `holo.js`

2. **Add enhancement registration** to standalone modules:
   - `toc.js` → register as `data-bengal="toc"`
   - `tabs.js` → register as `data-bengal="tabs"`
   - `lightbox.js` → register as `data-bengal="lightbox"`

3. **Remove overlapping functionality**:
   - Remove TOC highlighting from `main.js:259-293` (keep in `toc.js`)
   - Remove docs-nav scroll spy from `interactive.js:171-242` (move to `enhancements/docs-nav.js` or keep in `interactive.js` if docs-specific)
   - Keep smooth scroll in `main.js` (it's the canonical implementation)

4. **Handle `interactive.js` responsibilities**:
   - Keep as single module with multiple `data-bengal` registrations:
     - `data-bengal="back-to-top"` → Back to top button
     - `data-bengal="reading-progress"` → Reading progress bar
     - `data-bengal="docs-nav"` → Docs navigation scroll spy (if keeping docs-specific)
   - Alternative: Split into separate modules if responsibilities diverge

### Phase 3: Reorganize Files (1 hour)

**Goal**: Clear directory structure

```bash
# Create directories
mkdir -p assets/js/core
mkdir -p assets/js/vendor

# Move core modules
mv theme-toggle.js core/theme.js  # After merge with theme-init.js
mv search.js core/search.js       # After merge with search-*.js
mv nav-dropdown.js core/nav-dropdown.js
mv session-path-tracker.js core/session-path-tracker.js

# Move vendor
mv lunr.min.js vendor/
mv tabulator.min.js vendor/

# Move remaining to enhancements/
mv toc.js enhancements/
mv tabs.js enhancements/
mv lightbox.js enhancements/
mv holo.js enhancements/           # After merge with holo-cards.js
mv interactive.js enhancements/
mv copy-link.js enhancements/
mv action-bar.js enhancements/
mv data-table.js enhancements/
mv lazy-loaders.js enhancements/

# Clean up duplicates and merged files
rm enhancements/toc.js             # Duplicate
rm enhancements/mobile-nav.js      # Duplicate
rm enhancements/tabs.js            # Duplicate
rm enhancements/theme-toggle.js    # Duplicate
rm search-modal.js                  # Merged into core/search.js
rm search-page.js                  # Merged into core/search.js
rm search-preload.js                # Merged into core/search.js
rm holo-cards.js                   # Merged into enhancements/holo.js
rm theme-init.js                   # Merged into core/theme.js
```

### Phase 4: Update Templates & Bundler (1 hour)

**Goal**: Templates and bundler use new paths and patterns

1. **Update `base.html` script loading order**:
   - Move `utils.js` and `bengal-enhance.js` to synchronous load in `<head>`
   - Update `core/theme.js` path (or keep inline init)
   - Update `core/search.js`, `core/nav-dropdown.js`, `core/session-path-tracker.js` paths
   - Remove manual `<script>` tags for enhancement modules (they'll lazy-load)

2. **Update bundler** (`bengal/utils/js_bundler.py`):
   - Update `get_theme_js_bundle_order()` to reflect new paths:
     - `core/theme.js` instead of `theme-toggle.js`
     - `core/search.js` instead of `search.js`, `search-modal.js`, `search-page.js`, `search-preload.js`
     - `core/nav-dropdown.js` (new)
     - `core/session-path-tracker.js` (new)
     - `enhancements/*.js` paths for moved modules
   - Ensure bundle order maintains dependency relationships

3. **Replace manual `<script>` tags** for enhancements with `data-bengal` attributes in templates

4. **Update any hardcoded paths** in templates or other JS files

---

## Responsibility Matrix (Post-Consolidation)

| Feature | Module | Trigger | Notes |
|---------|--------|---------|-------|
| Theme switching | `core/theme.js` | Auto-init (synchronous in `<head>`) | Prevents FOUC |
| Search | `core/search.js` | Auto-init (deferred) | Merged from 4 files |
| Navigation dropdowns | `core/nav-dropdown.js` | Auto-init (deferred) | Always needed |
| Session tracking | `core/session-path-tracker.js` | Auto-init (deferred) | Analytics |
| Code copy buttons | `main.js` | Auto-init | Core functionality |
| External link icons | `main.js` | Auto-init | Core functionality |
| Lazy loading | `main.js` | Auto-init | Core functionality |
| Keyboard detection | `main.js` | Auto-init | Core functionality |
| TOC + scroll spy | `enhancements/toc.js` | `data-bengal="toc"` | Lazy-loaded |
| Tabs | `enhancements/tabs.js` | `data-bengal="tabs"` | Lazy-loaded |
| Mobile nav | `enhancements/mobile-nav.js` | `data-bengal="mobile-nav"` | Lazy-loaded |
| Lightbox | `enhancements/lightbox.js` | `data-bengal="lightbox"` | Lazy-loaded, feature-gated |
| Holo effects | `enhancements/holo.js` | `data-bengal="holo"` | Lazy-loaded, merged from 2 files |
| Back to top | `enhancements/interactive.js` | `data-bengal="back-to-top"` | Lazy-loaded |
| Reading progress | `enhancements/interactive.js` | `data-bengal="reading-progress"` | Lazy-loaded |
| Docs nav scroll spy | `enhancements/interactive.js` | `data-bengal="docs-nav"` | Lazy-loaded, docs-specific |
| Copy link | `enhancements/copy-link.js` | `data-bengal="copy-link"` | Lazy-loaded |
| Action bar | `enhancements/action-bar.js` | Auto-init or `data-bengal="action-bar"` | May need auto-init |
| Data table | `enhancements/data-table.js` | Lazy-loaded via `BENGAL_LAZY_ASSETS` | Via lazy-loaders |
| Graph modules | `graph-*.js` (root) | Lazy-loaded via `BENGAL_LAZY_ASSETS` | Remain in root |

---

## Files to Delete

After consolidation, these files should be removed:

```
# Duplicate modules (keep root versions)
enhancements/toc.js           # Duplicate - root version is more complete
enhancements/mobile-nav.js    # Duplicate - root version is more complete
enhancements/tabs.js          # Duplicate - root version registers with enhance
enhancements/theme-toggle.js  # Duplicate - root version registers with enhance

# Merged modules
search-modal.js               # Merged into core/search.js
search-page.js                # Merged into core/search.js
search-preload.js             # Merged into core/search.js
holo-cards.js                 # Merged into enhancements/holo.js
theme-init.js                 # Merged into core/theme.js (or kept inline in base.html)
```

**Total files removed**: 9 files
**Total files moved**: 12 files (to core/ or enhancements/)
**Net reduction**: ~30% fewer JS files to manage


## Testing Checklist

After each phase:

- [ ] Theme toggle works (light/dark/system)
- [ ] Search modal opens and returns results
- [ ] TOC highlights correct section on scroll
- [ ] TOC collapse/expand works
- [ ] Tabs switch correctly
- [ ] Mobile nav opens/closes
- [ ] Lightbox zooms images
- [ ] Code copy buttons work
- [ ] Back to top button appears on scroll
- [ ] Reading progress bar updates
- [ ] External links get icons
- [ ] Keyboard navigation works
- [ ] No console errors
- [ ] No duplicate event listeners (memory leak prevention)

---

## Success Criteria

1. **Single source of truth**: No duplicate modules
2. **Consistent patterns**: All modules follow standard template
3. **Clear ownership**: Responsibility matrix shows exactly which module handles what
4. **Declarative usage**: Most features triggered via `data-bengal` attributes
5. **Documented**: README.md updated with new architecture

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing sites | Keep backward compatibility exports (`window.BengalNav`, `window.BengalTOC`, etc.) |
| Theme FOUC | Option A: Load `core/theme.js` synchronously in `<head>`. Option B: Keep inline init in `<head>` (current approach) |
| Missing features during migration | Test each phase independently with full test checklist |
| Enhancement lazy-load failures | Graceful degradation (HTML still works). `bengal-enhance.js` handles errors gracefully |
| Bundle order incorrect | Update `js_bundler.py:get_theme_js_bundle_order()` immediately after file moves |
| Template paths break | Update `base.html` script tags in same commit as file moves |
| Lazy-loading path issues | Verify `bengal-enhance.js` baseUrl config matches new `enhancements/` location |

---

## Decision Points

1. **Keep `interactive.js` or split?**
   - Option A: Keep as single module with multiple `data-bengal` registrations
   - Option B: Split into `back-to-top.js`, `reading-progress.js`, etc.
   - **Recommendation**: Option A (fewer files, related functionality)

2. **Where does docs navigation scroll spy live?**
   - Currently in `interactive.js:171-242` (handles docs-nav links only)
   - TOC scroll spy is in `toc.js` (handles TOC links)
   - **Recommendation**: Keep docs-nav scroll spy in `interactive.js` with `data-bengal="docs-nav"` registration (docs-specific, related to other interactive features)

3. **Graph modules (`graph-contextual.js`, `graph-minimap.js`)?**
   - Keep separate or merge?
   - **Recommendation**: Keep separate in root (different features, lazy-loaded via `BENGAL_LAZY_ASSETS`, not part of enhancement system)

4. **Action bar auto-init vs enhancement registration?**
   - Currently auto-initializes on page load
   - Could register as `data-bengal="action-bar"` for lazy-loading
   - **Recommendation**: Keep auto-init (always needed when action-bar HTML is present, not conditional)

---

## Next Steps

1. [ ] Review RFC, adjust priorities
2. [ ] Execute Phase 1: Consolidate duplicates
3. [ ] Execute Phase 2: Standardize patterns
4. [ ] Execute Phase 3: Reorganize files
5. [ ] Execute Phase 4: Update templates & bundler
   - [ ] Update `base.html` script loading order
   - [ ] Update `js_bundler.py:get_theme_js_bundle_order()`
   - [ ] Verify `bengal-enhance.js` baseUrl config
6. [ ] Test all features with test checklist
7. [ ] Update README.md with new architecture
8. [ ] Move RFC to `plan/implemented/`

## Implementation Notes

- **Bundle compatibility**: When `bundle_js=true`, bundler must include all moved files in correct order
- **Enhancement lazy-loading**: `bengal-enhance.js` loads from `/assets/js/enhancements/{name}.js` - verify paths match after reorganization
- **Backward compatibility**: Keep all `window.Bengal*` namespace exports for existing sites
- **FOUC prevention**: Test both synchronous load and inline init approaches, choose based on performance

## RFC Improvements (2025-12-06)

Based on codebase analysis, this RFC includes the following improvements:

1. **Added missing modules**: Included `nav-dropdown.js`, `action-bar.js`, `session-path-tracker.js` in reorganization plan
2. **Clarified FOUC prevention**: Documented current inline approach vs proposed synchronous load, with recommendation to test both
3. **Added bundler update requirement**: Phase 4 now includes updating `js_bundler.py:get_theme_js_bundle_order()` to reflect new file paths
4. **Enhanced evidence table**: Added notes column with specific details about each module's state
5. **Expanded file structure**: Included all modules in proposed structure, including graph modules note
6. **Improved responsibility matrix**: Added notes column and included all modules with trigger mechanisms
7. **Enhanced risks section**: Added bundler order and template path risks with mitigation strategies
8. **Clarified decision points**: Added action bar auto-init vs enhancement registration decision
9. **Expanded implementation notes**: Added specific technical considerations for bundle compatibility and lazy-loading
10. **Added file count metrics**: Documented net reduction in files to manage
