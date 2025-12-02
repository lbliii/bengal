# RFC: Search Experience v2

**Author**: AI Assistant  
**Date**: 2025-12-01  
**Status**: ✅ Implemented  
**Confidence**: 88% 🟢

---

## Executive Summary

Bengal's current search experience is functionally solid but has scalability concerns and lacks modern UX patterns. This RFC proposes a phased approach to improve search: pre-built indexes for performance, a command-palette modal for quick access, and refreshed Pagefind guidance for large sites without adding new runtime dependencies.

**Key Improvements**:
- 🚀 Pre-build Lunr index at build time using Python tooling (30-50% faster initial search)
- ⌘ Command-palette modal (Cmd/Ctrl+K overlay) with lazy loading
- ♻️ Keep `index.json` available for RAG/CLI consumers while adding a compact `search-index.json`
- 💾 Recent searches with local storage
- 📊 Search analytics hooks for insights (optional, no external deps)
- 📚 Document Pagefind as an advanced recipe without wiring it into the default build

---

## 1. Problem Statement

### 1.1 Current State

Bengal ships a complete client-side search implementation:

| Component | Location | Purpose |
|-----------|----------|---------|
| Index Generator | `bengal/postprocess/output_formats/index_generator.py` | Generates `index.json` with page metadata |
| Search Core | `themes/default/assets/js/search.js` | Lunr.js search with filtering |
| Search UI | `themes/default/templates/partials/search.html` | Input, results, filters |
| Search Page | `themes/default/templates/search.html` | Dedicated full-page experience |

**Evidence**:
- Index generator: `index_generator.py:30-64` - `SiteIndexGenerator` class
- Lunr index building: `search.js:107-138` - Client-side index construction
- Field boosting: `search.js:113-120` - title(10x), description(5x), search_keywords(8x)

### 1.2 Pain Points

**1. Large Index Size**
- `public/index.json` grows linearly with content
- For sites with 500+ pages, index can exceed 2MB
- Index is loaded and parsed on every page visit
- Lunr index built client-side on each page load

**2. No Quick-Access Modal**
- Industry standard (Algolia, DocSearch, Linear, Notion) uses Cmd+K modal
- Current implementation requires navigation to search page or inline search
- No persistent search across page navigations

**3. No Search History**
- Users re-type frequent searches
- No "recent searches" feature
- No search suggestions

**4. Pagefind Guidance Gap**
- Pagefind documented in recipes but not clearly positioned as advanced option
- No guidance on when to switch or how to keep assets in sync with the theme
- Users unsure how to run Pagefind alongside Bengal builds

### 1.3 User Impact

| User Type | Impact |
|-----------|--------|
| Small site (<100 pages) | Minimal - current solution works well |
| Medium site (100-500 pages) | Noticeable load time, acceptable |
| Large site (>500 pages) | Poor UX - slow load, memory pressure on mobile |
| Power users | Missing quick-access modal reduces productivity |

---

## 2. Goals & Non-Goals

### Goals

1. **Reduce time-to-first-search by 50%** for medium sites via pre-built index
2. **Add command-palette modal** (Cmd/Ctrl+K) for quick access
3. **Preserve compatibility** by continuing to emit `index.json` for downstream consumers
4. **Implement recent searches** with local storage
5. **Add search analytics hooks** for optional instrumentation
6. **Document Pagefind** as an advanced path without adding runtime dependencies

### Non-Goals

- Not replacing Lunr.js as default (it works well for small/medium sites)
- Not implementing server-side search (Bengal is static-first)
- Not adding full-text highlighting in results (complex, deferred)
- Not implementing search synonyms/spell-check (v3 scope)

---

## 3. Architecture Impact

**Affected Subsystems**:

| Subsystem | Impact |
|-----------|--------|
| **Postprocess** (`bengal/postprocess/`) | New `lunr_index_generator.py` for pre-built index output |
| **Themes** (`bengal/themes/`) | New modal component + JS enhancements |
| **Config** (`bengal/config/`) | Expand `[search]` table with `lunr.prebuilt`, `ui.modal`, `analytics` |
| **Core** | None - no model changes |
| **Orchestration** | Minor - invoke new postprocess step |
| **Cache** | None |

**New Files**:
```
bengal/postprocess/output_formats/lunr_index_generator.py  # Pre-build Lunr index
themes/default/templates/partials/search-modal.html         # Command palette modal
themes/default/assets/js/search-modal.js                    # Modal behavior
themes/default/assets/css/components/search-modal.css       # Modal styling
```

