# RFC: Versioning UX Improvements

**Status**: Draft  
**Created**: 2025-12-20  
**Subsystem**: core/version, rendering/templates, postprocess  

---

## Problem Statement

When a user toggles to a previous version and that specific page doesn't exist in the target version, they get a 404 error. This creates a poor user experience.

**Current behavior**:
1. User is on `/docs/content/versioning/folder-mode/` (v2)
2. User selects "v1" from version dropdown
3. JavaScript constructs `/docs/v1/content/versioning/folder-mode/`
4. Browser navigates → 404 (page doesn't exist in v1)

**Expected behavior**:
1. User is on `/docs/content/versioning/folder-mode/` (v2)
2. User selects "v1" from version dropdown
3. System detects target page doesn't exist
4. System falls back to closest match:
   - `/docs/v1/content/versioning/` (section index), OR
   - `/docs/v1/` (version root)
5. User lands on valid page with helpful context

### Secondary Issue: Ordering/Nesting Validation

The current v1 test fixture (`site/content/_versions/v1/`) is minimal (only 3 pages) and doesn't adequately exercise:
- Weight-based ordering across versions
- Nested section hierarchy in versioned content
- Subsection filtering in navigation

---

## Evidence

### Current Implementation

**Version selector** (`version-selector.html:57-104`):
```javascript
function handleVersionChange(versionPrefix) {
  const currentPath = window.location.pathname;
  // ... URL construction logic ...

  // Navigate directly without validation
  window.location.href = newPath;  // ← Problem: no existence check
}
```

**URL construction** is correct, but there's no validation that the target exists.

### Version-aware navigation works correctly

`bengal/core/section.py:463-510` provides `pages_for_version()` and `subsections_for_version()` methods that properly filter content by version. Navigation sidebar already uses these.

---

## Goals

1. **Smart fallback on version switch**: When target page doesn't exist, navigate to the best available fallback
2. **Zero 404s from version switching**: All version switches land on valid pages
3. **Preserve user context**: Land as close to the original context as possible
4. **Static-site compatible**: Solution works without server-side logic
5. **Validate ordering/nesting**: Expand test fixtures to exercise full versioning behavior

### Non-Goals

- Cross-version content comparison
- Automatic content migration hints
- Server-side redirect support (out of scope for static hosting)

---

## Design Options

### Option A: Build-time Version Manifest (Recommended)

Generate a JSON manifest during build listing all pages per version. Embed manifest reference in template for client-side validation.

**Build output**:
```json
// public/_version-manifest.json
{
  "v2": [
    "/docs/",
    "/docs/get-started/",
    "/docs/content/versioning/",
    "/docs/content/versioning/folder-mode/"
  ],
  "v1": [
    "/docs/",
    "/docs/get-started/",
    "/docs/get-started/installation/"
  ]
}
```

**Template changes** (`version-selector.html`):
```javascript
// Fetch manifest once (cached by browser)
let versionManifest = null;

async function loadVersionManifest() {
  if (versionManifest) return versionManifest;
  const response = await fetch('/_version-manifest.json');
  versionManifest = await response.json();
  return versionManifest;
}

async function handleVersionChange(versionPrefix) {
  const manifest = await loadVersionManifest();
  const targetVersion = versionPrefix.replace('/', '') || 'latest';
  const versionPages = manifest[targetVersion] || [];

  // Construct target path
  let targetPath = constructTargetPath(versionPrefix);

  // Fallback cascade if target doesn't exist
  if (!versionPages.includes(targetPath)) {
    targetPath = findBestFallback(targetPath, versionPages);
  }

  window.location.href = targetPath;
}

function findBestFallback(targetPath, versionPages) {
  // 1. Try section index (parent)
  const parts = targetPath.split('/').filter(Boolean);
  while (parts.length > 1) {
    parts.pop();
    const parentPath = '/' + parts.join('/') + '/';
    if (versionPages.includes(parentPath)) {
      return parentPath;
    }
  }

  // 2. Fall back to version root (first versioned section)
  return versionPages[0] || '/';
}
```

**Pros**:
- ✅ Works with static hosting
- ✅ No visible delay (manifest cached)
- ✅ Simple fallback logic
- ✅ Build-time validated

**Cons**:
- ❌ Extra file in output (`_version-manifest.json`)
- ❌ Manifest can grow large for huge sites (mitigated: paths only, no metadata)

**Estimated size**: ~10KB for 1000 pages (acceptable)

---

### Option B: Client-side HEAD Request

Before navigating, use `fetch()` with HEAD method to check if target URL exists.

```javascript
async function handleVersionChange(versionPrefix) {
  const targetPath = constructTargetPath(versionPrefix);

  try {
    const response = await fetch(targetPath, { method: 'HEAD' });
    if (response.ok) {
      window.location.href = targetPath;
      return;
    }
  } catch (e) { }

  // Fallback cascade
  const fallbackPath = await findFallbackWithHEAD(targetPath, versionPrefix);
  window.location.href = fallbackPath;
}
```

**Pros**:
- ✅ No build-time changes
- ✅ Always accurate (real-time check)

**Cons**:
- ❌ Network latency on each switch (visible delay)
- ❌ Multiple HEAD requests for fallback cascade
- ❌ May fail on some static hosts (CORS)
- ❌ Poor UX: loading indicator needed

---

### Option C: Inline Manifest per Page

Embed the current version's page list in each page's HTML.

```html
<script>
  const currentVersionPages = {{ version_pages | tojson }};
</script>
```

**Pros**:
- ✅ Instant lookup (already loaded)
- ✅ No extra request

**Cons**:
- ❌ Increases HTML size of every page
- ❌ Need to know ALL other versions' pages (not just current)
- ❌ Duplicated data across all pages

---

## Recommendation

**Option A (Build-time Version Manifest)** provides the best balance of UX and implementation simplicity:

1. Single JSON file generated during build
2. Fetched once and cached by browser
3. Enables instant client-side validation
4. Works with any static host

---

## Implementation Plan

### Phase 1: Version Manifest Generation

1. Create `bengal/postprocess/version_manifest.py`:
   - `VersionManifestGenerator` class
   - Collect all page URLs grouped by version
   - Write `_version-manifest.json` to output directory

2. Wire into build pipeline (`bengal/orchestration/build_orchestrator.py`):
   - Call manifest generator after page rendering
   - Only generate if versioning is enabled

### Phase 2: Smart Version Selector

1. Update `bengal/themes/default/templates/partials/version-selector.html`:
   - Add manifest loading and caching
   - Implement fallback cascade logic
   - Add loading indicator during manifest fetch (first time only)

2. Add user feedback:
   - Toast/banner when landing on fallback page
   - "This page doesn't exist in {version}. Showing the closest match."

### Phase 3: Expand Test Fixtures

1. Expand `site/content/_versions/v1/`:
   - Add more nested sections matching v2 structure
   - Include weight-based ordering examples
   - Create pages that DON'T exist in v2 (to test both directions)

2. Update `tests/roots/test-versioned/`:
   - Add explicit ordering tests
   - Add pages with different weights per version
   - Add subsection nesting tests

### Phase 4: Integration Tests

1. Add tests for manifest generation:
   - Verify all versioned pages included
   - Verify format is correct
   - Verify manifest updates on incremental builds

2. Add e2e tests for version switching:
   - Test fallback cascade
   - Test both directions (latest→old, old→latest)
   - Test deeply nested pages

---

## Files Changed

| File | Change |
|------|--------|
| `bengal/postprocess/version_manifest.py` | NEW: Manifest generator |
| `bengal/orchestration/build_orchestrator.py` | Wire manifest generation |
| `bengal/themes/default/templates/partials/version-selector.html` | Smart fallback logic |
| `site/content/_versions/v1/` | Expand test content |
| `tests/roots/test-versioned/` | Expand test fixture |
| `tests/unit/test_version_manifest.py` | NEW: Unit tests |
| `tests/integration/test_versioning_ux.py` | NEW: Integration tests |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Large manifest for huge sites | Performance | Paginate or compress if >100KB |
| Manifest not cached | Extra request | Use proper cache headers, service worker |
| JavaScript disabled | No fallback | Acceptable: 404 behavior unchanged |

---

## Success Criteria

- [ ] Version switching never results in 404 (when target version has any content)
- [ ] Fallback lands on logical page (section index > version root)
- [ ] User sees feedback when landing on fallback
- [ ] Manifest size <50KB for 5000 page site
- [ ] Ordering/nesting works correctly across versions

---

## Open Questions

1. **Fallback message UX**: Toast, banner, or inline message?
2. **Manifest caching strategy**: How long? Service worker?
3. **Very large sites**: Should we split manifest by section?

---

## References

- `bengal/themes/default/templates/partials/version-selector.html` - Current implementation
- `bengal/core/version.py` - Version model
- `bengal/core/section.py:463-510` - Version-aware section methods
- `site/content/docs/content/versioning/` - User documentation
