# Autodoc Section Index Bug Fix

## Problem

When running `bengal site serve` after generating autodoc documentation, section validation fails with errors like:

```
Section 'api' at .../content/api has no index page. This should not happen after finalization.
```

This happens for autodoc-generated directory structures but NOT for Bengal's own documentation site.

## Root Cause

The issue occurs due to an interaction between incremental builds and section finalization:

1. **Autodoc generates pages without `_index.md` files**
   - `bengal utils autodoc` creates pages like `content/api/apps/module.md`
   - It creates directory structures (`api/`, `api/apps/`) but NO `_index.md` files
   - This is intentional - section finalization should auto-generate these

2. **`bengal site serve` enables strict mode**
   - Line 102 in `serve.py`: `site.config["strict_mode"] = True`
   - Strict mode makes section validation errors fatal instead of warnings
   - Bengal's own docs don't fail because they don't use strict mode during normal builds

3. **Incremental builds skip "unaffected" sections**
   - Section finalization (lines 75-81 in `section.py`) checks if sections are "affected"
   - A section is "affected" only if one of its pages changed
   - If a section was never finalized (missing index) and its pages haven't changed, it's skipped

4. **The bug scenario:**
   ```
   a) User has existing site with cache
   b) User runs `bengal utils autodoc` → creates 925 new pages
   c) User runs `bengal site serve`:
      - Incremental build detects autodoc pages already built (from autodoc run)
      - New sections (api, apps, audit, etc.) have NO index pages
      - Pages haven't "changed" since autodoc wrote them
      - Sections aren't in `affected_sections`
      - Section finalization skips them
      - Validation fails because sections have no index pages
   ```

## Key Code Locations

### Where strict mode is enabled
- `bengal/cli/commands/serve.py:102` - Always enables strict mode

### Where affected_sections is computed
- `bengal/orchestration/build.py:367-378` - Only includes sections with changed pages

### Where section finalization is skipped
- `bengal/orchestration/section.py:76-78` - Skips sections not in affected_sections

### Where validation fails
- `bengal/orchestration/section.py:416-420` - Checks for missing index pages
- `bengal/orchestration/build.py:475-483` - Raises exception in strict mode

## Why Bengal's Own Docs Work

Bengal's own documentation site works because:
1. It doesn't use `bengal site serve` in CI/CD (uses `bengal site build`)  
2. Regular builds don't enable strict mode by default
3. The warnings are shown but don't fail the build
4. During development, if you clean the build cache, sections get properly finalized

## Solution

### Option 1: Always finalize sections without index pages (RECOMMENDED)

Modify `finalize_sections` to check if a section is missing an index page BEFORE deciding to skip it:

```python
def finalize_sections(self, affected_sections: set[str] | None = None) -> None:
    archive_count = 0
    for section in self.site.sections:
        # ALWAYS finalize sections without index pages (even in incremental builds)
        needs_finalization = not self._has_index_recursive(section)

        if needs_finalization:
            archives_created = self._finalize_recursive(section)
        elif affected_sections is not None and str(section.path) not in affected_sections:
            archives_created = self._finalize_recursive_filtered(section, affected_sections)
        else:
            archives_created = self._finalize_recursive(section)

        archive_count += archives_created
```

**Pros:**
- Guarantees all sections have index pages
- Fixes the bug without breaking incremental builds
- Low performance cost (checking existence is O(1))

**Cons:**
- Adds slight overhead to check every section

### Option 2: Mark autodoc sections as "affected"

Modify the incremental build logic to mark sections containing autodoc-generated pages as affected:

```python
# In build.py, after determining affected_sections:
if autodoc_config.get("python", {}).get("enabled"):
    autodoc_output = Path(autodoc_config["python"].get("output_dir", "content/api"))
    for section in self.site.sections:
        if autodoc_output in section.path.parents or section.path == autodoc_output:
            affected_sections.add(str(section.path))
```

**Pros:**
- Explicitly handles autodoc case
- Could be extended for other dynamic content

**Cons:**
- Requires autodoc-specific logic in build orchestrator
- Doesn't fix the general case (other ways to create sections)
- More complex

### Option 3: Disable strict mode for `serve` command

Remove `site.config["strict_mode"] = True` from serve.py.

**Pros:**
- Simple one-line change
- Matches behavior of build command

**Cons:**
- Doesn't fix the underlying bug
- Loses valuable error detection during development
- Not recommended (strict mode is useful)

## Recommended Fix

**Implement Option 1** - modify section finalization to always finalize sections without index pages.

This is the most robust solution because:
- It fixes the root cause (sections can exist without index pages after finalization)
- It's defensive programming (ensures post-condition is met)
- It's cheap (checking for index page is O(1))
- It works for all cases (not just autodoc)

## Implementation Plan

1. Add `_has_index_recursive()` helper to check if a section or any subsection lacks an index
2. Modify `finalize_sections()` to always finalize sections without indexes
3. Add test case for autodoc-generated sections in incremental builds
4. Update documentation about section finalization guarantees

## Testing Strategy

1. **Reproduce the bug:**
   ```python
   # Create autodoc structure without indexes
   # Run build with cache
   # Verify sections get indexes even in incremental mode
   ```

2. **Test performance:**
   ```python
   # Ensure checking for missing indexes doesn't slow down builds
   # Should be negligible (O(n) where n = number of sections)
   ```

3. **Test with Bengal's own docs:**
   ```bash
   cd site
   bengal utils autodoc
   bengal site serve --verbose
   # Should work without errors
   ```

## Related Issues

- Section validation should probably not run before finalization completes
- The error message "This should not happen after finalization" is accurate - it IS a bug
- Consider adding health check for sections without indexes

## Files to Modify

- `bengal/orchestration/section.py` - Add helper and modify finalization logic
- `tests/unit/orchestration/test_section_orchestrator.py` - Add incremental build test
- `tests/integration/test_autodoc_integration.py` - Add end-to-end test