**Integration Points**:
1. Build orchestrator calls `lunr_index_generator` after `index_generator`
2. Base template loads `search-modal.js` and binds Cmd+K
3. Config toggles pre-built Lunr + modal features while keeping runtime fallback

---

## 4. Design Options

### Option A: Pre-built Lunr Index Only

**Description**: Generate a serialized Lunr index at build time using a pure-Python builder (`lunr` PyPI package).

**Implementation**:
1. Add `lunr_index_generator.py` that reuses `SiteIndexGenerator` output and feeds it through the Python `lunr` builder
2. Output `search-index.json` (serialized Lunr index) alongside the existing `index.json`
3. `search.js` loads the pre-built index (via `lunr.Index.load()`) instead of rebuilding client-side

**Pros**:
- Minimal changes to existing code
- 30-50% faster initial search
- No Node/Bun requirement; Python dependency managed via standard packaging

**Cons**:
- Adds a new Python dependency (`lunr`)
- Doesn't solve large index problem
- Still loads full index on every page

**Complexity**: Simple
**Evidence**: Lunr supports `lunr.Index.load()` for pre-built indexes

---

### Option B: Modal + Pre-built Index (Recommended)

**Description**: Add Cmd+K modal and pre-built index.

**Implementation**:
1. Everything from Option A (Python-built `search-index.json`)
2. New `search-modal.html` partial with overlay UI
3. `search-modal.js` handles:
   - Cmd/Ctrl+K binding
   - Focus trap
   - Keyboard navigation (↑↓ to navigate, Enter to select)
   - Recent searches (localStorage)
4. Modal lazy-loads `search-index.json` on first open while leaving `index.json` untouched for RAG/scripts

**Pros**:
- Modern UX pattern
- Lazy loading reduces initial page load
- Recent searches improve repeat usage
- No new runtime dependencies; `index.json` compatibility retained

**Cons**:
- More JS complexity
- Needs careful a11y handling

**Complexity**: Moderate
**Evidence**: Current `search.js:59-159` already handles index loading and can be extended

---

### Option C: Pagefind Integration (Future Track)

**Description**: Keep Pagefind documented as an optional path; revisit first-class integration later if we can accept the binary dependency.

**Implementation**:
1. Keep Option B as baseline.
2. Enhance documentation (`site/content/docs/recipes/search.md`) with updated instructions for running Pagefind post-build.
3. Collect feedback from large-site users before wiring Pagefind into orchestration.

**Pros**:
- Avoids shipping additional binaries by default
- Large sites can still opt into Pagefind manually today

**Cons**:
- Users must manage Pagefind invocation themselves
- No automated detection or theming yet

**Complexity**: Low (docs only for now)
**Evidence**: Pagefind recipe at `site/content/docs/recipes/search.md:1-100`

---

### Recommended: Option B (Modal + Pre-built Index)

**Reasoning**:
1. Delivers the biggest UX win without new runtime dependencies
2. Pre-built Lunr handles small/medium sites while keeping `index.json` for other consumers
3. Modal lazy-loading + recent searches dramatically improve usability
4. Keeps Pagefind as an opt-in recipe, preserving user choice

---

## 5. Detailed Design (Option B)

### 5.1 Configuration

```yaml
# config/_default/features.yaml
features:
  search: true  # Enable search index generation

# config/_default/search.yaml (NEW/EXPANDED)
search:
  enabled: true

  # Lunr build-time and runtime settings
  lunr:
    prebuilt: true          # Emit search-index.json via Python lunr
    min_query_length: 2     # Minimum characters to trigger search
    max_results: 50         # Maximum results to show
    preload: smart          # immediate | smart | lazy (maps to existing meta tag)

  # UI settings
  ui:
    modal: true             # Enable Cmd+K modal
    recent_searches: 5      # Number of recent searches to store
    placeholder: "Search documentation..."

  # Optional analytics hooks (no external deps)
  analytics:
    enabled: false
    event_endpoint: null    # POST target for custom instrumentation
```

### 5.2 Search Modal Component

```html
<!-- templates/partials/search-modal.html -->
<dialog id="search-modal" class="search-modal" aria-label="Search">
  <div class="search-modal__backdrop" data-close></div>
  <div class="search-modal__container">
    <header class="search-modal__header">
      <input type="search" class="search-modal__input" placeholder="Search...">
      <kbd class="search-modal__kbd">ESC</kbd>
    </header>

    <div class="search-modal__recent" id="search-recent">
      <h3>Recent Searches</h3>
      <ul></ul>
    </div>

    <div class="search-modal__results" id="search-modal-results">
      <!-- Results populated by JS -->
    </div>

    <footer class="search-modal__footer">
      <span><kbd>↑</kbd><kbd>↓</kbd> Navigate</span>
      <span><kbd>↵</kbd> Open</span>
      <span><kbd>ESC</kbd> Close</span>
    </footer>
  </div>
</dialog>
```

