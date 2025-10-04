# Section Validation Timing Fix

**Date:** October 4, 2025  
**Issue:** Section validation errors about missing output paths during dev server startup

---

## 🐛 The Problem

When running `bengal serve` in strict mode, the build was failing with validation errors:

```
❌ Section validation errors:
   • Section 'function-reference' index page has no output path set. URL generation may fail.
   • Section 'function-reference' index page has no output path set. URL generation may fail.
   • Section 'function-reference' index page has no output path set. URL generation may fail.

❌ Server failed: Build failed: 3 section validation error(s)
```

---

## 🔍 Root Cause

**Build pipeline timing issue:**

The SectionOrchestrator validation was running in **Phase 2** (Section Finalization), but output paths weren't being set until **Phase 6** (Rendering).

### Build Pipeline Order

```
Phase 1: Discovery
  └─ Content files discovered, Page objects created
  └─ Sections identified, explicit _index.md pages added
  └─ ❌ No output paths set yet

Phase 2: Section Finalization ⚠️  VALIDATION RUNS HERE
  └─ Auto-generate archive indexes for sections without _index.md
  └─ Validate sections have index pages
  └─ ❌ Validation checked for output paths (TOO EARLY!)

Phase 3: Taxonomies & Dynamic Pages
Phase 4: Menus
Phase 5: Incremental build detection

Phase 6: Rendering ✅  OUTPUT PATHS SET HERE
  └─ RenderOrchestrator.process() called
  └─ _set_output_paths_for_all_pages() sets output paths
  └─ Pages rendered
```

### Why It Failed

1. Explicit `_index.md` files (like `function-reference/_index.md`) were added to sections during Phase 1
2. These pages had `output_path = None` because output paths aren't set until Phase 6
3. Section validation in Phase 2 checked `if not section.index_page.output_path`
4. Validation failed even though everything was structurally correct

---

## ✅ The Solution

**Remove output path validation from section validation.**

Output paths are a **rendering concern**, not a **structural section concern**.

### Code Changes

**File:** `bengal/orchestration/section.py`

**Before:**
```python
def _validate_recursive(self, section: 'Section') -> List[str]:
    errors = []
    
    # Check if section has index page
    if not section.index_page:
        errors.append(f"Section '{section.name}' has no index page")
    
    # ❌ PROBLEM: Checking output path too early
    if section.index_page and not section.index_page.output_path:
        errors.append(
            f"Section '{section.name}' index page has no output path set. "
            "URL generation may fail."
        )
    
    return errors
```

**After:**
```python
def _validate_recursive(self, section: 'Section') -> List[str]:
    errors = []
    
    # Check if section has index page
    if not section.index_page:
        errors.append(f"Section '{section.name}' has no index page")
    
    # Note: We don't validate output paths here because they're set later
    # in the render phase. This validation runs in Phase 2 (finalization),
    # while output paths are set in Phase 6 (rendering).
    
    return errors
```

---

## 🎯 What Section Validation Should Check

**✅ Structural concerns (Phase 2):**
- All sections have index pages (explicit `_index.md` or auto-generated archive)
- Section hierarchy is valid

**❌ NOT structural concerns:**
- Output paths (set in Phase 6)
- URL generation (depends on output paths)
- File system operations (rendering concern)

---

## 🧪 Testing

**Before fix:**
```bash
$ cd examples/showcase
$ bengal serve
❌ Server failed: Build failed: 3 section validation error(s)
```

**After fix:**
```bash
$ cd examples/showcase
$ bengal serve
✅ Server starts successfully
```

---

## 📝 Lessons Learned

### 1. Validation Timing Matters

Validation should only check things that are supposed to be ready at that point in the pipeline. Don't validate Phase 6 concerns in Phase 2.

### 2. Separation of Concerns

- **SectionOrchestrator:** Ensures sections are structurally complete
- **RenderOrchestrator:** Handles output paths and rendering
- **Validation:** Should match the phase it runs in

### 3. Error Message Clues

The same error appearing 3 times was a hint that:
- It wasn't actually 3 different errors
- The validation was recursing through subsections
- The logic was correct but running too early

---

## ✅ Status

**Fixed:** Section validation no longer checks output paths  
**Tested:** Dev server starts successfully in showcase site  
**Impact:** No breaking changes, pure bug fix

---

## 🔗 Related Files

- `bengal/orchestration/section.py` - SectionOrchestrator validation
- `bengal/orchestration/build.py` - Build pipeline phases
- `bengal/orchestration/render.py` - Output path setting

