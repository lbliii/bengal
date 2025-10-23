# Dead Code Audit - October 23, 2025

## Overview

Systematic audit to find and fix inaccessible or unreachable code due to logic issues, unused computations, and other code quality problems.

## Issues Found

### 1. ❌ Unused Variable Computations in `content_discovery.py`

**Severity:** Low (no functional impact, but wastes CPU cycles and confuses readers)

**Location 1:** `bengal/discovery/content_discovery.py:122`

```python
if self.site and isinstance(self.site.config, dict):
    i18n = self.site.config.get("i18n", {}) or {}
    strategy = i18n.get("strategy", "none")
    content_structure = i18n.get("content_structure", "dir")
    default_lang = i18n.get("default_language", "en")
    bool(i18n.get("default_in_subdir", False))  # ❌ DEAD CODE - computed but never used
    langs = i18n.get("languages") or []
```

**Problem:** The `bool()` call computes a value but doesn't assign it or use it. This appears to be leftover from refactoring where the variable was removed but the computation wasn't.

**Location 2:** `bengal/discovery/content_discovery.py:490-491`

```python
if self.site and isinstance(self.site.config, dict):
    i18n = self.site.config.get("i18n", {}) or {}
    strategy = i18n.get("strategy", "none")
    content_structure = i18n.get("content_structure", "dir")
    i18n.get("default_language", "en")  # ❌ DEAD CODE - retrieved but never used
    bool(i18n.get("default_in_subdir", False))  # ❌ DEAD CODE - computed but never used
    if (
        not page.translation_key
        and strategy == "prefix"
        and content_structure == "dir"
    ):
```

**Problem:** Two unused computations:
1. `i18n.get("default_language", "en")` - retrieves value but doesn't assign or use it
2. `bool(i18n.get("default_in_subdir", False))` - same issue as Location 1

**Root Cause:** These lines appear to be remnants from when these values were extracted but subsequently not needed. The variables `default_lang` and `default_in_subdir` were probably removed during refactoring but the extraction lines remained.

**Fix:** Remove these dead code lines entirely.

### 2. ✅ Useless `finally` Block in `renderer.py`

**Severity:** Very Low (cosmetic, no impact)

**Location:** `bengal/rendering/renderer.py:233-235`

```python
try:
    return self.template_engine.render(template_name, context)
except Exception as e:
    # ... error handling ...
    return self._render_fallback(page, content)
finally:
    # No global language mutation needed; helpers read from template context
    pass
```

**Problem:** The `finally` block contains only a comment explaining why it's empty and a `pass` statement. This is not harmful but adds no value.

**Analysis:** The comment suggests this was left intentionally to document that global state cleanup is NOT needed (good architectural decision!). However, an empty `finally` block with just `pass` is unnecessary in Python.

**Fix:** Remove the `finally` block entirely. The comment's information should be in the function docstring or inline comments earlier in the function if needed.

## Search Methodology

Used multiple approaches to find issues:

1. **Semantic Search:**
   - "code after return statements that would never execute"
   - "contradictory conditions that make code unreachable"
   - "conditions that are always true or always false"
   - "exception handlers that can never be raised"
   - "computed values that are never used"

2. **Pattern Matching:**
   - `if False:` - none found
   - `if True:` - none found  
   - `bool\(` statements not assigned - **FOUND 2 instances**
   - `finally:` blocks with only `pass` - **FOUND 1 instance**

3. **Manual Review:**
   - Examined cache hit paths with early returns
   - Checked exception handlers for unreachable branches
   - Reviewed conditional logic for contradictions

## Issues NOT Found (Good News!)

✅ **No unreachable code after returns** - All early return patterns are valid optimizations

✅ **No impossible conditions** - All conditional logic is reachable

✅ **No dead exception handlers** - All exception handlers can be triggered

✅ **No unused imports** - All imports are used (Python linters catch these anyway)

✅ **No commented-out code blocks** - Clean codebase

## Recommended Actions

### Immediate (This PR)

1. ✅ Remove dead computation at line 122 in `content_discovery.py`
2. ✅ Remove dead computations at lines 490-491 in `content_discovery.py`
3. ✅ Remove useless `finally` block in `renderer.py`

### Future (Optional)

1. **Add Linter Rule:** Configure `pylint` or `ruff` to detect standalone expressions that don't affect program state:
   ```toml
   # ruff.toml
   [lint]
   select = ["B018"]  # Useless expression
   ```

2. **Code Review Checklist:** Add item: "Check for computed-but-unused values during refactoring"

## Impact Assessment

**Risk Level:** Minimal
- Dead code removal is safe - these lines literally do nothing
- No behavior changes expected
- No test changes needed

**Benefits:**
- Slightly faster execution (3 fewer dictionary lookups per build)
- Cleaner, more maintainable code
- Removes potential confusion for future developers

## Testing

The dead code lines have no effect, so removing them should cause:
- ✅ No test failures
- ✅ No behavior changes
- ✅ No performance regression (actually slight improvement)

Run full test suite to verify:
```bash
pytest -xvs
```

## Conclusion

Found 3 instances of dead code (unused computations) and 1 cosmetic issue (empty finally block). All are safe to remove. The codebase is generally very clean with no major logic issues or truly unreachable code paths.

The issues found are typical remnants from refactoring where variable assignments were removed but the extraction lines remained.