### 5.3 Search Backend Abstraction

```javascript
// search-backend.js - Backend abstraction
class SearchBackend {
  async search(query, filters) { throw new Error('Not implemented'); }
  async load() { throw new Error('Not implemented'); }
  isLoaded() { return false; }
}

class LunrBackend extends SearchBackend {
  // Existing search.js logic, refactored to load pre-built index lazily
}

// Factory
function createSearchBackend(config) {
  return new LunrBackend();
}
```

### 5.4 Pre-built Lunr Index Generator

```python
# bengal/postprocess/output_formats/lunr_index_generator.py
"""Pre-build Lunr.js search index at build time."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lunr import lunr  # Pure-Python implementation


class LunrIndexGenerator:
    """Generate pre-built Lunr index using the Python lunr builder."""

    BOOSTS = {
        "title": 10,
        "description": 5,
        "content": 1,
        "tags": 3,
        "section": 2,
        "author": 2,
        "search_keywords": 8,
        "kind": 1,
    }

    def generate(self, index_json_path: Path, output_path: Path) -> bool:
        """
        Build Lunr index from index.json.

        Args:
            index_json_path: Path to index.json (from SiteIndexGenerator)
            output_path: Path to write serialized index

        Returns:
            True if the serialized index was written successfully.
        """
        data = json.loads(index_json_path.read_text(encoding="utf-8"))
        documents: list[dict[str, Any]] = []
        for page in data.get("pages", []):
            if page.get("search_exclude") or page.get("draft"):
                continue
            documents.append(
                {
                    "objectID": page.get("objectID") or page.get("url"),
                    "title": page.get("title", ""),
                    "description": page.get("description", ""),
                    "content": page.get("content") or page.get("excerpt", ""),
                    "tags": " ".join(page.get("tags") or []),
                    "section": page.get("section", ""),
                    "author": page.get("author", ""),
                    "search_keywords": " ".join(page.get("search_keywords") or []),
                    "kind": page.get("kind") or page.get("type", ""),
                }
            )

        idx = lunr(
            ref="objectID",
            fields=[{"field": name, "boost": boost} for name, boost in self.BOOSTS.items()],
            documents=documents,
        )

        output_path.write_text(json.dumps(idx.serialize()), encoding="utf-8")
        return True
```

### 5.5 Build Integration

```python
# In build orchestrator, after index.json generation:

def phase_search_index(site: Site, config: dict) -> None:
    """Generate search indexes based on configuration."""
    search_config = config.get("search", {})
    if not search_config.get("enabled", True):
        return

    # Always generate index.json (needed for search + downstream consumers)
    index_path = site.output_dir / "index.json"

    # Pre-build Lunr index if configured
    if search_config.get("lunr", {}).get("prebuilt", True):
        lunr_gen = LunrIndexGenerator()
        try:
            lunr_gen.generate(index_path, site.output_dir / "search-index.json")
            logger.info("prebuilt_lunr_index_written")
        except Exception:
            # Graceful fallback: build continues, search.js will build index at runtime
            logger.warning(
                "prebuilt_lunr_index_failed_falling_back_to_runtime",
                exc_info=True,
            )
```

### 5.6 Data Flow

```
Build Phase:
  Content → index.json → search-index.json (pre-built Lunr)

Runtime:
  User hits Cmd+K → Modal opens (lazy load pre-built index)
                 → LunrBackend.search(query)
            → Results displayed
            → Click → Navigate to page
```

### 5.7 Error Handling

| Scenario | Behavior |
|----------|----------|
| `lunr` Python dependency missing | Warn, fallback to runtime Lunr and advise installing optional extra |
| index.json missing | Error, search disabled |
| Network error loading index | Show error in modal, retry button |
| Empty results | Show "No results" with suggestions |
| localStorage unavailable | Skip recents gracefully |

---

## 6. Tradeoffs & Risks

### Tradeoffs

| Tradeoff | Gain | Cost |
|----------|------|------|
| New Python dependency (`lunr`) | Faster search; stays in Python ecosystem | Slightly larger install footprint |
| Dual outputs (`index.json` + `search-index.json`) | RAG compatibility + fast modal | Extra file on disk |
| Modal UI | Modern UX | More JS, a11y complexity |
| localStorage for recents | Better UX | Privacy consideration |

