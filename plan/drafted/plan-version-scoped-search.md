# Plan: Version-Scoped Search Indexes

**RFC**: rfc-version-scoped-search.md  
**Status**: Ready  
**Estimated**: 6 hours  
**Priority**: P2

---

## Phase 1: Index Generator (Backend)

### 1.1 Add version field to page summaries

**File**: `bengal/postprocess/output_formats/index_generator.py`  
**Method**: `page_to_summary()`

```python
# After line ~250 (isAutodoc block)
if page.version:
    summary["version"] = page.version
```

**Commit**: `postprocess: add version field to search index page entries`

---

### 1.2 Add version grouping helper

**File**: `bengal/postprocess/output_formats/index_generator.py`  
**Add method** to `SiteIndexGenerator`:

```python
def _group_by_version(self, pages: list[Page]) -> dict[str | None, list[Page]]:
    """Group pages by version ID (None for unversioned)."""
    by_version: dict[str | None, list[Page]] = {}
    for page in pages:
        version = getattr(page, 'version', None)
        by_version.setdefault(version, []).append(page)
    return by_version

def _is_latest_version(self, version_id: str) -> bool:
    """Check if version_id is the latest version."""
    if not hasattr(self.site, 'version_config') or not self.site.version_config:
        return True
    version = self.site.version_config.get_version(version_id)
    return version is not None and version.latest
```

**Commit**: `postprocess: add version grouping helpers to SiteIndexGenerator`

---

### 1.3 Refactor generate() for per-version output

**File**: `bengal/postprocess/output_formats/index_generator.py`  
**Modify**: `generate()` method

- If versioning disabled: single index (current behavior)
- If versioning enabled: generate per-version indexes

```python
def generate(self, pages: list[Page]) -> Path | list[Path]:
    # Check if versioning is enabled
    versioning_enabled = getattr(self.site, 'versioning_enabled', False)

    if not versioning_enabled:
        # Single index (unchanged behavior)
        return self._generate_single_index(pages)

    # Per-version indexes
    generated = []
    by_version = self._group_by_version(pages)

    for version_id, version_pages in by_version.items():
        path = self._generate_version_index(version_id, version_pages)
        generated.append(path)

    return generated

def _generate_single_index(self, pages: list[Page]) -> Path:
    """Generate single index.json (original behavior)."""
    # Move existing generate() logic here
    ...

def _generate_version_index(self, version_id: str | None, pages: list[Page]) -> Path:
    """Generate index for specific version."""
    # Determine output path
    if version_id is None or self._is_latest_version(version_id):
        index_path = self._get_index_path()  # existing logic
    else:
        # Versioned path: docs/v1/index.json
        index_path = self.site.output_dir / "docs" / version_id / "index.json"
        index_path.parent.mkdir(parents=True, exist_ok=True)

    # Build and write index
    site_data = self._build_index_data(pages)
    self._write_if_changed(index_path, json.dumps(site_data, ...))
    return index_path
```

**Commit**: `postprocess: generate per-version search indexes when versioning enabled`

---

### 1.4 Update OutputFormatsGenerator to handle list return

**File**: `bengal/postprocess/output_formats/__init__.py`  
**Modify**: Lines ~234-242

Handle both single Path and list[Path] return from `index_gen.generate()`.

**Commit**: `postprocess: handle per-version index paths in OutputFormatsGenerator`

---

## Phase 2: Lunr Pre-built Indexes

### 2.1 Extend LunrIndexGenerator for per-version

**File**: `bengal/postprocess/output_formats/lunr_index_generator.py`

Modify to accept version-specific index path and generate matching `search-index.json`.

```python
def generate(self, index_path: Path) -> Path | None:
    """Generate pre-built Lunr index alongside index.json."""
    # Determine output path relative to index_path
    search_index_path = index_path.parent / "search-index.json"
    ...
```

**Commit**: `postprocess: generate per-version pre-built Lunr indexes`

---

### 2.2 Update OutputFormatsGenerator to generate per-version Lunr

**File**: `bengal/postprocess/output_formats/__init__.py`  

Loop over generated index paths and create Lunr index for each.

**Commit**: `postprocess: generate Lunr indexes for each version`

---

## Phase 3: Frontend (Theme)

### 3.1 Add version meta tag to base template

**File**: `bengal/themes/default/templates/base.html`  
**Location**: In `<head>` section near other bengal meta tags

```html
{% if page.version %}
<meta name="bengal:version" content="{{ page.version }}">
{% endif %}
```

**Commit**: `theme: emit bengal:version meta tag for versioned pages`

