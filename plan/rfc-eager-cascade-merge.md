# RFC: Eager Cascade Merge

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2026-01-30  
**Related**: CascadeSnapshot Migration, Template Selection Bug

## Summary

Replace Bengal's late-binding cascade resolution with an eager merge strategy. After building `CascadeSnapshot`, merge resolved cascade values directly into each page's metadata. This eliminates the duality between `page.metadata.get("type")` and `page.type`, creating a single source of truth.

## Problem

### Current Architecture

Bengal's cascade system has two access patterns:

```python
# Pattern 1: Direct metadata access (bypasses cascade)
page_type = page.metadata.get("type")  # Returns None if not in frontmatter

# Pattern 2: Property access (resolves cascade)
page_type = page.type  # Resolves from CascadeSnapshot
```

Every code path must know which pattern to use. This caused a subtle bug where template selection used Pattern 1, resulting in wrong templates being selected for pages that rely on cascaded `type` values.

### The Bug

```
docs/_index.md:     cascade: { type: doc }
docs/about/_index.md:  (no type in frontmatter, relies on cascade)

Template selection:  page.metadata.get("type") → None → wrong template
Body tag rendering:  page.type → "doc" → correct attribute
```

The page rendered with `<body data-type="doc">` but used the wrong template because template selection didn't use cascade-aware access.

### Root Cause

Late binding creates a **knowledge burden** on developers. They must remember:
- Which keys are cascadable
- Which accessor to use for each situation
- That `metadata.get()` and property access return different values

This is a class of bugs waiting to happen.

## Proposal

### Eager Merge Strategy

After building `CascadeSnapshot`, immediately merge resolved cascade values into each page's metadata:

```
┌─────────────────────────────────────────────────────────────────┐
│                     CURRENT (Late Binding)                       │
├─────────────────────────────────────────────────────────────────┤
│  Discovery → Snapshot → Render (resolve on each property access) │
│                              ↓                                   │
│                     page.type resolves cascade                   │
│                     page.metadata.get() bypasses                 │
│                     TWO SOURCES OF TRUTH                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     PROPOSED (Eager Merge)                       │
├─────────────────────────────────────────────────────────────────┤
│  Discovery → Snapshot → Apply to Pages → Render                  │
│                              ↓                                   │
│                     Cascade values merged into metadata          │
│                     page.type reads from metadata                │
│                     page.metadata.get() returns same value       │
│                     ONE SOURCE OF TRUTH                          │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Frontmatter wins**: Explicit values in frontmatter override cascade
2. **Apply once**: Merge happens once after snapshot build, not on every access
3. **Track origin**: Record which keys came from cascade (for debugging/provenance)
4. **Keep snapshot**: `CascadeSnapshot` remains for incremental build invalidation

## Design

### New Method: `CascadeSnapshot.apply_to_page()`

```python
def apply_to_page(self, page: Page, content_dir: Path) -> set[str]:
    """
    Merge resolved cascade values into page's metadata.

    Args:
        page: Page to apply cascade to
        content_dir: Content directory root (for section path calculation)

    Returns:
        Set of keys that were added from cascade (not overwritten).

    Behavior:
        - Frontmatter values take precedence over cascade
        - Only keys defined in ancestor cascade blocks are considered
        - Tracks which keys came from cascade via _cascade_keys metadata
    """
    section_path = self._get_section_path(page, content_dir)
    applied_keys: set[str] = set()

    # Get all keys that could be cascaded to this section
    for key in self.get_cascade_keys(section_path):
        if key not in page.metadata:  # Frontmatter wins
            value = self.resolve(section_path, key)
            if value is not None:
                page.metadata[key] = value
                applied_keys.add(key)

    # Track origin for debugging and provenance
    existing_cascade_keys = page.metadata.get("_cascade_keys", [])
    page.metadata["_cascade_keys"] = list(set(existing_cascade_keys) | applied_keys)

    return applied_keys
```

### New Method: `CascadeSnapshot.get_cascade_keys()`

```python
def get_cascade_keys(self, section_path: str) -> set[str]:
    """
    Get all keys that could be cascaded to a section path.

    Walks up the section hierarchy collecting all cascade keys.
    """
    keys: set[str] = set()
    current = section_path

    while current:
        if current in self._data:
            keys.update(self._data[current].keys())
        # Move to parent
        if "/" in current:
            current = current.rsplit("/", 1)[0]
        elif current:
            current = ""
        else:
            break

    # Also check root
    if "" in self._data:
        keys.update(self._data[""].keys())

    return keys