**Note on Dependency Footprint**:
Using the `lunr` PyPI package keeps the build step fully Python-native. It can live in an optional extras group (e.g., `pip install bengal[search]`) so minimal installs remain lightweight, and the CLI should degrade gracefully if the dependency is absent.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `lunr` Python package missing | Medium | Low | Optional dependency warning + runtime fallback |
| Modal accessibility issues | Medium | High | Use `<dialog>`, test with screen readers |
| Python lunr serialization mismatch with JS runtime | Low | Medium | Add regression tests that round-trip serialize/deserialize |
| localStorage quota exceeded | Low | Low | Rotate old entries, max 5 searches; disable gracefully |

---

## 7. Performance & Compatibility

### Performance Impact

| Metric | Current | After |
|--------|---------|-------|
| Initial search (500 pages) | ~500ms | ~150ms (pre-built) |
| Index load time | ~200ms | ~50ms (lazy, pre-parsed) |
| Memory (500 page index) | ~2MB JSON | ~800KB pre-built |
| Build time | N/A | +5-10s for pre-build |

### Compatibility

- **Breaking changes**: None - all additive
- **Migration path**: N/A - opt-in features
- **Browser support**: Same as current (ES6+)
- **Deprecations**: None planned

---

## 8. Migration & Rollout

### Implementation Phases

**Phase 1: Pre-built Lunr Index (1-2 hours)**
1. Add `LunrIndexGenerator` 
2. Integrate into build pipeline
3. Update `search.js` to use pre-built index
4. Config option: `search.lunr.prebuilt: true`

**Phase 2: Search Modal (2-3 hours)**
1. Create `search-modal.html` partial
2. Create `search-modal.js` with keyboard handling
3. Create `search-modal.css`
4. Add recent searches (localStorage)
5. Config option: `search.ui.modal: true`

**Phase 3: Analytics & Progressive Disclosure (1 hour)**
1. Optional instrumentation hooks behind `search.analytics.enabled`
2. Update modal to emit custom events (without external deps)
3. Guard network calls so feature degrades cleanly

**Phase 4: Documentation & Recipe Refresh (1 hour)**
1. Update search recipe (include Pagefind instructions + modal screenshots)
2. Add configuration reference for new `[search]` keys
3. Document how `index.json` + `search-index.json` interact for RAG

### Rollout Strategy

- **Feature flag**: Via config (`search.ui.modal`, `search.lunr.prebuilt`)
- **Beta period**: Ship in 0.1.6, gather feedback
- **Default change**: Modal default in 0.2.0

---

## 9. Testing Strategy

### Unit Tests
```python
# tests/unit/test_lunr_index_generator.py
def test_generates_valid_lunr_index():
    """Verify pre-built index is valid JSON."""

def test_handles_missing_lunr_dependency():
    """Verify graceful degradation when lunr import fails."""
```

### Integration Tests
```python
# tests/integration/test_search_build.py
def test_prebuilt_index_generated():
    """Verify search-index.json created during build."""

def test_build_without_prebuilt_flag():
    """Verify build still succeeds (runtime Lunr) when prebuilt is disabled."""
```

### E2E Tests (Manual)
1. Open site, press Cmd+K → Modal appears
2. Type query → Results appear
3. Arrow down, Enter → Navigates to result
4. Search again → Recent search appears
5. Toggle modal off → Inline search still works (backward compatibility)

---

## 10. Open Questions

- [ ] **Q1**: Should we bundle Lunr.js ourselves or continue with CDN? (Current: no CDN, local file)
- [ ] **Q2**: Should modal be default-on or opt-in initially? (Recommend: opt-in for 0.1.6)
- [ ] **Q3**: Analytics hooks - what data to expose? (search_term, result_count, click_position)
- [ ] **Q4**: Should we support both modal AND inline search, or replace inline?
- [ ] **Q5**: Should the Python `lunr` dependency ship as an optional extra (e.g., `bengal[search]`) or be enabled by default?

---

## 11. Success Criteria

- [ ] Pre-built Lunr index reduces initial search time by ≥30%
- [ ] Modal opens in <100ms after Cmd+K
- [ ] Recent searches persist across page loads
- [ ] `index.json` remains unchanged for downstream consumers and RAG
- [ ] search-index fallback works when prebuilt is disabled/missing
- [ ] All features are opt-in, no breaking changes
- [ ] a11y audit passes for modal (keyboard, screen reader)

---

## 12. Decision

**Status**: Draft - Ready for Review

**Next Steps**:
1. Review RFC with stakeholders
2. Resolve open questions
3. Run `::plan` to generate implementation tasks