---

### 3.2 Add version detection to search.js

**File**: `bengal/themes/default/assets/js/core/search.js`  
**Location**: After `resolveBaseUrl()` function (~line 99)

```javascript
/**
 * Detect current version from meta tag or URL
 */
function detectCurrentVersion() {
    // Meta tag (authoritative)
    const meta = document.querySelector('meta[name="bengal:version"]');
    if (meta) {
        return meta.getAttribute('content');
    }

    // Fallback: parse URL pattern /docs/v1/...
    const match = window.location.pathname.match(/\/docs\/(v\d+)\//);
    return match ? match[1] : null;
}
```

**Commit**: `theme(search): add version detection from meta tag and URL`

---

### 3.3 Modify index URL building for versions

**File**: `bengal/themes/default/assets/js/core/search.js`  
**Modify**: `loadSearchIndex()` and related functions

```javascript
function buildVersionedIndexUrl(baseurl) {
    const version = detectCurrentVersion();

    if (!version) {
        // Unversioned or latest
        return buildIndexUrl('index.json', baseurl);
    }

    // Version-specific: /docs/v1/index.json
    return buildIndexUrl(`docs/${version}/index.json`, baseurl);
}

// In loadSearchIndex():
const indexUrl = buildVersionedIndexUrl(baseurl);
```

**Commit**: `theme(search): load version-specific search index`

---

### 3.4 Update pre-built index URL for versions

**File**: `bengal/themes/default/assets/js/core/search.js`  
**Modify**: `tryLoadPrebuiltIndex()`

Check for version-specific `search-index.json` path.

**Commit**: `theme(search): load version-specific pre-built Lunr index`

---

## Phase 4: Testing

### 4.1 Unit test: version field in summary

**File**: `tests/unit/postprocess/test_output_formats_index_json.py`

```python
def test_page_summary_includes_version():
    """Version field added to page entries."""
    page = make_page(version="v1")
    generator = SiteIndexGenerator(site)
    summary = generator.page_to_summary(page)
    assert summary.get("version") == "v1"

def test_page_summary_omits_version_when_none():
    """Version field omitted when page has no version."""
    page = make_page(version=None)
    summary = generator.page_to_summary(page)
    assert "version" not in summary
```

**Commit**: `tests: add version field unit tests for index generator`

---

### 4.2 Unit test: version grouping

**File**: `tests/unit/postprocess/test_output_formats_index_json.py`

```python
def test_group_by_version():
    """Pages grouped correctly by version."""
    pages = [
        make_page(version="v1", title="A"),
        make_page(version="v2", title="B"),
        make_page(version="v1", title="C"),
        make_page(version=None, title="D"),
    ]
    by_version = generator._group_by_version(pages)
    assert len(by_version["v1"]) == 2
    assert len(by_version["v2"]) == 1
    assert len(by_version[None]) == 1
```

**Commit**: `tests: add version grouping unit tests`

---

### 4.3 Integration test: versioned site build

**File**: `tests/integration/test_versioned_search.py` (new)

```python
def test_versioned_site_generates_scoped_indexes():
    """Full build with versioning generates per-version indexes."""
    site = build_versioned_site()

    # Latest version at root
    assert (site.output_dir / "index.json").exists()

    # v1 version in subdirectory
    assert (site.output_dir / "docs/v1/index.json").exists()

    # Verify content separation
    latest = json.loads((site.output_dir / "index.json").read_text())
    v1 = json.loads((site.output_dir / "docs/v1/index.json").read_text())

    # No v1 pages in latest
    assert all(p.get("version") != "v1" for p in latest["pages"])
    # Only v1 pages in v1 index
    assert all(p.get("version") == "v1" for p in v1["pages"])
```

**Commit**: `tests: add integration test for versioned search indexes`

---

## Summary

| Phase | Tasks | Effort |
|-------|-------|--------|
| 1. Index Generator | 1.1-1.4 | 2 hours |
| 2. Lunr Indexes | 2.1-2.2 | 1 hour |
| 3. Frontend | 3.1-3.4 | 1.5 hours |
| 4. Testing | 4.1-4.3 | 1.5 hours |

**Total**: ~6 hours

---

## Verification Checklist

- [ ] `bengal build` on versioned site generates per-version `index.json`
- [ ] Each version's index only contains pages from that version
- [ ] Pre-built Lunr indexes generated per version
- [ ] Frontend loads correct index based on current URL
- [ ] Sites without versioning work unchanged
- [ ] All existing tests pass
- [ ] New tests pass
