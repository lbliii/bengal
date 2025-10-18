# Cascade Changes Not Applied in Incremental Builds

## Status
**ANALYSIS COMPLETE** - Ready for implementation

## Problem

When using `bengal serve` (live server), changes to cascade metadata in section `_index.md` files do not propagate to all descendant pages. The user must stop the server and run a full `bengal build` to see the changes applied.

### Example Scenario
```yaml
# content/docs/_index.md
---
title: "Documentation"
cascade:
  type: docs  # Add or change this
  layout: doc-page
---
```

**Expected Behavior:** All pages under `content/docs/` should immediately inherit the new cascade values.

**Actual Behavior:** Only `_index.md` itself is rebuilt. Child pages keep their old metadata from cache.

## Root Cause

The incremental build system (`IncrementalOrchestrator`) only tracks direct file changes. When a page is modified, it rebuilds only that specific page. It does not understand cascade dependencies.

### Current Behavior in `find_work_early()`

```python
# bengal/orchestration/incremental.py, lines 177-189
for page in self.site.pages:
    if page.metadata.get("_generated"):
        continue

    if self.cache.is_changed(page.source_path):
        pages_to_rebuild.add(page.source_path)  # Only the changed page!
```

When `content/docs/_index.md` changes:
1. ✅ `_index.md` is marked for rebuild
2. ❌ `docs/page1.md`, `docs/page2.md`, etc. are NOT marked for rebuild
3. ❌ Cached versions of child pages still have old metadata
4. ❌ Cascade is applied during discovery, but pages aren't re-rendered

### Why Cascade is Applied But Not Visible

The cascade logic runs in `ContentOrchestrator._apply_cascades()`:
- It correctly updates `page.metadata` with cascade values
- BUT incremental rendering only rebuilds changed pages
- Child pages use cached HTML from previous build (before cascade change)
- Their in-memory metadata is correct, but output files are stale

## Solution

Detect cascade changes and mark all descendant pages for rebuild.

### Implementation Plan

**Location:** `bengal/orchestration/incremental.py` - `IncrementalOrchestrator.find_work_early()`

**After detecting changed pages, add cascade dependency tracking:**

```python
# NEW: Check for cascade changes and mark dependent pages
for page in list(pages_to_rebuild):  # Iterate over snapshot
    # Check if this is a section index with cascade
    if "_index" in page.source_path.stem or "index" in page.source_path.stem:
        # Find the section this page belongs to
        page_obj = next((p for p in self.site.pages if p.source_path == page), None)
        if page_obj and "cascade" in page_obj.metadata:
            # This is a section index with cascade - find all affected pages
            affected_pages = self._find_cascade_affected_pages(page_obj)
            pages_to_rebuild.update(affected_pages)
            if verbose:
                change_summary["Cascade changes"].append(
                    f"{page.name} cascade affects {len(affected_pages)} pages"
                )
```

**New helper method:**

```python
def _find_cascade_affected_pages(self, index_page: Page) -> set[Path]:
    """
    Find all pages affected by a cascade change in a section index.

    Args:
        index_page: Section _index.md page with cascade metadata

    Returns:
        Set of page source paths that should be rebuilt
    """
    affected = set()

    # Find the section that owns this index page
    for section in self.site.sections:
        if section.index_page == index_page:
            # Get all pages in this section and subsections recursively
            for page in section.regular_pages_recursive:
                # Don't add generated pages (they have virtual paths)
                if not page.metadata.get("_generated"):
                    affected.add(page.source_path)
            break

    return affected
```

### Edge Cases to Handle

1. **Root-level cascade** (from top-level pages): Affects ALL pages in site
   - Detect: Page not in any section + has cascade
   - Action: Mark all non-generated pages for rebuild

2. **Nested cascades**: Parent and child sections both have cascade
   - Current behavior: Child cascade overrides parent
   - Action: Changing either should mark all descendants for rebuild

3. **Cascade removal**: Deleting `cascade:` from front matter
   - The changed file is detected, descendants marked for rebuild
   - Works the same way as adding/changing cascade

4. **Performance**: Large sites with deep section hierarchies
   - Cost: O(sections × pages_per_section) = O(total_pages)
   - Acceptable: Only runs when _index.md actually changes
   - Alternative: Could cache section→pages mapping

## Testing Plan

### Unit Tests

```python
# tests/unit/orchestration/test_incremental_orchestrator.py

def test_cascade_change_marks_descendants_for_rebuild():
    """When section _index.md with cascade changes, mark all descendants."""

def test_root_cascade_marks_all_pages():
    """When top-level page with cascade changes, mark all pages."""

def test_nested_cascade_change():
    """When nested section cascade changes, mark its descendants only."""

def test_cascade_removal():
    """When cascade is removed from _index.md, descendants are rebuilt."""
```

### Manual Testing

1. Create site with section hierarchy:
   ```
   content/
     docs/
       _index.md  (with cascade)
       page1.md
       page2.md
       advanced/
         _index.md
         guide.md
   ```

2. Start `bengal serve`

3. Modify `docs/_index.md` cascade value

4. Verify all pages in `docs/` are rebuilt (check terminal output)

5. Verify browser shows updated metadata in rendered pages

## Implementation Checklist

- [ ] Add cascade change detection to `find_work_early()`
- [ ] Implement `_find_cascade_affected_pages()` helper
- [ ] Handle root-level cascade (pages not in sections)
- [ ] Add unit tests for cascade dependency tracking
- [ ] Test with nested sections
- [ ] Test with large sites (performance check)
- [ ] Update documentation if needed

## Related Code

- `bengal/orchestration/incremental.py` - Incremental build logic
- `bengal/orchestration/content.py` - Cascade application (`_apply_cascades()`)
- `bengal/core/section.py` - Section structure (`regular_pages_recursive`)
- `bengal/server/build_handler.py` - Dev server file watching

## Notes

- This is a correctness fix, not an optimization
- Slight performance cost when `_index.md` changes (acceptable trade-off)
- Could be optimized later with section→pages caching if needed
- Similar approach could be used for other dependency types (includes, shortcodes)