```

### Integration Point: `ContentOrchestrator.apply_cascades()`

```python
def apply_cascades(self, site: Site) -> None:
    """Build cascade snapshot and apply to all pages."""
    # Build immutable snapshot (existing)
    site.build_cascade_snapshot()

    # NEW: Apply cascade values to all pages
    content_dir = site.root_path / "content"
    applied_count = 0

    for page in site.pages.values():
        keys = site.cascade.apply_to_page(page, content_dir)
        if keys:
            applied_count += 1

    logger.info(
        "cascade_applied",
        total_pages=len(site.pages),
        pages_with_cascade=applied_count,
    )
```

### Simplified Page Properties

After eager merge, properties become simple metadata lookups:

```python
# Before (complex late binding)
@property
def type(self) -> str | None:
    if "type" in self.metadata:
        cascade_keys = self.metadata.get("_cascade_keys", [])
        if "type" not in cascade_keys:
            return self.metadata.get("type")

    if self._site and self._section:
        try:
            content_dir = self._site.root_path / "content"
            section_path = str(self._section.path.relative_to(content_dir))
            cascade_value = self._site.cascade.resolve(section_path, "type")
            if cascade_value is not None:
                return cascade_value
        except (ValueError, AttributeError):
            pass

    if self.core is not None and self.core.type:
        return self.core.type

    return self.metadata.get("type")

# After (simple lookup)
@property
def type(self) -> str | None:
    """Get page type (from frontmatter or cascade, already merged)."""
    return self.metadata.get("type")
```

### PageProxy Handling

PageProxy objects need cascade applied when created during incremental builds:

```python
class PageProxy:
    def __init__(self, core: PageCore, site: Site):
        self._core = core
        self._site = site
        self._metadata: dict[str, Any] | None = None

        # Apply cascade immediately if snapshot available
        if site.cascade:
            self._apply_cascade()

    def _apply_cascade(self) -> None:
        """Merge cascade values into proxy metadata."""
        if self._metadata is None:
            self._metadata = dict(self._core.metadata or {})

        content_dir = self._site.root_path / "content"
        self._site.cascade.apply_to_page(self, content_dir)
```

## Incremental Builds

### How It Works Today

1. Provenance filter tracks cascade sources for each page
2. When cascade source changes, hash mismatch triggers rebuild
3. Page is re-rendered with fresh cascade values

### How It Works With Eager Merge

1. Provenance filter tracks cascade sources (unchanged)
2. When cascade source changes, hash mismatch triggers rebuild
3. During rebuild:
   - Page is re-created or loaded from cache
   - `apply_to_page()` is called with fresh snapshot
   - Metadata reflects new cascade values
4. Page is re-rendered

The key insight: **cascade application happens per-page**, so incremental builds naturally get fresh values when pages are rebuilt.

## Migration Path

### Phase 1: Add Eager Merge (Non-Breaking)

1. Add `apply_to_page()` and `get_cascade_keys()` to `CascadeSnapshot`
2. Call `apply_to_page()` after building snapshot
3. Keep existing late-binding properties (they now return same value)
4. Add tests to verify both patterns return same value

### Phase 2: Simplify Properties

1. Simplify `type`, `variant`, `layout` properties to just read metadata
2. Remove `_resolve_cascade_from_snapshot()` method
3. Remove `_resolve_cascade_from_sections()` fallback
4. Update PageProxy to use same pattern

### Phase 3: Cleanup

1. Remove the template selection fix (now unnecessary)
2. Remove any other code that was working around the duality
3. Update documentation

## Files to Modify

| File | Change |
|------|--------|
| `bengal/core/cascade_snapshot.py` | Add `apply_to_page()`, `get_cascade_keys()` |
| `bengal/orchestration/content.py` | Call apply after snapshot build |
| `bengal/core/page/metadata.py` | Simplify `type`/`variant` properties |
| `bengal/core/page/proxy.py` | Apply cascade on creation, simplify properties |
| `bengal/rendering/renderer.py` | Revert template selection fix (optional) |

## Testing Strategy

### Unit Tests

```python
def test_apply_to_page_merges_cascade():
    """Cascade values are merged into page metadata."""
    snapshot = CascadeSnapshot({"docs": {"type": "doc"}})
    page = create_test_page(section="docs", metadata={})

    snapshot.apply_to_page(page, content_dir)

    assert page.metadata.get("type") == "doc"
    assert "_cascade_keys" in page.metadata
    assert "type" in page.metadata["_cascade_keys"]

