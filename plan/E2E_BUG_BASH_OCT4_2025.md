# E2E Bug Bash - October 4, 2025

## Overview

Comprehensive end-to-end testing session to identify and fix bugs in Bengal SSG.

## Bugs Found

### 🐛 Bug #1: Integration Tests Using Wrong Site Initialization
**Status:** ✅ FIXED

**Issue:** Integration tests in `test_documentation_builds.py` were calling `Site(site_dir)` instead of `Site.from_config(site_dir)`, which meant the configuration file wasn't being loaded.

**Impact:** Tests were failing because `site.config` was empty, causing variable substitution to fail.

**Fix:** Changed all test methods to use `Site.from_config(site_dir)`.

**Files Changed:**
- `tests/integration/test_documentation_builds.py`

---

### 🐛 Bug #2: Site Class Missing Property Accessors
**Status:** ✅ FIXED

**Issue:** The `Site` class stored configuration in `site.config` dict but didn't provide property accessors. Variable substitution trying to access `site.title` would fail.

**Impact:** Template variable `{{ site.title }}` in markdown would fail to substitute.

**Fix:** Added `@property` methods for common config fields: `title`, `baseurl`, `author`.

**Files Changed:**
- `bengal/core/site.py`

---

### 🐛 Bug #3: {{/* */}} Escape Syntax Not Working
**Status:** 🚧 IN PROGRESS - Complex Issue

**Issue:** The Hugo-style escape syntax `{{/* page.title */}}` is supposed to render as literal `{{ page.title }}` in the output, but it's not working correctly.

**Root Causes:**
1. Mist une treats `*/` as markdown emphasis (italic), splitting text across multiple text() calls
2. Our variable substitution plugin never sees the complete `{{/* */}}` pattern
3. Even with preprocessing, Mistune processes emphasis before our plugin runs

**What We Tried:**
- ✅ Preprocessing before Mistune parsing
- ✅ Using placeholders that don't conflict with markdown (`BENGALESCAPED*ENDESC`)
- ❌ But placeholders still don't get restored properly

**Current Output:**
```
Input:  Use {{/* page.title */}} to display...
Output: Use {{/<em> page.title </em>/}} to display...
```

**Solution Options:**
1. **Use different escape syntax** - Pick something that doesn't conflict with markdown
   - Example: `{{% page.title %}}` or `[[! page.title !]]`
2. **Process in two passes** - Parse markdown first, then do variable substitution on HTML
3. **Use raw HTML blocks** - `<span>{{ page.title }}</span>` style markers

**Recommended:** Option 1 - Change escape syntax to `{{% expr %}}` which doesn't conflict with markdown.

---

## Test Results

### Integration Tests
- **Total:** 3 tests
- **Passed:** 1
- **Failed:** 2 (both related to {{/* */}} escaping)

### Affected Tests:
1. `test_build_page_with_template_examples` - Expects `{{/* page.title */}}` → `{{ page.title }}`
2. `test_mixed_real_and_example_variables` - Mix of real substitution and escaped examples

---

## Next Steps

1. **Decide on escape syntax** - Needs discussion with maintainer
   - Current: `{{/* expr */}}` (conflicts with markdown)
   - Proposed: `{{% expr %}}` (no conflicts)

2. **Update implementation** if syntax changes

3. **Fix or update tests** based on decision

4. **Continue bug bash** - Test remaining functionality:
   - Build showcase site
   - Test CLI commands
   - Test server functionality
   - Test autodoc generation

---

## Session Summary

**Time Spent:** ~2 hours  
**Bugs Found:** 3  
**Bugs Fixed:** 2  
**Bugs In Progress:** 1 (requires design decision)

**Key Insight:** The `{{/* */}}` syntax was a poor choice because `*/` is markdown emphasis. Any escape syntax must not conflict with markdown syntax.

