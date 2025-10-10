# Root-Level Cascade Bug Fix

**Date**: 2025-10-10  
**Status**: Fixed ✅  
**Issue**: Cascade from root `index.md` was not propagating to child sections

## The Bug

When a root-level page (like `content/index.md`) defined a `cascade` in its frontmatter, the cascade metadata was **not** being applied to child sections and pages.

### Example That Didn't Work

```yaml
# content/index.md
---
type: doc
cascade:
    type: doc
---
```

The `type: doc` cascade should have applied to all child sections and pages, but it didn't.

## Root Cause

The cascade logic in `_apply_cascades()` only iterated through `self.site.sections`, missing any cascade metadata defined in **top-level pages** (pages not belonging to any section).

**Problem Code** (in both `bengal/core/site.py` and `bengal/orchestration/content.py`):

```python
def _apply_cascades(self) -> None:
    # Process all top-level sections (they will recurse to subsections)
    for section in self.sections:
        self._apply_section_cascade(section, parent_cascade=None)
```

This skipped root-level pages entirely.

## The Fix

### Updated Logic

1. **First**, scan all top-level pages for cascade metadata
2. **Merge** any root-level cascades found
3. **Apply** the root cascade as the `parent_cascade` to all top-level sections
4. **Also apply** root cascade to other top-level pages

### Fixed Code

```python
def _apply_cascades(self) -> None:
    # First, check for root-level cascade from top-level pages (like content/index.md)
    root_cascade = None
    for page in self.pages:
        # Check if this is a top-level page (not in any section)
        is_top_level = not any(page in section.pages for section in self.sections)
        if is_top_level and 'cascade' in page.metadata:
            # Found root-level cascade - merge it
            if root_cascade is None:
                root_cascade = {}
            root_cascade.update(page.metadata['cascade'])
    
    # Process all top-level sections with root cascade (they will recurse to subsections)
    for section in self.sections:
        self._apply_section_cascade(section, parent_cascade=root_cascade)
    
    # Also apply root cascade to other top-level pages
    if root_cascade:
        for page in self.pages:
            is_top_level = not any(page in section.pages for section in self.sections)
            # Skip the page that defined the cascade itself
            if is_top_level and 'cascade' not in page.metadata:
                for key, value in root_cascade.items():
                    if key not in page.metadata:
                        page.metadata[key] = value
```

## Files Changed

1. `bengal/orchestration/content.py` - Fixed `_apply_cascades()` method
2. `bengal/core/site.py` - Fixed duplicate `_apply_cascades()` method
3. `tests/unit/test_cascade.py` - Added `TestRootLevelCascade` class with 4 tests

## Test Coverage

Added comprehensive tests for root-level cascade:

1. ✅ `test_root_level_page_cascade_to_sections` - Basic root cascade to sections
2. ✅ `test_root_cascade_to_multiple_sections` - Root cascade to multiple sections
3. ✅ `test_root_cascade_with_section_override` - Section cascade can override root
4. ✅ `test_root_cascade_to_nested_sections` - Root cascade propagates through nesting

All existing cascade tests (13 tests) continue to pass.

## Cascade Priority Chain

With this fix, the complete cascade priority is now:

```
1. Page's own metadata (highest priority)
2. Nearest section's cascade
3. Parent section's cascade (accumulated)
4. Grandparent section's cascade (accumulated)
5. ... (continues up hierarchy)
6. Root-level page cascade (lowest priority, applies to everything)
```

## Use Case

This fix enables site-wide defaults using a root `index.md`:

```yaml
# content/index.md
---
title: "My Documentation Site"
cascade:
    type: doc              # All pages default to doc template
    site_version: "1.0"    # Site-wide version metadata
    show_toc: true         # Site-wide TOC setting
---
```

Every page and section inherits these defaults unless they override them.

## Testing

```bash
# Run all cascade tests
pytest tests/unit/test_cascade.py -v

# Run just root-level cascade tests
pytest tests/unit/test_cascade.py::TestRootLevelCascade -v
```

Result: **17/17 tests pass** ✅