def test_frontmatter_wins_over_cascade():
    """Explicit frontmatter values override cascade."""
    snapshot = CascadeSnapshot({"docs": {"type": "doc"}})
    page = create_test_page(section="docs", metadata={"type": "custom"})

    snapshot.apply_to_page(page, content_dir)

    assert page.metadata.get("type") == "custom"
    assert "type" not in page.metadata.get("_cascade_keys", [])

def test_metadata_get_and_property_return_same():
    """Both access patterns return the same value after merge."""
    snapshot = CascadeSnapshot({"docs": {"type": "doc"}})
    page = create_test_page(section="docs", metadata={})

    snapshot.apply_to_page(page, content_dir)

    assert page.metadata.get("type") == page.type
```

### Integration Tests

```python
def test_template_selection_uses_cascaded_type():
    """Template selection works with cascaded type values."""
    # Create site with cascade
    site = create_test_site(
        files={
            "docs/_index.md": "---\ncascade:\n  type: doc\n---",
            "docs/about/_index.md": "---\ntitle: About\n---",
        }
    )

    # Build
    site.discover_content()
    site.apply_cascades()

    # Verify template selection
    about_page = site.get_page("docs/about/_index.md")
    template = renderer._get_template_name(about_page)

    assert "doc" in template  # Should use doc template

def test_incremental_build_cascade_change():
    """Incremental build detects cascade changes."""
    # Full build
    site = create_test_site(...)
    build(site)

    # Modify cascade
    modify_file("docs/_index.md", cascade={"type": "tutorial"})

    # Incremental build
    pages_rebuilt = incremental_build(site)

    # Verify affected pages were rebuilt
    assert "docs/about/_index.md" in pages_rebuilt
    assert site.get_page("docs/about/_index.md").type == "tutorial"
```

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Performance: applying to all pages | O(n) single pass; cascade resolution is fast |
| Memory: storing cascade keys | Small overhead; list of strings per page |
| Breaking changes | Phase 1 is non-breaking; properties return same value |
| Proxy metadata consistency | Apply cascade immediately on proxy creation |

## Alternatives Considered

### 1. Keep Late Binding, Add Linting

Add a linter rule that warns when `metadata.get()` is used for cascadable keys.

**Rejected**: Doesn't eliminate the bug class; relies on developer discipline.

### 2. Make `metadata` Property Cascade-Aware

Override `metadata` to return a dict-like object that resolves cascade on access.

**Rejected**: Surprising behavior; hard to debug; performance overhead on every access.

### 3. Deprecate Direct Metadata Access

Add runtime warnings when accessing cascadable keys via `metadata.get()`.

**Rejected**: Too noisy; doesn't fix existing code; just delays the problem.

## Success Metrics

1. **Zero duality bugs**: `page.metadata.get("type")` and `page.type` always return the same value
2. **Simpler code**: Property implementations reduced from ~30 lines to ~2 lines
3. **No regression**: All existing tests pass
4. **Performance**: Build time not significantly impacted

## Timeline

- **Phase 1**: 1-2 hours (add methods, integrate, test)
- **Phase 2**: 1-2 hours (simplify properties, update proxy)
- **Phase 3**: 30 min (cleanup)

Total: ~4 hours

## Open Questions

1. Should we apply cascade to sections as well as pages?
2. Should `_cascade_keys` be exposed as a public property?
3. Should we emit a debug log when cascade overwrites a value?

## References

- Hugo's cascade implementation: https://gohugo.io/content-management/front-matter/#front-matter-cascade
- Original template selection bug fix: `renderer.py:742`
- CascadeSnapshot implementation: `bengal/core/cascade_snapshot.py`
