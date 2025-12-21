# RFC: Version-Scoped Search Indexes

**Status**: Draft  
**Created**: 2025-12-20  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P2 (Medium)  
**Depends On**: rfc-versioned-documentation.md (implemented)

---

## Problem Statement

Bengal generates a single `index.json` containing all pages from all versions. When searching on a versioned page (e.g., `/docs/v1/guide/`), users see results from ALL versions mixed together.

**Current**: Search on v1 → results from v1, v2, v3 (confusing)  
**Desired**: Search on v1 → results from v1 only

---

## Goals

1. **Version-scoped search** - Results match current version
2. **Backward compatible** - Sites without versioning unchanged
3. **Smaller indexes** - Faster load per version

## Non-Goals

- Cross-version search toggle (YAGNI - navigate to other version instead)
- Version-aware autocomplete

---

## Design

Generate per-version index files:

```
public/
├── index.json           # Latest version only
└── docs/
    └── v1/
        └── index.json   # v1 pages only
```

Frontend detects version from URL and loads appropriate index.

---

## Implementation

### Task 1: Add version field to index entries

`bengal/postprocess/output_formats/index_generator.py`

```python
def page_to_summary(self, page: Page) -> dict[str, Any]:
    summary = { ... }

    # Add version if available
    if page.version:
        summary["version"] = page.version

    return summary
```

**Evidence**: `Page.version` exists at `bengal/core/page/__init__.py:184`

### Task 2: Group pages by version in generator

```python
def _group_by_version(self, pages: list[Page]) -> dict[str | None, list[Page]]:
    """Group pages by version ID."""
    by_version: dict[str | None, list[Page]] = {}
    for page in pages:
        version = getattr(page, 'version', None)
        by_version.setdefault(version, []).append(page)
    return by_version
```

### Task 3: Generate per-version indexes

```python
def generate(self, pages: list[Page]) -> list[Path]:
    if not self._versioning_enabled():
        return [self._generate_single_index(pages)]

    generated = []
    by_version = self._group_by_version(pages)

    for version_id, version_pages in by_version.items():
        path = self._generate_version_index(version_id, version_pages)
        generated.append(path)

    return generated

def _generate_version_index(self, version_id: str | None, pages: list[Page]) -> Path:
    """Generate index for a specific version."""
    if version_id is None or self._is_latest_version(version_id):
        # Latest version: output_dir/index.json
        output_path = self.site.output_dir / "index.json"
    else:
        # Older version: output_dir/docs/v1/index.json
        output_path = self.site.output_dir / "docs" / version_id / "index.json"

    self._write_index(output_path, pages)
    return output_path
```

### Task 4: Extend LunrIndexGenerator for per-version pre-built indexes

Generate `search-index.json` per version alongside `index.json`.

### Task 5: Frontend version detection

`bengal/themes/default/assets/js/core/search.js`

```javascript
function detectCurrentVersion() {
    // Check meta tag first (authoritative)
    const meta = document.querySelector('meta[name="bengal:version"]');
    if (meta) return meta.getAttribute('content');

    // Fallback: parse URL
    const match = window.location.pathname.match(/\/docs\/(v\d+)\//);
    return match ? match[1] : null;
}

function buildVersionedIndexUrl(baseurl) {
    const version = detectCurrentVersion();

    if (!version) {
        return buildIndexUrl('index.json', baseurl);
    }

    // Version-specific: /docs/v1/index.json
    return buildIndexUrl(`docs/${version}/index.json`, baseurl);
}
```

### Task 6: Emit version meta tag in templates

`bengal/themes/default/templates/base.html`

```html
{% if page.version %}
<meta name="bengal:version" content="{{ page.version }}">
{% endif %}
```

---

## File Changes

| File | Change |
|------|--------|
| `bengal/postprocess/output_formats/index_generator.py` | Add version field, per-version generation |
| `bengal/postprocess/output_formats/lunr_index_generator.py` | Per-version pre-built indexes |
| `bengal/themes/default/assets/js/core/search.js` | Version detection, versioned index URL |
| `bengal/themes/default/templates/base.html` | Emit `bengal:version` meta tag |

---

## Testing

```python
def test_index_includes_version_field():
    page = make_page(version="v1")
    summary = generator.page_to_summary(page)
    assert summary.get("version") == "v1"

def test_generates_per_version_indexes():
    pages = [make_page(version="v1"), make_page(version="v2")]
    paths = generator.generate(pages)
    assert (output_dir / "index.json").exists()  # latest/v2
    assert (output_dir / "docs/v1/index.json").exists()

def test_version_detection_from_url():
    # Mock URL: /docs/v1/guide/
    version = detectCurrentVersion()
    assert version == "v1"
```

---

## Timeline

| Task | Effort |
|------|--------|
| Add version field to entries | 30 min |
| Group pages by version | 30 min |
| Generate per-version indexes | 1 hour |
| Extend LunrIndexGenerator | 1 hour |
| Frontend version detection | 1 hour |
| Emit version meta tag | 15 min |
| Unit tests | 1 hour |
| Integration test | 30 min |

**Total**: ~6 hours
